"""Load and validate the account-scope policy contract.

The harness refuses to run against an unknown policy version before it
touches anything (acceptance criterion: "the harness rejects an unknown
policy version before either changes anything").
"""
from __future__ import annotations

import json
from typing import Any

SUPPORTED_VERSION = "v1"


class PolicyError(RuntimeError):
    pass


def load(path: str) -> dict[str, Any]:
    with open(path) as f:
        doc = json.load(f)
    version = doc.get("version")
    if version != SUPPORTED_VERSION:
        raise PolicyError(
            f"unsupported policy version {version!r}; this harness only "
            f"understands {SUPPORTED_VERSION!r}"
        )
    if doc.get("contract") != "account-scope":
        raise PolicyError(f"unexpected contract {doc.get('contract')!r}")
    collections = doc.get("collections")
    if not isinstance(collections, dict) or not collections:
        raise PolicyError("policy has no collections")
    families = doc.get("probe_families")
    if not isinstance(families, dict) or not families:
        raise PolicyError("policy has no probe_families")
    # Every family must declare a status this harness understands; an unknown
    # status must stop the run rather than be silently dropped from the
    # enforced and pending sets.
    for pid, fam in families.items():
        status = fam.get("status")
        if status not in ("enforced", "pending"):
            raise PolicyError(
                f"probe family {pid!r} has unknown status {status!r}; "
                f"expected 'enforced' or 'pending'"
            )
    # Every probe id a collection lists must be a declared family.
    for name, row in collections.items():
        for pid in row.get("probes", []):
            if pid not in families:
                raise PolicyError(
                    f"collection {name!r} lists undeclared probe family {pid!r}"
                )
    return doc


def enforced_pairs(doc: dict[str, Any]) -> list[tuple[str, str]]:
    """(collection, family) pairs whose family is enforced today."""
    families = doc["probe_families"]
    out = []
    for name, row in doc["collections"].items():
        for pid in row.get("probes", []):
            if families[pid].get("status") == "enforced":
                out.append((name, pid))
    return out


def pending_pairs(doc: dict[str, Any]) -> list[tuple[str, str]]:
    families = doc["probe_families"]
    out = []
    for name, row in doc["collections"].items():
        for pid in row.get("probes", []):
            if families[pid].get("status") == "pending":
                out.append((name, pid))
    return out
