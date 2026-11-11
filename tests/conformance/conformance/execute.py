"""Running one fixture and turning its result into a receipt entry.

``run_fixture`` is what the live plugin (``test_corpus.py``) calls for
each fixture, and what the self-tests call with fake targets, so the
rules are tested where they are applied:

- the fixture runs under its budget and a deadline; a fixture that raises,
  runs out of budget, or runs past its deadline is ``inconclusive``;
- every contained sub-case the manifest lists needs an outcome from the
  fixture (one it skipped is ``inconclusive``), and an outcome for a
  sub-case the manifest doesn't list fails; pending sub-cases are
  recorded as pending with their closing leaf;
- a row with no contained sub-case (a ``not-applicable`` row) reports one
  outcome for the whole fixture, and passes only as ``not-applicable``;
- whatever the fixture hands back is read as text, so a result in the
  wrong shape is a recorded failure, never an exception that leaves the
  fixture without a receipt entry;
- any problem makes a ``contained`` or ``not-applicable`` outcome
  ``inconclusive``, so a receipt never states either beside a failing
  verdict;
- any canary in what the fixture saw fails it, whatever the fixture
  concluded;
- every route the manifest lists for the fixture must be one it exercised;
- the kept evidence is redacted, capped, and checksummed, and a canary
  that survives redaction fails the run;
- a failed teardown fails the fixture;
- the verdict is the strict comparison with the manifest's expectation.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .budget import Budget, deadline
from .canaries import CanarySet
from .outcomes import Outcome, decide
from .receipts import FixtureReceipt, cap_evidence, checksum
from .redaction import clean, redact

DEFAULT_MAX_REQUESTS = 25
DEFAULT_MAX_WALL_SECONDS = 120.0
DEFAULT_DEADLINE_SECONDS = 180.0

_WORST = [Outcome.DETECTED.value, Outcome.INCONCLUSIVE.value, Outcome.NOT_APPLICABLE.value, Outcome.CONTAINED.value]
_OUTCOMES = frozenset(_WORST)
# The outcomes that meet an expectation; a problem turns either
# inconclusive, so a receipt never states one beside a failing verdict.
_MET = frozenset({Outcome.CONTAINED.value, Outcome.NOT_APPLICABLE.value})
# The live run's case per fixture (test_corpus.py).
FIXTURE_CASE = "::test_fixture["


@dataclass
class Ran:
    receipt: FixtureReceipt
    passed: bool
    message: str


def _worst(outcomes: list[str]) -> str:
    return min(outcomes, key=_WORST.index) if outcomes else Outcome.INCONCLUSIVE.value


def _text(value: Any) -> str:
    """What a fixture handed back, as text whatever its type."""
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    try:
        return json.dumps(value, sort_keys=True, default=str)
    except (TypeError, ValueError):
        return repr(value)


def _outcome(value: Any, what: str, problems: list[str]) -> str:
    if isinstance(value, str) and value in _OUTCOMES:
        return value
    problems.append(f"{what}: not an outcome")
    return Outcome.INCONCLUSIVE.value


def fixtures_decided(reports: Iterable[Any]) -> int:
    """How many fixture cases a live run passed or failed, from pytest's
    reports. The receipt-coverage case is bookkeeping, not a fixture, so
    it never counts: a run whose every fixture was skipped decided none."""
    return sum(1 for r in reports if FIXTURE_CASE in getattr(r, "nodeid", ""))


def run_fixture(
    fx,
    module,
    make_context: Callable[[Budget], Any],
    canaries: CanarySet,
    target: str,
    *,
    max_requests: int = DEFAULT_MAX_REQUESTS,
    max_wall_seconds: float = DEFAULT_MAX_WALL_SECONDS,
    deadline_seconds: float = DEFAULT_DEADLINE_SECONDS,
) -> Ran:
    budget = Budget(max_requests, max_wall_seconds)
    ctx = make_context(budget)
    canary_values = list(canaries.present_values().values())
    problems: list[str] = []

    result = None
    try:
        with deadline(deadline_seconds):
            result = module.run(ctx)
    except Exception as err:  # the fixture failed to decide
        problems.append(f"{type(err).__name__}: {err}")
    finally:
        failed_teardown = ctx.teardown()
    if failed_teardown:
        problems.append(f"teardown left accounts behind: {len(failed_teardown)}")

    # Read as text whatever the fixture handed back, so a result in the
    # wrong shape is a recorded problem, not an exception.
    raw_subcases = getattr(result, "subcases", None) or {}
    raw_evidence = getattr(result, "evidence", None) or {}
    if not isinstance(raw_subcases, dict):
        problems.append("sub-case outcomes aren't a mapping")
        raw_subcases = {}
    if not isinstance(raw_evidence, dict):
        problems.append("evidence isn't a mapping")
        raw_evidence = {"evidence": raw_evidence}
    subcase_outcomes = {_text(k): _outcome(v, f"sub-case {_text(k)}", problems) for k, v in raw_subcases.items()}
    evidence_raw = {_text(k): _text(v) for k, v in raw_evidence.items()}
    seen = "\n".join([_text(getattr(result, "canary_text", ""))] + list(evidence_raw.values()))
    note = redact(_text(getattr(result, "note", "")), canary_values)

    # Sub-cases: each contained one needs an outcome; unknown ones fail.
    listed = {s.id for s in fx.subcases}
    unknown = sorted(set(subcase_outcomes) - listed)
    if unknown:
        problems.append("outcomes for sub-cases the manifest doesn't list: " + ", ".join(unknown))
    entries: list[dict[str, Any]] = []
    contained_outcomes: list[str] = []
    for sub in fx.subcases:
        if sub.status == "pending":
            entries.append({"id": sub.id, "status": "pending", "closing_leaf": sub.closing_leaf})
            continue
        got = subcase_outcomes.get(sub.id, Outcome.INCONCLUSIVE.value)
        if sub.id not in subcase_outcomes:
            problems.append(f"no outcome for {sub.id}")
        contained_outcomes.append(got)
        entries.append({"id": sub.id, "status": "contained", "closing_leaf": sub.closing_leaf, "outcome": got})

    if fx.contained_subcases():
        observed = _worst(contained_outcomes)
    else:
        # No contained sub-case: the fixture reports one outcome for the
        # whole row, which a not-applicable row meets as not-applicable.
        overall = getattr(result, "overall", None)
        if result is not None and overall is None:
            problems.append("no outcome for the fixture")
        observed = Outcome.INCONCLUSIVE.value if overall is None else _outcome(overall, "the fixture", problems)

    # Any canary in what the fixture saw is a finding, whatever it decided.
    hits = canaries.hits(seen)
    hit_names = sorted(name for name, hit in hits.items() if hit)
    if hit_names:
        observed = Outcome.DETECTED.value
        problems.append("canary seen: " + ", ".join(hit_names))

    # The routes the manifest lists must be ones the fixture exercised.
    exercised = list(ctx.log.routes)
    unexercised = [route for route in fx.routes if route not in exercised]
    if unexercised:
        problems.append("listed routes not exercised: " + ", ".join(unexercised))

    evidence = {}
    sums = {}
    for name, text in cap_evidence({k: redact(v, canary_values) for k, v in evidence_raw.items()}).items():
        if not clean(text, canary_values):
            # Kept out of the receipt, and the run fails with its entry.
            problems.append(f"a canary survived redaction of {name}")
            text = "<withheld: a canary survived redaction>"
        evidence[name] = text
        sums[name] = checksum(text)

    if problems and observed in _MET:
        observed = Outcome.INCONCLUSIVE.value
    expectation = fx.expectation(target)
    verdict = decide(observed, expectation)
    passed = verdict.passed and not problems

    reason = redact("; ".join(problems) or verdict.reason, canary_values)
    receipt = FixtureReceipt(
        id=fx.id,
        status="ran",
        closing_leaf=fx.closing_leaf,
        target=target,
        outcome=verdict.outcome if not hit_names else Outcome.DETECTED.value,
        expectation=expectation,
        verdict="pass" if passed else "fail",
        legacy_classified=bool(getattr(result, "legacy_classified", False)),
        subcases=entries,
        routes=exercised,
        evidence=evidence,
        checksums=sums,
        canary_hits=hits,
        budget=budget.snapshot(),
        reason=reason,
        note=note,
    )
    message = f"{fx.id} [{target}]: {receipt.outcome}"
    if reason:
        message += f"; {reason}"
    if note:
        message += f"; note: {note}"
    if evidence and not passed:
        message += "; evidence: " + " | ".join(f"{k}={v[:500]}" for k, v in evidence.items())
    return Ran(receipt, passed, message)


def quarantined(fx, skip, target: str) -> FixtureReceipt:
    """The receipt entry for a fixture the skip ledger quarantines."""
    return FixtureReceipt(
        id=fx.id,
        status="quarantined",
        closing_leaf=fx.closing_leaf,
        target=target,
        expectation=fx.expectation(target),
        quarantine={"owner": skip.owner, "expiry": skip.expiry.isoformat(), "reason": skip.reason},
        note=f"quarantined until {skip.expiry.isoformat()} ({skip.owner})",
    )
