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


# ---- inline test helpers (the runtime drivers no longer accept shorthand) ----

def _adj_to_verbose(adj):
    keys = list(adj.keys())
    id_for_key = {k: i for i, k in enumerate(keys)}
    nodes = []
    for i, k in enumerate(keys):
        try:
            val = int(k)
        except (TypeError, ValueError):
            val = k
        neighbor_ids = [id_for_key[str(n)] for n in adj[k] if str(n) in id_for_key]
        nodes.append({"id": i, "fields": {"val": val}, "links": {"neighbors": neighbor_ids}})
    return {"nodes": nodes, "entry": 0 if nodes else None}


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
    inp = {"node": _adj_to_verbose({"1": [2], "2": [1]})}
    out = _run_py(code, snippet, inp)
    assert out["entry"] == 0
    assert len(out["nodes"]) == 2
    assert out["nodes"][0]["fields"] == {"val": 1}
    assert out["nodes"][0]["links"]["neighbors"] == [1]
    assert out["nodes"][1]["fields"] == {"val": 2}
    assert out["nodes"][1]["links"]["neighbors"] == [0]


def test_py_runtime_rejects_legacy_adj_shape():
    """An adjacency dict reaching the graph driver at runtime must be rejected."""
    code = "def cloneGraph(node):\n    return node\n"
    snippet = py_wrapper(DEFAULT_ENTRY)
    err = _run_py_expect_error(code, snippet, {"node": {"1": [2], "2": [1]}})
    assert "verbose JSON" in err and "graph driver" in err, err


def test_validate_rejects_legacy_input_shape():
    bad = {**DEFAULT_ENTRY, "input_shape": "graph_adjacency"}
    errors = py_validate(bad)
    assert any("input_shape" in e and "graph_adjacency" in e for e in errors), errors


def test_js_validate_rejects_legacy_input_shape():
    bad = {**DEFAULT_ENTRY, "input_shape": "graph_adjacency"}
    errors = js_validate(bad)
    assert any("input_shape" in e and "graph_adjacency" in e for e in errors), errors


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
    assert "_output_shape" in snippet
    assert "'verbose'" in snippet


def test_py_graph_output_shape_adjacency():
    entry = {**DEFAULT_ENTRY, "output_shape": "graph_adjacency"}
    code = "def cloneGraph(node):\n    return node\n"
    snippet = py_wrapper(entry)
    out = _run_py(code, snippet, {"node": _adj_to_verbose({"1": [2], "2": [1]})})
    assert out == {"1": [2], "2": [1]}


def test_py_graph_unsupported_output_shape_rejected():
    bad = {**DEFAULT_ENTRY, "output_shape": "bogus_shape"}
    errors = py_validate(bad)
    assert any("output_shape" in e and "bogus_shape" in e for e in errors), errors


def test_py_graph_validate_accepts_verbose():
    for entry in (DEFAULT_ENTRY, {**DEFAULT_ENTRY, "output_shape": "verbose"}):
        assert py_validate(entry) == []


def test_py_graph_validate_accepts_adjacency():
    assert py_validate({**DEFAULT_ENTRY, "output_shape": "graph_adjacency"}) == []


def test_js_graph_output_shape_verbose_explicit():
    from drivers.javascript.graph import wrapper_snippet
    snippet = wrapper_snippet(VERBOSE_OUT_ENTRY)
    assert "outputShape" in snippet
    assert '"verbose"' in snippet


def test_js_graph_unsupported_output_shape_rejected():
    bad = {**DEFAULT_ENTRY, "output_shape": "bogus_shape"}
    errors = js_validate(bad)
    assert any("output_shape" in e and "bogus_shape" in e for e in errors), errors


def test_js_graph_validate_accepts_verbose():
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
