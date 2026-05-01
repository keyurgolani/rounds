from drivers._shorthand import to_verbose


def test_linked_list_array_singly():
    template = {"name": "Node",
                "fields": [{"name": "val", "type": "int"}],
                "links": [{"name": "next", "arity": "single"}]}
    result = to_verbose([1, 2, 3], shape="linked_list_array", template=template)
    assert result == {
        "nodes": [
            {"id": 0, "fields": {"val": 1}, "links": {"next": 1}},
            {"id": 1, "fields": {"val": 2}, "links": {"next": 2}},
            {"id": 2, "fields": {"val": 3}, "links": {"next": None}},
        ],
        "entry": 0,
    }


def test_linked_list_array_empty():
    template = {"name": "Node",
                "fields": [{"name": "val", "type": "int"}],
                "links": [{"name": "next", "arity": "single"}]}
    result = to_verbose([], shape="linked_list_array", template=template)
    assert result == {"nodes": [], "entry": None}


def test_binary_tree_level_order():
    template = {"name": "TreeNode",
                "fields": [{"name": "val", "type": "int"}],
                "links": [{"name": "left", "arity": "single"},
                          {"name": "right", "arity": "single"}]}
    result = to_verbose([1, 2, 3, None, 5], shape="tree_level_order", template=template)
    # Node 0 (val=1) -> left=1, right=2
    # Node 1 (val=2) -> left=None, right=3
    # Node 2 (val=3) -> left=None, right=None
    # Node 3 (val=5) -> left=None, right=None
    assert result["entry"] == 0
    assert len(result["nodes"]) == 4
    assert result["nodes"][0] == {"id": 0, "fields": {"val": 1},
                                   "links": {"left": 1, "right": 2}}
    assert result["nodes"][1] == {"id": 1, "fields": {"val": 2},
                                   "links": {"left": None, "right": 3}}
    assert result["nodes"][2] == {"id": 2, "fields": {"val": 3},
                                   "links": {"left": None, "right": None}}


def test_binary_tree_level_order_empty():
    template = {"name": "TreeNode",
                "fields": [{"name": "val", "type": "int"}],
                "links": [{"name": "left", "arity": "single"},
                          {"name": "right", "arity": "single"}]}
    assert to_verbose([], shape="tree_level_order", template=template) == \
        {"nodes": [], "entry": None}


def test_graph_adjacency_dict():
    template = {"name": "Node",
                "fields": [{"name": "val", "type": "int"}],
                "links": [{"name": "neighbors", "arity": "list"}]}
    result = to_verbose({"1": [2, 3], "2": [1], "3": [1]},
                         shape="graph_adjacency", template=template)
    # Three nodes; each has neighbors as list of refs.
    assert result["entry"] == 0
    assert len(result["nodes"]) == 3
    assert result["nodes"][0]["fields"] == {"val": 1}
    assert sorted(result["nodes"][0]["links"]["neighbors"]) == [1, 2]


def test_verbose_passthrough():
    template = {"name": "Node",
                "fields": [{"name": "val", "type": "int"}],
                "links": [{"name": "next", "arity": "single"}]}
    payload = {"nodes": [{"id": 0, "fields": {"val": 9}, "links": {"next": None}}],
               "entry": 0}
    assert to_verbose(payload, shape="verbose", template=template) == payload
