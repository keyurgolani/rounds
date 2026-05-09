import json
import os
import subprocess
import sys
import tempfile

from drivers.python.tree import validate as py_validate, wrapper_snippet as py_wrapper
from drivers.javascript.tree import validate as js_validate, wrapper_snippet as js_wrapper


DEFAULT_ENTRY = {
    "kind": "tree",
    "name": "invertTree",
    "params": [{"name": "root", "type": "node"}],
    "returns": "node",
}


# ---- inline test helpers (the runtime drivers no longer accept shorthand) ----

def _level_order_to_verbose(values):
    if not values:
        return {"nodes": [], "entry": None}
    nodes = []
    id_for_pos = {}
    for pos, v in enumerate(values):
        if v is None:
            continue
        id_for_pos[pos] = len(nodes)
        nodes.append({
            "id": len(nodes),
            "fields": {"val": v},
            "links": {"left": None, "right": None},
        })
    if 0 not in id_for_pos:
        return {"nodes": [], "entry": None}
    queue = [(0, id_for_pos[0])]
    cursor = 1
    while queue and cursor < len(values):
        _, parent_id = queue.pop(0)
        for link_name in ("left", "right"):
            if cursor >= len(values):
                break
            child_pos = cursor
            cursor += 1
            if values[child_pos] is None:
                continue
            child_id = id_for_pos[child_pos]
            nodes[parent_id]["links"][link_name] = child_id
            queue.append((child_pos, child_id))
    return {"nodes": nodes, "entry": 0}


def test_validate_requires_name():
    errs = py_validate({"kind": "tree"})
    assert any("'name'" in e for e in errs)


def test_py_inverts_binary_tree():
    code = (
        "def invertTree(root):\n"
        "    if root is None: return None\n"
        "    root.left, root.right = invertTree(root.right), invertTree(root.left)\n"
        "    return root\n"
    )
    snippet = py_wrapper(DEFAULT_ENTRY)
    out = _run_py(code, snippet, {"root": _level_order_to_verbose([4, 2, 7, 1, 3, 6, 9])})
    assert _level_order(out) == [4, 7, 2, 9, 6, 3, 1]


def test_js_inverts_binary_tree():
    code = (
        "function invertTree(root) {\n"
        "  if (!root) return null;\n"
        "  const l = invertTree(root.right);\n"
        "  const r = invertTree(root.left);\n"
        "  root.left = l; root.right = r;\n"
        "  return root;\n"
        "}\n"
    )
    snippet = js_wrapper(DEFAULT_ENTRY)
    out = _run_js(code, snippet, {"root": _level_order_to_verbose([4, 2, 7, 1, 3, 6, 9])})
    assert _level_order(out) == [4, 7, 2, 9, 6, 3, 1]


def test_py_runtime_rejects_legacy_array_shape():
    """A level-order array reaching the tree driver at runtime must be rejected."""
    code = "def invertTree(root):\n    return root\n"
    snippet = py_wrapper(DEFAULT_ENTRY)
    err = _run_py_expect_error(code, snippet, {"root": [4, 2, 7, 1, 3, 6, 9]})
    assert "verbose JSON" in err and "tree driver" in err, err


def test_validate_rejects_legacy_input_shape():
    bad = {**DEFAULT_ENTRY, "input_shape": "tree_level_order"}
    errors = py_validate(bad)
    assert any("input_shape" in e and "tree_level_order" in e for e in errors), errors


def test_js_validate_rejects_legacy_input_shape():
    bad = {**DEFAULT_ENTRY, "input_shape": "tree_level_order"}
    errors = js_validate(bad)
    assert any("input_shape" in e and "tree_level_order" in e for e in errors), errors


def _level_order(verbose):
    """Walk the verbose graph in level-order to compare against expected list."""
    by_id = {n["id"]: n for n in verbose["nodes"]}
    if verbose.get("entry") is None:
        return []
    out = []
    queue = [verbose["entry"]]
    while queue:
        cur = queue.pop(0)
        if cur is None:
            out.append(None); continue
        node = by_id[cur]
        out.append(node["fields"]["val"])
        l = node["links"].get("left"); r = node["links"].get("right")
        queue.append(l)
        queue.append(r)
    while out and out[-1] is None:
        out.pop()
    return out


LEVEL_ORDER_OUT_ENTRY = {
    "kind": "tree",
    "name": "identity",
    "params": [{"name": "root", "type": "node"}],
    "returns": "node",
    "output_shape": "tree_level_order",
}


def test_py_tree_output_shape_level_order_round_trip():
    code = (
        "def identity(root):\n"
        "    return root\n"
    )
    snippet = py_wrapper(LEVEL_ORDER_OUT_ENTRY)
    out = _run_py(code, snippet, {"root": _level_order_to_verbose([3, 9, 20, None, None, 15, 7])})
    assert out == [3, 9, 20, None, None, 15, 7]


def test_py_tree_output_shape_level_order_trims_trailing_nulls():
    code = (
        "def identity(root):\n"
        "    return root\n"
    )
    snippet = py_wrapper(LEVEL_ORDER_OUT_ENTRY)
    out = _run_py(code, snippet, {"root": _level_order_to_verbose([1, 2, 3, None, None, 4, 5])})
    assert out == [1, 2, 3, None, None, 4, 5]


def test_py_tree_output_shape_level_order_empty():
    code = (
        "def identity(root):\n"
        "    return root\n"
    )
    snippet = py_wrapper(LEVEL_ORDER_OUT_ENTRY)
    out = _run_py(code, snippet, {"root": _level_order_to_verbose([])})
    assert out == []


def test_py_tree_output_shape_invert():
    code = (
        "def identity(root):\n"
        "    if root is None: return None\n"
        "    root.left, root.right = root.right, root.left\n"
        "    if root.left: identity(root.left)\n"
        "    if root.right: identity(root.right)\n"
        "    return root\n"
    )
    snippet = py_wrapper(LEVEL_ORDER_OUT_ENTRY)
    out = _run_py(code, snippet, {"root": _level_order_to_verbose([1, 2, 3])})
    assert out == [1, 3, 2]


def test_py_tree_validate_rejects_unknown_output_shape():
    bad = {**DEFAULT_ENTRY, "output_shape": "totally_made_up"}
    errors = py_validate(bad)
    assert any("output_shape" in e and "totally_made_up" in e for e in errors), errors


def test_py_tree_validate_accepts_known_output_shapes():
    for shape in ("verbose", "tree_level_order"):
        entry = {**DEFAULT_ENTRY, "output_shape": shape}
        assert py_validate(entry) == []


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


def test_js_tree_output_shape_level_order_round_trip():
    code = "function identity(root) { return root; }\n"
    snippet = js_wrapper(LEVEL_ORDER_OUT_ENTRY)
    out = _run_js(code, snippet, {"root": _level_order_to_verbose([3, 9, 20, None, None, 15, 7])})
    assert out == [3, 9, 20, None, None, 15, 7]


def test_js_tree_output_shape_level_order_invert():
    code = (
        "function identity(root) {\n"
        "  if (!root) return null;\n"
        "  const t = root.left; root.left = root.right; root.right = t;\n"
        "  if (root.left) identity(root.left);\n"
        "  if (root.right) identity(root.right);\n"
        "  return root;\n"
        "}\n"
    )
    snippet = js_wrapper(LEVEL_ORDER_OUT_ENTRY)
    out = _run_js(code, snippet, {"root": _level_order_to_verbose([1, 2, 3])})
    assert out == [1, 3, 2]


def test_js_tree_output_shape_level_order_empty():
    code = "function identity(root) { return root; }\n"
    snippet = js_wrapper(LEVEL_ORDER_OUT_ENTRY)
    out = _run_js(code, snippet, {"root": _level_order_to_verbose([])})
    assert out == []


def test_js_tree_validate_rejects_unknown_output_shape():
    bad = {**DEFAULT_ENTRY, "output_shape": "totally_made_up"}
    errors = js_validate(bad)
    assert any("output_shape" in e and "totally_made_up" in e for e in errors), errors


def test_js_tree_validate_accepts_known_output_shapes():
    for shape in ("verbose", "tree_level_order"):
        entry = {**DEFAULT_ENTRY, "output_shape": shape}
        assert js_validate(entry) == []


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


def test_py_tree_output_shape_level_order_actually_trims_trailing_nulls():
    """Verify the trim path actually fires by inverting [1,2,None,3] —
    BFS yields [1, None, 2, None, 3, None, None] before trim, which
    becomes [1, None, 2, None, 3] after trim."""
    code = (
        "def identity(root):\n"
        "    if root is None: return None\n"
        "    root.left, root.right = root.right, root.left\n"
        "    if root.left: identity(root.left)\n"
        "    if root.right: identity(root.right)\n"
        "    return root\n"
    )
    snippet = py_wrapper(LEVEL_ORDER_OUT_ENTRY)
    out = _run_py(code, snippet, {"root": _level_order_to_verbose([1, 2, None, 3])})
    assert out == [1, None, 2, None, 3]


def test_py_tree_validate_rejects_template_without_links():
    bad = {**DEFAULT_ENTRY, "node_template": {"name": "T", "fields": [{"name": "val", "type": "int"}], "links": []}}
    errors = py_validate(bad)
    assert any("at least one link" in e for e in errors), errors


def test_js_tree_validate_rejects_template_without_links():
    bad = {**DEFAULT_ENTRY, "node_template": {"name": "T", "fields": [{"name": "val", "type": "int"}], "links": []}}
    errors = js_validate(bad)
    assert any("at least one link" in e for e in errors), errors
