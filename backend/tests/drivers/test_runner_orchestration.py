from runner import run_one


def test_run_one_routes_to_function_driver_python():
    code = "def add(a, b): return a + b\n"
    out = run_one(code, "python", {"kind": "function", "name": "add"}, {"a": 2, "b": 3})
    assert out.return_value == 5
    assert out.error is None


def test_run_one_routes_to_class_ops_driver_python():
    code = (
        "class Counter:\n"
        "    def __init__(self, s): self.n = s\n"
        "    def inc(self, by): self.n += by; return self.n\n"
    )
    out = run_one(code, "python", {"kind": "class_ops", "class": "Counter"},
                  {"ops": ["Counter", "inc"], "args": [[1], [2]]})
    assert out.return_value == [None, 3]


def test_run_one_returns_validate_error_on_bad_entry():
    out = run_one("def f(): pass", "python", {"kind": "function"}, {})
    assert out.error and "missing 'name'" in out.error


def test_run_one_unsupported_language_returns_error():
    out = run_one("", "ruby", {"kind": "function", "name": "f"}, {})
    assert out.error and "ruby" in out.error.lower()
