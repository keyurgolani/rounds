"""The job kinds' handlers (ROUNDS-00A-L03 PRs 2 and 3).

``run``, ``evaluate``, ``run_project``, and ``take_home_run`` (PR 2), and
``grade`` and ``take_home_submit`` (PR 3), each run what their route runs
at ``ROUNDS_GATE_EXECUTION_DEFINITIONS=enforce``, in the slot the worker
claimed, from the job alone:

1. ``prepare``, before the job takes a slot: its key (scratch or grading)
   has to be on, or the job ends ``canceled``; and its input has to pass
   the route's own request model and its pinned definition resolve from
   the compiled store in the image (never PocketBase, never the caller's
   token), or it ends ``denied``, ``definition-invalid``. Either way
   nothing started.
2. ``budget_s``: the attempt's wall budget, what its route was admitted
   for.
3. ``run``: the parts, the output the route would have answered, fitted
   to the envelope's 256 KiB, and the definition's receipt. A cancel stops
   the process in flight, and the next case never starts.

Each part's class: ``passed``, ``candidate-failure``, ``resource-limit``
``wall_time``, or ``definition-invalid`` when the run couldn't start. A
take-home run's results read as ``envelope.harness_parts`` reads #2's fd 3
channel, and so do a grade's and a take-home submission's. Scratch
envelopes carry no score; a grading envelope carries the server's, only on
an end the run earned, and its graded row's content goes with it
(``Result.graded``). Cleanup is ``confirmed`` only once every run's
scratch directory is gone and its process group is empty.
"""
from __future__ import annotations

import hashlib
import os
import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Sequence

from pydantic import BaseModel, ValidationError

import runner as snippets
from app import definitions, execution as definition_runs, sandbox
from app.errors import TypedError
from execution import envelope, jobs, keys, kinds
from execution.envelope import Part
from execution.executor import LegacyExecutor, Observation
from execution.worker import InvalidJob, Result, Withdrawn
from routers import ai_coding, runner as coding, take_home
from schemas import CodeRunResult, DefinitionEvaluateRequest, DefinitionRunRequest

# How many prepared jobs a handler keeps until they run.
PLANS_KEPT = 64


@dataclass
class Plan:
    """What a job runs, checked once in ``prepare``."""

    request: BaseModel
    resolved: definitions.Resolved
    extra: dict[str, Any] = field(default_factory=dict)


def cleanup_of(controls: Sequence[sandbox.Control]) -> str:
    """``confirmed`` once every run that started has its scratch directory
    gone and its process group empty, ``unconfirmed`` otherwise."""
    for control in controls:
        if control.cwd is not None and os.path.exists(control.cwd):
            return "unconfirmed"
        if control.pid is not None and not sandbox.group_gone(control.pid):
            return "unconfirmed"
    return "confirmed"


def observation(job_id: str, controls: Sequence[sandbox.Control], texts: Sequence[str],
                exit_status: int | None = None) -> Observation:
    """The operator view's measurements of the visible output, and the
    cleanup state."""
    data = "\x00".join(texts).encode("utf-8", errors="surrogatepass")
    return Observation(
        run_id=job_id, exit_status=exit_status, stdout="", stderr="", truncated=False, output_bytes=len(data),
        output_sha256=hashlib.sha256(data).hexdigest(), wall_ms=0, limit=None, canceled=False,
        cleanup=cleanup_of(controls),
    )


def snippet_part(part_id: str, outcome: snippets.ExecutionOutcome, control: sandbox.Control) -> Part:
    """One snippet run's class. A run that ended before a process started
    (a driver or entry the definition got wrong) is the definition's."""
    if outcome.timed_out:
        return Part(part_id, "resource-limit", "wall_time")
    if outcome.error is not None and control.pid is None:
        return Part(part_id, "definition-invalid")
    return Part(part_id, "candidate-failure" if outcome.error is not None else "passed")


class _Scratch:
    kind: str
    track: str
    model: type[BaseModel]

    def __init__(self) -> None:
        self._plans: OrderedDict[str, Plan] = OrderedDict()
        self._lock = threading.Lock()

    # -- the plan ----------------------------------------------------------

    def check(self, request: BaseModel, resolved: definitions.Resolved) -> dict[str, Any]:
        """The kind's own checks of a resolved definition, as its route runs
        them; raises InvalidJob."""
        return {}

    def _plan(self, job: Any) -> Plan:
        try:
            request = self.model.model_validate({**job.input, "definition": job.definition})
        except ValidationError:
            raise InvalidJob from None
        ref = request.definition
        if ref.track != self.track:
            raise InvalidJob
        try:
            resolved = definitions.store().resolve(ref.track, ref.slug, ref.variant, ref.version,
                                                   route=jobs.ROUTES[self.kind])
        except TypedError:
            raise InvalidJob from None
        return Plan(request, resolved, self.check(request, resolved))

    def plan(self, job: Any) -> Plan:
        """The job's plan from ``prepare``, or a new one."""
        with self._lock:
            kept = self._plans.get(job.id)
        return kept if kept is not None else self._plan(job)

    def _forget(self, job: Any) -> None:
        with self._lock:
            self._plans.pop(job.id, None)

    # -- the handler -------------------------------------------------------

    def key(self) -> str:
        """The effective value of the key this kind runs under, as a
        claimed job sees it."""
        return keys.scratch(worker=True)

    def prepare(self, job: Any) -> None:
        if self.key() != "on":
            raise Withdrawn
        prepared = self._plan(job)
        with self._lock:
            self._plans[job.id] = prepared
            while len(self._plans) > PLANS_KEPT:
                self._plans.popitem(last=False)

    def budget_s(self, job: Any) -> int:
        return kinds.part_wall_s(self.kind)

    def run(self, job: Any, executor: LegacyExecutor, slot: sandbox.Sandbox, stop: threading.Event) -> Result:
        try:
            return self.execute(job, self.plan(job), slot, stop)
        finally:
            self._forget(job)

    def execute(self, job: Any, plan: Plan, slot: sandbox.Sandbox, stop: threading.Event) -> Result:
        raise NotImplementedError


class RunHandler(_Scratch):
    kind, track, model = "run", "coding", DefinitionRunRequest

    def execute(self, job, plan, slot, stop):
        request, resolved = plan.request, plan.resolved
        document = resolved.document
        control = sandbox.Control(stop=stop)
        outcome = snippets.run_one(request.code, document["variant"], document["entry"], request.input,
                                   timeout_s=kinds.part_wall_s(self.kind), sandbox=slot, control=control)
        if outcome.stopped:
            return Result(parts=[], observation=observation(job.id, [control], []))
        body = CodeRunResult(
            stdout=outcome.stdout, stderr=outcome.stderr, return_value=outcome.return_value, error=outcome.error,
            duration_ms=outcome.duration_ms, truncated=outcome.truncated, definition=resolved.receipt(),
        ).model_dump(mode="json")
        return Result(
            parts=[snippet_part("run", outcome, control)],
            output=envelope.fit_output(body),
            definition=resolved.receipt(),
            observation=observation(job.id, [control], [outcome.stdout, outcome.stderr]),
        )


class EvaluateHandler(_Scratch):
    kind, track, model = "evaluate", "coding", DefinitionEvaluateRequest

    def check(self, request, resolved):
        cases = list(enumerate(resolved.document["cases"]))
        if request.case_ids is not None:
            known = {case["case_id"] for _i, case in cases}
            if any(case_id not in known for case_id in request.case_ids):
                raise InvalidJob
            wanted = set(request.case_ids)
            cases = [(i, case) for i, case in cases if case["case_id"] in wanted]
        if request.tags is not None:
            tags = set(request.tags)
            cases = [(i, case) for i, case in cases if tags & set(case.get("tags") or [])]
        if not cases or len(cases) > kinds.KINDS[self.kind].max_parts:
            raise InvalidJob
        try:
            predicates = coding._predicates(resolved)
        except (TypedError, KeyError, ValueError):
            raise InvalidJob from None
        return {"selected": cases, "predicates": predicates}

    def budget_s(self, job):
        selected = self.plan(job).extra["selected"]
        return sum(coding.TIME_CLASS_S[case["time_class"]] for _i, case in selected)

    def execute(self, job, plan, slot, stop):
        request, resolved = plan.request, plan.resolved
        document = resolved.document
        selected, ran, controls = plan.extra["selected"], [], []
        for _i, case in selected:
            if stop.is_set():
                break
            control = sandbox.Control(stop=stop)
            controls.append(control)
            outcome = snippets.run_one(request.code, document["variant"], document["entry"], case["input"],
                                       timeout_s=coding.TIME_CLASS_S[case["time_class"]], sandbox=slot,
                                       control=control)
            if outcome.stopped:
                break
            ran.append(outcome)
        if stop.is_set() or len(ran) < len(selected):
            return Result(parts=[], observation=observation(job.id, controls, []))
        scored = coding.score_definition_cases(selected, ran, plan.extra["predicates"])
        scored.definition = resolved.receipt()
        parts = []
        for (_i, case), outcome, control, result in zip(selected, ran, controls, scored.results):
            part = snippet_part(case["case_id"], outcome, control)
            if part.outcome_class == "passed" and not result.passed:
                part = Part(case["case_id"], "candidate-failure")
            parts.append(part)
        return Result(
            parts=parts,
            output=envelope.fit_output(scored.model_dump(mode="json")),
            definition=resolved.receipt(),
            observation=observation(job.id, controls, [o.stdout + o.stderr for o in ran]),
        )


class RunProjectHandler(_Scratch):
    kind, track, model = "run_project", "ai-coding", ai_coding.DefinitionRunProjectRequest

    def check(self, request, resolved):
        checkpoints = resolved.document["checkpoints"]
        if request.checkpoint >= len(checkpoints) or checkpoints[request.checkpoint]["run"] is None:
            raise InvalidJob
        if definition_runs.files_problem(request.files, resolved) is not None:
            raise InvalidJob
        return {"step": ai_coding.bounded_run_step(checkpoints[request.checkpoint]["run"])}

    def budget_s(self, job):
        return int(self.plan(job).extra["step"]["wall_s"])

    def execute(self, job, plan, slot, stop):
        step = plan.extra["step"]
        control = sandbox.Control(stop=stop)
        ran = definition_runs.run_step(step, plan.request.files, slot, control=control)
        if ran.stopped:
            return Result(parts=[], observation=observation(job.id, [control], []))
        answer = ai_coding.run_project_answer(ran, step["wall_s"], plan.resolved)
        if ran.timed_out:
            part = Part("run", "resource-limit", "wall_time")
        else:
            part = Part("run", "passed" if answer.passed else "candidate-failure")
        return Result(
            parts=[part],
            output=envelope.fit_output(answer.model_dump(mode="json")),
            definition=plan.resolved.receipt(),
            observation=observation(job.id, [control], [ran.stdout, ran.stderr], ran.returncode),
        )


class TakeHomeRunHandler(_Scratch):
    kind, track, model = "take_home_run", "take-home", take_home.DefinitionTakeHomeRunRequest

    def check(self, request, resolved):
        if resolved.document.get("result_protocol") != "fd3":
            raise InvalidJob
        if definition_runs.files_problem(request.files, resolved) is not None:
            raise InvalidJob
        return {"checkpoint": resolved.document["checkpoints"][0]}

    def execute(self, job, plan, slot, stop):
        checkpoint, resolved = plan.extra["checkpoint"], plan.resolved
        control = sandbox.Control(stop=stop)
        graded = definition_runs.grade(checkpoint, resolved.document["files"], plan.request.files, slot,
                                       kinds.part_wall_s(self.kind), control=control)
        if stop.is_set():
            return Result(parts=[], observation=observation(job.id, [control], []))
        body = take_home.harness_output(checkpoint, graded, resolved)
        return Result(
            parts=envelope.harness_parts(graded.score, graded.timed_out),
            output=envelope.fit_output(body),
            definition=resolved.receipt(),
            observation=observation(job.id, [control], []),
        )


SCRATCH_HANDLERS: dict[str, _Scratch] = {
    handler.kind: handler
    for handler in (RunHandler(), EvaluateHandler(), RunProjectHandler(), TakeHomeRunHandler())
}


# ---------------------------------------------------------------------------
# The grading kinds (PR 3)
# ---------------------------------------------------------------------------


class GradeHandler(_Scratch):
    """A grade: every checkpoint in order, each held to its own 45 s, in
    the one slot the job claimed. A checkpoint's part is its results read
    as ``envelope.harness_parts`` reads them, folded into one class, so a
    checkpoint out of time is ``resource-limit`` and the others keep their
    own. The graded row's content is each checkpoint's server totals and
    per-result outcomes, with no verdict or score where the run didn't earn
    one."""

    kind, track, model = "grade", "ai-coding", ai_coding.DefinitionGradeRequest

    def key(self):
        return keys.grading(worker=True)

    def check(self, request, resolved):
        checkpoints = resolved.document["checkpoints"]
        if not checkpoints or len(checkpoints) > kinds.KINDS[self.kind].max_parts:
            raise InvalidJob
        if definition_runs.files_problem(request.files, resolved) is not None:
            raise InvalidJob
        return {"checkpoints": checkpoints}

    def budget_s(self, job):
        return kinds.part_wall_s(self.kind) * len(self.plan(job).extra["checkpoints"])

    def execute(self, job, plan, slot, stop):
        resolved = plan.resolved
        checkpoints = plan.extra["checkpoints"]
        wall_s = kinds.part_wall_s(self.kind)
        controls, runs = [], []
        for checkpoint in checkpoints:
            if stop.is_set():
                break
            control = sandbox.Control(stop=stop)
            controls.append(control)
            runs.append(definition_runs.grade(checkpoint, resolved.document["files"], plan.request.files, slot,
                                              wall_s, control=control))
        if stop.is_set() or len(runs) < len(checkpoints):
            return Result(parts=[], observation=observation(job.id, controls, []))
        parts = [
            envelope.fold(f"checkpoint-{checkpoint['index']}",
                          envelope.harness_parts(run.score, run.timed_out, run.limit))
            for checkpoint, run in zip(checkpoints, runs)
        ]
        entries = [ai_coding.graded_checkpoint(checkpoint, run, part)
                   for checkpoint, run, part in zip(checkpoints, runs, parts)]
        scores = [entry["score"] for entry in entries]
        return Result(
            parts=parts,
            score=sum(scores) / len(scores) if all(s is not None for s in scores) else None,
            definition=resolved.receipt(),
            observation=observation(job.id, controls, []),
            graded={"test_results": entries},
        )


class TakeHomeSubmitHandler(_Scratch):
    """A take-home submission: the one fd 3 checkpoint, as a take-home run
    grades it, within the submission's 120 s. Its parts are its criteria,
    and its graded row keeps the server's score and verdict only where the
    run earned them."""

    kind, track, model = "take_home_submit", "take-home", take_home.DefinitionTakeHomeSubmitRequest

    def key(self):
        return keys.grading(worker=True)

    def check(self, request, resolved):
        if resolved.document.get("result_protocol") != "fd3":
            raise InvalidJob
        if definition_runs.files_problem(request.files, resolved) is not None:
            raise InvalidJob
        return {"checkpoint": resolved.document["checkpoints"][0]}

    def execute(self, job, plan, slot, stop):
        checkpoint, resolved = plan.extra["checkpoint"], plan.resolved
        control = sandbox.Control(stop=stop)
        run = definition_runs.grade(checkpoint, resolved.document["files"], plan.request.files, slot,
                                    kinds.part_wall_s(self.kind), control=control)
        if stop.is_set():
            return Result(parts=[], observation=observation(job.id, [control], []))
        parts = envelope.harness_parts(run.score, run.timed_out, run.limit)
        return Result(
            parts=parts,
            score=run.score.score,
            definition=resolved.receipt(),
            observation=observation(job.id, [control], []),
            graded={"harness_output": take_home.graded_harness_output(checkpoint, run, resolved, parts)},
        )


GRADING_HANDLERS: dict[str, _Scratch] = {
    handler.kind: handler for handler in (GradeHandler(), TakeHomeSubmitHandler())
}
