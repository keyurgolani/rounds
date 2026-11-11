"""rounds.execution-envelope/v1 (ROUNDS-00A-L03): how parts add up to the
envelope's outcome, the fd 3 channel's absent, empty, and partial cases,
and the checks ``complete`` makes, which the runner's ``validate`` makes
first. Every fixture here goes through both, and they agree."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from execution import envelope, kinds
from execution.envelope import InvalidEnvelope, Part

HOOKS = Path(__file__).resolve().parents[2] / "pocketbase" / "pb_hooks"
RECEIPT = {"track": "coding", "slug": "two-sum", "variant": "python", "content_version": 1,
           "checksum": "sha256:" + "e" * 64}


def _build(state="completed", outcome_class="passed", limit=None, score=None, **extra):
    return envelope.build(
        job_id="job000000000001", result=envelope.outcome(state, outcome_class, limit), cleanup="confirmed",
        worker="runner-a", attempt_number=1, source_checksum="c" * 64, input_digest="d" * 64, queued_at=100,
        started_at=101, finished_at=102, score=score, **extra,
    )


# ---- aggregation ----------------------------------------------------------


@pytest.mark.parametrize(
    "parts, expected",
    [
        ([Part("a", "passed"), Part("b", "passed")], ("completed", "passed", True, None)),
        ([Part("a", "passed"), Part("b", "candidate-failure")], ("completed", "candidate-failure", True, None)),
        ([Part("a", "passed"), Part("b", "resource-limit", "wall_time")], ("timed-out", "resource-limit", True, "wall_time")),
        ([Part("a", "candidate-failure"), Part("b", "resource-limit", "memory")], ("completed", "resource-limit", True, "memory")),
        ([Part("a", "passed"), Part("b", "infrastructure-degraded")], ("failed", "infrastructure-degraded", False, None)),
        ([Part("a", "resource-limit", "wall_time"), Part("b", "worker-lost")], ("failed", "worker-lost", False, None)),
        ([Part("a", "definition-invalid"), Part("b", "infrastructure-degraded")], ("denied", "definition-invalid", False, None)),
        ([Part("a", "canceled"), Part("b", "definition-invalid"), Part("c", "policy-violation")],
         ("denied", "policy-violation", False, None)),
        ([Part("a", "canceled"), Part("b", "passed")], ("canceled", "canceled", False, None)),
        ([], ("failed", "infrastructure-degraded", False, None)),
    ],
    ids=["all-passed", "one-failed", "wall-time", "other-limit", "degraded", "worker-lost", "definition-invalid",
         "policy-first", "canceled", "nothing-ran"],
)
def test_parts_add_up_to_one_outcome(parts, expected):
    out = envelope.aggregate(parts)
    assert (out.state, out.outcome_class, out.authoritative, out.limit) == expected


def test_a_part_outside_the_classes_or_a_limit_unnamed_is_refused():
    with pytest.raises(InvalidEnvelope):
        envelope.aggregate([Part("a", "skipped")])
    with pytest.raises(InvalidEnvelope):
        envelope.aggregate([Part("a", "resource-limit")])


# ---- the fd 3 result channel ---------------------------------------------


@pytest.mark.parametrize("reported", [None, {}], ids=["absent", "empty"])
@pytest.mark.parametrize("killed_by, cls", [("wall_time", "resource-limit"), ("output", "resource-limit"),
                                            (None, "infrastructure-degraded")])
def test_an_absent_or_empty_channel_is_the_limit_that_killed_the_child_or_degraded(reported, killed_by, cls):
    parts = envelope.channel_parts(["a", "b"], reported, killed_by)
    assert [(p.id, p.outcome_class, p.limit) for p in parts] == [("a", cls, killed_by), ("b", cls, killed_by)]
    out = envelope.aggregate(parts)
    assert out.outcome_class == cls and out.limit == killed_by
    assert out.authoritative is (cls == "resource-limit")


@pytest.mark.parametrize("killed_by, cls", [("wall_time", "resource-limit"), (None, "infrastructure-degraded")])
def test_each_id_a_partial_channel_leaves_out_gets_the_same_class(killed_by, cls):
    parts = envelope.channel_parts(["a", "b", "c"], {"a": "passed", "b": "failed", "zz": "passed"}, killed_by)
    assert [(p.id, p.outcome_class) for p in parts] == [("a", "passed"), ("b", "candidate-failure"), ("c", cls)]


def test_a_full_channel_scores_on_what_it_reported():
    parts = envelope.channel_parts(["a", "b"], {"a": "passed", "b": "passed"}, None)
    assert envelope.aggregate(parts) == envelope.outcome("completed", "passed")


def test_an_unknown_limit_is_refused():
    with pytest.raises(InvalidEnvelope):
        envelope.channel_parts(["a"], None, "gpu")


# ---- what a result never is ------------------------------------------------


@pytest.mark.parametrize(
    "state, cls, limit",
    [("timed-out", "resource-limit", "wall_time"), ("completed", "resource-limit", "processes"),
     ("failed", "worker-lost", None), ("failed", "infrastructure-degraded", None),
     ("timed-out", "infrastructure-degraded", None), ("denied", "definition-invalid", None),
     ("denied", "policy-violation", None), ("canceled", "canceled", None)],
)
def test_no_limit_loss_outage_or_definition_error_scores(state, cls, limit):
    env = _build(state, cls, limit, parts=[Part("a", cls if cls != "resource-limit" else cls, limit)])
    assert env["user_view"]["score"] is None
    # A part says its class, never passed: false.
    assert all(set(part) == {"id", "outcome_class", "limit"} for part in env["user_view"]["parts"])
    with pytest.raises(InvalidEnvelope):
        _build(state, cls, limit, score=0.0)


def test_only_a_passed_or_failed_solution_scores_and_only_from_0_to_1():
    assert _build(score=1.0)["user_view"]["score"] == 1.0
    assert _build("completed", "candidate-failure", score=0.25)["user_view"]["score"] == 0.25
    for score in (-0.1, 1.5, float("nan"), True):
        with pytest.raises(InvalidEnvelope):
            _build(score=score)


def test_the_user_view_has_only_the_v1_keys_and_no_harness_output():
    env = _build(parts=[Part("case-1", "passed")], definition=RECEIPT)
    assert tuple(env["user_view"]) == envelope.USER_VIEW_KEYS
    assert tuple(env["operator_view"]) == envelope.OPERATOR_VIEW_KEYS
    assert env["user_view"]["output"] is None and env["operator_view"]["image_digest"] is None
    assert env["operator_view"]["executor_kind"] == "legacy-in-process"


def _leaves(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _leaves(item)
    elif isinstance(value, list):
        for item in value:
            yield from _leaves(item)
    else:
        yield value


def test_a_run_with_hidden_material_shows_only_outcome_classes_and_the_servers_totals():
    """D9: the account reads its own envelope, so a grading envelope's user
    view is enums, ids, times, the score, and the receipt, and no text a
    run printed or a hidden test held."""
    assert {k for k, kind in kinds.KINDS.items() if kind.hidden_material} == {"grade", "take_home_submit"}
    parts = [Part("checkpoint-1", "passed"), Part("checkpoint-2", "candidate-failure"),
             Part("checkpoint-3", "resource-limit", "wall_time")]
    env = _build("timed-out", "resource-limit", "wall_time", parts=parts, definition=RECEIPT,
                 rubric={"state": "requested"}, hidden_material=True)
    user = env["user_view"]
    assert user["output"] is None and user["score"] is None
    allowed = (set(kinds.OUTCOME_CLASSES) | set(kinds.LIMITS) | set(kinds.TERMINAL) | set(kinds.CLEANUP)
               | set(envelope.RUBRIC_STATES) | {envelope.ENVELOPE_VERSION, "job000000000001"}
               | {p.id for p in parts} | {v for v in RECEIPT.values() if isinstance(v, str)})
    for leaf in _leaves(user):
        assert leaf is None or isinstance(leaf, (bool, int, float)) or leaf in allowed, leaf
    with pytest.raises(InvalidEnvelope):
        _build(parts=[Part("a", "passed")], output={"stdout": "ok"}, hidden_material=True)
    # A scratch kind may show visible output, within #2's cap.
    assert _build(output={"stdout": "ok"})["user_view"]["output"] == {"stdout": "ok"}


@pytest.mark.parametrize(
    "change",
    [
        lambda u: u["parts"][0].update(expected=[1, 2]),
        lambda u: u["parts"][0].update(stdout="hidden"),
        lambda u: u["parts"][0].update(id="a b"),
        lambda u: u["parts"][0].update(outcome_class="skipped"),
        lambda u: u["parts"].extend([{"id": f"p{i}", "outcome_class": "passed", "limit": None} for i in range(64)]),
        lambda u: u.update(definition=dict(RECEIPT, harness="tests/hidden.py")),
        lambda u: u.update(definition=dict(RECEIPT, checksum="e" * 64)),
        lambda u: u.update(rubric={"state": "completed", "feedback": "text"}),
        lambda u: u.update(rubric={"state": "graded"}),
        lambda u: u.update(output="text"),
        lambda u: u.update(output={"stdout": "x" * envelope.OUTPUT_MAX_CHARS}),
        lambda u: u.update(job_id="not-a-record-id"),
        lambda u: u.update(started_at=-1),
    ],
    ids=["part-expected", "part-stdout", "part-id", "part-class", "too-many-parts", "receipt-extra", "receipt-checksum",
         "rubric-text", "rubric-state", "output-text", "output-size", "job-id", "times"],
)
def test_nothing_but_the_v1_shapes_gets_into_the_user_view(change):
    env = _build(parts=[Part("a", "passed")], definition=RECEIPT, score=1.0)
    change(env["user_view"])
    with pytest.raises(InvalidEnvelope):
        envelope.validate(env)


# ---- the store makes the same checks --------------------------------------


def _mutations():
    """Envelopes ``validate`` and ``checkResult`` both have to judge."""
    base = _build(parts=[Part("a", "passed")], score=1.0)
    cases = [("valid", base)]
    for state, terminal in kinds.TERMINAL.items():
        for cls in terminal.classes:
            limit = "wall_time" if (state, cls) == ("timed-out", "resource-limit") else (
                "memory" if cls == "resource-limit" else None)
            cases.append((f"valid-{state}-{cls}", _build(state, cls, limit)))

    def change(name, fn):
        env = copy.deepcopy(base)
        fn(env)
        cases.append((name, env))

    change("extra-key", lambda e: e.update(extra=1))
    change("state-class", lambda e: (e.update(outcome_class="worker-lost"), e["user_view"].update(outcome_class="worker-lost")))
    change("authoritative", lambda e: (e.update(authoritative=False), e["user_view"].update(authoritative=False)))
    change("authoritative-int", lambda e: (e.update(authoritative=1), e["user_view"].update(authoritative=1)))
    change("cleanup", lambda e: (e.update(cleanup="done"), e["user_view"].update(cleanup="done")))
    change("version", lambda e: e["user_view"].update(version="rounds.execution-envelope/v2"))
    change("operator-version", lambda e: e["operator_view"].update(version="v0"))
    change("user-key", lambda e: e["user_view"].update(stdout="x"))
    change("user-missing", lambda e: e["user_view"].pop("rubric"))
    change("operator-key", lambda e: e["operator_view"].update(hidden="x"))
    change("views-disagree", lambda e: e["user_view"].update(state="failed"))
    change("limit-unnamed", lambda e: e["user_view"].update(limit="gpu"))
    change("limit-without-class", lambda e: e["user_view"].update(limit="memory"))
    change("parts", lambda e: e["user_view"].update(parts={}))
    change("score-high", lambda e: e["user_view"].update(score=2))
    change("score-text", lambda e: e["user_view"].update(score="1"))
    change("executor", lambda e: e["operator_view"].update(executor_kind="docker"))
    change("bytes", lambda e: e["operator_view"].update(output_bytes=-1))
    change("bytes-float", lambda e: e["operator_view"].update(output_bytes=1.5))
    change("exit", lambda e: e["operator_view"].update(exit_status="0"))
    change("output-size", lambda e: e["user_view"].update(output={"stdout": "x" * envelope.OUTPUT_MAX_CHARS}))
    change("part-key", lambda e: e["user_view"]["parts"][0].update(expected=[1]))
    change("receipt", lambda e: e["user_view"].update(definition={"track": "coding", "slug": "two-sum"}))
    change("rubric", lambda e: e["user_view"].update(rubric={"state": "completed", "feedback": "x"}))
    change("operator-size", lambda e: e["operator_view"].update(worker="w" * envelope.OPERATOR_VIEW_MAX_CHARS))
    # One emoji is two UTF-16 code units, as JavaScript counts: over the
    # cap in code units, well under it in code points.
    change("output-size-utf16", lambda e: e["user_view"].update(
        output={"s": "\U0001F600" * (envelope.OUTPUT_MAX_CHARS // 2 + 10)}))
    cases.append(("valid-receipt-and-output", _build(parts=[Part("a", "passed")], score=1.0, definition=RECEIPT,
                                                     rubric={"state": "lost"}, output={"stdout": "ok"})))
    change("state-type", lambda e: e.update(state=["completed"]))
    return cases


def _python_accepts(env) -> bool:
    try:
        envelope.validate(env)
    except InvalidEnvelope:
        return False
    return True


def test_validate_and_the_stores_check_agree_on_every_fixture():
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    cases = _mutations()
    script = (
        "globalThis.__hooks = process.argv[1];"
        "const e = require(process.argv[1] + '/execution.js');"
        "const cases = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
        "console.log(JSON.stringify(cases.map((c) => e.checkResult(c) !== null)));"
    )
    res = subprocess.run([node, "-e", script, str(HOOKS)], input=json.dumps([env for _, env in cases]),
                         capture_output=True, text=True, timeout=60, check=True)
    store_accepts = json.loads(res.stdout)
    for (name, env), accepted in zip(cases, store_accepts, strict=True):
        assert _python_accepts(env) is accepted, name
        assert accepted is name.startswith("valid"), name
