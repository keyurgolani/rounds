"""PocketBase gate hooks (ROUNDS-00A-L01), run under node with the
PocketBase globals stubbed: the signup check reads the SIGNUPS gate and
its alias, and boot logs every gate once."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1] / "pb_hooks"

HARNESS = r"""
const path = require("path");
const [hooksDir, file, envJson] = process.argv.slice(1);
const env = JSON.parse(envJson);
const handlers = {};
const logs = [];
const errors = [];
globalThis.__hooks = hooksDir;
globalThis.$os = { getenv: (key) => (key in env ? env[key] : "") };
globalThis.BadRequestError = class BadRequestError extends Error {};
globalThis.onRecordBeforeCreateRequest = (fn, ...collections) => { handlers.create = { fn, collections }; };
globalThis.onAfterBootstrap = (fn) => { handlers.boot = { fn }; };
console.log = (...a) => logs.push(a.join(" "));
console.error = (...a) => errors.push(a.join(" "));
require(path.join(hooksDir, file));
const out = { collections: handlers.create ? handlers.create.collections : null, logs, errors };
if (handlers.create) {
  try {
    handlers.create.fn({ record: {} });
    out.outcome = "allowed";
  } catch (err) {
    out.outcome = err instanceof BadRequestError ? "blocked" : "crashed: " + err.message;
  }
}
if (handlers.boot) handlers.boot.fn({});
process.stdout.write(JSON.stringify(out));
"""


def _run(file: str, env: dict) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run(
        [node, "-e", HARNESS, str(HOOKS), file, json.dumps(env)],
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    return json.loads(res.stdout)


@pytest.mark.parametrize(
    "env,outcome",
    [
        ({}, "allowed"),
        ({"ROUNDS_DISABLE_SIGNUPS": "false"}, "allowed"),
        ({"ROUNDS_DISABLE_SIGNUPS": "true"}, "blocked"),
        ({"ROUNDS_DISABLE_SIGNUPS": "1"}, "blocked"),
        ({"ROUNDS_GATE_SIGNUPS": "disabled"}, "blocked"),
        ({"ROUNDS_GATE_SIGNUPS": " Disabled "}, "blocked"),
        ({"ROUNDS_GATE_SIGNUPS": "enabled"}, "allowed"),
        ({"ROUNDS_GATE_SIGNUPS": "enabled", "ROUNDS_DISABLE_SIGNUPS": "true"}, "allowed"),
        ({"ROUNDS_GATE_SIGNUPS": "not-a-value"}, "blocked"),
        ({"VITE_DISABLE_SIGNUPS": "true"}, "allowed"),
    ],
)
def test_the_signup_hook_follows_the_signups_gate(env, outcome):
    result = _run("main.pb.js", env)
    assert result["collections"] == ["users"]
    assert result["outcome"] == outcome


def test_boot_logs_every_pocketbase_gate_in_one_line():
    result = _run("gates.pb.js", {"ROUNDS_DISABLE_SIGNUPS": "true"})
    (line,) = result["logs"]
    assert json.loads(line) == {
        "v": "obs/v1",
        "event": "gates",
        "service": "pocketbase",
        "gates": {"SIGNUPS": {"value": "disabled", "source": "alias"}},
    }
    assert result["errors"] == []


def test_boot_flags_an_invalid_gate_without_its_raw_value():
    raw = "Placeholder-Not-A-Gate-Value"
    result = _run("gates.pb.js", {"ROUNDS_GATE_SIGNUPS": raw})
    (line,) = result["logs"]
    assert json.loads(line)["gates"]["SIGNUPS"] == {"value": "disabled", "source": "invalid"}
    (error,) = result["errors"]
    assert "ROUNDS_GATE_SIGNUPS" in error
    assert raw.lower() not in error.lower() and raw.lower() not in line.lower()


def test_the_gate_module_is_not_auto_loaded_as_a_hook_file():
    # PocketBase loads only *.pb.js files, so the shared module stays a
    # plain require target.
    assert (HOOKS / "gates.js").exists()
    assert not (HOOKS / "gates.js").name.endswith(".pb.js")
    source = (HOOKS / "main.pb.js").read_text()
    assert "require(`${__hooks}/gates.js`)" in source
