import pytest
from runner import run_one, ExecutionOutcome


def test_run_captures_stdout():
    code = "def solve(x):\n    print('hello'); return x * 2"
    outcome = run_one(code, "python", {"kind": "function", "name": "solve"}, {"x": 5})
    assert outcome.stdout.strip() == "hello"
    assert outcome.return_value == 10
    assert outcome.error is None
    assert outcome.duration_ms >= 0


def test_run_captures_stderr():
    code = "import sys\ndef solve():\n    sys.stderr.write('oh no\\n'); return 1"
    outcome = run_one(code, "python", {"kind": "function", "name": "solve"}, {})
    assert "oh no" in outcome.stderr
    assert outcome.return_value == 1


def test_run_captures_exception_message():
    code = "def solve():\n    raise ValueError('boom')"
    outcome = run_one(code, "python", {"kind": "function", "name": "solve"}, {})
    assert outcome.error is not None
    assert "boom" in outcome.error
    assert outcome.return_value is None


def test_run_respects_timeout():
    code = "import time\ndef solve():\n    time.sleep(5); return 1"
    outcome = run_one(code, "python", {"kind": "function", "name": "solve"}, {}, timeout_s=1)
    assert outcome.error is not None
    assert "time" in outcome.error.lower() or "timeout" in outcome.error.lower()


def test_run_truncates_stdout_over_cap():
    code = "def solve():\n    print('x' * 70000); return 1"
    outcome = run_one(code, "python", {"kind": "function", "name": "solve"}, {}, output_cap_bytes=64 * 1024)
    assert len(outcome.stdout) <= 64 * 1024 + 100  # allow trailing newline slop
    assert outcome.truncated is True


def test_run_class_based_ops():
    """LRU-style: ops + args parallel arrays, per-op return values collected."""
    code = (
        "class Counter:\n"
        "    def __init__(self, start): self.n = start\n"
        "    def inc(self, by): self.n += by; return self.n\n"
        "    def get(self): return self.n\n"
    )
    input_data = {
        "ops": ["Counter", "inc", "inc", "get"],
        "args": [[10], [2], [3], []],
    }
    outcome = run_one(code, "python", {"kind": "class_ops", "class": "Counter"}, input_data)
    assert outcome.return_value == [None, 12, 15, 15]
    assert outcome.error is None


def test_run_javascript_basic():
    code = "function solve(a, b) { console.log('js'); return a + b; }"
    outcome = run_one(code, "javascript", {"kind": "function", "name": "solve"}, {"a": 2, "b": 3})
    assert outcome.stdout.strip() == "js"
    assert outcome.return_value == 5
