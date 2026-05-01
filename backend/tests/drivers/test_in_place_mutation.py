import json
import os
import subprocess
import sys
import tempfile

from drivers.python.in_place_mutation import validate as py_validate, wrapper_snippet as py_wrapper
from drivers.javascript.in_place_mutation import validate as js_validate, wrapper_snippet as js_wrapper


def test_validate_requires_name_and_mutates():
    errs = py_validate({"kind": "in_place_mutation"})
    assert any("'name'" in e for e in errs)
    assert any("'mutates'" in e for e in errs)


def test_validate_accepts_minimal_entry():
    assert py_validate({"kind": "in_place_mutation", "name": "f", "mutates": "x"}) == []


def test_py_wrapper_returns_mutated_arg():
    code = "def reverseString(s):\n    s.reverse()\n"
    snippet = py_wrapper({"kind": "in_place_mutation", "name": "reverseString", "mutates": "s"})
    out = _run_py(code, snippet, {"s": ["h", "e", "l", "l", "o"]})
    assert out == ["o", "l", "l", "e", "h"]


def test_js_wrapper_returns_mutated_arg():
    code = "function reverseString(s) { s.reverse(); }\n"
    snippet = js_wrapper({"kind": "in_place_mutation", "name": "reverseString", "mutates": "s"})
    out = _run_js(code, snippet, {"s": ["h", "e", "l", "l", "o"]})
    assert out == ["o", "l", "l", "e", "h"]


def _run_py(user_code, snippet, input_value):
    wrapper = f"""
import json, sys
{user_code}
{snippet}
print(json.dumps(_drive(json.loads(sys.argv[1]))))
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(wrapper); path = f.name
    try:
        res = subprocess.run([sys.executable, path, json.dumps(input_value)],
                             capture_output=True, text=True, timeout=5)
        return json.loads(res.stdout.strip().split("\n")[-1])
    finally:
        os.unlink(path)


def _run_js(user_code, snippet, input_value):
    wrapper = f"""
{user_code}
{snippet}
console.log(JSON.stringify(_drive(JSON.parse(process.argv[2]))));
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(wrapper); path = f.name
    try:
        res = subprocess.run(["node", path, json.dumps(input_value)],
                             capture_output=True, text=True, timeout=5)
        return json.loads(res.stdout.strip().split("\n")[-1])
    finally:
        os.unlink(path)
