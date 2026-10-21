"""Shared result type and helpers for the fixtures.

A fixture returns a :class:`Result`: an outcome per contained sub-case it
checked (the manifest lists them), the named text artifacts it wants
retained (the plugin redacts and checksums them), the text to scan for
canary hits, and a note. A fixture never writes a receipt or an artifact
itself; the plugin does, so redaction and the receipt schema stay in one
place. The fixture's overall outcome is its worst sub-case outcome.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from conformance.outcomes import Outcome

# Worst first: one detecting sub-case makes the fixture detect.
_SEVERITY = [Outcome.DETECTED.value, Outcome.INCONCLUSIVE.value, Outcome.NOT_APPLICABLE.value, Outcome.CONTAINED.value]


@dataclass
class Result:
    subcases: dict[str, str]
    legacy_classified: bool = True
    evidence: dict[str, str] = field(default_factory=dict)
    canary_text: str = ""
    note: str = ""

    @property
    def outcome(self) -> str:
        if not self.subcases:
            return Outcome.INCONCLUSIVE.value
        return min(self.subcases.values(), key=_SEVERITY.index)


def result(subcases: dict[str, str], note: str = "", *, evidence: dict[str, str] | None = None,
           canary_text: str = "") -> Result:
    return Result(dict(subcases), True, evidence or {}, canary_text, note)


def contained(subcase: str, note: str = "", **kwargs) -> Result:
    return result({subcase: Outcome.CONTAINED.value}, note, **kwargs)


def detected(subcase: str, note: str, **kwargs) -> Result:
    return result({subcase: Outcome.DETECTED.value}, note, **kwargs)


def inconclusive(subcase: str, note: str, **kwargs) -> Result:
    return result({subcase: Outcome.INCONCLUSIVE.value}, note, **kwargs)


def code_of(body) -> str | None:
    """The typed envelope's ``code``, or None for any other body."""
    return body.get("code") if isinstance(body, dict) else None
