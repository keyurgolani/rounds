"""The harness's Legacy Artifact Snapshot phases (ROUNDS-00A-L04, PRs 2
and 3) are wired: run.sh runs each phase the probe defines, in order, the
probe runner dispatches each, the harness turns the gate on for PocketBase
and both runners, runs the PDF renderer only for the render phases, keeps
the render decision lines and the recovery backup in the run's state
rather than its receipts, and the scan secret the harness gives the
runners is one the signer accepts. The phases themselves run in CI's
harness job."""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest
import yaml

from app import legacy_receipt

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "harness"
PROBE = HARNESS / "probes" / "legacy_snapshot_check.py"


def _phases() -> list[str]:
    tree = ast.parse(PROBE.read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == "PHASES" for t in node.targets):
            return [k.value for k in node.value.keys]  # type: ignore[union-attr]
    raise AssertionError("no PHASES in the probe")


def test_run_sh_runs_every_snapshot_phase_in_order():
    run_sh = (HARNESS / "run.sh").read_text()
    order = [m.group(1) for m in re.finditer(r"^\s*probe (snapshot-(?!store)[a-z-]+)", run_sh, re.M)]
    assert order == ["snapshot-create", "snapshot-render", "snapshot-render-audit", "snapshot-render-down",
                     "snapshot-create-down", "snapshot-create-retry", "snapshot-create-off", "snapshot-scan",
                     "snapshot-create-again", "snapshot-recovery"]
    assert sorted(order) == sorted(_phases())
    # Both scans run, and the first is signed and verified on the runner.
    assert "scan_report scan-1" in run_sh and "scan_report scan-2" in run_sh
    assert "app.legacy_receipt sign" in run_sh and "app.legacy_receipt verify" in run_sh
    assert '[ "${legacy_rc}" -ne 0 ]' in run_sh
    # The audit reads the decision lines saved after the render phase, and
    # the renderer is stopped for the render-down phase.
    lines = run_sh.splitlines()
    at = {name: next(i for i, line in enumerate(lines) if line.strip() == f"probe {name} || legacy_rc=1")
          for name in ("snapshot-render", "snapshot-render-audit", "snapshot-render-down", "snapshot-recovery")}
    assert "render_decisions" in lines[at["snapshot-render"] + 1]
    assert lines[at["snapshot-render-down"] - 1].strip() == "compose stop pdf-renderer"
    before_recovery = "\n".join(lines[at["snapshot-render-down"]:at["snapshot-recovery"]])
    assert "compose stop runner runner-b frontend pocketbase" in before_recovery
    assert "backup_and_restore" in before_recovery


def test_the_probe_runner_dispatches_every_snapshot_phase():
    text = (HARNESS / "probes" / "run.py").read_text()
    assert 'phase.startswith("snapshot-")' in text
    # snapshot-store is the store migration's check, dispatched first.
    assert text.index('phase == "snapshot-store"') < text.index('phase.startswith("snapshot-")')
    for phase in _phases():
        assert phase.startswith("snapshot-") and phase != "snapshot-store"


def test_the_renderer_runs_as_prod_runs_it_and_only_when_a_render_phase_starts_it():
    services = yaml.safe_load((HARNESS / "compose.yml").read_text())["services"]
    renderer = services["pdf-renderer"]
    assert renderer["profiles"] == ["renderer"]
    assert renderer["build"]["context"] == "../backend/pdf_renderer"
    assert "ports" not in renderer
    assert not any("pdf-renderer" in str(svc.get("depends_on", "")) for svc in services.values())
    run_sh = (HARNESS / "run.sh").read_text()
    assert "--profile renderer" in run_sh and "-pdf-renderer:test" in run_sh
    # The runners call it where prod's do.
    prod = yaml.safe_load((ROOT / "docker-compose.prod.yml").read_text())["services"]
    assert "pdf-renderer" in prod


def test_render_decisions_and_the_backup_stay_out_of_the_uploaded_receipts():
    run_sh = (HARNESS / "run.sh").read_text()
    decisions = re.search(r"render_decisions\(\) \{(.*?)\n\}", run_sh, re.S).group(1)
    assert '"${STATE_DIR}/render-decisions.jsonl"' in decisions and "RECEIPTS_DIR" not in decisions
    backup = re.search(r"backup_and_restore\(\) \{(.*?)\n\}", run_sh, re.S).group(1)
    assert '"${STATE_DIR}:/backup"' in backup and "RECEIPTS_DIR" not in backup
    # The archive carries storage/, where the snapshots' files live.
    assert "./storage/" in backup
    probe = PROBE.read_text()
    assert 'Path(os.environ.get("SNAPSHOT_DECISIONS_PATH", "/state/render-decisions.jsonl"))' in probe


def test_the_harness_passes_the_gate_to_pocketbase_and_both_runners():
    services = yaml.safe_load((HARNESS / "compose.yml").read_text())["services"]
    for name in ("pocketbase", "runner", "runner-b"):
        env = services[name]["environment"]
        assert "ROUNDS_GATE_LEGACY_SNAPSHOT_CREATE=${ROUNDS_GATE_LEGACY_SNAPSHOT_CREATE:-}" in env, name


def test_the_probe_reads_every_rd02_input_and_its_declared_outcome(monkeypatch):
    monkeypatch.syspath_prepend(str(HARNESS / "probes"))
    monkeypatch.setenv("RD02_DIR", str(ROOT / "tests" / "conformance" / "rd_02"))
    import importlib

    probe = importlib.import_module("legacy_snapshot_check")
    probe = importlib.reload(probe)
    found = probe.fixtures()
    assert len(found) == len(list((ROOT / "tests" / "conformance" / "rd_02").glob("*.json"))) > 0
    for fx in found:
        assert fx["expect"]["status"] in ("ok", "ineligible"), fx["name"]
        assert {"template_id", "data"} <= set(fx["input"]), fx["name"]
    # The phases need one eligible input on the default template to build on.
    assert any(fx["expect"]["status"] == "ok" and fx["input"].get("template_id") == "modern"
               and not fx["expect"].get("template_fallback") for fx in found)


def _probe(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(HARNESS / "probes"))
    monkeypatch.setenv("SNAPSHOT_STATE_PATH", str(tmp_path / "snapshot.json"))
    monkeypatch.setenv("SNAPSHOT_DECISIONS_PATH", str(tmp_path / "decisions.jsonl"))
    import importlib

    return importlib.reload(importlib.import_module("legacy_snapshot_check"))


RENDERS = [
    {"kind": "owner", "cid": "c1", "status": 200, "code": None},
    {"kind": "foreign", "cid": "c2", "status": 404, "code": "not_found"},
    {"kind": "legacy", "cid": "c3", "status": 422, "code": "legacy_request_rejected"},
]
LINES = [
    {"event": "decision", "route": "/api/pdf/render", "correlation_id": "c1", "status": 200, "quota": "charged"},
    {"event": "decision", "route": "/api/pdf/render", "correlation_id": "c2", "status": 404, "code": "not_found",
     "quota": "refunded"},
    {"event": "decision", "route": "/api/pdf/render", "correlation_id": "c3", "status": 422,
     "code": "legacy_request_rejected", "quota": "skipped"},
    {"event": "decision", "route": "/api/pdf/snapshots", "correlation_id": "c9", "status": 201, "quota": "charged"},
]


def _audit(monkeypatch, tmp_path, lines):
    probe = _probe(monkeypatch, tmp_path)
    (tmp_path / "snapshot.json").write_text(json.dumps({"renders": RENDERS}))
    (tmp_path / "decisions.jsonl").write_text("".join(json.dumps(line) + "\n" for line in lines))
    from admission_check import Checks

    checks = Checks()
    probe.run_render_audit(checks)
    return checks


def test_the_render_audit_passes_a_run_where_only_the_owner_rendered(monkeypatch, tmp_path):
    checks = _audit(monkeypatch, tmp_path, LINES)
    assert (checks.passed, checks.failed) == (2, 0)


@pytest.mark.parametrize("change", [
    # A refused request that rendered after all.
    lambda lines: lines[1].update(status=200, code=None),
    # One that took a slot: charged, not refunded.
    lambda lines: lines[1].update(quota="charged"),
    # A render the probe never made answered 200.
    lambda lines: lines.append({"event": "decision", "route": "/api/pdf/render", "correlation_id": "cx",
                                "status": 200, "quota": "charged"}),
    # A refusal with no line at all.
    lambda lines: lines.pop(2),
], ids=["refusal-rendered", "refusal-took-a-slot", "unrecorded-render", "missing-line"])
def test_the_render_audit_fails_when_a_render_ran_without_an_owners_snapshot(monkeypatch, tmp_path, change):
    lines = json.loads(json.dumps(LINES))
    change(lines)
    assert _audit(monkeypatch, tmp_path, lines).failed > 0


def test_the_harness_scan_secret_is_one_the_signer_accepts():
    run_sh = (HARNESS / "run.sh").read_text()
    (template,) = re.findall(r'^SCAN_SECRET_V="([^"]+)"', run_sh, re.M)
    secret = template.replace("${RUN_ID}", "1700000000-12345")
    assert len(legacy_receipt.key_for("rounds/legacy-snapshot-scan/v1", secret)) == 32
    assert "AI_KEY_SECRET=%s" in run_sh
