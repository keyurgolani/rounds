"""Machine-readable receipts for the containment corpus.

One receipt file per run, ``rounds-containment-receipt/v1`` (#7's
wrapper). It carries the run context (commit, corpus version, target,
image references, the contract versions, the canary-set id, and the
run's total probe spend) and one entry for every manifest row:

- a fixture that ran records its outcome and verdict, one status per
  sub-case (``contained`` with the outcome it reached, or ``pending``
  with the leaf that closes it), the routes it actually exercised, the
  redacted evidence and its checksums, a canary-hit boolean per canary,
  its budget spend, the reason for its verdict, and its own note;
- a quarantined fixture records the skip ledger's owner and expiry;
- a pending row records the leaf that closes it.

Receipts state ``contained``, ``not-applicable``, ``pending``, or
``quarantined`` only on a passing run (orchestrator decision D4): a
``detected`` or ``inconclusive`` entry exists only in a failing run's
receipt, which is a CI artifact, never committed. Unlanded context
fields read ``absent``.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from . import RECEIPT_SCHEMA

# The most redacted evidence one fixture keeps in the receipt.
EVIDENCE_MAX_CHARS = 256 * 1024


def checksum(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def cap_evidence(evidence: dict[str, str]) -> dict[str, str]:
    """The evidence, cut to ``EVIDENCE_MAX_CHARS`` in all, with a marker
    where it was cut."""
    out: dict[str, str] = {}
    left = EVIDENCE_MAX_CHARS
    for name, text in evidence.items():
        if left <= 0:
            out[name] = "<truncated>"
            continue
        if len(text) > left:
            out[name] = text[:left] + "<truncated>"
            left = 0
        else:
            out[name] = text
            left -= len(text)
    return out


@dataclass
class FixtureReceipt:
    id: str
    status: str  # "ran", "quarantined", or "pending"
    closing_leaf: str
    target: str = ""
    outcome: str = ""
    expectation: str = ""
    verdict: str = ""
    legacy_classified: bool = False
    subcases: list[dict[str, Any]] = field(default_factory=list)
    routes: list[str] = field(default_factory=list)
    evidence: dict[str, str] = field(default_factory=dict)
    checksums: dict[str, str] = field(default_factory=dict)
    canary_hits: dict[str, bool] = field(default_factory=dict)
    budget: dict[str, float] = field(default_factory=dict)
    reason: str = ""
    note: str = ""
    quarantine: dict[str, str] = field(default_factory=dict)


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
    budget_total: dict[str, float] = field(default_factory=dict)
    fixtures: list[FixtureReceipt] = field(default_factory=list)

    def add(self, receipt: FixtureReceipt) -> None:
        if any(f.id == receipt.id for f in self.fixtures):
            raise ValueError(f"{receipt.id} already has a receipt entry")
        self.fixtures.append(receipt)

    def ids(self) -> list[str]:
        return [f.id for f in self.fixtures]

    def missing(self, manifest_ids: Iterable[str]) -> dict[str, list[str]]:
        """The manifest rows without an entry, and entries no row names."""
        want, have = set(manifest_ids), set(self.ids())
        return {"missing": sorted(want - have), "unknown": sorted(have - want)}

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def write(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
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
