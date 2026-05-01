import json
import os
import subprocess
import sys
import tempfile

from drivers.python._node_codegen import emit_class, emit_inflate, emit_deflate
from drivers.javascript._node_codegen import (
    emit_class as js_emit_class,
    emit_inflate as js_emit_inflate,
    emit_deflate as js_emit_deflate,
)


def test_emit_class_includes_name_and_fields():
    template = {"name": "Node",
                "fields": [{"name": "val", "type": "int"}],
                "links": [{"name": "next", "arity": "single"}]}
    src = emit_class(template)
    assert "class Node:" in src
    assert "self.val = val" in src
    assert "self.next = next" in src


def test_emit_class_with_list_link_default():
    template = {"name": "Node",
                "fields": [{"name": "val", "type": "int"}],
                "links": [{"name": "children", "arity": "list"}]}
    src = emit_class(template)
    assert "self.children = children if children is not None else []" in src


def test_inflate_then_deflate_round_trips_singly_linked():
    template = {"name": "Node",
                "fields": [{"name": "val", "type": "int"}],
                "links": [{"name": "next", "arity": "single"}]}
    verbose = {"nodes": [
        {"id": 0, "fields": {"val": 1}, "links": {"next": 1}},
        {"id": 1, "fields": {"val": 2}, "links": {"next": None}},
    ], "entry": 0}
    user_code = emit_class(template) + emit_inflate(template) + emit_deflate(template)
    out = _run_py(user_code, f"head = _inflate({verbose!r})\n"
                             f"print(json.dumps(_deflate(head)))")
    assert out == verbose


def _run_py(user_code, action):
    wrapper = f"""
import json, sys
{user_code}
{action}
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(wrapper); path = f.name
    try:
        res = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=5)
        if res.returncode != 0:
            raise AssertionError(f"non-zero exit: {res.stderr}")
        return json.loads(res.stdout.strip().split("\n")[-1])
    finally:
        os.unlink(path)


def test_js_inflate_then_deflate_round_trips_singly_linked():
    template = {"name": "Node",
                "fields": [{"name": "val", "type": "int"}],
                "links": [{"name": "next", "arity": "single"}]}
    verbose = {"nodes": [
        {"id": 0, "fields": {"val": 1}, "links": {"next": 1}},
        {"id": 1, "fields": {"val": 2}, "links": {"next": None}},
    ], "entry": 0}
    user_code = js_emit_class(template) + js_emit_inflate(template) + js_emit_deflate(template)
    action = (f"const head = _inflate({json.dumps(verbose)});\n"
              f"console.log(JSON.stringify(_deflate(head)));")
    out = _run_js(user_code, action)
    assert out == verbose


def _run_js(user_code, action):
    wrapper = f"""
{user_code}
{action}
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".js", delete=False) as f:
        f.write(wrapper); path = f.name
    try:
        res = subprocess.run(["node", path], capture_output=True, text=True, timeout=5)
        if res.returncode != 0:
            raise AssertionError(f"non-zero exit: {res.stderr}")
        return json.loads(res.stdout.strip().split("\n")[-1])
    finally:
        os.unlink(path)
