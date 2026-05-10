"""Take-home runner unit tests. Doesn't depend on any seeded
assignment — uses inline file dicts."""
from take_home.runner import run_assignment, _parse_harness_output


def test_parses_well_formed_harness_output_from_last_line():
    stdout = """
preamble: setting up
test setup ok
{"criteria": [{"id":"a","passed":true,"weight":1.0,"logs":""}], "score": 1.0, "duration_ms": 12}
""".strip()
    score, criteria, err = _parse_harness_output(stdout)
    assert err is None
    assert score == 1.0
    assert criteria == [{"id": "a", "passed": True, "weight": 1.0, "logs": ""}]


def test_returns_error_when_no_harness_json_present():
    score, criteria, err = _parse_harness_output("hello\nworld\n")
    assert score == 0.0
    assert criteria == []
    assert err and "harness" in err.lower()


def test_run_assignment_round_trip_minimal_python_harness():
    files = {
        "harness.py": (
            "import json\n"
            "print(json.dumps({\"criteria\": [{\"id\":\"x\",\"passed\":True,\"weight\":1.0,\"logs\":\"\"}], \"score\": 1.0, \"duration_ms\": 1}))\n"
        ),
    }
    r = run_assignment(files, "python3 harness.py", timeout_s=10)
    assert r.error is None, r.error
    assert r.score == 1.0
    assert r.criteria[0]["id"] == "x"
