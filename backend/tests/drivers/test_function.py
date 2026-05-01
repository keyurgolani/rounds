import json
import subprocess
import sys
import tempfile

from drivers.python.function import validate, wrapper_snippet


def test_validate_requires_name():
    assert "missing 'name'" in " ".join(validate({"kind": "function"}))


def test_validate_accepts_minimal_entry():
    assert validate({"kind": "function", "name": "foo"}) == []


def test_wrapper_invokes_function_with_kwargs():
    code = "def add(a, b): return a + b\n"
    snippet = wrapper_snippet({"kind": "function", "name": "add"})
    out = _run_python(code, snippet, {"a": 2, "b": 3})
    assert out == 5


def test_wrapper_invokes_function_with_positional_list():
    code = "def first(a, b, c): return a\n"
    snippet = wrapper_snippet({"kind": "function", "name": "first"})
    out = _run_python(code, snippet, [1, 2, 3])
    assert out == 1


def test_wrapper_invokes_function_with_scalar():
    code = "def square(x): return x * x\n"
    snippet = wrapper_snippet({"kind": "function", "name": "square"})
    out = _run_python(code, snippet, 4)
    assert out == 16


def _run_python(user_code, snippet, input_value):
    """Helper: build a wrapper, exec it, return parsed result."""
    wrapper = f"""
import json, sys
{user_code}
{snippet}
print(json.dumps(_drive(json.loads(sys.argv[1]))))
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(wrapper)
        path = f.name
    try:
        res = subprocess.run(
            [sys.executable, path, json.dumps(input_value)],
            capture_output=True, text=True, timeout=5,
        )
        return json.loads(res.stdout.strip().split("\n")[-1])
    finally:
        import os
        os.unlink(path)


from drivers.javascript.function import (
    validate as js_validate,
    wrapper_snippet as js_wrapper,
)


def test_js_validate_requires_name():
    assert "missing 'name'" in " ".join(js_validate({"kind": "function"}))


def test_js_wrapper_invokes_function_with_kwargs():
    code = "function add(a, b) { return a + b; }\n"
    snippet = js_wrapper({"kind": "function", "name": "add"})
    out = _run_js(code, snippet, {"a": 2, "b": 3})
    assert out == 5


def test_js_wrapper_invokes_function_with_positional_list():
    code = "function first(a, b, c) { return a; }\n"
    snippet = js_wrapper({"kind": "function", "name": "first"})
    out = _run_js(code, snippet, [1, 2, 3])
    assert out == 1


def test_js_wrapper_invokes_function_with_scalar():
    code = "function square(x) { return x * x; }\n"
    snippet = js_wrapper({"kind": "function", "name": "square"})
    out = _run_js(code, snippet, 4)
    assert out == 16


def _run_js(user_code, snippet, input_value):
    wrapper = f"""
{user_code}
{snippet}
console.log(JSON.stringify(_drive(JSON.parse(process.argv[2]))));
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(wrapper)
        path = f.name
    try:
        res = subprocess.run(
            ["node", path, json.dumps(input_value)],
            capture_output=True, text=True, timeout=5,
        )
        return json.loads(res.stdout.strip().split("\n")[-1])
    finally:
        import os
        os.unlink(path)
