"""The harness's share capability phase (ROUNDS-00B-L03 stage 2) is wired:
run.sh runs it while signups are still on, with both runners and nginx up,
and fails the run when it fails; the probe runner dispatches it; and the
probe holds the runner's owner fields. The phase itself runs in CI's
harness job."""
from __future__ import annotations

import re
from pathlib import Path

from app import share_capabilities

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "harness"


def _phase_lines() -> list[str]:
    run_sh = (HARNESS / "run.sh").read_text()
    return [m.group(0) for m in re.finditer(r'^echo "--- phase [0-9a-z]+:.*$|^\s*probe [a-z-]+\b', run_sh, re.M)]


def test_run_sh_runs_the_phase_after_the_snapshots_and_before_signups_close():
    lines = _phase_lines()
    at = lines.index("probe share-capabilities")
    assert lines[at - 1].startswith('echo "--- phase 3k: share capabilities')
    assert lines.index("probe snapshot-create-again") < at < lines.index("probe hook")
    run_sh = (HARNESS / "run.sh").read_text()
    phase = run_sh[run_sh.index('echo "--- phase 3k'):run_sh.index('echo "--- phase 4')]
    assert "restart_runners" in phase and "share_rc=$?" in phase
    assert '[ "${share_rc}" -ne 0 ]' in run_sh


def test_the_probe_runner_dispatches_the_phase():
    text = (HARNESS / "probes" / "run.py").read_text()
    assert 'if phase == "share-capabilities":' in text and "share_capability_check.main()" in text


def test_the_probe_checks_the_owner_fields_the_runner_answers(monkeypatch):
    monkeypatch.syspath_prepend(str(HARNESS / "probes"))
    import importlib

    probe = importlib.import_module("share_capability_check")
    # The probe checks the list, which adds the resume each link shares.
    assert probe.OWNER_FIELDS == set(share_capabilities.LIST_FIELDS)
    assert probe.ROUTE == "/api/share/capabilities"
    assert probe.NOT_FOUND == {"detail": "Not found.", "code": "not_found"}
