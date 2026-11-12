"""The harness's stage 4 phases (harness/probes/admission_deploy.py) and the
verdict that requires them (ROUNDS-00A-L01 stage 4).

The phases themselves run against the built images in harness/run.sh. Here
their decisions run against canned answers, the closure report runs through
the real runner in process, and the verdict is shown to require every
admission check."""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for extra in (ROOT / "harness", ROOT / "harness" / "probes"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

import admission_check as ac  # noqa: E402
import admission_deploy as ad  # noqa: E402
import run as harness_run  # noqa: E402
import verify_deployment as vd  # noqa: E402
from factory import Account  # noqa: E402


class Writer:
    def __init__(self) -> None:
        self.rows = []

    def write(self, r) -> None:
        self.rows.append(r)

    def by_id(self) -> dict:
        out: dict = {}
        for r in self.rows:
            out.setdefault(r.probe_id, []).append(r)
        return out


ACCT = Account(tag="t", email="t@harness.invalid", password="p")
ACCT.token = "token-placeholder"
CID = "0123456789abcdef0123456789abcdef"
GOOD = {"env": ["HOME", "LANG", "LC_ALL", "LOGNAME", "PATH", "PYTHONDONTWRITEBYTECODE", "TMPDIR", "USER"],
        "uid": 10002, "app_writable": False, "home_mode": 0o700, "home_owned": True, "tmpdir_is_home": True}
JOB = "jobaaaaaaaaaaa1"
# two-sum's entry, which every harness run names (admission_check.TWO_SUM).
TWO_SUM_ENTRY = {"kind": "function", "name": "two_sum",
                 "params": [{"name": "nums", "type": "int[]"}, {"name": "target", "type": "int"}], "returns": "int[]"}


def reported(facts) -> list[tuple[int, dict, dict]]:
    """A run's job answer, then the job ended with ``facts`` as its return
    value."""
    ended = {"job_id": JOB, "state": "completed", "outcome_class": "passed", "retryable": False,
             "cancel_requested": False, "envelope": {"output": {"return_value": facts}}}
    return [(202, {"job_id": JOB, "state": "queued"}, {}), (200, ended, {})]


def answering(monkeypatch, *answers):
    queue = list(answers)

    def fake_call(*_args, **_kwargs):
        return queue.pop(0)

    monkeypatch.setattr(ac, "call", fake_call)


def typed(code: str, detail: str = "The request doesn't match what this route accepts.") -> bytes:
    return json.dumps({"detail": detail, "code": code, "correlation_id": CID}).encode()


def raw_answering(monkeypatch, answer):
    """check_order's first request reads the raw answer; ``answer`` is the
    answer, or a function of the body sent."""
    sent = []

    def fake_raw(_base, _path, _token, body, keyed=True):
        sent.append((body, keyed))
        return answer(body) if callable(answer) else answer

    monkeypatch.setattr(ad, "_raw_call", fake_raw)
    return sent


# ---- the closure report ---------------------------------------------------------


def test_a_clean_report_passes_every_closure(monkeypatch):
    answering(monkeypatch, *reported(GOOD))
    w = Writer()
    ad.check_closures(w, "http://runner:8000", ACCT)
    assert [(r.probe_id, r.passed) for r in w.rows] == [
        ("admission.closure.child-env.minimal", True),
        ("admission.closure.candidate.unprivileged", True),
        ("admission.closure.scratch.private", True),
    ]


@pytest.mark.parametrize(
    "change, failing",
    [
        ({"env": GOOD["env"] + ["AI_KEY_SECRET"]}, "admission.closure.child-env.minimal"),
        ({"uid": 0}, "admission.closure.candidate.unprivileged"),
        ({"app_writable": True}, "admission.closure.candidate.unprivileged"),
        ({"home_mode": 0o755}, "admission.closure.scratch.private"),
        ({"tmpdir_is_home": False}, "admission.closure.scratch.private"),
    ],
    ids=["runner-setting", "root", "writable-app", "open-home", "shared-tmp"],
)
def test_a_report_that_breaks_a_closure_fails_only_it(monkeypatch, change, failing):
    answering(monkeypatch, *reported({**GOOD, **change}))
    w = Writer()
    ad.check_closures(w, "http://runner:8000", ACCT)
    assert {r.probe_id for r in w.rows if not r.passed} == {failing}


def test_a_report_names_variables_never_values(monkeypatch):
    answering(monkeypatch, *reported({**GOOD, "env": GOOD["env"] + ["PB_ADMIN_PASSWORD"]}))
    w = Writer()
    ad.check_closures(w, "http://runner:8000", ACCT)
    (env,) = w.by_id()["admission.closure.child-env.minimal"]
    assert env.detail == "unexpected variables: PB_ADMIN_PASSWORD"


def test_no_report_fails_all_three(monkeypatch):
    answering(monkeypatch, (503, {"code": "worker_unavailable"}, {}))
    w = Writer()
    ad.check_closures(w, "http://runner:8000", ACCT)
    assert len(w.rows) == 3 and not any(r.passed for r in w.rows)


def test_a_job_that_ended_without_output_fails_all_three(monkeypatch):
    canceled = {"job_id": JOB, "state": "canceled", "outcome_class": "canceled", "envelope": None}
    answering(monkeypatch, (202, {"job_id": JOB, "state": "queued"}, {}), (200, canceled, {}))
    w = Writer()
    ad.check_closures(w, "http://runner:8000", ACCT)
    assert len(w.rows) == 3 and not any(r.passed for r in w.rows)
    assert all("ended=canceled/canceled" in r.detail for r in w.rows)


def test_the_closure_report_runs_through_the_real_runner():
    # Outside the image the runner isn't root, so the uid can't be a
    # candidate's here; the environment and scratch are the runner's own.
    from runner import run_one

    outcome = run_one(ad.CLOSURE_CODE, "python", TWO_SUM_ENTRY, ac.run_body()["input"], timeout_s=10)
    assert outcome.error is None, outcome.error
    facts = outcome.return_value
    # macOS adds its own text-encoding variable to every process; the image is Linux.
    os_added = {"__CF_USER_TEXT_ENCODING"} if sys.platform == "darwin" else set()
    assert set(facts["env"]) <= ad.ALLOWED_ENV | os_added
    assert facts["home_mode"] == 0o700 and facts["home_owned"] is True and facts["tmpdir_is_home"] is True
    assert "AI_KEY_SECRET" not in facts["env"]


# ---- the order of the chain ------------------------------------------------------


def test_fields_then_key_then_lookup_passes(monkeypatch):
    sent = raw_answering(monkeypatch, (422, typed("invalid_request"), {"x-correlation-id": CID}))
    answering(monkeypatch, (400, {"code": "idempotency_key_required"}, {}))
    w = Writer()
    ad.check_order(w, "http://runner:8000", ACCT)
    assert [(r.probe_id, r.passed) for r in w.rows] == [
        ("admission.policy.fields-before-idempotency", True),
        ("admission.error-shape.no-echo", True),
        ("admission.policy.idempotency-before-lookup", True),
    ]
    # The first request carries no key, so only its fields can refuse it.
    ((body, keyed),) = sent
    assert keyed is False and any(name.startswith("s4echo") for name in body)


def test_a_lookup_before_the_key_fails(monkeypatch):
    raw_answering(monkeypatch, (422, typed("invalid_request"), {"x-correlation-id": CID}))
    answering(monkeypatch, (404, {"code": "definition_not_found"}, {}))
    w = Writer()
    ad.check_order(w, "http://runner:8000", ACCT)
    assert [r.probe_id for r in w.rows if not r.passed] == ["admission.policy.idempotency-before-lookup"]


def _echoing(body: dict) -> tuple[int, bytes, dict]:
    # A validation list that names each field it refused, as FastAPI's own does.
    detail = [{"loc": ["body", name], "msg": "Extra inputs are not permitted"} for name in body]
    return 422, json.dumps({"detail": detail, "code": "invalid_request", "correlation_id": CID}).encode(), \
        {"x-correlation-id": CID}


@pytest.mark.parametrize(
    "answer",
    [_echoing, (422, b'{"detail":[{"loc":["body"],"msg":"Field required"}]}', {}),
     (422, typed("invalid_request"), {})],
    ids=["names-the-fields", "untyped-list", "no-correlation-header"],
)
def test_a_refusal_that_isnt_the_safe_shape_fails_only_no_echo(monkeypatch, answer):
    raw_answering(monkeypatch, answer)
    answering(monkeypatch, (400, {"code": "idempotency_key_required"}, {}))
    w = Writer()
    ad.check_order(w, "http://runner:8000", ACCT)
    failing = {r.probe_id for r in w.rows if not r.passed}
    assert "admission.error-shape.no-echo" in failing
    assert "admission.policy.idempotency-before-lookup" not in failing


def test_a_no_echo_receipt_never_carries_the_marker(monkeypatch):
    sent = raw_answering(monkeypatch, _echoing)
    answering(monkeypatch, (400, {"code": "idempotency_key_required"}, {}))
    w = Writer()
    ad.check_order(w, "http://runner:8000", ACCT)
    ((body, _keyed),) = sent
    marker = next(k for k in body if k.startswith("s4echo"))
    assert all(marker not in r.detail for r in w.rows)


# ---- the event loop while a job runs ---------------------------------------------


@pytest.fixture
def two_replicas(monkeypatch):
    monkeypatch.setattr(ac, "RUNNERS", ["http://runner:8000", "http://runner-b:8000"])


def _job_states(monkeypatch, *states):
    seen = iter([state if isinstance(state, dict) else {"job_id": JOB, "state": state} for state in states])
    monkeypatch.setattr(ac, "job_until", lambda *_args, **_kwargs: next(seen))


def _posting(monkeypatch, health) -> list[str]:
    """The event loop check's calls: each run it submits is a job, and each
    /health read answers the next status in ``health``. Answers the keys
    the runs went in under."""
    keys, statuses = [], iter(health)

    def fake_call(_base, method, _path, _token=None, _body=None, headers=None, timeout=30):
        if method == "POST":
            keys.append(headers["Idempotency-Key"])
            return 202, {"job_id": JOB, "state": "queued"}, {}
        return next(statuses), {}, {}

    monkeypatch.setattr(ac, "call", fake_call)
    return keys


# Each case is how a read saw each run it submitted, then how the last run ended.
@pytest.mark.parametrize(
    "seen, finished, health, ok",
    [
        (("started",), "completed", [200] * 6, True),
        (("started",), "timed-out", [200] * 6, True),
        (("completed",) * 3, "completed", [200] * 6, False),
        (("started",), "completed", [200, 503, 200, 200, 200, 200], False),
        (("started",), "failed", [200] * 6, False),
        (("completed", "started"), "completed", [200] * 6, True),
    ],
    ids=["free", "free-until-its-limit", "never-seen-running", "a-replica-unhealthy", "the-job-failed",
         "seen-running-on-a-later-try"],
)
def test_the_event_loop_check(monkeypatch, two_replicas, seen, finished, health, ok):
    _job_states(monkeypatch, *seen, finished)
    keys = _posting(monkeypatch, health)
    w = Writer()
    ad.check_event_loop(w, "http://runner:8000", ACCT)
    ((row,),) = w.by_id().values()
    assert row.probe_id == "admission.closure.event-loop.free" and row.passed is ok
    # Each replica answered three times while the job ran.
    assert row.observed_status == (200 if 503 not in health else 503)
    # One run for each read, each under a key of its own.
    assert len(set(keys)) == len(keys) == len(seen)


def test_each_run_sent_again_names_the_one_before_its_state_and_its_run_time(monkeypatch, two_replicas, capsys):
    ended = [{"job_id": JOB, "state": "completed", "envelope": {"output": {"duration_ms": 2104 + i}}}
             for i in range(3)]
    _job_states(monkeypatch, *ended, "completed")
    keys = _posting(monkeypatch, [200] * 6)
    w = Writer()
    ad.check_event_loop(w, "http://runner:8000", ACCT)
    ((row,),) = w.by_id().values()
    assert row.passed is False and row.detail.startswith("busy=False ") and row.detail.endswith(" tries=3")
    out = capsys.readouterr().out
    assert out.splitlines() == [
        f"INFO admission.closure.event-loop.free: resubmitted, key={keys[0]} state=completed ran_ms=2104 (try 2 of 3)",
        f"INFO admission.closure.event-loop.free: resubmitted, key={keys[1]} state=completed ran_ms=2105 (try 3 of 3)",
    ]
    assert ACCT.token not in out


def test_a_wait_for_a_running_job_reads_it_as_it_is_and_a_wait_for_its_end_long_polls(monkeypatch):
    paths, answers = [], iter([{"state": "leased"}, {"state": "started"}, {"state": "completed"}])

    def fake_call(_base, _method, path, *_args, **_kwargs):
        paths.append(path)
        return 200, next(answers), {}

    monkeypatch.setattr(ac, "call", fake_call)
    running = ac.job_until("http://runner:8000", ACCT.token, JOB, lambda a: a.get("state") in ("started", *ac.ENDED))
    assert running["state"] == "started"
    assert ac.job_until("http://runner:8000", ACCT.token, JOB)["state"] == "completed"
    assert paths == [f"{ac.JOBS}/{JOB}?wait=0", f"{ac.JOBS}/{JOB}?wait=0", f"{ac.JOBS}/{JOB}?wait=5"]


@pytest.mark.parametrize(
    "envelope, took",
    [
        ({"output": {"duration_ms": 2104}, "started_at": 100, "finished_at": 103}, 2104),
        ({"output": None, "started_at": 100, "finished_at": 103}, 3000),
        ({"output": None, "started_at": None, "finished_at": 103}, None),
        ({"output": {"duration_ms": True}, "started_at": None, "finished_at": None}, None),
        (None, None),
    ],
    ids=["its-output-timing", "start-to-end", "never-started", "no-timing", "not-ended"],
)
def test_a_jobs_run_time(envelope, took):
    assert ac.ran_ms({"job_id": JOB, "envelope": envelope}) == took


# ---- the store speaks admission/v1 and counts only what it admitted ------------


@pytest.mark.parametrize(
    "after, ok",
    [
        ({"v": "admission/v1", "hour": 7, "requests": 1}, True),
        ({"v": "admission/v1", "hour": 7, "requests": 3}, False),
        ({"v": "admission/v1", "hour": 7, "requests": 0}, False),
        ({"v": "admission/v0", "hour": 7, "requests": 1}, False),
        ({"v": "admission/v1", "hour": 8, "requests": 0}, True),
        ({"v": "admission/v1", "hour": 8, "requests": 2}, False),
    ],
    ids=["counted-once", "refusals-counted", "nothing-counted", "other-version", "hour-turned", "hour-turned-extra"],
)
def test_the_store_contract(monkeypatch, after, ok):
    monkeypatch.setattr(ac, "usage", lambda _token: after)
    w = Writer()
    ad.check_store_contract(w, "http://runner:8000", ACCT, {"v": "admission/v1", "hour": 7, "requests": 0})
    ((row,),) = w.by_id().values()
    assert row.probe_id == "admission.policy.version" and row.passed is ok


# ---- the gates line the launcher saves ------------------------------------------


def test_the_saved_gates_line_is_read_per_phase(tmp_path, monkeypatch):
    monkeypatch.setenv("RECEIPTS_PATH", str(tmp_path / "receipts.jsonl"))
    (tmp_path / "gates-deploy.log").write_text('runner-1  | {"event":"gates","gates":{},"service":"runner"}\n')
    (tmp_path / "gates-emergency-enable-runner-b.log").write_text('runner-b-1  | {"event":"gates"}\n')
    assert '"event":"gates"' in ad.gates_log("deploy")
    assert ad.gates_log("emergency-disable") == ""
    # The second replica's line is saved apart from the first's.
    assert "runner-b-1" in ad.gates_log("emergency-enable", "runner-b")
    assert ad.gates_log("emergency-enable") == ""
    assert ad.REPLICA_SERVICES == ("runner", "runner-b")


def test_the_replica_services_are_the_launchers_runner_urls_in_order():
    text = (ROOT / "harness" / "run.sh").read_text()
    urls = re.search(r'^RUNNER_URLS="([^"]+)"', text, re.M).group(1).split(",")
    assert tuple(u.split("//")[1].split(":")[0] for u in urls) == ad.REPLICA_SERVICES


# ---- every check is reported and required ---------------------------------------


def test_every_harness_check_has_a_receipt_call():
    source = (ROOT / "harness" / "probes" / "admission_deploy.py").read_text()
    for check_id in ad.CHECKS:
        assert source.count(f'"{check_id}"') >= 2, check_id


def test_a_full_run_requires_every_admission_check():
    assert harness_run.admission_check_ids() == set(vd.ADMISSION_CHECKS) | set(ad.CHECKS)


def _doc() -> dict:
    enforced = "account-scope.view.cross-account.denied"
    return {"version": "v1", "contract": "account-scope", "deny_contract": {"view": {"status": 404}},
            "probe_families": {enforced: {"status": "enforced", "deny_key": "view", "operation": "view",
                                          "actor": "authenticated-other"}},
            "collections": {"campaigns": {"current_rules": {}, "probes": [enforced]}}}


def _row(probe_id: str, passed: bool = True, collection: str = "c") -> dict:
    return {"probe_id": probe_id, "collection": collection, "operation": "o", "actor": "a", "expected_status": 1,
            "observed_status": 1, "passed": passed, "request_time_ms": 1}


def _baseline() -> list[dict]:
    return [_row("account-scope.view.cross-account.denied", collection="campaigns"),
            _row(harness_run.READBACK_PROBE, collection="campaigns")]


def _write(tmp_path, rows) -> str:
    path = tmp_path / "r.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return str(path)


def test_the_verdict_passes_with_every_admission_receipt(tmp_path):
    ids = harness_run.admission_check_ids()
    path = _write(tmp_path, _baseline() + [_row(i) for i in sorted(ids)])
    assert harness_run.run_verdict(_doc(), path, ids) == 0


def test_the_verdict_fails_on_a_missing_admission_receipt(tmp_path, capsys):
    ids = harness_run.admission_check_ids()
    dropped = "deployment.gates.disabled-route.denied"
    path = _write(tmp_path, _baseline() + [_row(i) for i in sorted(ids) if i != dropped])
    assert harness_run.run_verdict(_doc(), path, ids) == 1
    assert f"missing result for admission check {dropped}" in capsys.readouterr().out


def test_the_verdict_fails_on_a_failed_admission_receipt(tmp_path, capsys):
    ids = harness_run.admission_check_ids()
    rows = _baseline() + [_row(i, passed=i != "admission.emergency.enabled.restored") for i in sorted(ids)]
    assert harness_run.run_verdict(_doc(), _write(tmp_path, rows), ids) == 1
    assert "admission check admission.emergency.enabled.restored failed" in capsys.readouterr().out
