"""The harness's Legacy Artifact Snapshot phases (ROUNDS-00A-L04, PR 2)
are wired: run.sh runs each phase the probe defines, the probe runner
dispatches each, the harness turns the gate on for PocketBase and both
runners, and the scan secret the harness gives the runners is one the
signer accepts. The phases themselves run in CI's harness job."""
from __future__ import annotations

import ast
import re
from pathlib import Path

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
    order = [m.group(1) for m in re.finditer(r"^\s*probe (snapshot-(?:create[a-z-]*|scan))\b", run_sh, re.M)]
    assert order == ["snapshot-create", "snapshot-create-down", "snapshot-create-retry", "snapshot-create-off",
                     "snapshot-scan", "snapshot-create-again"]
    assert sorted(order) == sorted(_phases())
    # Both scans run, and the first is signed and verified on the runner.
    assert "scan_report scan-1" in run_sh and "scan_report scan-2" in run_sh
    assert "app.legacy_receipt sign" in run_sh and "app.legacy_receipt verify" in run_sh
    assert '[ "${legacy_rc}" -ne 0 ]' in run_sh


def test_the_probe_runner_dispatches_every_snapshot_phase():
    text = (HARNESS / "probes" / "run.py").read_text()
    assert 'phase.startswith("snapshot-create") or phase == "snapshot-scan"' in text
    for phase in _phases():
        assert phase.startswith("snapshot-create") or phase == "snapshot-scan"


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


def test_the_harness_scan_secret_is_one_the_signer_accepts():
    run_sh = (HARNESS / "run.sh").read_text()
    (template,) = re.findall(r'^SCAN_SECRET_V="([^"]+)"', run_sh, re.M)
    secret = template.replace("${RUN_ID}", "1700000000-12345")
    assert len(legacy_receipt.key_for("rounds/legacy-snapshot-scan/v1", secret)) == 32
    assert "AI_KEY_SECRET=%s" in run_sh
