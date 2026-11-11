"""JSON-line receipts for the account-scope harness.

One line per probe. Fields carry no record contents and no secrets: only
run id, commit, binary digest, migration list, the policy and migration-list
checksums, probe id, collection, operation, actor, expected and observed
status, and request time. Record ids are per-run throwaway PocketBase ids,
never account identifiers.

Every string a receipt carries goes through a redactor before the line is
written: a secret registered with the writer (an account's session token or
password) becomes its case-local label, and anything shaped like a session
token or a harness password becomes a fixed label, registered or not.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from typing import Any

# PocketBase session tokens are JWTs, and the account factory's passwords
# have a fixed shape (factory._gen_password). The harness admin password has
# none, so each phase registers it with its writer (run.new_writer).
JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]{4,}")
PASSWORD_RE = re.compile(r"Hx[0-9a-f]{32}!9")
REDACTED_TOKEN = "<redacted:token>"
REDACTED_PASSWORD = "<redacted:password>"


class Redactor:
    """Replaces secrets in strings before they're written anywhere."""

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}

    def register(self, secret: str, label: str) -> None:
        # Short values would redact ordinary text; the harness's secrets are
        # all long.
        if isinstance(secret, str) and len(secret) >= 8:
            self._secrets[secret] = f"<{label}>"

    def text(self, value: str) -> str:
        # Longest first, so a secret that contains another is replaced whole.
        for secret in sorted(self._secrets, key=len, reverse=True):
            value = value.replace(secret, self._secrets[secret])
        value = JWT_RE.sub(REDACTED_TOKEN, value)
        return PASSWORD_RE.sub(REDACTED_PASSWORD, value)

    def value(self, value: Any) -> Any:
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, (list, tuple)):
            return [self.value(v) for v in value]
        if isinstance(value, dict):
            return {(self.text(k) if isinstance(k, str) else k): self.value(v) for k, v in value.items()}
        return value


@dataclass
class Receipt:
    probe_id: str
    collection: str
    operation: str
    actor: str
    expected_status: int
    observed_status: int
    passed: bool
    request_time_ms: int
    detail: str = ""
    # Run-level context (filled by the writer).
    version: str = "v1"
    run_id: str = ""
    commit: str = ""
    binary_digest: str = ""
    binary_arch: str = ""
    phase: str = ""
    migrations: list[str] = field(default_factory=list)
    policy_checksum: str = ""
    migrations_checksum: str = ""


def file_checksum(path: str) -> str:
    """sha256 of a file, or "" when it isn't there."""
    try:
        with open(path, "rb") as f:
            return "sha256:" + hashlib.sha256(f.read()).hexdigest()
    except OSError:
        return ""


def list_checksum(names: list[str]) -> str:
    return "sha256:" + hashlib.sha256("\n".join(names).encode("utf-8")).hexdigest()


class ReceiptWriter:
    def __init__(self, path: str, context: dict[str, Any], redactor: Redactor | None = None) -> None:
        self.path = path
        self.context = context
        self.redactor = redactor or Redactor()
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def register_secret(self, secret: str, label: str) -> None:
        self.redactor.register(secret, label)

    def write(self, r: Receipt) -> None:
        r.version = "v1"
        r.run_id = self.context.get("run_id", "")
        r.commit = self.context.get("commit", "")
        r.binary_digest = self.context.get("binary_digest", "")
        r.binary_arch = self.context.get("binary_arch", "")
        r.phase = self.context.get("phase", "")
        r.migrations = self.context.get("migrations", [])
        r.policy_checksum = self.context.get("policy_checksum", "")
        r.migrations_checksum = self.context.get("migrations_checksum", "")
        # Every field, then the serialized line once more, so nothing that
        # only takes a secret's shape once it's serialized gets through.
        line = self.redactor.text(json.dumps(self.redactor.value(asdict(r)), separators=(",", ":")))
        with open(self.path, "a") as f:
            f.write(line + "\n")


def read_all(path: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not os.path.exists(path):
        return out
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out
