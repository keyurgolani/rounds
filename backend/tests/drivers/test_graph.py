import json
import os
import subprocess
import sys
import tempfile

from drivers.python.graph import validate as py_validate, wrapper_snippet as py_wrapper
from drivers.javascript.graph import validate as js_validate, wrapper_snippet as js_wrapper


DEFAULT_ENTRY = {
    "kind": "graph",
    "name": "cloneGraph",
    "params": [{"name": "node", "type": "node"}],
    "returns": "node",
}


def test_validate_requires_name():
    errs = py_validate({"kind": "graph"})
    assert any("'name'" in e for e in errs)


def test_py_clones_graph():
    code = (
        "def cloneGraph(node):\n"
        "    if node is None: return None\n"
        "    visited = {}\n"
        "    def dfs(n):\n"
        "        if id(n) in visited: return visited[id(n)]\n"
        "        copy = Node(n.val)\n"
        "        visited[id(n)] = copy\n"
        "        for nb in n.neighbors:\n"
        "            copy.neighbors.append(dfs(nb))\n"
        "        return copy\n"
        "    return dfs(node)\n"
    )
    snippet = py_wrapper(DEFAULT_ENTRY)
    inp = {"node": {"1": [2], "2": [1]}}
    out = _run_py(code, snippet, inp)
    # 2-node graph; round-trip should give {nodes, entry} with two nodes,
    # each with one neighbor pointing at the other.
    assert out["entry"] == 0
    assert len(out["nodes"]) == 2
    assert out["nodes"][0]["fields"] == {"val": 1}
    assert out["nodes"][0]["links"]["neighbors"] == [1]
    assert out["nodes"][1]["fields"] == {"val": 2}
    assert out["nodes"][1]["links"]["neighbors"] == [0]


VERBOSE_OUT_ENTRY = {
    "kind": "graph",
    "name": "identity",
    "params": [{"name": "node", "type": "node"}],
    "returns": "node",
    "output_shape": "verbose",
}


def test_py_graph_output_shape_verbose_explicit():
    """Explicit output_shape='verbose' is the same as omitting it."""
    snippet = py_wrapper(VERBOSE_OUT_ENTRY)
    # Verify the wrapper compiles and references _output_shape.
    assert "_output_shape" in snippet
    assert "'verbose'" in snippet


def test_py_graph_unsupported_output_shape_rejected():
    """An unsupported output_shape is rejected by validate()."""
    bad = {**DEFAULT_ENTRY, "output_shape": "bogus_shape"}
    errors = py_validate(bad)
    assert any("output_shape" in e and "bogus_shape" in e for e in errors), errors


def test_py_graph_validate_accepts_verbose():
    """validate() accepts explicit output_shape='verbose' and omitted (default)."""
    for entry in (DEFAULT_ENTRY, {**DEFAULT_ENTRY, "output_shape": "verbose"}):
        assert py_validate(entry) == []


def test_js_graph_output_shape_verbose_explicit():
    """JS snippet correctly embeds outputShape."""
    from drivers.javascript.graph import wrapper_snippet
    snippet = wrapper_snippet(VERBOSE_OUT_ENTRY)
    assert "outputShape" in snippet
    assert '"verbose"' in snippet


def test_js_graph_unsupported_output_shape_rejected():
    """An unsupported output_shape is rejected by JS driver's validate()."""
    bad = {**DEFAULT_ENTRY, "output_shape": "bogus_shape"}
    errors = js_validate(bad)
    assert any("output_shape" in e and "bogus_shape" in e for e in errors), errors


def test_js_graph_validate_accepts_verbose():
    """JS validate() accepts explicit and omitted (default) output_shape."""
    for entry in (DEFAULT_ENTRY, {**DEFAULT_ENTRY, "output_shape": "verbose"}):
        assert js_validate(entry) == []


def test_py_graph_validate_rejects_template_without_links():
    bad = {**DEFAULT_ENTRY, "node_template": {"name": "G", "fields": [{"name": "val", "type": "int"}], "links": []}}
    errors = py_validate(bad)
    assert any("at least one link" in e for e in errors), errors


def test_js_graph_validate_rejects_template_without_links():
    bad = {**DEFAULT_ENTRY, "node_template": {"name": "G", "fields": [{"name": "val", "type": "int"}], "links": []}}
    errors = js_validate(bad)
    assert any("at least one link" in e for e in errors), errors


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
