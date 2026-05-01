import json
import os
import subprocess
import sys
import tempfile

from drivers.python.custom import validate as py_validate, wrapper_snippet as py_wrapper
from drivers.javascript.custom import validate as js_validate, wrapper_snippet as js_wrapper


def test_validate_requires_drivers_for_target_language():
    errs = py_validate({"kind": "custom"})
    assert any("python" in e for e in errs)


def test_validate_accepts_when_python_driver_present():
    assert py_validate({"kind": "custom",
                        "drivers": {"python": "def _drive(i): return i\n"}}) == []


def test_py_wrapper_inlines_driver_code():
    user = "def double(x): return x * 2\n"
    entry = {"kind": "custom",
             "drivers": {"python": "def _drive(inp):\n    return double(inp['x']) + 1\n"}}
    snippet = py_wrapper(entry)
    out = _run_py(user, snippet, {"x": 4})
    assert out == 9  # double(4) + 1


def test_js_wrapper_inlines_driver_code():
    user = "function double(x) { return x * 2; }\n"
    entry = {"kind": "custom",
             "drivers": {"javascript": "function _drive(inp) { return double(inp.x) + 1; }\n"}}
    snippet = js_wrapper(entry)
    out = _run_js(user, snippet, {"x": 4})
    assert out == 9


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
