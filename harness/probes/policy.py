"""Load and validate the account-scope policy contract.

The harness refuses to run against an unknown policy version before it
touches anything (acceptance criterion: "the harness rejects an unknown
policy version before either changes anything").
"""
from __future__ import annotations

import datetime
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
    validate_cases(doc.get("cases"), families)
    return doc


# The case table (ROUNDS-00B-L05): rows that aren't one family on one
# collection, such as runner routes, realtime, logs, and surfaces that have no
# server yet. A row this suite proves itself carries its own id as its
# receipts' probe id; a row an existing check already proves names that check
# in `evidence` instead of repeating it.
CASE_STATUSES = ("pass", "pending", "quarantined", "slot")
CASE_SURFACES = ("pb:", "realtime:", "runner:", "share:", "nginx:", "logs:")
CASE_EXPECTED = ("allow", "uniform_not_found", "uniform_reject", "unauthenticated", "not_routed")
CASE_LANES = ("pr",)
CASE_LEAF = "ROUNDS-00B-L05"
# A phase whose own exit code is the evidence (the launcher fails the run when
# it fails); these phases print checks rather than write receipts.
EVIDENCE_PHASES = ("demo-on", "demo-off")
# A quarantined row is a flake with an owner, and comes back within this long.
QUARANTINE_MAX_DAYS = 14
_REQUIRED_CASE_KEYS = ("surface", "actor", "expected", "control", "owner_leaf", "status", "lane", "guarantee")


def _iso_date(value: Any, where: str) -> datetime.date:
    if not isinstance(value, str):
        raise PolicyError(f"{where} must be an ISO date string")
    try:
        return datetime.date.fromisoformat(value)
    except ValueError:
        raise PolicyError(f"{where} is not an ISO date: {value!r}") from None


def validate_cases(cases: Any, families: dict[str, Any] | None = None) -> None:
    """Refuse a case table this harness can't decide on.

    A `pass` row names its evidence. `pending` and `slot` rows name the leaf
    that closes them and carry no evidence, so nothing can prove them by
    accident. A `quarantined` row names an owner and expires at most 14 days
    after it was quarantined.
    """
    if cases is None:
        return
    if not isinstance(cases, dict):
        raise PolicyError("cases must be an object keyed by case id")
    for cid, row in cases.items():
        if not isinstance(row, dict):
            raise PolicyError(f"case {cid!r} is not an object")
        missing = [k for k in _REQUIRED_CASE_KEYS if not row.get(k)]
        if missing:
            raise PolicyError(f"case {cid!r} is missing {', '.join(missing)}")
        status = row["status"]
        if status not in CASE_STATUSES:
            raise PolicyError(f"case {cid!r} has unknown status {status!r}")
        if not str(row["surface"]).startswith(CASE_SURFACES):
            raise PolicyError(f"case {cid!r} has unknown surface {row['surface']!r}")
        if row["expected"] not in CASE_EXPECTED:
            raise PolicyError(f"case {cid!r} has unknown expected outcome {row['expected']!r}")
        if row["lane"] not in CASE_LANES:
            raise PolicyError(f"case {cid!r} has unknown lane {row['lane']!r}")
        evidence = row.get("evidence", [])
        if not isinstance(evidence, list) or not all(isinstance(e, str) and e for e in evidence):
            raise PolicyError(f"case {cid!r} evidence must be a list of check ids")
        for e in evidence:
            if e.startswith("phase:") and e[len("phase:"):] not in EVIDENCE_PHASES:
                raise PolicyError(f"case {cid!r} names unknown evidence phase {e!r}")
        if status == "pass" and not evidence:
            raise PolicyError(f"case {cid!r} is pass but names no evidence")
        if status in ("pending", "slot"):
            if evidence:
                raise PolicyError(f"case {cid!r} is {status} and must carry no evidence")
            if row["owner_leaf"] == CASE_LEAF:
                raise PolicyError(f"case {cid!r} is {status} and must name the leaf that closes it")
        if status == "quarantined":
            if not row.get("quarantined_on") or not row.get("expires"):
                raise PolicyError(f"case {cid!r} is quarantined without quarantined_on and expires")
            start = _iso_date(row["quarantined_on"], f"case {cid!r} quarantined_on")
            end = _iso_date(row["expires"], f"case {cid!r} expires")
            if end < start or (end - start).days > QUARANTINE_MAX_DAYS:
                raise PolicyError(f"case {cid!r} quarantine must expire within {QUARANTINE_MAX_DAYS} days")
            if not evidence:
                raise PolicyError(f"case {cid!r} is quarantined but names no evidence")
        elif "expires" in row:
            _iso_date(row["expires"], f"case {cid!r} expires")
        if families is not None:
            for e in evidence:
                if e in families and families[e].get("status") != "enforced":
                    raise PolicyError(f"case {cid!r} names pending family {e!r} as evidence")


def cases_by_status(doc: dict[str, Any], status: str) -> dict[str, dict[str, Any]]:
    return {cid: row for cid, row in (doc.get("cases") or {}).items() if row["status"] == status}


def expired_cases(doc: dict[str, Any], today: datetime.date) -> list[str]:
    """Rows whose expiry is before `today`."""
    return sorted(cid for cid, row in (doc.get("cases") or {}).items()
                  if "expires" in row and _iso_date(row["expires"], cid) < today)


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
