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


def test_run_class_ops_dispatches_to_the_named_class_past_a_helper_class():
    # The class an entry names runs; a helper class beside it is never
    # mistaken for it (a regression the request path's tests carried until
    # ROUNDS-00A-L03 PR 4).
    from tests.test_coding_endpoints import LRU_CODE

    input_data = {
        "ops": ["LRUCache", "put", "put", "get", "put", "get", "get"],
        "args": [[2], [1, 1], [2, 2], [1], [3, 3], [2], [3]],
    }
    outcome = run_one(LRU_CODE, "python", {"kind": "class_ops", "class": "LRUCache"}, input_data)
    assert outcome.error is None
    assert outcome.return_value == [None, None, None, 1, None, -1, 3]


def test_run_names_an_entry_without_its_function_name():
    outcome = run_one("def f(): pass", "python", {"kind": "function"}, {})
    assert outcome.error and "missing 'name'" in outcome.error


def test_run_javascript_basic():
    code = "function solve(a, b) { console.log('js'); return a + b; }"
    outcome = run_one(code, "javascript", {"kind": "function", "name": "solve"}, {"a": 2, "b": 3})
    assert outcome.stdout.strip() == "js"
    assert outcome.return_value == 5


def test_run_one_add_two_numbers_real_listnode():
    """End-to-end: real ListNode chains in, flat array out."""
    code = (
        "def add_two_numbers(l1, l2):\n"
        "    dummy = ListNode()\n"
        "    tail = dummy\n"
        "    carry = 0\n"
        "    while l1 or l2 or carry:\n"
        "        d1 = l1.val if l1 else 0\n"
        "        d2 = l2.val if l2 else 0\n"
        "        total = d1 + d2 + carry\n"
        "        tail.next = ListNode(total % 10)\n"
        "        tail = tail.next\n"
        "        carry = total // 10\n"
        "        l1 = l1.next if l1 else None\n"
        "        l2 = l2.next if l2 else None\n"
        "    return dummy.next\n"
    )
    entry = {
        "kind": "linked_list",
        "name": "add_two_numbers",
        "params": [
            {"name": "l1", "type": "node"},
            {"name": "l2", "type": "node"},
        ],
        "output_shape": "linked_list_array",
    }

    def _list(values):
        return {
            "nodes": [
                {"id": i, "fields": {"val": v}, "links": {"next": (i + 1) if i + 1 < len(values) else None}}
                for i, v in enumerate(values)
            ],
            "entry": 0 if values else None,
        }

    outcome = run_one(code, "python", entry, {"l1": _list([2, 4, 3]), "l2": _list([5, 6, 4])})
    assert outcome.error is None, outcome.error
    assert outcome.return_value == [7, 0, 8]


# ---- the result comes back on its own channel (ROUNDS-00A-L01) ---------------------------

MORE_THAN_KEPT = 5 * 1024 * 1024  # each output stream keeps its first 4 MiB


def test_a_correct_python_result_survives_more_output_than_is_kept():
    code = f"def solve(x):\n    print('x' * {MORE_THAN_KEPT})\n    return x + 1"
    outcome = run_one(code, "python", {"kind": "function", "name": "solve"}, {"x": 41}, timeout_s=10)
    assert outcome.error is None, outcome.error
    assert outcome.return_value == 42
    assert outcome.truncated is True
    assert len(outcome.stdout) <= 64 * 1024


def test_a_correct_javascript_result_survives_more_output_than_is_kept():
    code = f"function solve(x) {{ process.stdout.write('y'.repeat({MORE_THAN_KEPT})); return x * 2; }}"
    outcome = run_one(code, "javascript", {"kind": "function", "name": "solve"}, {"x": 21}, timeout_s=10)
    assert outcome.error is None, outcome.error
    assert outcome.return_value == 42
    assert outcome.truncated is True


def test_marker_like_output_doesnt_change_the_result():
    code = "def solve():\n    print('__RUNNER_RESULT__999')\n    return 1"
    outcome = run_one(code, "python", {"kind": "function", "name": "solve"}, {})
    assert outcome.return_value == 1
    assert "__RUNNER_RESULT__999" in outcome.stdout


def test_a_program_that_exits_before_returning_has_no_result():
    code = "import os\ndef solve():\n    os._exit(0)"
    outcome = run_one(code, "python", {"kind": "function", "name": "solve"}, {})
    assert outcome.return_value is None
    assert outcome.error == "The program ended without returning a result."


def test_a_result_over_4_mib_is_refused():
    code = f"def solve():\n    return 'r' * {4 * 1024 * 1024}"
    outcome = run_one(code, "python", {"kind": "function", "name": "solve"}, {}, timeout_s=10)
    assert outcome.return_value is None
    assert outcome.error == "The result is over 4 MiB."


def test_a_result_path_swapped_for_a_symlink_is_not_read(tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text('"symlinked-sentinel"')
    code = (
        "import os, sys\n"
        "def solve():\n"
        f"    os.symlink({str(secret)!r}, sys.argv[2])\n"
        "    os._exit(0)\n"
    )
    outcome = run_one(code, "python", {"kind": "function", "name": "solve"}, {})
    assert outcome.return_value is None
    assert outcome.error == "The program ended without returning a result."
    assert "symlinked-sentinel" not in outcome.stdout + outcome.stderr


# ---- a job's run (ROUNDS-00A-L03 PR 2) -------------------------------------------


def test_a_run_its_job_stops_says_stopped_and_leaves_no_scratch_or_group():
    import os
    import threading
    import time

    from app import sandbox

    control = sandbox.Control()
    threading.Timer(0.3, control.stop.set).start()
    started = time.monotonic()
    outcome = run_one("import time\ndef solve():\n    time.sleep(30)", "python",
                      {"kind": "function", "name": "solve"}, {}, timeout_s=30, control=control)
    assert time.monotonic() - started < 10
    assert outcome.stopped is True and outcome.timed_out is False and outcome.return_value is None
    assert control.pid is not None and sandbox.group_gone(control.pid, wait_s=5)
    assert control.cwd is not None and not os.path.exists(control.cwd)


def test_a_run_out_of_time_says_timed_out_never_stopped():
    from app import sandbox

    control = sandbox.Control()
    outcome = run_one("def solve():\n    while True:\n        pass", "python", {"kind": "function", "name": "solve"},
                      {}, timeout_s=1, control=control)
    assert outcome.timed_out is True and outcome.stopped is False and outcome.error is not None


def test_a_run_without_a_control_is_as_it_was():
    outcome = run_one("def solve():\n    return 3", "python", {"kind": "function", "name": "solve"}, {})
    assert (outcome.return_value, outcome.error, outcome.timed_out, outcome.stopped) == (3, None, False, False)
