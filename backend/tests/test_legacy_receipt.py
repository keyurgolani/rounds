"""Signing the legacy snapshot scan's report (ROUNDS-00A-L04, PR 2).

The report the hook's scan writes (run here under node, through
pocketbase/tests/legacy_snapshots_runner.cjs) verifies its own checksum in
Python, signs under HKDF-SHA256 over AI_KEY_SECRET with the scan's label,
and stops verifying when a count, the checksum, the signature, or the
secret changes. No secret, key, or id reaches the output."""
from __future__ import annotations

import hashlib
import hmac
import io
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from app import canonical, legacy_receipt

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / "pocketbase" / "pb_hooks"
SCAN_RUNNER = ROOT / "pocketbase" / "tests" / "legacy_snapshots_runner.cjs"
# Test values, not a deployment's.
SECRET = "test-scan-secret-" + "1" * 32
OTHER_SECRET = "test-scan-secret-" + "2" * 32
MARKUP = "<!DOCTYPE html><html><body><p>x</p></body></html>"


def scan_report() -> dict:
    """A report from the hook's own scan, over two accounts' sources."""
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    state = {
        "users": {"acct00000000001": {}, "acct00000000002": {"is_demo": True}},
        "resumes": {
            "resumeaaaaaaaa1": {"user": "acct00000000001", "updated": "2026-10-20 10:00:00.000Z",
                                "template_id": "modern", "design": {}, "data": {}},
            "resumebbbbbbbb1": {"user": "acct00000000002", "updated": "2026-10-20 10:00:00.000Z",
                                "template_id": "modern", "design": {}, "data": {}},
        },
        "variants": {},
    }
    program = {"state": state, "steps": [{"op": "scan", "materializer": [{"ok": {"markup": MARKUP}}],
                                          "commit": "abc1234"}]}
    out = subprocess.run([node, str(SCAN_RUNNER), str(HOOKS)], input=json.dumps(program), capture_output=True,
                         text=True, timeout=60, check=True)
    (result,) = json.loads(out.stdout)["results"]
    return result["report"]


def run(argv, secret=SECRET, stdin=b""):
    out, err = io.StringIO(), io.StringIO()
    env = {} if secret is None else {legacy_receipt.SECRET_ENV: secret}
    code = legacy_receipt.main(argv, env=env, stdin=io.BytesIO(stdin), stdout=out, stderr=err)
    return code, out.getvalue(), err.getvalue()


def write(tmp_path: Path, name: str, value) -> str:
    path = tmp_path / name
    path.write_text(json.dumps(value) if not isinstance(value, str) else value)
    return str(path)


def hkdf_sha256(secret: bytes, info: bytes) -> bytes:
    """RFC 5869 with no salt and one block, written out apart from the module."""
    prk = hmac.new(b"\0" * 32, secret, hashlib.sha256).digest()
    return hmac.new(prk, info + b"\x01", hashlib.sha256).digest()


# ---- the hook's report verifies in Python ------------------------------------------


def test_the_scans_own_checksum_verifies_here():
    report = scan_report()
    assert report["schema"] == "legacy-snapshot-scan/v1"
    legacy_receipt.check_checksum(report)


def test_sign_then_verify_round_trips_and_prints_only_counts(tmp_path):
    report = scan_report()
    code, signed_text, err = run(["sign", write(tmp_path, "report.json", report)])
    assert code == 0, err
    signed = json.loads(signed_text)
    assert {k: v for k, v in signed.items() if k != "signature"} == report
    assert signed["signature"]["alg"] == "HMAC-SHA256"
    assert signed["signature"]["key"] == "rounds/legacy-snapshot-scan/v1"
    code, out, err = run(["verify", write(tmp_path, "signed.json", signed)])
    assert code == 0, err
    assert out.startswith("verified legacy-snapshot-scan/v1 " + report["checksum"])
    for text in (signed_text, out, err):
        assert SECRET not in text and "acct00000000001" not in text and "resumeaaaaaaaa1" not in text


def test_the_key_is_hkdf_sha256_over_the_secret_with_the_scans_label():
    report = scan_report()
    signed = legacy_receipt.sign(report, SECRET)
    key = hkdf_sha256(SECRET.encode(), b"rounds/legacy-snapshot-scan/v1")
    want = hmac.new(key, canonical.canonical(report), hashlib.sha256).hexdigest()
    assert signed["signature"]["value"] == want


def test_a_report_on_stdin_signs_to_a_new_private_file(tmp_path):
    out = tmp_path / "signed.json"
    code, _, err = run(["sign", "-", "--out", str(out)], stdin=json.dumps(scan_report()).encode())
    assert code == 0, err
    assert stat.S_IMODE(os.stat(out).st_mode) == 0o600
    assert run(["verify", str(out)])[0] == 0
    # It never overwrites a file.
    assert run(["sign", "-", "--out", str(out)], stdin=json.dumps(scan_report()).encode())[0] == 2


# ---- what doesn't verify ----------------------------------------------------------------


def _signed() -> dict:
    return legacy_receipt.sign(scan_report(), SECRET)


def _recount(report: dict) -> dict:
    """A changed count with its checksum recomputed, so only the signature
    can tell."""
    body = {k: v for k, v in report.items() if k not in ("checksum", "signature")}
    return {**report, "checksum": canonical.checksum(body)}


@pytest.mark.parametrize("tamper, why", [
    (lambda r: {**r, "totals": {**r["totals"], "eligible": r["totals"]["eligible"] + 1}}, "checksum"),
    (lambda r: _recount({**r, "totals": {**r["totals"], "eligible": r["totals"]["eligible"] + 1}}), "signature"),
    (lambda r: {**r, "signature": {**r["signature"], "value": "0" * 64}}, "signature"),
    (lambda r: {**r, "signature": {**r["signature"], "key": "rounds/other/v1"}}, "schema's"),
    (lambda r: {k: v for k, v in r.items() if k != "signature"}, "isn't signed"),
    (lambda r: {**r, "schema": "legacy-snapshot-scan/v2"}, "not a report this signs"),
])
def test_a_changed_report_doesnt_verify(tmp_path, tamper, why):
    code, _, err = run(["verify", write(tmp_path, "r.json", tamper(_signed()))])
    assert code == 1 and why in err


def test_another_secret_doesnt_verify(tmp_path):
    path = write(tmp_path, "r.json", _signed())
    assert run(["verify", path], secret=OTHER_SECRET)[0] == 1


def test_sign_refuses_a_report_whose_checksum_is_wrong_or_already_signed(tmp_path):
    report = scan_report()
    bad = {**report, "totals": {**report["totals"], "sources": 99}}
    assert run(["sign", write(tmp_path, "bad.json", bad)])[0] == 1
    assert run(["sign", write(tmp_path, "signed.json", _signed())])[0] == 1


@pytest.mark.parametrize("raw", ["not json", "[1, 2]", json.dumps({"schema": "something-else/v1"})])
def test_anything_but_a_scan_report_is_refused(tmp_path, raw):
    assert run(["sign", write(tmp_path, "r.json", raw)])[0] == 1


@pytest.mark.parametrize("secret", [None, "", legacy_receipt.DEV_SECRET])
def test_no_secret_or_the_development_placeholder_signs_nothing(tmp_path, secret):
    code, out, err = run(["sign", write(tmp_path, "r.json", scan_report())], secret=secret)
    assert code == 2 and out == "" and legacy_receipt.SECRET_ENV in err


def test_usage_errors_are_exit_2(tmp_path):
    assert run([])[0] == 2
    assert run(["sign", str(tmp_path / "missing.json")])[0] == 2
