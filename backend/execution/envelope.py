"""The durable result envelope, ``rounds.execution-envelope/v1``
(ROUNDS-00A-L03).

One envelope per attempt. ``complete`` in pocketbase/pb_hooks/execution.js
writes it with the attempt's and the job's terminal state in one
transaction, and refuses one that doesn't pass the same checks as
``validate`` here, so the runner never sends what the store would refuse.

Parts (cases, checkpoints, criteria) carry their own outcome class, and
``aggregate`` turns them into the envelope's:

1. Any non-authoritative part makes the envelope non-authoritative, with
   the first of ``NON_AUTHORITATIVE`` the parts carry.
2. Otherwise one ``resource-limit`` part makes it an authoritative
   ``resource-limit`` envelope that names the limit and scores null:
   ``timed-out`` for ``wall_time``, ``completed`` for any other limit.
3. Otherwise ``passed`` when every part passed, else
   ``candidate-failure``.

``channel_parts`` reads #2's fd 3 result channel: an absent or empty
channel is ``resource-limit`` when an enforced limit killed the child and
``infrastructure-degraded`` otherwise, and each id a partial channel
leaves out gets the same class.

The user view carries no hidden-harness output: a part is its id, class,
and limit, and ``output`` is the visible output a handler chose to show,
or null. The operator view adds the digests, measurements, and the
executor's kind.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from execution import kinds

ENVELOPE_VERSION = "rounds.execution-envelope/v1"
EXECUTOR_KINDS = ("legacy-in-process", "isolated-worker")
USER_VIEW_KEYS = (
    "version", "job_id", "state", "outcome_class", "authoritative", "limit", "parts", "score", "definition",
    "queued_at", "started_at", "finished_at", "cleanup", "rubric", "output",
)
OPERATOR_VIEW_KEYS = (
    "version", "executor_kind", "worker", "attempt_number", "source_checksum", "input_digest", "output_sha256",
    "output_bytes", "exit_status", "cpu_time_ms", "peak_rss_bytes", "build_revision", "image_digest", "graded_row",
)
# pb_hooks/execution.js caps each view's JSON at as many characters.
USER_VIEW_MAX_CHARS = 1024 * 1024
OPERATOR_VIEW_MAX_CHARS = 64 * 1024
# The order a disagreement between parts resolves in.
NON_AUTHORITATIVE = ("policy-violation", "definition-invalid", "canceled", "worker-lost", "infrastructure-degraded")
_STATE_FOR = {
    "policy-violation": "denied",
    "definition-invalid": "denied",
    "canceled": "canceled",
    "worker-lost": "failed",
    "infrastructure-degraded": "failed",
}


class InvalidEnvelope(ValueError):
    """A result outside rounds.execution-envelope/v1."""


@dataclass(frozen=True)
class Part:
    """One case, checkpoint, or criterion."""

    id: str
    outcome_class: str
    limit: str | None = None

    def view(self) -> dict[str, Any]:
        return {"id": self.id, "outcome_class": self.outcome_class, "limit": self.limit}


@dataclass(frozen=True)
class Outcome:
    state: str
    outcome_class: str
    authoritative: bool
    limit: str | None = None


def outcome(state: str, outcome_class: str, limit: str | None = None) -> Outcome:
    """The outcome for a terminal state and class, checked against
    ``kinds.TERMINAL``."""
    terminal = kinds.TERMINAL.get(state)
    if terminal is None or outcome_class not in terminal.classes:
        raise InvalidEnvelope(f"{state} doesn't end {outcome_class}")
    if (outcome_class == "resource-limit") != (limit is not None):
        raise InvalidEnvelope("a resource-limit names its limit, and only it does")
    if limit is not None and limit not in kinds.LIMITS:
        raise InvalidEnvelope(f"unknown limit {limit}")
    return Outcome(state, outcome_class, outcome_class in terminal.authoritative, limit)


def aggregate(parts: Sequence[Part]) -> Outcome:
    """The envelope's outcome from its parts. No parts at all means
    nothing ran, which is the infrastructure's failure."""
    if not parts:
        return outcome("failed", "infrastructure-degraded")
    classes = [part.outcome_class for part in parts]
    unknown = sorted(set(classes) - set(kinds.OUTCOME_CLASSES) - {"passed", "candidate-failure"})
    if unknown:
        raise InvalidEnvelope(f"unknown outcome class {unknown[0]}")
    for cls in NON_AUTHORITATIVE:
        if cls in classes:
            return outcome(_STATE_FOR[cls], cls)
    limited = [part for part in parts if part.outcome_class == "resource-limit"]
    if limited:
        limit = limited[0].limit
        if limit not in kinds.LIMITS:
            raise InvalidEnvelope("a resource-limit part names its limit")
        return outcome("timed-out" if limit == "wall_time" else "completed", "resource-limit", limit)
    if all(cls == "passed" for cls in classes):
        return outcome("completed", "passed")
    return outcome("completed", "candidate-failure")


def channel_parts(expected: Iterable[str], reported: Mapping[str, str] | None, killed_by: str | None) -> list[Part]:
    """Each expected part's class from the fd 3 result channel.
    ``reported`` maps each id the channel carried to ``passed`` or
    ``failed``, and is None when the channel was absent; ``killed_by`` is
    the enforced limit that killed the child, if one did."""
    if killed_by is not None and killed_by not in kinds.LIMITS:
        raise InvalidEnvelope(f"unknown limit {killed_by}")
    out: list[Part] = []
    for part_id in expected:
        result = (reported or {}).get(part_id)
        if result == "passed":
            out.append(Part(part_id, "passed"))
        elif result == "failed":
            out.append(Part(part_id, "candidate-failure"))
        elif killed_by is not None:
            out.append(Part(part_id, "resource-limit", killed_by))
        else:
            out.append(Part(part_id, "infrastructure-degraded"))
    return out


def build(
    *,
    job_id: str,
    result: Outcome,
    cleanup: str,
    worker: str,
    attempt_number: int,
    source_checksum: str,
    input_digest: str,
    queued_at: int,
    started_at: int | None,
    finished_at: int,
    parts: Sequence[Part] = (),
    score: float | None = None,
    definition: Mapping[str, Any] | None = None,
    rubric: Mapping[str, Any] | None = None,
    output: Mapping[str, Any] | None = None,
    executor_kind: str = "legacy-in-process",
    output_sha256: str | None = None,
    output_bytes: int | None = None,
    exit_status: int | None = None,
    cpu_time_ms: int | None = None,
    peak_rss_bytes: int | None = None,
    build_revision: str | None = None,
    image_digest: str | None = None,
) -> dict[str, Any]:
    """The result ``complete`` takes, checked with ``validate``."""
    envelope = {
        "state": result.state,
        "outcome_class": result.outcome_class,
        "authoritative": result.authoritative,
        "cleanup": cleanup,
        "user_view": {
            "version": ENVELOPE_VERSION,
            "job_id": job_id,
            "state": result.state,
            "outcome_class": result.outcome_class,
            "authoritative": result.authoritative,
            "limit": result.limit,
            "parts": [part.view() for part in parts],
            "score": score,
            "definition": dict(definition) if definition is not None else None,
            "queued_at": queued_at,
            "started_at": started_at,
            "finished_at": finished_at,
            "cleanup": cleanup,
            "rubric": dict(rubric) if rubric is not None else None,
            "output": dict(output) if output is not None else None,
        },
        "operator_view": {
            "version": ENVELOPE_VERSION,
            "executor_kind": executor_kind,
            "worker": worker,
            "attempt_number": attempt_number,
            "source_checksum": source_checksum,
            "input_digest": input_digest,
            "output_sha256": output_sha256,
            "output_bytes": output_bytes,
            "exit_status": exit_status,
            "cpu_time_ms": cpu_time_ms,
            "peak_rss_bytes": peak_rss_bytes,
            "build_revision": build_revision,
            "image_digest": image_digest,
            # PR 3 writes the graded row with the envelope.
            "graded_row": None,
        },
    }
    validate(envelope)
    return envelope


def _count(value: Any) -> bool:
    return value is None or (isinstance(value, int) and not isinstance(value, bool) and value >= 0)


def _within(value: Any, limit: int) -> bool:
    """Whether ``value``'s JSON fits ``limit`` characters as JavaScript
    counts them, in UTF-16 code units."""
    try:
        text = json.dumps(value, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return False
    return len(text.encode("utf-16-le", errors="surrogatepass")) // 2 <= limit


def validate(envelope: Any) -> None:
    """Raise ``InvalidEnvelope`` unless ``envelope`` is one ``complete``
    takes. The same checks as ``checkResult`` in
    pocketbase/pb_hooks/execution.js."""
    if not isinstance(envelope, dict) or set(envelope) != {
        "state", "outcome_class", "authoritative", "cleanup", "user_view", "operator_view",
    }:
        raise InvalidEnvelope("the envelope's keys")
    terminal = kinds.TERMINAL.get(envelope["state"]) if isinstance(envelope["state"], str) else None
    if terminal is None or envelope["outcome_class"] not in terminal.classes:
        raise InvalidEnvelope("the state and class")
    if envelope["authoritative"] is not (envelope["outcome_class"] in terminal.authoritative):
        raise InvalidEnvelope("authoritative")
    if envelope["cleanup"] not in kinds.CLEANUP:
        raise InvalidEnvelope("cleanup")
    user = envelope["user_view"]
    if not isinstance(user, dict) or set(user) != set(USER_VIEW_KEYS):
        raise InvalidEnvelope("the user view's keys")
    if user["version"] != ENVELOPE_VERSION:
        raise InvalidEnvelope("the user view's version")
    for key in ("state", "outcome_class", "authoritative", "cleanup"):
        if user[key] != envelope[key] or type(user[key]) is not type(envelope[key]):
            raise InvalidEnvelope(f"the user view's {key}")
    if user["limit"] is not None and user["limit"] not in kinds.LIMITS:
        raise InvalidEnvelope("the limit")
    if (envelope["outcome_class"] == "resource-limit") != (user["limit"] is not None):
        raise InvalidEnvelope("a resource-limit names its limit, and only it does")
    if not isinstance(user["parts"], list):
        raise InvalidEnvelope("parts")
    score = user["score"]
    if score is not None:
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score):
            raise InvalidEnvelope("score")
        if not 0 <= score <= 1 or envelope["outcome_class"] not in ("passed", "candidate-failure"):
            raise InvalidEnvelope("only a passed or failed solution scores")
    if not _within(user, USER_VIEW_MAX_CHARS):
        raise InvalidEnvelope("the user view isn't JSON within its size")
    operator = envelope["operator_view"]
    if not isinstance(operator, dict) or set(operator) != set(OPERATOR_VIEW_KEYS):
        raise InvalidEnvelope("the operator view's keys")
    if operator["version"] != ENVELOPE_VERSION:
        raise InvalidEnvelope("the operator view's version")
    if operator["executor_kind"] not in EXECUTOR_KINDS:
        raise InvalidEnvelope("executor_kind")
    for key in ("output_bytes", "cpu_time_ms", "peak_rss_bytes"):
        if not _count(operator[key]):
            raise InvalidEnvelope(key)
    exit_status = operator["exit_status"]
    if exit_status is not None and (isinstance(exit_status, bool) or not isinstance(exit_status, int)):
        raise InvalidEnvelope("exit_status")
    if not _within(operator, OPERATOR_VIEW_MAX_CHARS):
        raise InvalidEnvelope("the operator view isn't JSON within its size")
