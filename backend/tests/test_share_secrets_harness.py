"""The harness's share secrets phases (ROUNDS-00B-L04) are wired: run.sh
runs them after the share capability phase and before signups close, with
PocketBase stopped for the degraded one, and fails the run when any fails;
the scan's logs and pb_data stay in the state folder, never the receipts,
and go right after the scan; both runners get the gate and the resolver's
secret; the probe runner dispatches the three phases; and the probe's
scanner finds what it looks for. The phases themselves run in CI's harness
job."""
from __future__ import annotations

import io
import json
import re
import sys
import tarfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
HARNESS = ROOT / "harness"
sys.path.insert(0, str(HARNESS / "probes"))

import share_secrets_check as probe  # noqa: E402
from receipts import ReceiptWriter, read_all  # noqa: E402

POLICY = ROOT / "docs" / "security" / "account-scope.v1.json"
CASES = {
    "isolation.share-resolver.password.uniform",
    "isolation.share-resolver.throttle.independent",
    "isolation.logs.share-secret.absent",
    "isolation.logs.share-client-address.absent",
}


def _run_sh() -> str:
    return (HARNESS / "run.sh").read_text()


def _phase_lines() -> list[str]:
    return [m.group(0) for m in re.finditer(r'^echo "--- phase [0-9a-z]+:.*$|^\s*probe [a-z-]+\b', _run_sh(), re.M)]


def test_run_sh_runs_the_phases_after_share_capabilities_and_before_signups_close():
    lines = [line.strip() for line in _phase_lines()]
    at = lines.index("probe share-secrets")
    assert lines.index("probe share-capabilities") < at < lines.index("probe share-secrets-down")
    assert lines.index("probe share-secrets-down") < lines.index("probe share-secrets-scan") < lines.index("probe hook")
    text = _run_sh()
    phase = text[text.index('echo "--- phase 3l'):text.index('echo "--- phase 4')]
    assert "SNAPSHOT_GATE=enabled" in phase and "SHARE_GATE=enabled" in phase
    assert "compose up -d materializer" in phase and "restart_runners" in phase
    down = phase[phase.index('echo "--- phase 3m'):phase.index('echo "--- phase 3n')]
    assert down.index("compose stop pocketbase") < down.index("probe share-secrets-down") < down.index(
        "compose start pocketbase")
    assert '[ "${share_secrets_rc}" -ne 0 ]' in text


def test_the_scan_reads_files_kept_out_of_the_receipts_and_removes_them():
    text = _run_sh()
    scan = text[text.index('echo "--- phase 3n'):text.index('echo "--- phase 4')]
    assert 'SCAN_DIR="${STATE_DIR}/share-scan"' in scan
    assert "RECEIPTS_DIR" not in scan
    for svc in ("pocketbase", "runner", "runner-b", "frontend"):
        assert svc in scan.split("for svc in", 1)[1].split(";", 1)[0]
    assert scan.index("probe share-secrets-scan") < scan.index('rm -rf "${SCAN_DIR}"')
    assert probe.SCAN_DIR == Path("/state/share-scan") and probe.STATE.parent == Path("/state")


def test_both_runners_and_pocketbase_get_the_gate_and_the_resolver_secret():
    compose = yaml.safe_load((HARNESS / "compose.yml").read_text())
    runner = compose["services"]["runner"]["environment"]
    assert "ROUNDS_GATE_SHARE_CAPABILITY_RESOLUTION=${ROUNDS_GATE_SHARE_CAPABILITY_RESOLUTION:-}" in runner
    assert "ROUNDS_SHARE_RESOLVER_PASSWORD=${ROUNDS_SHARE_RESOLVER_PASSWORD:-}" in runner
    assert compose["services"]["runner-b"]["environment"] == runner
    assert "ROUNDS_SHARE_RESOLVER_PASSWORD=${ROUNDS_SHARE_RESOLVER_PASSWORD:-}" in compose["services"]["pocketbase"][
        "environment"]
    secret = re.search(r'^SHARE_RESOLVER_SECRET_V="([^"]+)"$', _run_sh(), re.M).group(1)
    assert 32 <= len(secret) <= 72 and "not-a-secret" in secret


def test_the_probe_runner_dispatches_the_phases():
    text = (HARNESS / "probes" / "run.py").read_text()
    assert 'if phase.startswith("share-secrets"):' in text and "share_secrets_check.main(phase, writer)" in text
    assert probe.PHASES == ("share-secrets", "share-secrets-down", "share-secrets-scan")


def test_the_receipts_are_this_leafs_pass_rows():
    cases = json.loads(POLICY.read_text())["cases"]
    source = (HARNESS / "probes" / "share_secrets_check.py").read_text()
    written = set(re.findall(r'receipt\(writer, "([a-z.-]+)"', source))
    assert written == CASES
    for cid in CASES:
        row = cases[cid]
        assert (row["status"], row["owner_leaf"], row["evidence"]) == ("pass", "ROUNDS-00B-L04", [cid])


# ---- the scanner ------------------------------------------------------------------------------------------


TOKEN = "sd1_AbCdEfGhIjKlMnOpQrStUv"
PASSWORD = "harness-share-pw-0123456789abcdef"


def test_the_scan_looks_for_every_form_a_bearer_or_password_could_take():
    import base64
    import hashlib
    import urllib.parse

    spaced = "a password with spaces/and+signs"
    values = set(probe.literals([TOKEN], [PASSWORD, spaced]))
    assert {TOKEN, base64.b64encode(TOKEN.encode()).decode(), base64.b64encode(TOKEN.encode()).decode().rstrip("="),
            base64.urlsafe_b64encode(TOKEN.encode()).decode().rstrip("=")} <= values
    assert {PASSWORD, hashlib.sha1(PASSWORD.encode()).hexdigest(), hashlib.sha256(PASSWORD.encode()).hexdigest(),
            hashlib.md5(PASSWORD.encode()).hexdigest()} <= values
    # A bearer needs no escaping, so its URL-encoded form is the bearer; a
    # password may need it.
    assert urllib.parse.quote(TOKEN, safe="") == TOKEN
    assert urllib.parse.quote(spaced, safe="") != spaced and urllib.parse.quote(spaced, safe="") in values


def test_the_flood_draws_bearers_under_key_ids_the_format_allows():
    # The current key id and two others, so the limit check also shows that
    # a bearer under another key id is counted.
    from app import share_secrets

    assert probe.KEY_IDS[0] == share_secrets.KEY_ID and len(set(probe.KEY_IDS)) == 3
    for key in probe.KEY_IDS:
        bearer = probe.random_bearer(key)
        assert share_secrets.well_formed(bearer) and share_secrets.key_id(bearer) == key


def test_the_scan_finds_bytes_inside_a_tarball(tmp_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tar:
        for name, data in (("pb_data/data.db", b"x" * 10 + TOKEN.encode() + b"y"), ("pb_data/logs.db", b"none")):
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    path = tmp_path / "pb_data.tar"
    path.write_bytes(buf.getvalue())
    assert probe.tar_hits(path, (TOKEN,)) == 1
    assert probe.tar_hits(path, ("sd1_ZyXwVuTsRqPoNmLkJiHgFe",)) == 0


def test_share_lines_with_the_address_count_apart_from_other_lines():
    log = "\n".join([
        '172.18.0.9 - - [11/Nov/2026:12:00:00 +0000] "POST /api/share/resolve HTTP/1.1" 404 23 "-" "x"',
        '172.18.0.9 - - [11/Nov/2026:12:00:01 +0000] "GET /r HTTP/1.1" 200 900 "-" "x"',
        '172.18.0.9 - - [11/Nov/2026:12:00:02 +0000] "GET / HTTP/1.1" 200 900 "-" "x"',
        'INFO:     172.18.0.9:51234 - "POST /api/share/resolve HTTP/1.1" 429 Too Many Requests',
        '172.18.0.19 - - [11/Nov/2026:12:00:03 +0000] "POST /api/share/resolve HTTP/1.1" 404 23 "-" "x"',
        '172.18.0.4 - - [11/Nov/2026:12:00:04 +0000] "GET /resumes HTTP/1.1" 200 900 "-" "x"',
    ])
    assert probe.address_lines(log, "172.18.0.9") == (3, 1)
    assert probe.address_lines(log, "172.18.0.1") == (0, 0)


def test_receipts_never_carry_a_bearer_or_a_password(tmp_path):
    writer = ReceiptWriter(str(tmp_path / "r.jsonl"), {"phase": "share-secrets"})
    held = probe.Secrets(writer)
    held.token(TOKEN)
    held.password(PASSWORD)
    probe.receipt(writer, "isolation.share-resolver.password.uniform", False, 404, 200,
                  f"saw {TOKEN} and {PASSWORD}")
    (row,) = read_all(str(tmp_path / "r.jsonl"))
    text = json.dumps(row)
    assert TOKEN not in text and PASSWORD not in text
    assert row["probe_id"] == "isolation.share-resolver.password.uniform" and row["passed"] is False
