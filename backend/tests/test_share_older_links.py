"""Older share links at the runner and the proxy (ROUNDS-00B-L06 stage 1).

The guarantees checked here:

  * an older link's address opens nothing: the runner has no route there,
    so every value, in any letter case and by any method, gets one 404
    with the same body as an address the runner never had, and nothing
    reaches PocketBase; no runner route changes or deletes an older link;
  * nginx answers that address itself, ahead of the runner group, with the
    share resolver's not-found body and headers, keeps no access-log line,
    and passes nothing on;
  * GET /api/share lists only the caller's own older links, read with the
    caller's own bearer and asking for only the fields the list shows; an
    entry holds what its owner sees and nothing more, one that pointed at
    another account's resume is never listed, and an empty or unknown
    status reads as one the server couldn't verify;
  * a caller PocketBase doesn't sign in gets unauthenticated before any
    read, a store that doesn't answer gets shares_unavailable without its
    own text, and the list writes nothing.

"Get a new link" is CreateShare with legacy_link_id
(backend/tests/test_share_commands.py), and the old-link page is the
browser's (frontend/src/pages/__tests__).
"""
from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

import httpx
import pytest

from app import share_capabilities
from routers import share

ROOT = Path(__file__).resolve().parents[2]
NGINX = ROOT / "frontend" / "nginx.conf"
OLDER_LOCATION = "location ~* ^/api/share/by-token(/|$) {"
RUNNER_GROUP = "location ~ ^/api/(share|pdf|ai|ai-coding|sd-practice|take-home)(/|$) {"

OWNER = "owner000000000a"
BEARER = "owner-bearer-placeholder"
AUTH_REFRESH = "/api/collections/users/auth-refresh"
RESUME = "res000000000001"
VARIANT = "var000000000001"
CAPABILITY = "capnew000000001"
TURNED_OFF = "2026-11-11 12:00:00.000Z"


# ---- the fake store ------------------------------------------------------------


class FakeStore:
    """PocketBase's auth-refresh and the older links' list, over one
    account's rows. Every request is recorded."""

    def __init__(self, rows: list | None = None) -> None:
        self.rows = list(rows or [])
        self.requests: list[httpx.Request] = []
        self.list_answer: httpx.Response | Exception | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "POST" and request.url.path == AUTH_REFRESH:
            if request.headers.get("authorization") != f"Bearer {BEARER}":
                return httpx.Response(401, json={"message": "The request requires valid record authorization token."})
            return httpx.Response(200, json={"token": BEARER, "record": {"id": OWNER, "is_demo": False}})
        if request.method == "GET" and request.url.path == share.LIST_PATH:
            if isinstance(self.list_answer, Exception):
                raise self.list_answer
            if self.list_answer is not None:
                return self.list_answer
            page, per_page = int(request.url.params["page"]), int(request.url.params["perPage"])
            items = self.rows[(page - 1) * per_page:page * per_page]
            return httpx.Response(200, json={"page": page, "perPage": per_page, "items": items})
        return httpx.Response(404, json={"message": "The requested resource wasn't found."})

    def lists(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.url.path == share.LIST_PATH]


@pytest.fixture
def store(monkeypatch):
    fake = FakeStore()
    real = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        return real(*args, transport=httpx.MockTransport(fake.handler), **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", client_factory)
    return fake


def link(n: int = 1, **over) -> dict:
    row = {"id": f"lnk{n:012d}", "created": f"2024-01-{n:02d} 10:00:00.000Z", "updated": TURNED_OFF,
           "resume": RESUME, "variant": "", "legacy_status": "migrated", "legacy_reason": "eligible",
           "turned_off_at": TURNED_OFF, "replaced_by": ""}
    row.update(over)
    return row


def _list(client, headers=None):
    return client.get("/api/share", headers={"Authorization": f"Bearer {BEARER}"} if headers is None else headers)


def _typed(res) -> tuple[int, str, str]:
    body = res.json()
    return res.status_code, body.get("code"), body.get("detail")


# ---- an older link's address opens nothing ----------------------------------------------


OLDER_PATHS = [
    "/api/share/by-token/AbCdEfGhIjKlMnOpQrStUv",
    "/api/share/by-token/x",
    "/api/share/by-token/sd1_AbCdEfGhIjKlMnOpQrStUv",
    "/api/share/by-token/AbCdEfGhIjKlMnOpQrStUv/more",
    "/api/share/by-token/",
    "/api/share/by-token",
    "/API/Share/By-Token/AbCdEfGhIjKlMnOpQrStUv",
    "/api/share/lnk000000000001",
]


@pytest.fixture
def never_had(client, store):
    res = client.get("/api/share/an-address-the-runner-never-had")
    assert res.status_code == 404
    store.requests.clear()
    return res.content


@pytest.mark.parametrize("method", ["GET", "POST", "PATCH", "PUT", "DELETE"])
@pytest.mark.parametrize("path", OLDER_PATHS)
def test_an_older_links_address_opens_nothing_and_reaches_no_store(client, store, never_had, method, path):
    res = client.request(method, path, headers={"Authorization": f"Bearer {BEARER}"})
    assert res.status_code == 404
    assert res.content == never_had
    assert store.requests == []


@pytest.mark.parametrize("method", ["DELETE", "PATCH", "PUT"])
def test_no_runner_route_changes_or_deletes_an_older_link(client, store, method):
    res = client.request(method, "/api/share", headers={"Authorization": f"Bearer {BEARER}"})
    assert res.status_code == 405
    assert store.requests == []


def _share_routes() -> set[tuple[str, str]]:
    from main import app

    out: set[tuple[str, str]] = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if path == "/api/share" or path.startswith("/api/share/"):
            out |= {(method, path) for method in getattr(route, "methods", None) or ()}
    return out


def test_the_runners_share_routes_are_new_links_their_resolver_and_the_older_links_list():
    assert _share_routes() == {
        ("POST", "/api/share"),
        ("GET", "/api/share"),
        ("GET", "/api/share/capabilities"),
        ("POST", "/api/share/capabilities/{capability_id}/revoke"),
        ("POST", "/api/share/capabilities/{capability_id}/rotate"),
        ("POST", "/api/share/resolve"),
    }


# ---- nginx answers that address itself ---------------------------------------------------


def _block(conf: str, head: str) -> str:
    """The body of the block that opens with ``head``, braces inside quotes
    skipped."""
    start = conf.index(head) + len(head)
    depth, quote = 1, ""
    for i in range(start, len(conf)):
        ch = conf[i]
        if quote:
            quote = "" if ch == quote else quote
        elif ch in "'\"":
            quote = ch
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return conf[start:i]
    raise AssertionError(f"{head} isn't closed")


def _directives(block: str) -> list[str]:
    lines = (line.strip() for line in block.splitlines())
    return [line.rstrip(";").strip() for line in lines if line and not line.startswith("#")]


def nginx_older_read() -> tuple[int, str, dict[str, str]]:
    """What nginx answers at an older link's address, from its config: the
    status, the body, and the headers it adds."""
    status, body, headers = 0, "", {}
    for directive in _directives(_block(NGINX.read_text(), OLDER_LOCATION)):
        header = re.fullmatch(r'add_header (\S+) "([^"]*)" always', directive)
        answer = re.fullmatch(r"return (\d{3}) '([^']*)'", directive)
        if header:
            headers[header.group(1)] = header.group(2)
        elif answer:
            status, body = int(answer.group(1)), answer.group(2)
    return status, body, headers


def test_nginx_answers_an_older_links_address_with_the_resolvers_not_found():
    status, body, headers = nginx_older_read()
    assert status == 404
    assert body == json.dumps(share_capabilities.NOT_FOUND_BODY, separators=(",", ":"))
    assert headers == share_capabilities.RESOLVER_HEADERS


def test_nginx_keeps_no_log_line_there_and_passes_nothing_on():
    directives = _directives(_block(NGINX.read_text(), OLDER_LOCATION))
    kinds = sorted({d.split()[0] for d in directives})
    assert kinds == ["access_log", "add_header", "default_type", "error_log", "return"]
    assert "access_log off" in directives
    assert "error_log /var/log/nginx/error.log crit" in directives
    assert "default_type application/json" in directives


def test_that_location_matches_the_address_in_any_letter_case_ahead_of_the_runner_group():
    conf = NGINX.read_text()
    assert conf.index(OLDER_LOCATION) < conf.index(RUNNER_GROUP)
    older = re.compile(OLDER_LOCATION.split(" ")[2], re.IGNORECASE)
    for path in ("/api/share/by-token", "/api/share/by-token/", "/api/share/by-token/x",
                 "/API/SHARE/BY-TOKEN/AbCdEfGhIjKlMnOpQrStUv"):
        assert older.search(path), path
    for path in ("/api/share", "/api/share/by-tokens", "/api/share/resolve", "/api/share/capabilities",
                 "/r/AbCdEfGhIjKlMnOpQrStUv"):
        assert not older.search(path), path


def test_the_deployment_verifier_checks_that_same_answer():
    sys.path.insert(0, str(ROOT / "harness"))
    import verify_deployment as vd

    status, body, headers = nginx_older_read()
    older = re.compile(OLDER_LOCATION.split(" ")[2], re.IGNORECASE)
    assert all(older.search(path) for path in vd.SHARE_READ_PATHS)
    assert (status, body.encode()) == (404, vd.SHARE_NOT_FOUND)
    assert {k.lower(): v for k, v in headers.items()} == dict(vd.SHARE_HEADERS,
                                                             **{"content-security-policy": vd.SHARE_READ_CSP})


# ---- GET /api/share: the caller's older links ------------------------------------------------


def test_the_list_reads_with_the_callers_own_bearer_and_asks_only_for_what_it_shows(client, store):
    store.rows = [link(1)]
    res = _list(client)
    assert res.status_code == 200
    (read,) = store.lists()
    assert read.headers["authorization"] == f"Bearer {BEARER}"
    assert {r.headers.get("authorization") for r in store.requests} == {f"Bearer {BEARER}"}
    params = dict(read.url.params)
    assert params.pop("fields").split(",") == [
        "id", "created", "updated", "resume", "variant", "legacy_status", "legacy_reason", "turned_off_at",
        "replaced_by", "expand.variant.resume", "expand.variant.name"]
    assert params == {"filter": f'user = "{OWNER}"', "sort": "-created,-id", "perPage": "200", "page": "1",
                      "skipTotal": "1", "expand": "variant"}


def test_each_entry_holds_what_its_owner_sees_and_nothing_more(client, store):
    store.rows = [link(1, views=7, user=OWNER, extra="placeholder")]
    (entry,) = _list(client).json()["legacy"]
    assert entry == {
        "id": "lnk000000000001", "status": "migrated", "reason": "eligible", "created": "2024-01-01 10:00:00.000Z",
        "turned_off_at": TURNED_OFF, "replaced_by": "", "replaced_at": "", "target": "resume", "resume_id": RESUME,
        "variant_id": "", "root_resume_id": RESUME, "variant_name": "",
    }
    assert set(_list(client).json()) == {"legacy"}


@pytest.mark.parametrize("status, reason", [("migrated", "eligible"), ("revoked_demo", "demo_account"),
                                            ("revoked_unverified", "token_format")])
def test_each_status_its_owner_sees_is_kept_with_its_reason(client, store, status, reason):
    store.rows = [link(1, legacy_status=status, legacy_reason=reason)]
    (entry,) = _list(client).json()["legacy"]
    assert (entry["status"], entry["reason"]) == (status, reason)


def test_a_link_that_pointed_at_another_accounts_resume_is_never_listed(client, store):
    store.rows = [link(1), link(2, legacy_status="revoked_ownership", legacy_reason="target_owner"), link(3)]
    assert [entry["id"] for entry in _list(client).json()["legacy"]] == ["lnk000000000001", "lnk000000000003"]


@pytest.mark.parametrize("status", ["", None, "made_up", 7, "MIGRATED"])
def test_an_empty_or_unknown_status_reads_as_one_the_server_couldnt_verify(client, store, status):
    store.rows = [link(1, legacy_status=status)]
    (entry,) = _list(client).json()["legacy"]
    assert entry["status"] == "revoked_unverified"


def test_a_variant_links_entry_names_its_resume_and_the_variants_name(client, store):
    store.rows = [link(1, resume="", variant=VARIANT,
                       expand={"variant": {"resume": RESUME, "name": "Variant for Acme"}})]
    (entry,) = _list(client).json()["legacy"]
    assert (entry["target"], entry["resume_id"], entry["variant_id"]) == ("variant", "", VARIANT)
    assert (entry["root_resume_id"], entry["variant_name"]) == (RESUME, "Variant for Acme")


def test_a_variant_that_is_gone_leaves_its_entry_under_no_resume(client, store):
    store.rows = [link(1, resume="", variant=VARIANT, legacy_status="revoked_unverified",
                       legacy_reason="target_missing")]
    (entry,) = _list(client).json()["legacy"]
    assert (entry["target"], entry["root_resume_id"], entry["variant_name"]) == ("variant", "", "")


def test_a_replaced_link_says_by_which_link_and_when(client, store):
    store.rows = [link(1, replaced_by=CAPABILITY, updated="2026-11-12 09:00:00.000Z"), link(2)]
    first, second = _list(client).json()["legacy"]
    assert (first["replaced_by"], first["replaced_at"]) == (CAPABILITY, "2026-11-12 09:00:00.000Z")
    assert (second["replaced_by"], second["replaced_at"]) == ("", "")


@pytest.mark.parametrize("row", [
    "not-a-row", None, 7,
    {"id": "short"},
    {"id": "LNK000000000001"},
])
def test_a_row_of_another_shape_is_left_out(client, store, row):
    store.rows = [row, link(2)]
    assert [entry["id"] for entry in _list(client).json()["legacy"]] == ["lnk000000000002"]


def test_odd_field_values_read_as_empty(client, store):
    store.rows = [link(1, resume=7, created=None, legacy_reason=["x"], turned_off_at={}, replaced_by="no",
                       expand="odd")]
    (entry,) = _list(client).json()["legacy"]
    assert (entry["resume_id"], entry["created"], entry["reason"], entry["turned_off_at"]) == ("", "", "", "")
    assert (entry["replaced_by"], entry["replaced_at"], entry["root_resume_id"]) == ("", "", "")


def test_the_list_pages_until_a_short_page(client, store):
    store.rows = [link(n % 28 + 1, id=f"lnk{n:012d}") for n in range(share.PAGE + 3)]
    entries = _list(client).json()["legacy"]
    assert len(entries) == share.PAGE + 3
    assert [r.url.params["page"] for r in store.lists()] == ["1", "2"]


def test_the_list_stops_at_its_page_cap(client, store):
    store.rows = [link(n % 28 + 1, id=f"lnk{n:012d}") for n in range(share.PAGE * (share.MAX_PAGES + 1))]
    entries = _list(client).json()["legacy"]
    assert len(entries) == share.PAGE * share.MAX_PAGES
    assert len(store.lists()) == share.MAX_PAGES


def test_an_account_with_no_older_links_gets_an_empty_list(client, store):
    res = _list(client)
    assert (res.status_code, res.json()) == (200, {"legacy": []})


# ---- refusals, and nothing written ----------------------------------------------------


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Basic placeholder"}, {"Authorization": "Bearer "}])
def test_a_request_with_no_bearer_is_unauthenticated_before_the_store_is_asked(client, store, headers):
    res = _list(client, headers=headers)
    assert _typed(res)[:2] == (401, "unauthenticated")
    assert store.requests == []


def test_a_bearer_pocketbase_doesnt_sign_in_is_unauthenticated_before_any_read(client, store):
    res = _list(client, headers={"Authorization": "Bearer someone-elses-placeholder"})
    assert _typed(res)[:2] == (401, "unauthenticated")
    assert [r.url.path for r in store.requests] == [AUTH_REFRESH]


@pytest.mark.parametrize("answer", [
    httpx.Response(500, text="PocketBase error: placeholder-internal-detail"),
    httpx.Response(400, json={"message": "placeholder-internal-detail"}),
    httpx.Response(200, text="placeholder-internal-detail"),
    httpx.Response(200, json={"message": "placeholder-internal-detail"}),
    httpx.Response(200, json={"items": "placeholder-internal-detail"}),
    httpx.ConnectError("placeholder-internal-detail"),
    httpx.ReadTimeout("placeholder-internal-detail"),
], ids=["5xx", "4xx", "not-json", "no-items", "items-not-a-list", "unreachable", "timeout"])
def test_a_store_that_doesnt_answer_gets_shares_unavailable_without_its_text(client, store, answer):
    store.list_answer = answer
    res = _list(client)
    assert _typed(res) == (503, "shares_unavailable", "Share links can't be loaded right now. Try again shortly.")
    assert "placeholder-internal-detail" not in res.text


def test_a_bearer_the_list_refuses_is_unauthenticated(client, store):
    store.list_answer = httpx.Response(401, json={"message": "placeholder-internal-detail"})
    res = _list(client)
    assert _typed(res)[:2] == (401, "unauthenticated")
    assert "placeholder-internal-detail" not in res.text


def test_the_list_writes_nothing(client, store):
    store.rows = [link(1), link(2, replaced_by=CAPABILITY)]
    _list(client)
    assert [(r.method, r.url.path) for r in store.requests] == [("POST", AUTH_REFRESH), ("GET", share.LIST_PATH)]


def test_the_share_router_makes_no_write_to_an_older_link_or_its_views():
    tree = ast.parse(Path(share.__file__).read_text())
    calls = sorted({node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "client"})
    assert calls == ["get"]
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    names |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) for alias in node.names}
    assert not names & {"pb_post", "pb_patch", "pb_delete", "pb_admin_get", "pb_admin_post", "admin_token"}
    assert "resume_share_views" not in Path(share.__file__).read_text()
