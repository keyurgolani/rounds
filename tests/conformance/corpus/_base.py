"""Shared result type and helpers for the fixtures.

A fixture returns a :class:`Result`: the outcome class it reached, the
named text artifacts it wants retained (redacted and checksummed by the
plugin), the text to scan for canary hits, and whether it had to classify
the outcome without #3's typed result classes. A fixture never writes a
receipt or an artifact itself; the plugin does that so redaction and the
receipt schema stay in one place.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from conformance.outcomes import Outcome


@dataclass
class Result:
    outcome: str
    legacy_classified: bool = True
    evidence: dict[str, str] = field(default_factory=dict)
    canary_text: str = ""
    note: str = ""


def contained(note: str = "", *, evidence: dict[str, str] | None = None, canary_text: str = "") -> Result:
    return Result(Outcome.CONTAINED.value, True, evidence or {}, canary_text, note)


def detected(note: str, *, evidence: dict[str, str] | None = None, canary_text: str = "") -> Result:
    return Result(Outcome.DETECTED.value, True, evidence or {}, canary_text, note)


def inconclusive(note: str) -> Result:
    return Result(Outcome.INCONCLUSIVE.value, False, {}, "", note)
