"""Outcome vocabulary and comparison for the containment corpus.

A fixture reports one outcome class for one (sub-case, target). The
plugin compares it with the manifest's expectation and decides the
verdict. Until #3's typed result classes land, the plugin classifies a
result from the HTTP status and the request timing and marks it
``legacy-classified``; the outcome vocabulary here is stable across that
change.

Outcomes
--------
``contained``       the guarantee held: the hostile request was denied,
                    refused, or answered without leaking. This is the
                    expected outcome on the branch under test for every
                    committed fixture.
``detected``        the guarantee did not hold: a containment regression.
                    Never expected on this branch; a fixture that detects
                    fails the lane with its id and redacted artifacts.
``not-applicable``  the surface the sub-case targets does not exist on
                    this branch yet, so there is nothing to contain. Needs
                    a manifest reason; never a skip. An outcome of its
                    own: a not-applicable row (or target) passes only by
                    answering not-applicable, and is recorded so. Runs as
                    ``contained`` once its surface lands.
``inconclusive``    the run could not decide: infrastructure degraded, a
                    worker was lost, a runtime was missing, nothing was
                    collected, or everything was skipped. Fails the lane.

A ``pending`` manifest row carries no fixture and is never run, so it has
no outcome; the plugin records it in the receipt as ``pending`` with the
closing leaf.

Verdict
-------
The verdict wraps the outcome for #7's receipt: a met expectation is
``pass`` and records the outcome it met, ``contained`` or
``not-applicable``; an unmet one is ``fail`` and records ``detected``.
``inconclusive`` is always ``fail``.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    CONTAINED = "contained"
    DETECTED = "detected"
    NOT_APPLICABLE = "not-applicable"
    INCONCLUSIVE = "inconclusive"


# The expectation a manifest row can declare for a runnable fixture.
EXPECTATIONS = frozenset({Outcome.CONTAINED.value, Outcome.NOT_APPLICABLE.value})

# Interactive routes allow the limit plus 2 s; take-home routes plus 5 s
# (#8 body, Data and API contracts). Used by the timing classifier until
# #3's typed classes arrive.
TIMING_SLACK_S = {"interactive": 2.0, "take-home": 5.0}


@dataclass(frozen=True)
class Verdict:
    outcome: str
    verdict: str  # "pass" or "fail"
    legacy_classified: bool
    reason: str = ""

    @property
    def passed(self) -> bool:
        return self.verdict == "pass"


def classify_denial(status: int) -> bool:
    """Whether an HTTP status is a containment denial rather than a
    request that was allowed to run. Any 4xx or the typed 503 refusals
    are denials; a 2xx is not. Used by fixtures that assert a hostile
    request never reaches execution."""
    return 400 <= status < 500 or status == 503


def decide(observed: str, expected: str) -> Verdict:
    """Compare an observed outcome with the manifest expectation.

    ``expected`` is ``contained`` or ``not-applicable``. The observed
    outcome is one of the :class:`Outcome` values. The result is the
    receipt verdict, with ``legacy_classified`` set whenever the observed
    outcome was derived without #3's typed classes (the caller passes
    that through from the fixture).
    """
    if observed not in {o.value for o in Outcome}:
        raise ValueError(f"unknown outcome {observed!r}")
    if expected not in EXPECTATIONS:
        raise ValueError(f"unknown expectation {expected!r}")
    if observed == Outcome.INCONCLUSIVE.value:
        return Verdict(Outcome.INCONCLUSIVE.value, "fail", False, "run could not decide")
    if observed == expected:
        # A met expectation is recorded as what it met: contained, or
        # not-applicable for a surface that is absent as expected.
        return Verdict(observed, "pass", False)
    if observed == Outcome.DETECTED.value:
        return Verdict(Outcome.DETECTED.value, "fail", False, "containment regression")
    # Any other mismatch (e.g. a surface expected absent that answered, or
    # a contained expectation that came back not-applicable) is a finding.
    return Verdict(
        Outcome.DETECTED.value,
        "fail",
        False,
        f"expected {expected}, observed {observed}",
    )
