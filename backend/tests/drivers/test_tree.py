import json
import os
import subprocess
import sys
import tempfile

from drivers.python.tree import validate as py_validate, wrapper_snippet as py_wrapper
from drivers.javascript.tree import wrapper_snippet as js_wrapper


DEFAULT_ENTRY = {
    "kind": "tree",
    "name": "invertTree",
    "params": [{"name": "root", "type": "node"}],
    "returns": "node",
}


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
    out = _run_py(code, snippet, {"root": [4, 2, 7, 1, 3, 6, 9]})
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
    out = _run_js(code, snippet, {"root": [4, 2, 7, 1, 3, 6, 9]})
    assert _level_order(out) == [4, 7, 2, 9, 6, 3, 1]


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
        # Only enqueue children if any non-null exists at this depth.
        queue.append(l)
        queue.append(r)
    while out and out[-1] is None:
        out.pop()
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
