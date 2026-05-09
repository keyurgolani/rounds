import json
import os
import subprocess
import sys
import tempfile

from drivers.python.linked_list import validate as py_validate, wrapper_snippet as py_wrapper
from drivers.javascript.linked_list import validate as js_validate, wrapper_snippet as js_wrapper


DEFAULT_ENTRY = {
    "kind": "linked_list",
    "name": "reverseList",
    "params": [{"name": "head", "type": "node"}],
    "returns": "node",
}


# ---- inline test helpers (the runtime drivers no longer accept shorthand) ----

def _list_to_verbose(values):
    if not values:
        return {"nodes": [], "entry": None}
    return {
        "nodes": [
            {"id": i, "fields": {"val": v}, "links": {"next": (i + 1) if i + 1 < len(values) else None}}
            for i, v in enumerate(values)
        ],
        "entry": 0,
    }


def test_validate_requires_name_and_params():
    errs = py_validate({"kind": "linked_list"})
    assert any("'name'" in e for e in errs)
    assert any("'params'" in e for e in errs)


def test_validate_accepts_default():
    assert py_validate(DEFAULT_ENTRY) == []


def test_py_reverses_singly_linked_list():
    code = (
        "def reverseList(head):\n"
        "    prev = None\n"
        "    while head:\n"
        "        nxt = head.next\n"
        "        head.next = prev\n"
        "        prev = head\n"
        "        head = nxt\n"
        "    return prev\n"
    )
    snippet = py_wrapper(DEFAULT_ENTRY)
    out = _run_py(code, snippet, {"head": _list_to_verbose([1, 2, 3])})
    assert _walk_chain(out) == [3, 2, 1]


def test_js_reverses_singly_linked_list():
    code = (
        "function reverseList(head) {\n"
        "  let prev = null;\n"
        "  while (head) {\n"
        "    const nxt = head.next;\n"
        "    head.next = prev;\n"
        "    prev = head;\n"
        "    head = nxt;\n"
        "  }\n"
        "  return prev;\n"
        "}\n"
    )
    snippet = js_wrapper(DEFAULT_ENTRY)
    out = _run_js(code, snippet, {"head": _list_to_verbose([1, 2, 3])})
    assert _walk_chain(out) == [3, 2, 1]


def test_py_supports_random_pointer_template():
    """LeetCode 138 — list with random pointer; verbose input shape."""
    entry = {
        "kind": "linked_list",
        "name": "copyRandomList",
        "params": [{"name": "head", "type": "node"}],
        "returns": "node",
        "node_template": {
            "name": "Node",
            "fields": [{"name": "val", "type": "int"}],
            "links": [
                {"name": "next", "arity": "single"},
                {"name": "random", "arity": "single", "nullable": True},
            ],
        },
    }
    code = (
        "def copyRandomList(head):\n"
        "    if head is None: return None\n"
        "    mp = {}\n"
        "    cur = head\n"
        "    while cur:\n"
        "        mp[id(cur)] = Node(cur.val)\n"
        "        cur = cur.next\n"
        "    cur = head\n"
        "    while cur:\n"
        "        if cur.next: mp[id(cur)].next = mp[id(cur.next)]\n"
        "        if cur.random: mp[id(cur)].random = mp[id(cur.random)]\n"
        "        cur = cur.next\n"
        "    return mp[id(head)]\n"
    )
    verbose = {
        "nodes": [
            {"id": 0, "fields": {"val": 7}, "links": {"next": 1, "random": None}},
            {"id": 1, "fields": {"val": 13}, "links": {"next": 2, "random": 0}},
            {"id": 2, "fields": {"val": 11}, "links": {"next": None, "random": 0}},
        ],
        "entry": 0,
    }
    snippet = py_wrapper(entry)
    out = _run_py(code, snippet, {"head": verbose})
    assert out["entry"] == 0
    assert len(out["nodes"]) == 3
    assert out["nodes"][0]["fields"] == {"val": 7}
    assert out["nodes"][1]["fields"] == {"val": 13}
    assert out["nodes"][2]["fields"] == {"val": 11}
    assert out["nodes"][1]["links"]["random"] == 0
    assert out["nodes"][2]["links"]["random"] == 0


def test_py_runtime_rejects_legacy_array_shape():
    """A flat array reaching the linked_list driver at runtime must be rejected."""
    code = "def reverseList(head):\n    return head\n"
    snippet = py_wrapper(DEFAULT_ENTRY)
    err = _run_py_expect_error(code, snippet, {"head": [1, 2, 3]})
    assert "verbose JSON" in err and "linked_list driver" in err, err


def test_validate_rejects_legacy_input_shape():
    """An entry with input_shape='linked_list_array' is rejected at build time."""
    bad = {**DEFAULT_ENTRY, "input_shape": "linked_list_array"}
    errors = py_validate(bad)
    assert any("input_shape" in e and "linked_list_array" in e for e in errors), errors


def test_js_validate_rejects_legacy_input_shape():
    bad = {**DEFAULT_ENTRY, "input_shape": "linked_list_array"}
    errors = js_validate(bad)
    assert any("input_shape" in e and "linked_list_array" in e for e in errors), errors


ARRAY_OUT_ENTRY = {
    "kind": "linked_list",
    "name": "identity",
    "params": [{"name": "head", "type": "node"}],
    "returns": "node",
    "output_shape": "linked_list_array",
}


def test_py_output_shape_linked_list_array_identity():
    code = (
        "def identity(head):\n"
        "    return head\n"
    )
    snippet = py_wrapper(ARRAY_OUT_ENTRY)
    out = _run_py(code, snippet, {"head": _list_to_verbose([1, 2, 3])})
    assert out == [1, 2, 3]


def test_py_output_shape_linked_list_array_reverse():
    code = (
        "def identity(head):\n"
        "    prev = None\n"
        "    while head:\n"
        "        nxt = head.next\n"
        "        head.next = prev\n"
        "        prev = head\n"
        "        head = nxt\n"
        "    return prev\n"
    )
    snippet = py_wrapper(ARRAY_OUT_ENTRY)
    out = _run_py(code, snippet, {"head": _list_to_verbose([1, 2, 3])})
    assert out == [3, 2, 1]


def test_py_output_shape_linked_list_array_empty():
    code = (
        "def identity(head):\n"
        "    return head\n"
    )
    snippet = py_wrapper(ARRAY_OUT_ENTRY)
    out = _run_py(code, snippet, {"head": _list_to_verbose([])})
    assert out == []


def test_validate_rejects_unknown_output_shape():
    bad = {**DEFAULT_ENTRY, "output_shape": "totally_made_up"}
    errors = py_validate(bad)
    assert any("output_shape" in e and "totally_made_up" in e for e in errors), errors


def test_validate_accepts_known_output_shapes():
    for shape in ("verbose", "linked_list_array"):
        entry = {**DEFAULT_ENTRY, "output_shape": shape}
        assert py_validate(entry) == []


def test_js_validate_rejects_unknown_output_shape():
    bad = {**DEFAULT_ENTRY, "output_shape": "totally_made_up"}
    errors = js_validate(bad)
    assert any("output_shape" in e and "totally_made_up" in e for e in errors), errors


def test_js_validate_accepts_known_output_shapes():
    for shape in ("verbose", "linked_list_array"):
        entry = {**DEFAULT_ENTRY, "output_shape": shape}
        assert js_validate(entry) == []


def test_js_output_shape_linked_list_array_identity():
    code = (
        "function identity(head) { return head; }\n"
    )
    snippet = js_wrapper(ARRAY_OUT_ENTRY)
    out = _run_js(code, snippet, {"head": _list_to_verbose([1, 2, 3])})
    assert out == [1, 2, 3]


def test_js_output_shape_linked_list_array_reverse():
    code = (
        "function identity(head) {\n"
        "  let prev = null;\n"
        "  while (head) { const n = head.next; head.next = prev; prev = head; head = n; }\n"
        "  return prev;\n"
        "}\n"
    )
    snippet = js_wrapper(ARRAY_OUT_ENTRY)
    out = _run_js(code, snippet, {"head": _list_to_verbose([1, 2, 3])})
    assert out == [3, 2, 1]


def test_js_output_shape_linked_list_array_empty():
    code = "function identity(head) { return head; }\n"
    snippet = js_wrapper(ARRAY_OUT_ENTRY)
    out = _run_js(code, snippet, {"head": _list_to_verbose([])})
    assert out == []


def test_js_runtime_rejects_legacy_array_shape():
    code = "function reverseList(head) { return head; }\n"
    snippet = js_wrapper(DEFAULT_ENTRY)
    err = _run_js_expect_error(code, snippet, {"head": [1, 2, 3]})
    assert "verbose JSON" in err and "linked_list driver" in err, err


def _walk_chain(verbose):
    if verbose.get("entry") is None:
        return []
    by_id = {n["id"]: n for n in verbose["nodes"]}
    out = []
    cur = verbose["entry"]
    while cur is not None:
        node = by_id[cur]
        out.append(node["fields"]["val"])
        cur = node["links"].get("next")
    return out


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
        if res.returncode != 0:
            raise AssertionError(f"non-zero exit: {res.stderr}")
        return json.loads(res.stdout.strip().split("\n")[-1])
    finally:
        os.unlink(path)


def _run_py_expect_error(user_code, snippet, input_value):
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
        assert res.returncode != 0, f"expected error, got success: {res.stdout!r}"
        return res.stderr
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
        if res.returncode != 0:
            raise AssertionError(f"non-zero exit: {res.stderr}")
        return json.loads(res.stdout.strip().split("\n")[-1])
    finally:
        os.unlink(path)


def _run_js_expect_error(user_code, snippet, input_value):
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
        assert res.returncode != 0, f"expected error, got success: {res.stdout!r}"
        return res.stderr
    finally:
        os.unlink(path)
