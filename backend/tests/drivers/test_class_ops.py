import json
import os
import subprocess
import sys
import tempfile

from drivers.python.class_ops import validate, wrapper_snippet


def test_validate_requires_class():
    errors = validate({"kind": "class_ops"})
    assert any("'class'" in e for e in errors)


def test_validate_accepts_minimal_entry():
    assert validate({"kind": "class_ops", "class": "Foo"}) == []


def test_wrapper_executes_op_sequence():
    code = (
        "class Counter:\n"
        "    def __init__(self, start): self.n = start\n"
        "    def inc(self, by): self.n += by; return self.n\n"
    )
    snippet = wrapper_snippet({"kind": "class_ops", "class": "Counter"})
    out = _run_py(code, snippet, {
        "ops": ["Counter", "inc", "inc"],
        "args": [[10], [2], [3]],
    })
    assert out == [None, 12, 15]


def test_wrapper_with_helper_class_does_not_misroute():
    """LRU regression — Node helper class must not be the dispatch target."""
    code = (
        "class Node:\n"
        "    def __init__(self, key=0, value=0):\n"
        "        self.key = key; self.value = value\n"
        "        self.next = None; self.previous = None\n"
        "class LRUCache:\n"
        "    def __init__(self, capacity):\n"
        "        self.capacity = capacity; self.cache = {}\n"
        "    def get(self, key):\n"
        "        return self.cache.get(key, -1)\n"
        "    def put(self, key, value):\n"
        "        self.cache[key] = value\n"
    )
    snippet = wrapper_snippet({"kind": "class_ops", "class": "LRUCache"})
    out = _run_py(code, snippet, {
        "ops": ["LRUCache", "put", "get"],
        "args": [[2], [1, 1], [1]],
    })
    assert out == [None, None, 1]


def _run_py(user_code, snippet, input_value):
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
        if res.returncode != 0:
            raise AssertionError(f"non-zero exit: {res.stderr}")
        return json.loads(res.stdout.strip().split("\n")[-1])
    finally:
        os.unlink(path)


from drivers.javascript.class_ops import (
    validate as js_validate,
    wrapper_snippet as js_wrapper,
)


def test_js_validate_requires_class():
    assert any("'class'" in e for e in js_validate({"kind": "class_ops"}))


def test_js_wrapper_executes_op_sequence():
    code = (
        "class Counter {\n"
        "  constructor(start) { this.n = start; }\n"
        "  inc(by) { this.n += by; return this.n; }\n"
        "}\n"
    )
    snippet = js_wrapper({"kind": "class_ops", "class": "Counter"})
    out = _run_js(code, snippet, {
        "ops": ["Counter", "inc", "inc"],
        "args": [[10], [2], [3]],
    })
    assert out == [None, 12, 15]


def test_js_wrapper_with_helper_class():
    code = (
        "class Node { constructor(k=0,v=0){this.k=k;this.v=v;} }\n"
        "class LRUCache {\n"
        "  constructor(cap) { this.cache = new Map(); this.cap = cap; }\n"
        "  get(k) { return this.cache.has(k) ? this.cache.get(k) : -1; }\n"
        "  put(k, v) { this.cache.set(k, v); return null; }\n"
        "}\n"
    )
    snippet = js_wrapper({"kind": "class_ops", "class": "LRUCache"})
    out = _run_js(code, snippet, {
        "ops": ["LRUCache", "put", "get"],
        "args": [[2], [1, 1], [1]],
    })
    assert out == [None, None, 1]


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
        if res.returncode != 0:
            raise AssertionError(f"non-zero exit: {res.stderr}")
        return json.loads(res.stdout.strip().split("\n")[-1])
    finally:
        os.unlink(path)
