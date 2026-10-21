"""Machine-readable receipts for the containment corpus.

One receipt file per run, ``rounds-containment-receipt/v1`` (#7's
wrapper). It carries the run context (commit, corpus version, target,
image references, the contract versions #2, #3, #6, and the resource
profile pin, and the canary-set id) and one entry per fixture. A
contained fixture records its outcome, the expectation it met, the
verdict, the checksums of its redacted request and response summaries,
and a canary-hit boolean per canary. A pending fixture records only that
it is pending and the leaf that closes it.

Receipts state ``contained`` or ``pending`` only (orchestrator decision
D4): the corpus commits no receipt that shows a sub-case exploitable, and
a ``detected`` outcome never reaches a committed receipt because a
detecting fixture fails the lane. Unlanded context fields read ``absent``.

The receipts file is written to a run directory that is git-ignored and
uploaded as a CI artifact; nothing here is committed to the repository.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any

from . import RECEIPT_SCHEMA


def checksum(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class FixtureReceipt:
    id: str
    status: str  # "contained" or "pending"
    closing_leaf: str
    target: str = ""
    outcome: str = ""
    expectation: str = ""
    verdict: str = ""
    legacy_classified: bool = False
    routes: list[str] = field(default_factory=list)
    checksums: dict[str, str] = field(default_factory=dict)
    canary_hits: dict[str, bool] = field(default_factory=dict)
    budget: dict[str, float] = field(default_factory=dict)
    note: str = ""


@dataclass
class RunReceipt:
    commit: str
    corpus_version: str
    target: str
    canary_set_id: str
    images: dict[str, str] = field(default_factory=dict)
    versions: dict[str, str] = field(default_factory=dict)
    schema: str = RECEIPT_SCHEMA
    run_id: str = ""
    fixtures: list[FixtureReceipt] = field(default_factory=list)

    def add(self, receipt: FixtureReceipt) -> None:
        self.fixtures.append(receipt)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(self.to_dict(), fh, indent=2, sort_keys=False)
            fh.write("\n")

    @property
    def passed(self) -> bool:
        return all(f.verdict in ("", "pass") for f in self.fixtures)


# Contract versions the receipt records. A version a later leaf
# introduces reads ``absent`` until that leaf lands (#8 body, Data and
# API contracts).
def default_versions() -> dict[str, str]:
    return {
        "definition": "test-definition/v1",
        "harness": "harness-revision/v1",
        "renderer_contract": "absent",
        "resource_profile": "execution-default.v1",
        "envelope": "absent",
    }
