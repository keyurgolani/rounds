"""A grading result's rubric review (ROUNDS-00A-L03 PR 3).

Two routes ask an AI provider to review a graded result against its
definition's rubric, at most once per result: the grade's,
``POST /api/ai-coding/grade/{job}/review``, and the submission's,
``POST /api/take-home/submit/{job}/review``. Admission runs steps 1 to 4 for both, behind the grading key
(``on`` only); the review's own charge is the store's. In order:

1. The account's own grading job of the route's kind, read with
   ``status``: another account's job, an unknown id, a malformed one, and a
   job of another kind are the same 404 ``not_found``. A job that didn't end
   with an authoritative result can't be reviewed (``not_reviewable``).
2. The rubric of the version that graded it, by the envelope's receipt,
   and the account's provider settings: PocketBase reads and the address
   check, never a provider call. Without a provider the answer says so,
   and nothing is charged or marked (``no_provider``).
3. ``review_start``, one store transaction: the files the caller resent
   have to be the ones that ran (``files_changed`` otherwise), and a
   result with no review yet gets its admission command (one request, no
   wall seconds, a lease for the call) and its rubric marked
   ``requested``, both or neither. Only then does the runner call the
   provider. A review already asked for answers where it stands:
   ``requested`` and still live is 409 ``already_in_flight``; ``completed``
   or ``lost`` is answered as it is.
4. The provider call, held to ``REVIEW_TIMEOUT_S``, with the rubric, the
   files, the server's outcomes, and the chats the graded row holds.
5. ``review_finish``: the review into the graded row and the rubric
   ``completed``, while the lease is live. A provider failure completes with
   a skipped review and a fixed sentence, and that result is never reviewed
   again; a finish too late leaves it ``lost`` (until #74 stages provider
   outcomes).

Every answer is ``{job_id, rubric_state, rubric_review, unavailable}``.
``rubric_review`` is the review this call wrote, else null (the graded row
holds it). Nothing here logs the files, the prompt, or what the provider
answered: ``execution.review`` lines carry the kind and a coarse code.
"""
from __future__ import annotations

import logging
import math
import re
from typing import Any, Mapping

import anyio
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

from ai_coding.rubric import REVIEW_TIMEOUT_S, SYSTEM_PROMPT, build_prompt, parse_ai_output
from app import admission, admission_state, definitions, gates, obs
from app.errors import TypedError
from execution import jobs, store

_log = logging.getLogger(__name__)

JOB_ID = re.compile(r"[a-z0-9]{15}")
# The fixed sentences a skipped review keeps, never a provider's own text.
PROVIDER_FAILED = "The review didn't finish, so this submission has no review."
UNREADABLE = "The review's answer couldn't be read, so this submission has no review."
# What a review keeps of the provider's answer, and how much of it.
_ITEMS_MAX = 64
_TEXT_MAX = 2000
_QUOTES_MAX = 20
_SUGGESTIONS_MAX = 10


def _emit(request: Request, kind: str, code: str) -> None:
    obs.emit("execution.review", correlation_id=obs.current_correlation_id(), kind=kind, code=code,
             service="runner")


def _answer(job_id: str, state: str | None, review: dict[str, Any] | None = None,
            unavailable: str | None = None) -> JSONResponse:
    return JSONResponse({"job_id": job_id, "rubric_state": state, "rubric_review": review,
                         "unavailable": unavailable})


def _unit(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, number)) if math.isfinite(number) else 0.0


def _text(value: Any, limit: int = _TEXT_MAX) -> str:
    return value[:limit] if isinstance(value, str) else ""


def normalized(parsed: Any) -> dict[str, Any]:
    """The review a graded row keeps of a provider's parsed answer: each
    item's id, score, evidence, quoted lines, and suggestions, and the
    total, each held to its type and size. An answer that couldn't be read
    keeps a fixed sentence instead."""
    if not isinstance(parsed, dict) or not isinstance(parsed.get("items"), list) or "parse_error" in parsed:
        return {"items": [], "total": 0.0, "skipped": True, "reason": UNREADABLE}
    items = []
    for raw in parsed["items"][:_ITEMS_MAX]:
        if not isinstance(raw, dict):
            continue
        quotes = []
        for quote in (raw.get("evidence_quotes") or [])[:_QUOTES_MAX]:
            if isinstance(quote, dict) and isinstance(quote.get("line"), int) and not isinstance(quote.get("line"), bool):
                quotes.append({"file": _text(quote.get("file"), 255), "line": quote["line"],
                               "quote": _text(quote.get("quote"), 300)})
        suggestions = [_text(s, 500) for s in (raw.get("suggestions") or [])[:_SUGGESTIONS_MAX] if isinstance(s, str)]
        items.append({"id": _text(raw.get("id"), 64), "score": _unit(raw.get("score")),
                      "evidence": _text(raw.get("evidence")), "evidence_quotes": quotes, "suggestions": suggestions})
    return {"items": items, "total": _unit(parsed.get("total"))}


def _reviewable(found: store.JobStatus, kind: str) -> bool:
    envelope = found.envelope
    return (
        found.job.kind == kind
        and isinstance(envelope, dict)
        and envelope.get("authoritative") is True
        and isinstance(envelope.get("definition"), dict)
    )


async def _call(cfg: Mapping[str, Any], rubric: Any, files: Mapping[str, str],
                material: Mapping[str, Any]) -> dict[str, Any]:
    """The provider's review, normalized; a skipped one when the call
    failed or ran out of time."""
    # Imported here: the AI router imports the admission chain, which this
    # module's callers import first.
    from routers.ai import _call_complete

    results = material["results"]
    if material["kind"] == "grade":
        test_results = {str(entry.get("index", i)): entry for i, entry in enumerate(results) if isinstance(entry, dict)}
    else:
        test_results = {"harness": {k: results.get(k) for k in ("score", "passed", "outcomes", "outcome_class")}}
    prompt = build_prompt(rubric=rubric if isinstance(rubric, dict) else {"items": []}, files=dict(files),
                          test_results=test_results, ai_chats=list(material["ai_chats"]))
    try:
        with anyio.fail_after(REVIEW_TIMEOUT_S):
            raw = await _call_complete(
                cfg["kind"], cfg["model"], cfg["api_key"], cfg["base_url"] or None,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1500,
                destination=cfg.get("destination"),
            )
    except Exception:  # noqa: BLE001
        # The provider's own text stays out of the row and the log.
        return {"items": [], "total": 0.0, "skipped": True, "reason": PROVIDER_FAILED}
    return normalized(parse_ai_output(raw))


async def review(request: Request, job_id: str, files: Mapping[str, str], kind: str) -> JSONResponse:
    """The review route for grading ``kind``; see the module docstring."""
    user = admission.account(request)
    if user is None:
        # Only an admitted request reaches here.
        raise TypedError("unauthenticated")
    if not JOB_ID.fullmatch(job_id):
        raise TypedError("not_found")
    key = admission_state.command_id(request.scope.get("headers") or [])
    if key is None:
        raise TypedError("idempotency_key_required")
    try:
        async with store.Caller(user["token"]) as caller:
            found = await caller.status(job_id)
            if found is None or found.job.kind != kind:
                raise TypedError("not_found")
            if not _reviewable(found, kind):
                _emit(request, kind, "not_reviewable")
                return _answer(job_id, None, unavailable="not_reviewable")
            try:
                document = definitions.store().pinned(found.envelope["definition"])
            except TypedError:
                _emit(request, kind, "not_reviewable")
                return _answer(job_id, None, unavailable="not_reviewable")
            try:
                # Imported here, as in _call.
                from routers.ai import _active_text_config

                cfg = await _active_text_config(user)
            except HTTPException as err:
                if isinstance(err, TypedError):
                    raise
                _emit(request, kind, "no_provider")
                return _answer(job_id, (found.envelope.get("rubric") or {}).get("state"), unavailable="no_provider")
            lease = admission_state.new_lease()
            started = await caller.review_start(job_id, jobs.digest(dict(files)), key,
                                                admission_state.lease_hash(lease), gates.value("ENFORCE_QUOTA"))
            if started is None:
                raise TypedError("not_found")
            if started.state != "requested":
                _emit(request, kind, started.state)
                return _answer(job_id, started.state)
            _emit(request, kind, "requested")
            written = await _call(cfg, document.get("rubric"), files, started.material)
            try:
                state = await caller.review_finish(job_id, lease, written)
            except store.Superseded:
                _emit(request, kind, "lost")
                return _answer(job_id, "lost")
            _emit(request, kind, "provider_failed" if written.get("skipped") else "completed")
            return _answer(job_id, state, review=written)
    except store.ReviewRefused as refused:
        _emit(request, kind, refused.code)
        if refused.code == "in_flight":
            raise TypedError("already_in_flight", retry_after=5) from None
        if refused.code == "mismatch":
            raise TypedError("idempotency_mismatch") from None
        return _answer(job_id, None, unavailable=refused.code)
    except store.ReviewOverQuota as over:
        _emit(request, kind, "quota_exceeded")
        code = "demo_limit_reached" if over.quota == "demo_limit" else "quota_exceeded"
        raise TypedError(code, retry_after=over.retry_after) from None
    except store.Unavailable:
        _emit(request, kind, "worker_unavailable")
        raise TypedError("worker_unavailable") from None
