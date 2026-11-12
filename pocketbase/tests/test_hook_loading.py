"""A hook file that fails to load stops PocketBase from starting.

The image's CMD runs PocketBase with --hooksWatch=false, so a hook file that
throws as it loads stops the start, and the log names the file. Every
compose file and the k8s manifest run that CMD, and every harness start that
loads the hooks passes the same flag. The harness checks PocketBase's log
each time it waits for PocketBase, and its phase 0, in CI only, starts the
image with a hook file that throws. Both run in CI's harness job.
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "harness"
RUN_SH = HARNESS / "run.sh"
SHELL_FILES = (RUN_SH, HARNESS / "migration_check.sh", ROOT / "tests" / "conformance" / "run.sh")
# The image's binary run with a subcommand, not a copy of the binary.
PB_COMMAND = re.compile(r"/pb/pocketbase\s+[a-z]")


def _cmd() -> list[str]:
    (line,) = [line for line in (ROOT / "pocketbase" / "Dockerfile").read_text().splitlines() if line.startswith("CMD ")]
    return json.loads(line[len("CMD "):])


def _function(text: str, name: str) -> str:
    """A shell function's definition, through its closing brace and newline."""
    start = text.index(f"\n{name}() {{\n") + 1
    return text[start:text.index("\n}\n", start) + 3]


def _phase(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end)]


def _commands(path: Path) -> list[str]:
    """The file's lines, each continued line joined to the next, comments left out."""
    joined = re.sub(r"\\\n\s*", " ", path.read_text())
    return [line for line in joined.splitlines() if not line.lstrip().startswith("#")]


def _flag(node: ast.expr, prefix: str) -> bool:
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and node.value.startswith(prefix)
    if isinstance(node, ast.JoinedStr) and node.values:
        head = node.values[0]
        return isinstance(head, ast.Constant) and str(head.value).startswith(prefix)
    return False


def _log_check(log: str) -> subprocess.CompletedProcess:
    """run.sh's own hook_log_clean, on the log given."""
    check = _function(RUN_SH.read_text(), "hook_log_clean")
    return subprocess.run(["bash", "-c", f'set -euo pipefail\n{check}hook_log_clean "$1"', "check", log],
                          capture_output=True, text=True, timeout=30)


def test_the_image_runs_pocketbase_with_watch_mode_off():
    cmd = _cmd()
    assert cmd[:2] == ["/pb/pocketbase", "serve"] and "--hooksDir=/pb/pb_hooks" in cmd
    assert [arg for arg in cmd if arg.startswith("--hooksWatch")] == ["--hooksWatch=false"]


def test_every_compose_file_and_the_k8s_manifest_run_the_image_cmd():
    for path in (ROOT / "docker-compose.yml", ROOT / "docker-compose.prod.yml", HARNESS / "compose.yml"):
        service = yaml.safe_load(path.read_text())["services"]["pocketbase"]
        assert not {"command", "entrypoint"} & set(service), path.name
    # The corpus overlay leaves PocketBase's service as the harness has it.
    assert "pocketbase" not in yaml.safe_load((ROOT / "tests" / "conformance" / "compose.yml").read_text())["services"]
    (deployment,) = [doc for doc in yaml.safe_load_all((ROOT / "k8s" / "pocketbase.yaml").read_text())
                     if doc and doc["kind"] == "Deployment"]
    for container in deployment["spec"]["template"]["spec"]["containers"]:
        assert not {"command", "args"} & set(container), container["name"]


def test_every_harness_command_that_loads_the_hooks_sets_watch_mode():
    commands = [(path.name, line) for path in SHELL_FILES for line in _commands(path)
                if PB_COMMAND.search(line) or "--hooksDir=" in line]
    # The snapshot scan, the migration check's migrate up, and phase 0's
    # start with watch mode on.
    assert len(commands) == 3, commands
    for name, line in commands:
        assert re.findall(r"--hooksWatch=\w+", line) in (["--hooksWatch=false"], ["--hooksWatch=true"]), (name, line)
    (watching,) = [line for _, line in commands if "--hooksWatch=true" in line]
    assert watching.lstrip().startswith('served="$(hook_control /pb/pocketbase serve ')


def test_every_probe_start_that_names_a_hooks_dir_turns_watch_mode_off():
    starts: dict[str, list[list[str]]] = {}
    for path in sorted((HARNESS / "probes").glob("*.py")):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.List) and any(_flag(e, "--hooksDir=") for e in node.elts):
                watch = [e.value for e in node.elts if isinstance(e, ast.Constant) and _flag(e, "--hooksWatch")]
                starts.setdefault(path.name, []).append(watch)
    assert {"demo_contain_migration_check.py", "legacy_share_migration_check.py",
            "relation_quarantine_check.py"} <= set(starts)
    for name, flags in starts.items():
        assert all(watch == ["--hooksWatch=false"] for watch in flags), name


def test_the_log_check_fails_on_a_hook_file_that_failed_to_load():
    clean = _log_check("pocketbase-1  | > Server started\n")
    assert clean.returncode == 0 and clean.stdout == "PASS hooks.load.no-failed-file\n"
    # The line PocketBase prints for the file, watch mode on or off.
    failed = _log_check("pocketbase-1  | Failed to execute load_error.pb.js:\npocketbase-1  |  - Error: thrown\n")
    assert failed.returncode == 1
    assert failed.stdout.startswith("FAIL hooks.load.no-failed-file: ") and "load_error.pb.js" in failed.stdout


def test_each_wait_for_pocketbase_checks_its_log_and_a_failure_fails_the_run():
    text = RUN_SH.read_text()
    wait = _function(text, "wait_pocketbase")
    assert wait.index("api/health") < wait.index('hook_log_clean "${log}" || up=1')
    phase_1 = _phase(text, 'echo "--- phase 1:', 'echo "--- phase 2:')
    assert phase_1.index("compose up -d pocketbase") < phase_1.index("wait_pocketbase || hooks_rc=1")
    assert '[ "${hooks_rc}" -ne 0 ]' in text


def test_phase_0_starts_the_image_with_a_throwing_hook_file_in_ci_only():
    text = RUN_SH.read_text()
    assert text.index("compose build pocketbase") < text.index('echo "--- phase 0:') < text.index('echo "--- phase 1:')
    phase_0 = _phase(text, 'echo "--- phase 0:', 'echo "--- phase 1:')
    gate = 'if [ "${GITHUB_ACTIONS:-}" = "true" ]; then'
    ci, local = phase_0[phase_0.index(gate):].split("\nelse\n")
    assert "hooks_rc=0" in phase_0[:phase_0.index(gate)]
    assert "throw new Error(" in ci and '> "${STATE_DIR}/load_error.pb.js"' in ci
    # Watch mode on first: PocketBase serves, and the log check flags the
    # file. Then the image's CMD, which must stop. Either failing fails the run.
    assert ci.index('[ "${served}" = "served" ] && ! hook_log_clean') < ci.index('stopped="$(hook_control)"')
    assert ci.index('stopped="$(hook_control)"') < ci.index('[ "${stopped}" = "stopped" ]')
    assert ci.count("hooks_rc=1") == 2
    assert "SKIP hooks.load-error" in local
    control = _function(text, "hook_control")
    assert "--network none" in control and "-v \"${STATE_DIR}/load_error.pb.js:/pb/pb_hooks/load_error.pb.js:ro\"" in control
    assert '[ "${code}" != "0" ] && grep -qF \'Failed to execute load_error.pb.js\'' in control
    # Its container goes at teardown, before the image does.
    cleanup = _function(text, "cleanup")
    assert cleanup.index('rm -f "${HOOK_CONTROL}"') < cleanup.index("rmi ${BUILT_IMAGES}")
