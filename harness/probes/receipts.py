"""JSON-line receipts for the account-scope harness.

One line per probe. Fields carry no record contents and no secrets: only
run id, commit, binary digest, migration list, probe id, collection,
operation, actor, expected and observed status, and request time. Record
ids are per-run throwaway PocketBase ids, never account identifiers.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any


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


class ReceiptWriter:
    def __init__(self, path: str, context: dict[str, Any]) -> None:
        self.path = path
        self.context = context
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def write(self, r: Receipt) -> None:
        r.version = "v1"
        r.run_id = self.context.get("run_id", "")
        r.commit = self.context.get("commit", "")
        r.binary_digest = self.context.get("binary_digest", "")
        r.binary_arch = self.context.get("binary_arch", "")
        r.phase = self.context.get("phase", "")
        r.migrations = self.context.get("migrations", [])
        with open(self.path, "a") as f:
            f.write(json.dumps(asdict(r), separators=(",", ":")) + "\n")


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
