"""Signs and verifies an operator's scan report (ROUNDS-00A-L04, PR 2).

``pocketbase legacy-snapshot-scan`` (pocketbase/pb_hooks/legacy_snapshots.js)
writes a JSON report of counts that carries its own ``checksum``: ``sha256:``
over the canonical JSON (RFC 8785, ``app.canonical``) of the report without
it. The runner holds ``AI_KEY_SECRET``, so it signs:

    python -m app.legacy_receipt sign REPORT [--out SIGNED]
    python -m app.legacy_receipt verify SIGNED

``sign`` checks the report's schema and checksum, then adds
``signature``: HMAC-SHA256 over the canonical JSON of the report without
its signature, under the key HKDF-SHA256 derives from ``AI_KEY_SECRET``
with the schema's label (``rounds/legacy-snapshot-scan/v1``). ``verify``
recomputes the checksum and the signature. REPORT may be ``-`` for stdin;
the signed report goes to stdout unless ``--out`` names a file, written
0600. Neither prints the secret, the key, or anything but counts.

Exit status: 0 done, 1 a report that isn't one this signs or doesn't
verify, 2 a usage or configuration error.

#14 (ROUNDS-00B-L06) signs its own report here under its own schema and
label (``LABELS``).

TODO(ROUNDS-14-L02): #73's keyring derives this key; until then it is
HKDF over AI_KEY_SECRET directly, as app.obs derives its pseudonym key.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import sys
from typing import Any, BinaryIO, TextIO

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app import canonical

SECRET_ENV = "AI_KEY_SECRET"
# The development compose file's placeholder (app.crypto): a signature
# under it proves nothing, so it signs nothing.
DEV_SECRET = "rounds-dev-key-DO-NOT-USE-IN-PROD"
ALGORITHM = "HMAC-SHA256"
# Report schema -> the HKDF label its key derives with.
LABELS: dict[str, str] = {"legacy-snapshot-scan/v1": "rounds/legacy-snapshot-scan/v1"}
MAX_REPORT_BYTES = 32 * 1024 * 1024


class ConfigError(Exception):
    """The command can't run here: no usable secret, or a file it can't use."""


class ReportError(Exception):
    """The report isn't one this signs, or it doesn't verify."""


def key_for(label: str, secret: str) -> bytes:
    """The signing key: HKDF-SHA256 over the secret with the label."""
    if not secret:
        raise ConfigError(f"{SECRET_ENV} is not set; sign on the runner that holds it")
    if secret == DEV_SECRET:
        raise ConfigError(f"{SECRET_ENV} is the development placeholder, so a signature under it proves nothing")
    return HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=label.encode("ascii")).derive(
        secret.encode("utf-8")
    )


def _without(report: dict[str, Any], *names: str) -> dict[str, Any]:
    return {k: v for k, v in report.items() if k not in names}


def _label(report: Any) -> str:
    if not isinstance(report, dict):
        raise ReportError("not a JSON object")
    label = LABELS.get(report.get("schema"))  # type: ignore[arg-type]
    if label is None:
        raise ReportError(f"not a report this signs; schema is one of {', '.join(sorted(LABELS))}")
    return label


def check_checksum(report: dict[str, Any]) -> None:
    try:
        want = canonical.checksum(_without(report, "checksum", "signature"))
    except canonical.CanonicalError as err:
        raise ReportError(f"not canonical JSON ({err})") from None
    if report.get("checksum") != want:
        raise ReportError("the report's checksum doesn't match its contents")


def signature_of(report: dict[str, Any], key: bytes) -> str:
    return hmac.new(key, canonical.canonical(_without(report, "signature")), hashlib.sha256).hexdigest()


def sign(report: Any, secret: str) -> dict[str, Any]:
    label = _label(report)
    if "signature" in report:
        raise ReportError("the report is already signed")
    check_checksum(report)
    key = key_for(label, secret)
    return {**report, "signature": {"alg": ALGORITHM, "key": label, "value": signature_of(report, key)}}


def verify(report: Any, secret: str) -> dict[str, Any]:
    label = _label(report)
    check_checksum(report)
    sig = report.get("signature")
    if not isinstance(sig, dict) or set(sig) != {"alg", "key", "value"}:
        raise ReportError("the report isn't signed")
    if sig["alg"] != ALGORITHM or sig["key"] != label or not isinstance(sig["value"], str):
        raise ReportError("the signature isn't this schema's")
    if not hmac.compare_digest(sig["value"], signature_of(report, key_for(label, secret))):
        raise ReportError("the signature doesn't match")
    return report


def summary(report: dict[str, Any]) -> str:
    totals = report.get("totals") if isinstance(report.get("totals"), dict) else {}
    parts = [f"{k}={v}" for k, v in sorted(totals.items()) if isinstance(v, int)]
    return " ".join([report["schema"], report["checksum"], f"complete={str(report.get('complete')).lower()}", *parts])


def _read(path: str, stdin: BinaryIO) -> Any:
    try:
        if path == "-":
            raw = stdin.read(MAX_REPORT_BYTES + 1)
        else:
            with open(path, "rb") as f:
                raw = f.read(MAX_REPORT_BYTES + 1)
    except OSError as err:
        raise ConfigError(f"can't read {path}: {err.strerror}") from None
    if len(raw) > MAX_REPORT_BYTES:
        raise ReportError("the report is larger than any scan writes")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise ReportError("not JSON") from None


def _write(report: dict[str, Any], out: str | None, stdout: TextIO) -> None:
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if out is None:
        stdout.write(text)
        return
    try:
        fd = os.open(out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except OSError as err:
        raise ConfigError(f"can't write {out}: {err.strerror}") from None
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)


def main(argv: list[str] | None = None, env: dict[str, str] | None = None,
         stdin: BinaryIO | None = None, stdout: TextIO | None = None, stderr: TextIO | None = None) -> int:
    env = os.environ if env is None else env
    stdin = sys.stdin.buffer if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    parser = argparse.ArgumentParser(prog="python -m app.legacy_receipt", description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    signing = sub.add_parser("sign", help="check a scan report and sign it")
    signing.add_argument("report", help="the report, or - for stdin")
    signing.add_argument("--out", help="write the signed report here (a new file, mode 0600) instead of stdout")
    checking = sub.add_parser("verify", help="check a signed report's checksum and signature")
    checking.add_argument("report", help="the signed report, or - for stdin")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exit_:
        return 2 if exit_.code else 0
    secret = env.get(SECRET_ENV, "")
    try:
        report = _read(args.report, stdin)
        if args.command == "sign":
            signed = sign(report, secret)
            _write(signed, args.out, stdout)
            stderr.write(f"signed {summary(signed)}\n")
        else:
            verify(report, secret)
            stdout.write(f"verified {summary(report)}\n")
    except ConfigError as err:
        stderr.write(f"legacy_receipt: {err}\n")
        return 2
    except ReportError as err:
        stderr.write(f"legacy_receipt: {err}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
