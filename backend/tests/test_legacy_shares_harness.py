"""The harness's older share links phases (ROUNDS-00B-L06 stage 1) are wired:
run.sh makes phase 3o's pb_data offline, starts PocketBase on it with both
runners behind the recorder, runs the stack probe and the scan, puts
PocketBase back on the main volume before signups close, and runs phase 15
offline; any failure fails the run. The recorder publishes no port and its
log is never the receipts; the scan's files stay in the state folder and go
right after it. Phase 15's fixture covers every outcome the migration
decides that a database can hold once #10 has run, and the identity check
holds only for the resolver's own login and lookups. The phases themselves
run in CI's harness job."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "harness"
sys.path.insert(0, str(HARNESS / "probes"))

import admission_migration_check  # noqa: E402
import legacy_share_check as stack  # noqa: E402
import legacy_share_migration_check as offline  # noqa: E402
from admission_check import Checks  # noqa: E402
from receipts import ReceiptWriter, read_all  # noqa: E402

POLICY = ROOT / "docs" / "security" / "account-scope.v1.json"
MANIFEST = ROOT / "pocketbase" / "migration-manifests" / "legacy-shares-v1.json"
CASES = {
    "isolation.share-legacy.replaced",
    "isolation.share-chain.capability-revoked",
    "isolation.share-resolver.not-found.uniform",
    "isolation.share-public.resolver-identity",
}


def _run_sh() -> str:
    return (HARNESS / "run.sh").read_text()


def _phase(text: str, start: str, end: str) -> str:
    return text[text.index(start):text.index(end)]


def test_phase_3o_upgrades_its_own_pb_data_behind_the_recorder_and_puts_pocketbase_back():
    text = _run_sh()
    phase = _phase(text, 'echo "--- phase 3o', 'echo "--- phase 4')
    order = [phase.index(step) for step in (
        "legacy-shares-fixture", 'PB_DATA_V="pb_data_legacy"', 'RUNNER_PB_URL="http://recorder:8090"',
        "compose up -d --force-recreate pocketbase", "compose up -d --force-recreate recorder", "restart_runners",
        "probe legacy-shares", "legacy-shares-scan", 'PB_DATA_V="pb_data"', 'RUNNER_PB_URL="http://pocketbase:8090"')]
    assert order == sorted(order)
    assert phase.rindex("compose up -d --force-recreate pocketbase") > phase.index('PB_DATA_V="pb_data"')
    assert "SNAPSHOT_GATE=enabled" in phase and "SHARE_GATE=enabled" in phase and "compose up -d materializer" in phase
    # Its PocketBase starts after 3n's and before signups close.
    assert text.index('echo "--- phase 3n') < text.index('echo "--- phase 3o') < text.index('echo "--- phase 4')
    assert '[ "${legacy_shares_rc}" -ne 0 ]' in text


def test_the_fixture_runs_offline_and_the_stack_probe_reads_the_recorder_read_only():
    phase = _phase(_run_sh(), 'echo "--- phase 3o', 'echo "--- phase 4')
    fixture = phase[:phase.index("legacy-shares-fixture")]
    assert "--network none" in fixture[fixture.rindex("${CONTAINER_BIN} run"):]
    probe = phase[phase.index("probe legacy-shares"):phase.index('SCAN_DIR="${STATE_DIR}/legacy-scan"')]
    assert '-v "${RECORDER_VOLUME}:/var/lib/rounds-recorder:ro"' in probe


def test_the_scan_reads_files_kept_out_of_the_receipts_and_removes_them():
    phase = _phase(_run_sh(), 'echo "--- phase 3o', 'echo "--- phase 4')
    assert 'SCAN_DIR="${STATE_DIR}/legacy-scan"' in phase
    assert "RECEIPTS_DIR" not in phase[phase.index('SCAN_DIR="${STATE_DIR}/legacy-scan"'):]
    assert phase.index("legacy-shares-scan") < phase.index('rm -rf "${SCAN_DIR}"')


def test_phase_15_runs_offline_after_14_and_fails_the_run():
    text = _run_sh()
    phase = _phase(text, 'echo "--- phase 15', "legacy_migration_rc=$?")
    assert text.index('echo "--- phase 14') < text.index('echo "--- phase 15')
    assert "--network none" in phase and "legacy-shares-migration" in phase and "/pb_hooks:ro" in phase
    assert '[ "${legacy_migration_rc}" -ne 0 ]' in text


def test_the_launcher_makes_and_removes_both_volumes():
    text = _run_sh()
    assert 'volume create "${LEGACY_VOLUME}"' in text and 'volume create "${RECORDER_VOLUME}"' in text
    cleanup = text[text.index("cleanup() {"):text.index("trap cleanup EXIT")]
    assert '"${LEGACY_VOLUME}"' in cleanup and '"${RECORDER_VOLUME}"' in cleanup
    # Both made before the first compose call that could name them.
    assert text.index('volume create "${LEGACY_VOLUME}"') < text.index('echo "--- phase 1:')


def test_the_recorder_publishes_no_port_and_the_runners_reach_pocketbase_through_a_variable():
    doc = yaml.safe_load((HARNESS / "compose.yml").read_text())
    rec = doc["services"]["recorder"]
    assert "ports" not in rec and rec["entrypoint"] == ["python", "recorder.py"]
    assert "RECORDER_LOG=/var/lib/rounds-recorder/recorder.jsonl" in rec["environment"]
    assert rec["volumes"] == ["recorder_log:/var/lib/rounds-recorder"]
    assert not any("ports" in svc for svc in doc["services"].values())
    runner_env = doc["services"]["runner"]["environment"]
    assert "POCKETBASE_URL=${RUNNER_POCKETBASE_URL:-http://pocketbase:8090}" in runner_env
    assert doc["services"]["pocketbase"]["volumes"] == ["${PB_DATA_VOLUME:-pb_data}:/pb/pb_data"]
    for name, env in (("pb_data_legacy", "PB_LEGACY_VOLUME"), ("recorder_log", "RECORDER_VOLUME")):
        assert doc["volumes"][name]["external"] is True and env in doc["volumes"][name]["name"]


def test_the_probe_runner_dispatches_the_four_phases():
    src = (HARNESS / "probes" / "run.py").read_text()
    for phase in ("legacy-shares-migration", "legacy-shares-fixture", "legacy-shares", "legacy-shares-scan"):
        assert f'"{phase}"' in src, phase
    assert stack.PHASES == ("legacy-shares-fixture", "legacy-shares", "legacy-shares-scan")


def test_the_stack_fixture_is_shaped_like_62d4eae():
    assert stack.BEFORE_R0 == admission_migration_check.BASE_BEFORE


def test_phase_15_covers_every_outcome_a_database_can_hold_after_10():
    manifest = json.loads(MANIFEST.read_text())
    reasons = {reason for listed in manifest["outcomes"].values() for reason in listed}
    planted = {reason for _id, _fields, _outcome, reason in offline.LIVE}
    planted |= {reason for _id, _fields, reason in offline.QUARANTINED}
    # #10's triggers refuse a link to another account's resume or variant, so
    # those two come only through #10's quarantine here; the migration's own
    # tests decide them (pocketbase/tests/test_legacy_share_migration.py).
    assert reasons - planted == {"target_owner", "parent_owner", "quarantined_other"}
    outcomes, counted = offline.expected_counts()
    assert sum(outcomes.values()) == len(offline.LIVE) + offline.BULK + len(offline.QUARANTINED)
    assert counted["eligible"] == 2 + offline.BULK


def _identity(tmp_path: Path, monkeypatch, lines: list[dict]) -> tuple[bool, list[dict]]:
    log = tmp_path / "recorder.jsonl"
    log.write_text("".join(json.dumps({"seq": n, "method": "POST", "status": 200, "length": 1, "owners": [], **line})
                           + "\n" for n, line in enumerate(lines, 1)))
    monkeypatch.setattr(stack, "RECORDER_LOG", str(log))
    out = tmp_path / "receipts.jsonl"
    writer = ReceiptWriter(str(out), {"phase": "legacy-shares"})
    c = Checks()
    stack.check_resolver_identity(c, writer, 0, len(lines))
    return c.failed == 0, read_all(str(out))


LOGIN = {"path": stack.RESOLVER_LOGIN, "auth": "none"}
LOOKUP = {"path": stack.RESOLVER_LOOKUP, "auth": "service"}


def test_the_identity_check_holds_for_the_resolvers_login_and_lookups(tmp_path, monkeypatch):
    ok, receipts = _identity(tmp_path, monkeypatch, [LOGIN, LOOKUP, LOOKUP])
    assert ok and receipts[0]["probe_id"] == "isolation.share-public.resolver-identity" and receipts[0]["passed"]


def test_the_identity_check_fails_on_any_other_identity_or_call(tmp_path, monkeypatch):
    for bad in ({"path": stack.RESOLVER_LOOKUP, "auth": "user"}, {"path": stack.RESOLVER_LOOKUP, "auth": "superuser"},
                {"path": "/api/collections/resume_share_links/records", "auth": "superuser"},
                {"path": stack.RESOLVER_LOGIN, "auth": "user"}):
        ok, receipts = _identity(tmp_path, monkeypatch, [LOGIN, LOOKUP, bad])
        assert not ok and not receipts[0]["passed"], bad


def test_the_identity_check_needs_a_lookup_to_have_happened(tmp_path, monkeypatch):
    ok, receipts = _identity(tmp_path, monkeypatch, [LOGIN])
    assert not ok and not receipts[0]["passed"]


def test_the_stack_phase_writes_the_receipts_of_four_pass_rows():
    src = (HARNESS / "probes" / "legacy_share_check.py").read_text()
    written = set(re.findall(r'receipt\(writer, "([a-z.-]+)"', src))
    assert written == CASES
    cases = json.loads(POLICY.read_text())["cases"]
    for cid in CASES:
        assert cases[cid]["status"] == "pass" and cases[cid]["evidence"] == [cid], cid
    assert cases["isolation.share-public.resolver-identity"]["guarantee"] == (
        "a public share request reaches PocketBase only as the share resolver's own service identity")


def _tagged_rows(tmp_path: Path, rows: list[tuple[str, str]]) -> Path:
    import sqlite3

    db = tmp_path / "logs.db"
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE _logs (id TEXT, level INTEGER, message TEXT, data TEXT, created TEXT, updated TEXT)")
    for n, (agent, url) in enumerate(rows):
        con.execute("INSERT INTO _logs VALUES (?, 0, ?, ?, '', '')",
                    (f"r{n}", f"GET {url}", json.dumps({"url": url, "userAgent": agent})))
    con.commit()
    con.close()
    return db


def test_the_scan_passes_over_only_the_every_value_checks_own_requests(tmp_path):
    value = "FixtureLinkValue0123456"
    own = (stack.PROBE_AGENT, f"{stack.LINKS_PATH}?token={value}")
    db = _tagged_rows(tmp_path, [own, own])
    assert stack.scan_db(db, (value,)) == (0, 2)
    for other in ("python-httpx/0.27.2", "Python-urllib/3.12", "", stack.PROBE_AGENT + "-x"):
        db.unlink()
        db = _tagged_rows(tmp_path, [own, (other, f"{stack.LINKS_PATH}?q={value}")])
        found, passed = stack.scan_db(db, (value,))
        assert passed == 1 and found == 2, other
