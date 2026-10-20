"""Scores a checkpoint from its result channel (ROUNDS-00A-L02).

A harness revision's grade driver writes one ``{id, outcome, reason}``
JSON line per result on fd 3 (``backend/definitions/harness/
rounds_harness.py``). ``score`` reads those bytes against the checkpoint's
expected results, which come from the server-owned revision, never from
the channel, and the server computes ``passed`` and ``score`` itself:

- A line that isn't exactly ``{id, outcome, reason}`` with an expected
  id, a known outcome and reason, and ``passed`` only with ``ok``, or an
  id reported twice, or a channel over ``CHANNEL_MAX_BYTES``, makes the
  whole channel malformed: every result is ``not-run`` with
  ``bad-result``.
- An expected id that isn't reported is ``not-run`` with ``no-result``.
  It never passes.
- ``passed`` needs every expected result passed and at least
  ``min_executed`` of them executed (passed or failed).
- ``score`` is the passed results' share of the weights, clamped to 0 to
  1, and 0 when fewer than ``min_executed`` executed.

TODO(ROUNDS-00A-L02): step 2's grade and take-home routes score through
this at ``ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce``; until then only the
tests call it. TODO(ROUNDS-00A-L03): #3 classes ``not-run`` results.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Sequence

OUTCOMES = ("passed", "failed", "not-run")
REASONS = ("ok", "assertion", "exception", "timeout", "no-result", "bad-result")
EXECUTED = frozenset({"passed", "failed"})
# 64 results at well under 1 KiB a line.
CHANNEL_MAX_BYTES = 64 * 1024
LINE_KEYS = frozenset({"id", "outcome", "reason"})


@dataclass(frozen=True)
class Result:
    id: str
    outcome: str
    reason: str


@dataclass(frozen=True)
class Score:
    results: tuple[Result, ...]
    executed: int
    passed: bool
    score: float
    malformed: bool

    def outcomes(self) -> list[dict[str, str]]:
        """The per-id outcomes a response may carry."""
        return [{"id": r.id, "outcome": r.outcome, "reason": r.reason} for r in self.results]


def _parse(channel: bytes, expected_ids: frozenset[str]) -> dict[str, Result] | None:
    """The reported results by id, or None when the channel is malformed."""
    if len(channel) > CHANNEL_MAX_BYTES:
        return None
    try:
        text = channel.decode("utf-8")
    except UnicodeDecodeError:
        return None
    reported: dict[str, Result] = {}
    for line in text.split("\n"):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except ValueError:
            return None
        if not isinstance(item, dict) or set(item) != LINE_KEYS:
            return None
        rid, outcome, reason = item["id"], item["outcome"], item["reason"]
        if not isinstance(rid, str) or rid not in expected_ids or rid in reported:
            return None
        if outcome not in OUTCOMES or reason not in REASONS:
            return None
        if (outcome == "passed") != (reason == "ok"):
            return None
        reported[rid] = Result(rid, outcome, reason)
    return reported


def score(channel: bytes, expected: Sequence[dict[str, Any]], min_executed: int) -> Score:
    """Scores ``channel`` against a checkpoint's ``results`` and
    ``min_executed`` from its harness revision."""
    ids = [str(r["id"]) for r in expected]
    weights = {str(r["id"]): float(r["weight"]) for r in expected}
    reported = _parse(channel, frozenset(ids))
    malformed = reported is None
    results = tuple(
        Result(rid, "not-run", "bad-result") if reported is None
        else reported.get(rid, Result(rid, "not-run", "no-result"))
        for rid in ids
    )
    executed = sum(1 for r in results if r.outcome in EXECUTED)
    enough = bool(ids) and executed >= max(1, min_executed)
    passed = enough and all(r.outcome == "passed" for r in results)
    total = sum(weights.values())
    if not enough:
        value = 0.0
    elif total > 0:
        value = sum(weights[r.id] for r in results if r.outcome == "passed") / total
    else:
        value = sum(1 for r in results if r.outcome == "passed") / len(results)
    if not math.isfinite(value):
        value = 0.0
    return Score(results, executed, passed, min(1.0, max(0.0, value)), malformed)
