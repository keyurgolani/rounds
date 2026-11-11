"""Legacy public share reads and owner routes (ROUNDS-00B-L03 stage 1).

The guarantees checked here:

  * a public read answers only ``{data, template_id, design}``: hidden
    sections are empty, unknown keys at any level are gone, and no owner name,
    link kind, record id, or owner appears anywhere in the body;
  * every failure is one 404 with byte-identical bodies and the same headers
    as a found read: kill switch, malformed token, unknown token, a link that
    leads nowhere, and the store failing;
  * the kill switch and the token format are decided before any lookup;
  * the read writes nothing and logs only the link's record id and a coarse
    outcome;
  * the owner list carries no view counts and reads only with the
    caller's own token;
  * a create naming a target the caller doesn't own and one naming a target
    that doesn't exist get the same answer, with no PocketBase text.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from routers import share

TOKEN = "AbCdEfGhIjKlMnOpQrStUv"
OTHER = "other0000000000b"
LINK = {"id": "lnk000000000001", "user": "owner000000000a", "resume": "res000000000001", "variant": "",
        "token": TOKEN, "expires_at": ""}
RESUME = {
    "id": "res000000000001",
    "user": "owner000000000a",
    "name": "Resume name A",
    "template_id": "langstaff",
    "design": {"layout": "two-column", "colors": {"primary": "#123456", "secret": "x"}, "extra": {"a": 1},
               "typography": {"heading": {"family": "Inter", "weight": 600, "bogus": True}}},
    "data": {
        "personalInfo": {"fullName": "Ada", "email": "ada@example.test", "website": "https://example.test",
                         "extraNote": "x"},
        "experience": [{"id": "e1", "company": "Acme", "position": "Eng", "highlights": ["a", 3],
                        "extraField": "x"}],
        "education": [{"id": "ed1", "institution": "Hidden U"}],
        "skills": [{"id": "s1", "category": "Lang", "items": ["Python"]}],
        "projects": [],
        "publications": [{"id": "p1", "title": "Hidden paper"}],
        "profiles": [],
        "sectionOrder": ["personal", "experience", "education", "skills", "projects", "publications", "profiles"],
        "hiddenSections": ["education", "publications"],
        "extraNotes": "x",
    },
}
VARIANT = {"id": "var000000000001", "user": "owner000000000a", "resume": "res000000000001",
           "name": "Variant for Acme", "data": {"personalInfo": {"fullName": "Ada V"}, "experience": []}}


class FakeStore:
    """The store reads public_read makes, from a fixed set of records."""

    def __init__(self, link=None, records=None, fail=None):
        self.link = link
        self.records = records or {}
        self.fail = fail
        self.calls: list[str] = []

    async def get(self, path, params=None):
        self.calls.append(path)
        if self.fail is not None:
            raise self.fail
        if path.endswith("/resume_share_links/records"):
            return {"items": [self.link] if self.link else []}
        rid = path.rsplit("/", 1)[-1]
        return self.records.get(rid)


def _read(client, token=TOKEN, store=None, env=None, monkeypatch=None):
    store = store or FakeStore(LINK, {RESUME["id"]: RESUME})
    if monkeypatch is not None:
        monkeypatch.delenv(share.KILL_SWITCH_ENV, raising=False)
        for k, v in (env or {}).items():
            monkeypatch.setenv(k, v)
    with patch("routers.share.pb_admin_get", store.get):
        res = client.get(f"/api/share/by-token/{token}")
    return res, store


def _headers(res):
    keep = {k.lower() for k in share.PUBLIC_HEADERS}
    return {k.lower(): v for k, v in res.headers.items() if k.lower() in keep}


def _walk(value):
    """Every key and string value anywhere in a JSON body."""
    if isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _walk(v)
    elif isinstance(value, list):
        for v in value:
            yield from _walk(v)
    elif isinstance(value, str):
        yield value


# ---- the projection --------------------------------------------------------


def test_a_found_read_answers_only_the_projection(client, monkeypatch):
    res, _ = _read(client, monkeypatch=monkeypatch)
    assert res.status_code == 200
    body = res.json()
    assert set(body) == {"data", "template_id", "design"}
    assert body["template_id"] == "langstaff"
    assert body["design"] == {"layout": "two-column", "colors": {"primary": "#123456"},
                              "typography": {"heading": {"family": "Inter", "weight": 600}}}
    data = body["data"]
    assert set(data) == {"personalInfo", "experience", "education", "skills", "projects", "publications",
                         "profiles", "sectionOrder"}
    assert data["personalInfo"] == {"fullName": "Ada", "email": "ada@example.test",
                                    "website": "https://example.test"}
    assert data["experience"] == [{"id": "e1", "company": "Acme", "position": "Eng", "highlights": ["a"]}]
    assert data["skills"] == [{"id": "s1", "category": "Lang", "items": ["Python"]}]


def test_hidden_sections_are_empty_and_not_named(client, monkeypatch):
    res, _ = _read(client, monkeypatch=monkeypatch)
    data = res.json()["data"]
    assert data["education"] == [] and data["publications"] == []
    assert "hiddenSections" not in data
    text = json.dumps(res.json())
    assert "Hidden U" not in text and "Hidden paper" not in text


def test_a_hidden_personal_section_is_empty_too(client, monkeypatch):
    resume = {**RESUME, "data": {**RESUME["data"], "hiddenSections": ["personal"]}}
    res, _ = _read(client, store=FakeStore(LINK, {RESUME["id"]: resume}), monkeypatch=monkeypatch)
    assert res.json()["data"]["personalInfo"] == {"fullName": ""}


def test_no_owner_metadata_appears_anywhere(client, monkeypatch):
    for store in (
        FakeStore(LINK, {RESUME["id"]: RESUME}),
        FakeStore({**LINK, "resume": "", "variant": VARIANT["id"]}, {VARIANT["id"]: VARIANT, RESUME["id"]: RESUME}),
    ):
        res, _ = _read(client, store=store, monkeypatch=monkeypatch)
        assert res.status_code == 200
        seen = set(_walk(res.json()))
        for leaked in ("name", "kind", "user", "token", "resume", "variant", "extraNotes",
                       "extraNote", "extraField", "extra", "secret",
                       RESUME["name"], VARIANT["name"], RESUME["id"], VARIANT["id"], LINK["id"], LINK["user"], TOKEN):
            assert leaked not in seen, leaked


def test_a_variant_link_reads_the_variant_data_and_the_parent_look(client, monkeypatch):
    store = FakeStore({**LINK, "resume": "", "variant": VARIANT["id"]}, {VARIANT["id"]: VARIANT, RESUME["id"]: RESUME})
    res, _ = _read(client, store=store, monkeypatch=monkeypatch)
    body = res.json()
    assert body["data"]["personalInfo"] == {"fullName": "Ada V"}
    assert body["template_id"] == "langstaff"


@pytest.mark.parametrize("template_id", [None, "", "Modern", "../x", "a" * 41, 7])
def test_an_odd_template_id_falls_back_to_the_default(template_id):
    assert share.project({}, template_id, {})["template_id"] == "modern"


def test_a_partial_section_order_is_dropped():
    out = share.project({"sectionOrder": ["experience", "personal"]}, "modern", {})
    assert "sectionOrder" not in out["data"]


def test_odd_data_shapes_project_to_empty_sections():
    out = share.project("not a dict", "modern", ["x"])
    assert out == {
        "data": {"personalInfo": {"fullName": ""}, "experience": [], "education": [], "skills": [],
                 "projects": [], "publications": [], "profiles": []},
        "template_id": "modern",
        "design": {},
    }


# ---- one not-found for every failure ---------------------------------------


@pytest.fixture
def missing(client, monkeypatch):
    res, _ = _read(client, store=FakeStore(None), monkeypatch=monkeypatch)
    assert res.status_code == 404
    return res


FAILURES = {
    "kill-switch": dict(env={share.KILL_SWITCH_ENV: "true"}),
    "kill-switch-yes": dict(env={share.KILL_SWITCH_ENV: "YES"}),
    # Any value outside the off list closes the read too.
    "kill-switch-on": dict(env={share.KILL_SWITCH_ENV: "on"}),
    "kill-switch-disabled": dict(env={share.KILL_SWITCH_ENV: "disabled"}),
    "kill-switch-garbage": dict(env={share.KILL_SWITCH_ENV: "TRUE!"}),
    # The link's owner must own the target, and a variant's parent too.
    "cross-account": dict(store=FakeStore(LINK, {RESUME["id"]: {**RESUME, "user": OTHER}})),
    "link-without-owner": dict(store=FakeStore({**LINK, "user": ""}, {RESUME["id"]: RESUME})),
    "variant-foreign": dict(store=FakeStore({**LINK, "resume": "", "variant": VARIANT["id"]},
                                            {VARIANT["id"]: {**VARIANT, "user": OTHER}, RESUME["id"]: RESUME})),
    "variant-parent-foreign": dict(store=FakeStore({**LINK, "resume": "", "variant": VARIANT["id"]},
                                                   {VARIANT["id"]: VARIANT, RESUME["id"]: {**RESUME, "user": OTHER}})),
    "malformed-short": dict(token="short"),
    "malformed-long": dict(token="a" * 65),
    "malformed-chars": dict(token="AbCdEfGhIjKlMnOp.Qr!"),
    "malformed-quote": dict(token='AbCdEfGhIjKlMnOp"abc"x'),
    "no-target": dict(store=FakeStore({**LINK, "resume": "", "variant": ""})),
    "resume-gone": dict(store=FakeStore(LINK, {})),
    "variant-gone": dict(store=FakeStore({**LINK, "resume": "", "variant": VARIANT["id"]}, {})),
    "variant-parent-gone": dict(store=FakeStore({**LINK, "resume": "", "variant": VARIANT["id"]},
                                                {VARIANT["id"]: VARIANT})),
    "pocketbase-error": dict(store=FakeStore(LINK, fail=HTTPException(status_code=500, detail="PocketBase error: x"))),
    "store-refused": dict(store=FakeStore(LINK, fail=HTTPException(status_code=502, detail="refused"))),
    "pocketbase-down": dict(store=FakeStore(LINK, fail=ConnectionError("refused"))),
}


@pytest.mark.parametrize("case", sorted(FAILURES))
def test_every_failure_is_byte_identical_to_a_missing_token(client, monkeypatch, missing, case):
    kwargs = dict(FAILURES[case])
    res, _ = _read(client, monkeypatch=monkeypatch, **kwargs)
    assert res.status_code == 404
    assert res.content == missing.content == b'{"detail":"Not found."}'
    assert _headers(res) == _headers(missing)


def test_found_and_not_found_carry_the_resolver_headers(client, monkeypatch, missing):
    found, _ = _read(client, monkeypatch=monkeypatch)
    want = {k.lower(): v for k, v in share.PUBLIC_HEADERS.items()}
    assert _headers(found) == want
    assert _headers(missing) == want
    assert want["cache-control"] == "no-store"
    assert want["content-security-policy"] == "default-src 'none'; frame-ancestors 'none'"


def test_the_headers_and_body_match_what_the_deployment_verifier_checks(client, monkeypatch, missing):
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "harness"))
    import verify_deployment as vd

    assert _headers(missing) == dict(vd.SHARE_HEADERS, **{"content-security-policy": vd.SHARE_READ_CSP})
    assert missing.content == vd.SHARE_NOT_FOUND


@pytest.mark.parametrize("env, token", [({share.KILL_SWITCH_ENV: "1"}, TOKEN), ({}, "x"), ({}, "ab cd" * 4)])
def test_the_kill_switch_and_token_format_come_before_any_lookup(client, monkeypatch, env, token):
    res, store = _read(client, token=token, env=env, monkeypatch=monkeypatch)
    assert res.status_code == 404
    assert store.calls == []


@pytest.mark.parametrize("value", ["false", "0", "", "no", "off", " OFF ", "False"])
def test_a_kill_switch_set_off_leaves_reads_on(client, monkeypatch, value):
    res, _ = _read(client, env={share.KILL_SWITCH_ENV: value}, monkeypatch=monkeypatch)
    assert res.status_code == 200


def test_list_fields_the_templates_read_are_always_lists():
    out = share.project({
        "experience": [{"id": "e1", "highlights": "not a list"}],
        "skills": [{"id": "s1"}],
        "projects": [{"id": "p1", "technologies": None, "highlights": {"a": 1}}],
    }, "modern", {})["data"]
    assert out["experience"] == [{"id": "e1", "highlights": []}]
    assert out["skills"] == [{"id": "s1", "items": []}]
    assert out["projects"] == [{"id": "p1", "technologies": [], "highlights": []}]


# ---- nothing written, nothing sensitive logged ------------------------------


def test_the_public_read_writes_nothing(client, monkeypatch):
    sent = []

    class NoWrites:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def request(self, method, *a, **k):
            sent.append(method)
            raise AssertionError("no PocketBase request beyond the fake reads")

        post = patch_ = put = delete = None

    with patch("httpx.AsyncClient", NoWrites):
        res, _ = _read(client, monkeypatch=monkeypatch)
    assert res.status_code == 200
    assert sent == []
    # No write helper is even in reach of the share module.
    assert not hasattr(share, "pb_admin_post") and not hasattr(share, "admin_token")


def test_the_share_module_names_no_view_writes():
    src = Path(share.__file__).read_text()
    assert "resume_share_views" not in src
    assert "pb_admin_post" not in src


@pytest.mark.parametrize("case, outcome", [
    ("found", "available"), ("missing", "not_found"), ("kill", "kill_switch"), ("down", "degraded"),
])
def test_reads_log_only_a_record_id_and_a_coarse_outcome(client, monkeypatch, capsys, case, outcome):
    kwargs = {
        "found": {},
        "missing": dict(store=FakeStore(None)),
        "kill": dict(env={share.KILL_SWITCH_ENV: "true"}),
        "down": dict(store=FakeStore(LINK, fail=ConnectionError("refused"))),
    }[case]
    capsys.readouterr()
    _read(client, monkeypatch=monkeypatch, **kwargs)
    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines()
             if line.startswith("{") and '"share.resolve"' in line]
    assert len(lines) == 1
    line = lines[0]
    assert line["code"] == outcome
    assert set(line) <= {"v", "event", "correlation_id", "record", "code"}
    if case == "found":
        assert line["record"] == LINK["id"]
    text = json.dumps(line)
    for secret in (TOKEN, LINK["user"], RESUME["name"], "testclient"):
        assert secret not in text


# ---- owner routes -----------------------------------------------------------

CALLER = {"id": "caller000000001", "token": "caller-token-placeholder"}


async def _caller(_request):
    return CALLER


def test_the_owner_list_has_no_view_counts_and_uses_the_owner_token(client):
    calls = []

    async def fake_get(token, path, params=None):
        calls.append(token)
        return {"items": [{"id": "lnk000000000001", "token": TOKEN, "resume": "res000000000001", "variant": "",
                           "created": "2026-11-10 00:00:00.000Z"}]}

    async def not_the_owner(*a, **k):
        raise AssertionError("the owner list uses the caller token only")

    with patch("routers.share.current_user", _caller), patch("routers.share.pb_get", fake_get), \
         patch("app.pb_auth.admin_token", not_the_owner):
        res = client.get("/api/share")
    assert res.status_code == 200
    assert res.json() == [{"id": "lnk000000000001", "token": TOKEN, "resume_id": "res000000000001",
                           "variant_id": None, "created": "2026-11-10 00:00:00.000Z"}]
    assert calls == [CALLER["token"]]


def test_a_new_link_token_has_the_format_the_hook_requires():
    import re

    for _ in range(50):
        assert re.fullmatch(r"[A-Za-z0-9_-]{22}", share._new_token())


@pytest.mark.parametrize("body", [{"resume_id": "res000000000001"}, {"variant_id": "var000000000001"}])
def test_a_foreign_target_and_a_missing_one_get_the_same_answer(client, body):
    # PocketBase answers both with its uniform relation denial; the runner
    # answers both with one not-found and none of PocketBase's text.
    denial = HTTPException(status_code=400, detail='PocketBase error: {"code":400,"message":"Failed to create record.","data":{}}')

    async def denied(_token, _path, _payload):
        raise denial

    with patch("routers.share.current_user", _caller), patch("routers.share.pb_post", denied):
        first = client.post("/api/share", json=body)
        second = client.post("/api/share", json=body)
    assert first.status_code == second.status_code == 404
    strip = lambda r: {k: v for k, v in r.json().items() if k != "correlation_id"}  # noqa: E731
    assert strip(first) == strip(second) == {"detail": "Not found.", "code": "not_found"}
    assert "PocketBase" not in first.text


def test_another_create_refusal_keeps_its_status_and_code(client):
    # Only the uniform relation denial becomes the not-found; a refusal such
    # as the demo account's passes through with PocketBase's code.
    refusal = HTTPException(status_code=403, detail='PocketBase error: {"code":"demo_not_permitted"}')

    async def refused(_token, _path, _payload):
        raise refusal

    with patch("routers.share.current_user", _caller), patch("routers.share.pb_post", refused):
        res = client.post("/api/share", json={"resume_id": "res000000000001"})
    assert res.status_code == 403
    assert "demo_not_permitted" in res.text


def test_a_create_still_names_the_caller_and_one_target(client):
    sent = {}

    async def fake_post(_token, path, payload):
        sent.update(payload)
        return {"id": "lnk000000000002", **payload, "created": ""}

    with patch("routers.share.current_user", _caller), patch("routers.share.pb_post", fake_post):
        res = client.post("/api/share", json={"resume_id": "res000000000001"})
    assert res.status_code == 200
    assert sent["user"] == CALLER["id"] and sent["resume"] == "res000000000001" and "variant" not in sent
    assert "view_count" not in res.json()
