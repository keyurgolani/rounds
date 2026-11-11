"""PDF proxy (ROUNDS-00A-L01, ROUNDS-00A-L04 PR 3): a render takes only
render-request/v1 and renders only the caller's own snapshot, as the
server stored it; a failed render never repeats the sidecar's text, and
health answers only ``{"status"}``.

PocketBase's records come from conftest's FakePocketBase, which answers
another account's record the way PocketBase does, with 404. The markup
file goes over httpx.MockTransport, so the real file read runs."""
from __future__ import annotations

import asyncio
import hashlib
import io
import json
import urllib.error

import httpx
import pytest

from app import legacy_snapshots
from conftest import TEST_ACCOUNT_ID, TEST_TOKEN
from tests.test_admission import _assert_typed, gate_env  # noqa: F401  (fixtures)

SIDECAR_TEXT = "sidecar-internal-detail at /srv/render.js:42"
PATH = "/api/pdf/render"
KEY = "0190f000-0000-7000-8000-00000000000a"
SOURCE = "resumeaaaaaaaa1"
SNAPSHOT = "snapaaaaaaaaaa1"
FILE = "snapshot_a1b2c3d4e5.html"
MARKUP = "<!DOCTYPE html><html><body><article data-resume-page>Résumé</article></body></html>"
CHECKSUM = "sha256:" + hashlib.sha256(MARKUP.encode()).hexdigest()
FILE_TOKEN = "file-token-placeholder"
RENDERER_FAILED = "The PDF renderer couldn't finish this document. Try again shortly."


def body(**change):
    out = {
        "snapshot_id": SNAPSHOT,
        "expected_checksum": CHECKSUM,
        "format": "pdf",
        "page_size": "A4",
        "margin_mm": 0,
        "locale": "en",
        "idempotency_id": KEY,
    }
    out.update(change)
    return {k: v for k, v in out.items() if v is not None}


class FakeResponse:
    def __init__(self, status=200, body=b"%PDF-1.7 test", content_type="application/pdf"):
        self.status = status
        self._body = body
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture
def sidecar(monkeypatch):
    from routers import pdf

    state = {"answer": FakeResponse(), "calls": [], "bodies": []}

    def urlopen(request, timeout=None):
        state["calls"].append(getattr(request, "full_url", request))
        data = getattr(request, "data", None)
        if data:
            state["bodies"].append(json.loads(data))
        answer = state["answer"]
        if isinstance(answer, Exception):
            raise answer
        return answer

    monkeypatch.setattr(pdf.urllib.request, "urlopen", urlopen)
    return state


class FakeFiles:
    """PocketBase's file token and protected-file routes."""

    def __init__(self) -> None:
        self.files: dict[tuple[str, str], bytes] = {(SNAPSHOT, FILE): MARKUP.encode()}
        self.calls: list[tuple[str, str, str | None]] = []
        self.token_status = 200
        self.file_status = 200

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path, request.headers.get("authorization")))
        if request.url.path == legacy_snapshots.FILE_TOKEN_PATH:
            if request.headers.get("authorization") != f"Bearer {TEST_TOKEN}":
                return httpx.Response(401, json={"code": 401})
            if self.token_status != 200:
                return httpx.Response(self.token_status, json={"code": self.token_status})
            return httpx.Response(200, json={"token": FILE_TOKEN})
        prefix = f"/api/files/{legacy_snapshots.SNAPSHOTS}/"
        assert request.url.path.startswith(prefix), request.url.path
        record_id, name = request.url.path[len(prefix):].split("/", 1)
        raw = self.files.get((record_id, name))
        if request.url.params.get("token") != FILE_TOKEN or raw is None:
            return httpx.Response(404, json={"code": 404})
        if self.file_status != 200:
            return httpx.Response(self.file_status, json={"code": self.file_status})
        return httpx.Response(200, content=raw, headers={"Content-Type": "text/html"})


@pytest.fixture
def files(monkeypatch):
    fake = FakeFiles()
    real = httpx.AsyncClient

    def client_factory(*args, **kwargs):
        return real(*args, transport=httpx.MockTransport(fake.handler), **kwargs)

    monkeypatch.setattr(legacy_snapshots.httpx, "AsyncClient", client_factory)
    return fake


@pytest.fixture
def snapshot(pocketbase, files):
    """The caller's own snapshot over its own resume."""
    pocketbase.add("resumes", id=SOURCE, user=TEST_ACCOUNT_ID)
    return pocketbase.add(
        "legacy_artifact_snapshots", id=SNAPSHOT, user=TEST_ACCOUNT_ID, source_kind="resume", source_id=SOURCE,
        content_checksum=CHECKSUM, markup=FILE,
    )


def post(client, headers, payload=None, key: str | None = KEY):
    sent = dict(headers)
    if key is not None:
        sent["Idempotency-Key"] = key
    return client.post(PATH, json=body() if payload is None else payload, headers=sent)


# ---- the owner's render -----------------------------------------------------------------


def test_the_owner_gets_the_pdf_of_the_markup_the_server_stored(client, signed_in, sidecar, snapshot, pocketbase, files):
    res = post(client, signed_in)
    assert res.status_code == 200
    assert res.content == b"%PDF-1.7 test"
    assert res.headers["content-type"].startswith("application/pdf")
    assert sidecar["bodies"] == [{"html": MARKUP, "marginMm": 0}]
    # Every read used the caller's own bearer.
    assert {token for token, _path, _params in pocketbase.calls} == {TEST_TOKEN}
    assert [c[1] for c in pocketbase.calls] == [
        f"/api/collections/legacy_artifact_snapshots/records/{SNAPSHOT}",
        f"/api/collections/resumes/records/{SOURCE}",
    ]
    assert files.calls[0] == ("POST", legacy_snapshots.FILE_TOKEN_PATH, f"Bearer {TEST_TOKEN}")


def test_a_variants_snapshot_needs_its_variant(client, signed_in, sidecar, pocketbase, files):
    pocketbase.add("resume_variants", id="variantaaaaaaa1", user=TEST_ACCOUNT_ID)
    pocketbase.add("legacy_artifact_snapshots", id=SNAPSHOT, user=TEST_ACCOUNT_ID, source_kind="variant",
                   source_id="variantaaaaaaa1", content_checksum=CHECKSUM, markup=FILE)
    assert post(client, signed_in).status_code == 200
    assert f"/api/collections/resume_variants/records/variantaaaaaaa1" in [c[1] for c in pocketbase.calls]


def test_the_margin_the_request_names_reaches_the_renderer(client, signed_in, sidecar, snapshot):
    assert post(client, signed_in, body(margin_mm=12.5)).status_code == 200
    assert sidecar["bodies"] == [{"html": MARKUP, "marginMm": 12.5}]


def test_without_an_idempotency_key_the_body_alone_names_the_command(client, signed_in, sidecar, snapshot):
    assert post(client, signed_in, key=None).status_code == 200


# ---- what a render may carry ------------------------------------------------------------


@pytest.mark.parametrize("payload", [
    {"html": "<p>hi</p>"},
    {"html": "<p>hi</p>", "margin_mm": 5},
    {**body(), "html": "<p>hi</p>"},
    {"html": ""},
])
def test_the_older_request_shape_is_refused_as_out_of_date_before_anything_runs(
    client, signed_in, sidecar, pocketbase, admission_store, payload
):
    res = post(client, signed_in, payload)
    _assert_typed(res, 422, "legacy_request_rejected")
    assert res.json()["detail"] == "This page is out of date. Reload it to continue."
    assert sidecar["calls"] == [] and pocketbase.calls == [] and admission_store.calls == []


@pytest.mark.parametrize("change", [
    {"snapshot_id": None},
    {"snapshot_id": "SNAPAAAAAAAAAA1"},
    {"snapshot_id": "short"},
    {"expected_checksum": None},
    {"expected_checksum": "sha256:" + "C" * 64},
    {"expected_checksum": "md5:" + "c" * 32},
    {"format": "png"},
    {"page_size": "Letter"},
    {"locale": "fr"},
    {"margin_mm": -1},
    {"margin_mm": 31},
    {"margin_mm": "0"},
    {"margin_mm": True},
    {"idempotency_id": None},
    {"idempotency_id": "0190f000-0000-4000-8000-00000000000a"},
    {"markup": "<p>x</p>"},
    {"template_id": "modern"},
    {"design": {}},
])
def test_anything_but_render_request_v1_is_refused_before_any_read(
    client, signed_in, sidecar, pocketbase, admission_store, change
):
    # None leaves the field out; any other value replaces or adds it.
    _assert_typed(post(client, signed_in, body(**change)), 422, "invalid_request")
    assert sidecar["calls"] == [] and pocketbase.calls == [] and admission_store.calls == []


@pytest.mark.parametrize("raw", [b"{not json", b"[]", b"null", b'"render"'])
def test_a_body_that_isnt_an_object_is_refused(client, signed_in, sidecar, pocketbase, raw):
    res = client.post(PATH, content=raw, headers={**signed_in, "Content-Type": "application/json"})
    _assert_typed(res, 422, "invalid_request")
    assert sidecar["calls"] == [] and pocketbase.calls == []


def test_an_idempotency_key_other_than_the_bodys_command_is_refused(client, signed_in, sidecar, snapshot, pocketbase):
    res = post(client, signed_in, key="0190f000-0000-7000-8000-00000000000b")
    _assert_typed(res, 422, "invalid_request")
    assert sidecar["calls"] == [] and pocketbase.calls == []


def test_the_idempotency_key_matches_whatever_its_letter_case(client, signed_in, sidecar, snapshot):
    assert post(client, signed_in, key=KEY.upper()).status_code == 200


# ---- whose snapshot -------------------------------------------------------------------------


def test_another_accounts_snapshot_answers_exactly_like_a_missing_one(client, signed_in, sidecar, pocketbase, files):
    pocketbase.add("resumes", id=SOURCE, user="u2", hidden=True)
    pocketbase.add("legacy_artifact_snapshots", id=SNAPSHOT, user="u2", source_kind="resume", source_id=SOURCE,
                   content_checksum=CHECKSUM, markup=FILE, hidden=True)
    foreign = post(client, signed_in)
    missing = post(client, signed_in, body(snapshot_id="zzzzzzzzzzzzzz9"), key=KEY)
    for res in (foreign, missing):
        _assert_typed(res, 404, "not_found")
    assert (foreign.status_code, foreign.json()["code"], foreign.json()["detail"]) == \
        (missing.status_code, missing.json()["code"], missing.json()["detail"])
    assert sidecar["calls"] == [] and files.calls == []


def test_a_snapshot_that_names_another_owner_is_not_found_even_if_visible(client, signed_in, sidecar, pocketbase, files):
    pocketbase.add("resumes", id=SOURCE, user="u2")
    pocketbase.add("legacy_artifact_snapshots", id=SNAPSHOT, user="u2", source_kind="resume", source_id=SOURCE,
                   content_checksum=CHECKSUM, markup=FILE)
    _assert_typed(post(client, signed_in), 404, "not_found")
    assert sidecar["calls"] == [] and files.calls == []


def test_a_snapshot_whose_source_belongs_to_another_owner_is_not_found(client, signed_in, sidecar, pocketbase, files):
    pocketbase.add("resumes", id=SOURCE, user="u2")
    pocketbase.add("legacy_artifact_snapshots", id=SNAPSHOT, user=TEST_ACCOUNT_ID, source_kind="resume",
                   source_id=SOURCE, content_checksum=CHECKSUM, markup=FILE)
    _assert_typed(post(client, signed_in), 404, "not_found")
    assert sidecar["calls"] == [] and files.calls == []


def test_a_snapshot_whose_source_is_gone_is_not_found(client, signed_in, sidecar, pocketbase, files):
    pocketbase.add("legacy_artifact_snapshots", id=SNAPSHOT, user=TEST_ACCOUNT_ID, source_kind="resume",
                   source_id=SOURCE, content_checksum=CHECKSUM, markup=FILE)
    _assert_typed(post(client, signed_in), 404, "not_found")
    assert sidecar["calls"] == [] and files.calls == []


@pytest.mark.parametrize("record", [
    {"source_kind": "draft"},
    {"source_id": "../../users/x"},
    {"source_kind": None},
])
def test_a_snapshot_record_off_its_shape_is_not_found(client, signed_in, sidecar, pocketbase, files, record):
    pocketbase.add("resumes", id=SOURCE, user=TEST_ACCOUNT_ID)
    fields = {"source_kind": "resume", "source_id": SOURCE, **record}
    pocketbase.add("legacy_artifact_snapshots", id=SNAPSHOT, user=TEST_ACCOUNT_ID, content_checksum=CHECKSUM,
                   markup=FILE, **fields)
    _assert_typed(post(client, signed_in), 404, "not_found")
    assert sidecar["calls"] == []


def test_a_checksum_other_than_the_snapshots_is_refused_before_its_file_is_read(
    client, signed_in, sidecar, snapshot, files
):
    res = post(client, signed_in, body(expected_checksum="sha256:" + "0" * 64))
    _assert_typed(res, 409, "checksum_mismatch")
    assert sidecar["calls"] == [] and files.calls == []


# ---- the stored file -----------------------------------------------------------------------------


@pytest.mark.parametrize("damage", ["changed", "missing", "too-large", "not-utf8", "bad-name"])
def test_a_stored_file_that_doesnt_hold_its_checksum_is_a_typed_failure_without_a_render(
    client, signed_in, sidecar, snapshot, files, pocketbase, caplog, damage
):
    if damage == "changed":
        files.files[(SNAPSHOT, FILE)] = b"<p>another document</p>"
    elif damage == "missing":
        del files.files[(SNAPSHOT, FILE)]
    elif damage == "too-large":
        files.files[(SNAPSHOT, FILE)] = b"x" * (legacy_snapshots.MAX_MARKUP_BYTES + 1)
    elif damage == "not-utf8":
        raw = b"\xff\xfe"
        files.files[(SNAPSHOT, FILE)] = raw
        pocketbase.records["legacy_artifact_snapshots"][SNAPSHOT]["content_checksum"] = \
            "sha256:" + hashlib.sha256(raw).hexdigest()
    else:
        pocketbase.records["legacy_artifact_snapshots"][SNAPSHOT]["markup"] = "../escape.html"
    payload = body(expected_checksum=pocketbase.records["legacy_artifact_snapshots"][SNAPSHOT]["content_checksum"])
    caplog.set_level("WARNING")
    res = post(client, signed_in, payload)
    _assert_typed(res, 503, "worker_unavailable")
    assert res.json()["detail"] == RENDERER_FAILED
    assert sidecar["calls"] == []
    assert any("stored markup is unusable" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("token_status,file_status,code", [
    (500, 200, "auth_unavailable"),
    (200, 500, "auth_unavailable"),
])
def test_pocketbase_trouble_reading_the_file_is_typed(
    client, signed_in, sidecar, snapshot, files, token_status, file_status, code
):
    files.token_status, files.file_status = token_status, file_status
    _assert_typed(post(client, signed_in), 503, code)
    assert sidecar["calls"] == []


@pytest.mark.parametrize("failure", [httpx.ConnectError("x"), httpx.ReadTimeout("x")])
def test_an_unreachable_pocketbase_while_reading_the_file_is_auth_unavailable(
    client, signed_in, sidecar, pocketbase, monkeypatch, failure
):
    pocketbase.add("resumes", id=SOURCE, user=TEST_ACCOUNT_ID)
    pocketbase.add("legacy_artifact_snapshots", id=SNAPSHOT, user=TEST_ACCOUNT_ID, source_kind="resume",
                   source_id=SOURCE, content_checksum=CHECKSUM, markup=FILE)
    real = httpx.AsyncClient

    def failing(request):
        raise failure

    monkeypatch.setattr(legacy_snapshots.httpx, "AsyncClient",
                        lambda *a, **kw: real(*a, transport=httpx.MockTransport(failing), **kw))
    _assert_typed(post(client, signed_in), 503, "auth_unavailable")
    assert sidecar["calls"] == []


def test_the_file_is_read_with_a_file_token_issued_to_the_caller(files):
    raw = asyncio.run(legacy_snapshots.read_markup(TEST_TOKEN, SNAPSHOT, FILE))
    assert raw == MARKUP.encode()
    (grant, read) = files.calls
    assert grant == ("POST", legacy_snapshots.FILE_TOKEN_PATH, f"Bearer {TEST_TOKEN}")
    assert read[:2] == ("GET", f"/api/files/legacy_artifact_snapshots/{SNAPSHOT}/{FILE}")


def test_a_file_token_pocketbase_refuses_is_unauthenticated(files):
    from app.errors import TypedError

    with pytest.raises(TypedError) as refused:
        asyncio.run(legacy_snapshots.read_markup("another-token", SNAPSHOT, FILE))
    assert refused.value.code == "unauthenticated"


# ---- the sidecar ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "failure",
    [
        urllib.error.HTTPError("http://pdf-renderer:4000/render", 500, "x", {}, io.BytesIO(SIDECAR_TEXT.encode())),
        urllib.error.HTTPError("http://pdf-renderer:4000/render", 400, "x", {}, io.BytesIO(SIDECAR_TEXT.encode())),
        urllib.error.HTTPError("http://pdf-renderer:4000/render", 422, "x", {}, io.BytesIO(SIDECAR_TEXT.encode())),
        urllib.error.URLError(SIDECAR_TEXT),
        urllib.error.URLError(TimeoutError(SIDECAR_TEXT)),
        ConnectionResetError(SIDECAR_TEXT),
        # The sidecar couldn't open a page in time.
        urllib.error.HTTPError("http://pdf-renderer:4000/render", 503, "x", {}, io.BytesIO(b'{"error":"unavailable"}')),
        # Connected, but no answer within the runner's wait: the sidecar
        # answers a document's own timeout before then.
        TimeoutError(SIDECAR_TEXT),
    ],
)
def test_a_failed_render_is_a_typed_503_without_sidecar_text(client, signed_in, sidecar, snapshot, failure):
    sidecar["answer"] = failure
    res = post(client, signed_in)
    assert res.status_code == 503
    body_ = res.json()
    assert set(body_) == {"detail", "code", "correlation_id"}
    assert body_["code"] == "worker_unavailable" and body_["detail"] == RENDERER_FAILED
    assert SIDECAR_TEXT not in res.text and "pdf-renderer" not in res.text


@pytest.mark.parametrize(
    "failure",
    [
        # The sidecar's own answer for a document that ran out of time.
        urllib.error.HTTPError("http://pdf-renderer:4000/render", 422, "x", {},
                               io.BytesIO(b'{"error":"render_timeout"}')),
    ],
)
def test_a_render_that_runs_out_of_time_is_a_typed_422_without_sidecar_text(
    client, signed_in, sidecar, snapshot, failure
):
    sidecar["answer"] = failure
    res = post(client, signed_in)
    assert res.status_code == 422
    body_ = res.json()
    assert set(body_) == {"detail", "code", "correlation_id"}
    assert body_["code"] == "render_timeout"
    assert SIDECAR_TEXT not in res.text and "pdf-renderer" not in res.text


def test_an_anonymous_render_never_reaches_the_sidecar(client, sidecar, pocketbase):
    res = client.post(PATH, json=body())
    assert res.status_code == 401
    assert sidecar["calls"] == [] and pocketbase.calls == []


def test_a_render_turned_off_answers_before_the_account_or_the_body(client, gate_env, sidecar, pocketbase):
    gate_env({"ROUNDS_GATE_PDF_RENDER": "disabled"})
    for payload in (body(), {"html": "<p>hi</p>"}):
        _assert_typed(client.post(PATH, json=payload, headers={"Authorization": f"Bearer {TEST_TOKEN}"}), 503,
                      "route_disabled")
    assert sidecar["calls"] == [] and pocketbase.calls == []


def test_the_snapshot_gate_doesnt_decide_whether_a_render_runs(client, signed_in, gate_env, sidecar, snapshot):
    gate_env({"ROUNDS_GATE_LEGACY_SNAPSHOT_CREATE": "disabled"})
    assert post(client, signed_in).status_code == 200


# ---- health ----------------------------------------------------------------------------------------


def test_health_answers_only_its_status(client, signed_in, sidecar):
    res = client.get("/api/pdf/health", headers=signed_in)
    assert res.status_code == 200
    assert res.json() == {"status": "ok"}


@pytest.mark.parametrize(
    "failure",
    [urllib.error.URLError(SIDECAR_TEXT), ConnectionRefusedError(SIDECAR_TEXT), FakeResponse(status=500)],
)
def test_an_unreachable_sidecar_is_503_with_only_its_status(client, signed_in, sidecar, failure):
    sidecar["answer"] = failure
    res = client.get("/api/pdf/health", headers=signed_in)
    assert res.status_code == 503
    assert res.json() == {"status": "unavailable"}
    assert SIDECAR_TEXT not in res.text


def test_anonymous_health_is_denied(client, sidecar):
    res = client.get("/api/pdf/health")
    assert res.status_code == 401
    assert sidecar["calls"] == []
