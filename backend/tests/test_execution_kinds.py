"""The execution kinds (ROUNDS-00A-L03): the runner's kinds, states, and
classes stay in step with pocketbase/pb_hooks/execution.js, each kind's
most with what admission admits it for, and each part's wall budget with
today's route timeout and #2's resource-profile/v1 job class."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from app import admission, obs
from execution import kinds
from routers import ai_coding, runner, take_home

HOOKS = Path(__file__).resolve().parents[2] / "pocketbase" / "pb_hooks"


@pytest.fixture(scope="module")
def hooks() -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    script = (
        "globalThis.__hooks = process.argv[1];"
        "const e = require(process.argv[1] + '/execution.js');"
        "const a = require(process.argv[1] + '/admission.js');"
        "console.log(JSON.stringify({kinds: e.KINDS, terminal: e.TERMINAL, retryable: e.RETRYABLE,"
        " cleanup: e.CLEANUP, limits: e.LIMITS, maxStarted: e.MAX_STARTED, operations: a.OPERATIONS}));"
    )
    res = subprocess.run([node, "-e", script, str(HOOKS)], capture_output=True, text=True, timeout=60, check=True)
    return json.loads(res.stdout)


def test_the_kinds_are_the_hooks_kinds(hooks):
    assert {name: {"purpose": k.purpose, "operation": k.operation} for name, k in kinds.KINDS.items()} == hooks["kinds"]
    assert list(kinds.KINDS) == list(hooks["kinds"])


def test_the_states_and_classes_are_the_hooks(hooks):
    assert {state: {"classes": list(t.classes), "authoritative": list(t.authoritative)}
            for state, t in kinds.TERMINAL.items()} == hooks["terminal"]
    assert list(kinds.RETRYABLE) == hooks["retryable"]
    assert list(kinds.CLEANUP) == hooks["cleanup"]
    assert list(kinds.LIMITS) == hooks["limits"]
    assert kinds.MAX_STARTED == hooks["maxStarted"]
    assert set(kinds.OUTCOME_CLASSES) == {c for t in kinds.TERMINAL.values() for c in t.classes}
    assert kinds.STATES == ("queued", *kinds.ACTIVE_STATES, *kinds.TERMINAL)


def test_each_kind_is_one_of_the_six_definition_operations():
    assert {k.operation for k in kinds.KINDS.values()} == admission.DEFINITION_OPERATIONS
    routes = {route.operation for route in admission.ROUTES.values()}
    assert all(k.operation in routes for k in kinds.KINDS.values())


def test_an_attempts_most_is_what_admission_admits_the_operation_for(hooks):
    for kind in kinds.KINDS.values():
        assert kind.max_budget_s == hooks["operations"][kind.operation][1], kind.name
    assert kinds.KINDS["evaluate"].max_budget_s == runner.EVALUATE_MAX_WALL_S
    assert kinds.KINDS["grade"].max_budget_s == ai_coding.GRADE_MAX_WALL_S


@pytest.mark.parametrize(
    "name, today",
    [
        ("run", runner.DEFAULT_TIMEOUT_S),
        ("evaluate", runner.LARGE_TAG_TIMEOUT_S),
        ("run_project", ai_coding.RUN_PROJECT_TIMEOUT_S),
        ("take_home_run", take_home.RUN_TIMEOUT_S),
        ("grade", ai_coding.GRADE_CHECKPOINT_TIMEOUT_S),
        ("take_home_submit", take_home.SUBMIT_TIMEOUT_S),
    ],
)
def test_a_parts_budget_is_todays_within_its_job_class(name, today):
    kind = kinds.KINDS[name]
    ceiling = kinds.profile()["job_classes"][kind.job_class]["wall_s_max"]
    assert kind.part_wall_s == today
    assert kinds.part_wall_s(name) == min(today, ceiling) == today


def test_the_job_classes_are_the_profiles():
    by_class = {cls: sorted(n for n, k in kinds.KINDS.items() if k.job_class == cls) for cls in kinds.JOB_CLASSES}
    assert by_class == {"interactive": ["evaluate", "run", "run_project"],
                        "project": ["grade", "take_home_run", "take_home_submit"]}
    assert set(kinds.profile()["job_classes"]) == set(kinds.JOB_CLASSES)


def test_every_kind_declares_the_states_and_classes():
    for kind in kinds.KINDS.values():
        assert kind.states == kinds.STATES and kind.outcome_classes == kinds.OUTCOME_CLASSES
        assert kind.purpose in kinds.PURPOSES


def test_the_job_metrics_take_exactly_these_labels():
    assert obs.FIELDS["kind"]("run") and not obs.FIELDS["kind"]("render")
    for name in kinds.KINDS:
        assert obs.FIELDS["kind"](name)
    for state in kinds.STATES:
        assert obs.FIELDS["state"](state)
    for cls in kinds.OUTCOME_CLASSES:
        assert obs.FIELDS["outcome_class"](cls)
    line = obs.build("execution.job", metric="rounds_job_terminal_total", value=1, kind="grade", purpose="grading",
                     state="completed", outcome_class="passed", executor_kind="legacy-in-process",
                     account="acct_0123456789abcdef", correlation_id="0" * 32)
    # A job metric carries no account or correlation id, even when a
    # caller passes one.
    assert line == {"v": "obs/v1", "event": "execution.job", "metric": "rounds_job_terminal_total", "value": 1,
                    "kind": "grade", "purpose": "grading", "state": "completed", "outcome_class": "passed",
                    "executor_kind": "legacy-in-process", "dropped": ["account", "correlation_id"]}
    assert obs.build("execution.worker", code="started", service="runner", account="acct_0123456789abcdef") == {
        "v": "obs/v1", "event": "execution.worker", "code": "started", "service": "runner", "dropped": ["account"],
    }
