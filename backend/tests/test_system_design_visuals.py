def test_sd_question_returns_visual_fields(client):
    res = client.get("/api/system-design/1")
    assert res.status_code == 200
    data = res.json()
    # All five fields must be present in the response (None allowed).
    for field in (
        "architecture_diagram",
        "sequence_diagram",
        "er_diagram",
        "thought_flow",
        "tradeoff_visual",
    ):
        assert field in data, f"missing field {field}"
    # At least the architecture diagram for question 1 must be populated by seed.
    assert data["architecture_diagram"] is not None
    assert "nodes" in data["architecture_diagram"]
    assert "edges" in data["architecture_diagram"]


def test_chat_app_question_has_visuals(client):
    res = client.get("/api/system-design/2")
    assert res.status_code == 200
    data = res.json()
    assert data["architecture_diagram"] is not None
    assert any(
        n["id"] == "kafka" for n in data["architecture_diagram"]["nodes"]
    ), "Chat app diagram should include Kafka"
    assert "WebSocket" in data["sequence_diagram"]
    assert data["tradeoff_visual"]["title"].lower().startswith("fan-out")


def test_rate_limiter_question_has_visuals(client):
    res = client.get("/api/system-design/3")
    assert res.status_code == 200
    data = res.json()
    assert data["architecture_diagram"] is not None
    node_ids = {n["id"] for n in data["architecture_diagram"]["nodes"]}
    assert "redis" in node_ids
    assert "INCR" in data["sequence_diagram"]
    assert "Token" in data["tradeoff_visual"]["options"][0]["label"]


def test_url_shortener_has_senior_topics(client):
    res = client.get("/api/system-design/1")
    assert res.status_code == 200
    data = res.json()

    # Field present in the response schema.
    assert "senior_topics" in data, "senior_topics field missing from response"

    # Populated for the URL Shortener question.
    topics = data["senior_topics"]
    assert topics is not None, "URL Shortener senior_topics should be populated"
    assert len(topics) == 7, f"expected 7 senior topics, got {len(topics)}"

    # Every topic has the required shape.
    required_keys = {"id", "title", "summary", "sections", "sources"}
    for t in topics:
        missing = required_keys - t.keys()
        assert not missing, f"topic {t.get('id')} missing keys: {missing}"
        assert isinstance(t["sections"], list) and len(t["sections"]) >= 3
        for s in t["sections"]:
            assert "heading" in s and "body" in s
        assert isinstance(t["sources"], list) and len(t["sources"]) >= 1
        for src in t["sources"]:
            assert "label" in src and "url" in src

    # At least one topic has an embedded Mermaid diagram.
    assert any(t.get("diagram") for t in topics), "at least one topic should carry a diagram"

    # Topic ids match the spec (ordering matters for the UI).
    expected_ids = [
        "cqrs-split",
        "abuse-safety-subsystem",
        "301-vs-302-defended",
        "multi-region-writes",
        "cache-hierarchy-stampede",
        "deep-linking-contract",
        "link-rot-product",
    ]
    assert [t["id"] for t in topics] == expected_ids


def test_url_shortener_inplace_refinements(client):
    """The 301-vs-302 trade_off entry and the new slo_contract detailed_design key."""
    res = client.get("/api/system-design/1")
    data = res.json()

    # Refinement A: 301 vs 302 entry replaced with richer content.
    tradeoff_options = [t["option"] for t in data["trade_offs"]]
    assert any("301" in opt and "302" in opt for opt in tradeoff_options)
    for t in data["trade_offs"]:
        if "301" in t["option"] and "302" in t["option"]:
            # Richer recommendation references 410 Gone and Senior Topics tab.
            assert "410" in t["recommendation"]
            assert "Senior Topics" in t["recommendation"]
            break

    # Refinement B: slo_contract in detailed_design.
    assert "slo_contract" in data["detailed_design"]
    assert "99.99%" in data["detailed_design"]["slo_contract"]


def test_rate_limiter_has_senior_topics(client):
    res = client.get("/api/system-design/3")
    assert res.status_code == 200
    data = res.json()

    # Field present in the response schema.
    assert "senior_topics" in data, "senior_topics field missing from response"

    # Populated for the Rate Limiter question.
    topics = data["senior_topics"]
    assert topics is not None, "Rate Limiter senior_topics should be populated"
    assert len(topics) == 7, f"expected 7 senior topics, got {len(topics)}"

    # Every topic has the required shape.
    required_keys = {"id", "title", "summary", "sections", "sources"}
    for t in topics:
        missing = required_keys - t.keys()
        assert not missing, f"topic {t.get('id')} missing keys: {missing}"
        assert isinstance(t["sections"], list) and len(t["sections"]) >= 3
        for s in t["sections"]:
            assert "heading" in s and "body" in s
        assert isinstance(t["sources"], list) and len(t["sources"]) >= 1
        for src in t["sources"]:
            assert "label" in src and "url" in src

    # At least one topic has an embedded Mermaid diagram.
    assert any(t.get("diagram") for t in topics), "at least one topic should carry a diagram"

    # Topic ids match the spec (ordering matters for the UI).
    expected_ids = [
        "gcra-algorithm",
        "local-plus-central-hybrid",
        "cost-based-limiting",
        "redis-hot-key-sharding",
        "fail-open-vs-fail-closed",
        "429-retry-after-contract",
        "rate-limit-vs-abuse-prevention",
    ]
    assert [t["id"] for t in topics] == expected_ids
