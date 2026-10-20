"""AI provider base URL destinations (ROUNDS-00A-L01, D3).

Loopback, link-local, metadata, other non-public addresses, and service
names answer 403 ``destination_denied``. Private networks do too unless
``ROUNDS_GATE_PROVIDER_PRIVATE_NETWORK`` is enabled."""
from __future__ import annotations

import asyncio
import datetime
import ipaddress
import socket
import ssl

import httpx
import pytest

from app import destinations, gates
from app.errors import TypedError


@pytest.fixture
def private_network(monkeypatch):
    def set_gate(value: str):
        monkeypatch.setattr(gates, "_snapshot", gates.load({"ROUNDS_GATE_PROVIDER_PRIVATE_NETWORK": value}, gates.RUNNER))

    set_gate("")
    return set_gate


@pytest.fixture
def resolves(monkeypatch):
    """Answers every lookup with the given addresses."""
    answers: dict[str, list[str]] = {}
    asked: list[str] = []

    async def fake(host, port):
        asked.append(host)
        if host not in answers:
            raise socket.gaierror("no such host")
        return answers[host]

    monkeypatch.setattr(destinations, "resolve", fake)
    fake.answers = answers
    fake.asked = asked
    return fake


def _check(url):
    asyncio.run(destinations.check(url))


def _denied(url) -> TypedError:
    with pytest.raises(TypedError) as err:
        _check(url)
    assert err.value.code == "destination_denied" and err.value.status_code == 403
    return err.value


# ---- what never needs a lookup -------------------------------------------------------


@pytest.mark.parametrize("url", ["", "   ", None])
def test_an_empty_base_url_means_the_public_default(private_network, resolves, url):
    _check(url)
    assert resolves.asked == []


@pytest.mark.parametrize(
    "url",
    [
        "ftp://models.example.com/v1",
        "file:///etc/passwd",
        "gopher://models.example.com",
        "models.example.com/v1",
        "http://",
        "http://:8080/v1",
        "https://models.example.com:99999/v1",
    ],
)
def test_only_http_and_https_with_a_host(private_network, resolves, url):
    _denied(url)
    assert resolves.asked == []


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:11434/v1",
        "http://LOCALHOST./v1",
        "http://api.localhost/v1",
        "http://pocketbase:8090/api",
        "http://runner:8000",
        "http://pdf-renderer:4000",
        "http://frontend",
        "http://ollama:11434/v1",
        "http://metadata.google.internal/computeMetadata/v1",
        "http://host.docker.internal:11434/v1",
        "http://runner.rounds.svc/v1",
        "http://runner.rounds.svc.cluster.local:8000",
        "http://kubernetes.default.svc",
    ],
)
def test_service_names_are_denied_without_a_lookup(private_network, resolves, url):
    _denied(url)
    assert resolves.asked == []


@pytest.mark.parametrize(
    "address",
    [
        "127.0.0.1", "127.8.9.10", "[::1]", "0.0.0.0", "[::]",
        "169.254.169.254", "169.254.170.2", "[fe80::1]", "100.100.100.200", "[fd00:ec2::254]",
        "224.0.0.1", "[ff02::1]", "240.0.0.1", "255.255.255.255", "192.0.2.10", "198.18.0.1",
        "[::ffff:127.0.0.1]", "[::ffff:169.254.169.254]", "[2002:7f00:1::]", "[64:ff9b::7f00:1]", "[fec0::1]",
    ],
)
def test_non_public_addresses_are_denied_whatever_the_gate(private_network, resolves, address):
    for value in ("disabled", "enabled"):
        private_network(value)
        _denied(f"http://{address}:8080/v1")
    assert resolves.asked == []


@pytest.mark.parametrize(
    "address", ["10.0.0.5", "172.16.3.4", "172.31.255.1", "192.168.1.20", "100.64.0.9", "[fd12:3456::1]"]
)
def test_private_addresses_follow_the_gate(private_network, resolves, address):
    private_network("")
    _denied(f"http://{address}:11434/v1")
    private_network("disabled")
    _denied(f"http://{address}:11434/v1")
    private_network("enabled")
    _check(f"http://{address}:11434/v1")
    assert resolves.asked == []


def test_an_invalid_gate_value_keeps_private_addresses_denied(private_network):
    private_network("yes-please")
    _denied("http://192.168.1.20:11434/v1")


@pytest.mark.parametrize("address", ["8.8.8.8", "1.1.1.1", "[2606:4700:4700::1111]"])
def test_public_addresses_pass(private_network, resolves, address):
    _check(f"https://{address}/v1")


# ---- names, by every address they resolve to -------------------------------------------


def test_a_public_name_passes(private_network, resolves):
    resolves.answers["api.example.com"] = ["93.184.215.14", "2606:2800:21f:cb07:6820:80da:af6b:8b2c"]
    _check("https://api.example.com/v1")
    assert resolves.asked == ["api.example.com"]


@pytest.mark.parametrize(
    "answers",
    [["127.0.0.1"], ["93.184.215.14", "10.0.0.8"], ["169.254.169.254"], ["::1"], ["fe80::1%eth0"]],
)
def test_a_name_that_resolves_anywhere_non_public_is_denied(private_network, resolves, answers):
    resolves.answers["models.example.com"] = answers
    _denied("https://models.example.com/v1")


def test_a_name_on_the_lan_follows_the_gate(private_network, resolves):
    resolves.answers["gpu-box.lan"] = ["192.168.1.30"]
    _denied("http://gpu-box.lan:11434/v1")
    private_network("enabled")
    _check("http://gpu-box.lan:11434/v1")


def test_a_name_that_doesnt_resolve_is_denied(private_network, resolves):
    err = _denied("https://nowhere.example.com/v1")
    assert err.detail == destinations.UNRESOLVED


def test_a_lookup_that_hangs_is_denied(private_network, monkeypatch):
    async def slow(host, port):
        await asyncio.sleep(10)
        return ["93.184.215.14"]

    monkeypatch.setattr(destinations, "resolve", slow)
    monkeypatch.setattr(destinations, "RESOLVE_TIMEOUT_S", 0.05)
    err = _denied("https://slow.example.com/v1")
    assert err.detail == destinations.UNRESOLVED


def test_metadata_addresses_are_never_private_network():
    for address in destinations.METADATA_ADDRESSES:
        assert not destinations.address_allowed(address, private_ok=True), address
    assert not destinations.address_allowed(ipaddress.ip_address("100.100.100.200"), private_ok=True)


# ---- every provider path checks ------------------------------------------------------------


def _provider_user():
    return {"id": "u1", "token": "test-token-placeholder", "record": {"id": "u1"}}


def test_creating_a_provider_on_loopback_is_refused_before_saving(client, monkeypatch, private_network):
    from routers import ai

    async def user(_request):
        return _provider_user()

    async def save(*_args, **_kwargs):
        pytest.fail("the provider was saved")

    monkeypatch.setattr(ai, "current_user", user)
    monkeypatch.setattr(ai, "pb_post", save)
    res = client.post(
        "/api/ai/providers",
        json={"kind": "openai-compatible", "label": "Local", "base_url": "http://127.0.0.1:11434/v1", "key": "test-key"},
    )
    assert res.status_code == 403
    assert res.json()["code"] == "destination_denied"


def test_updating_a_provider_to_a_service_name_is_refused_before_saving(client, monkeypatch, private_network):
    from routers import ai

    async def user(_request):
        return _provider_user()

    async def load(_user, _provider_id):
        return {"id": "p1", "user": "u1", "kind": "openai-compatible", "base_url": ""}

    async def save(*_args, **_kwargs):
        pytest.fail("the provider was saved")

    monkeypatch.setattr(ai, "current_user", user)
    monkeypatch.setattr(ai, "_load_provider", load)
    monkeypatch.setattr(ai, "pb_patch", save)
    res = client.patch(
        "/api/ai/providers/p1",
        json={"kind": "openai-compatible", "label": "X", "base_url": "http://pocketbase:8090/api"},
    )
    assert res.status_code == 403
    assert res.json()["code"] == "destination_denied"


def test_a_stored_provider_on_a_private_address_is_refused_before_any_call(monkeypatch, private_network):
    from routers import ai

    async def settings(_user):
        return {"text_provider": "p1", "text_model": "m"}

    async def load(_user, _provider_id):
        return {"id": "p1", "user": "u1", "kind": "openai-compatible", "base_url": "http://10.1.2.3:8000/v1", "encrypted_key": "e", "key_iv": "i"}

    monkeypatch.setattr(ai, "_load_settings", settings)
    monkeypatch.setattr(ai, "_load_provider", load)
    monkeypatch.setattr(ai, "decrypt", lambda *_a: "test-key")
    with pytest.raises(TypedError) as err:
        asyncio.run(ai._active_text_config(_provider_user()))
    assert err.value.code == "destination_denied"


@pytest.mark.parametrize("call", ["complete", "stream", "models"])
def test_every_provider_call_checks_its_base_url_again(monkeypatch, private_network, call):
    from routers import ai

    def no_network(*_args, **_kwargs):
        pytest.fail("a provider request was made")

    monkeypatch.setattr(ai.httpx, "AsyncClient", no_network)

    async def go():
        if call == "complete":
            await ai._call_complete("anthropic-compatible", "m", "k", "http://169.254.169.254/v1", system="s", messages=[])
        elif call == "stream":
            async for _chunk in ai._call_stream("anthropic-compatible", "m", "k", "http://169.254.169.254/v1", system="s", messages=[]):
                pass
        else:
            await ai._fetch_models("openai-compatible", "k", "http://169.254.169.254/v1")

    with pytest.raises(TypedError) as err:
        asyncio.run(go())
    assert err.value.code == "destination_denied"


# ---- every connection goes to a checked address, by name ------------------------------------

PUBLIC = "93.184.216.34"
PUBLIC_2 = "93.184.216.35"
PROVIDER_URL = "https://models.example.com/v1"
MESSAGES_REPLY = {"content": [{"type": "text", "text": "PONG"}]}


class Wire:
    """Stands in for the network behind the pinned transport: records
    each request it sends and answers with ``respond``."""

    def __init__(self) -> None:
        self.sent: list[httpx.Request] = []
        self.respond = lambda request: httpx.Response(200, json={})

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.sent.append(request)
        return self.respond(request)


@pytest.fixture
def wire(monkeypatch):
    found = Wire()
    network = httpx.MockTransport(found.handle)
    monkeypatch.setattr(destinations, "inner_transport", lambda host: network)
    return found


def _redirect(location: str, status: int = 307):
    return lambda request: httpx.Response(status, headers={"Location": location})


async def _drain(stream):
    async for _chunk in stream:
        pass


def _provider_calls():
    from routers import ai, sd_practice

    def complete(kind):
        return lambda url: ai._call_complete(kind, "m", "test-key", url, system="s", messages=[])

    def stream(kind):
        return lambda url: _drain(ai._call_stream(kind, "m", "test-key", url, system="s", messages=[]))

    return {
        "complete-openai": complete("openai-compatible"),
        "complete-anthropic": complete("anthropic-compatible"),
        "stream-openai": stream("openai-compatible"),
        "stream-anthropic": stream("anthropic-compatible"),
        "models": lambda url: ai._fetch_models("openai-compatible", "test-key", url),
        "practice-openai": lambda url: _drain(
            sd_practice._openai_stream_with_tools("m", "test-key", url, system="s", messages=[], tools=[])
        ),
        "practice-anthropic": lambda url: _drain(
            sd_practice._anthropic_stream_with_tools("m", "test-key", url, system="s", messages=[], tools=[])
        ),
    }


PROVIDER_CALLS = sorted(_provider_calls())


def _run_past_errors(coro) -> None:
    # The provider answers here aren't valid replies; what matters is
    # what was sent.
    try:
        asyncio.run(coro)
    except Exception:  # noqa: BLE001
        pass


@pytest.mark.parametrize("target", ["https://elsewhere.example.com/v1/chat", "http://169.254.169.254/latest/meta-data/"])
@pytest.mark.parametrize("call", PROVIDER_CALLS)
def test_no_provider_call_follows_a_redirect(private_network, resolves, wire, call, target):
    # Even to a public host: one request, to the provider, and no second hop.
    resolves.answers["models.example.com"] = [PUBLIC]
    resolves.answers["elsewhere.example.com"] = [PUBLIC_2]
    wire.respond = _redirect(target)
    _run_past_errors(_provider_calls()[call](PROVIDER_URL))
    assert [r.url.host for r in wire.sent] == [PUBLIC]
    assert resolves.asked == ["models.example.com"]


@pytest.mark.parametrize("call", PROVIDER_CALLS)
def test_each_provider_call_looks_up_once_and_connects_to_the_checked_address(private_network, resolves, wire, call):
    resolves.answers["models.example.com"] = [PUBLIC]
    _run_past_errors(_provider_calls()[call](PROVIDER_URL))
    assert resolves.asked == ["models.example.com"]
    (sent,) = wire.sent
    assert sent.url.host == PUBLIC
    assert sent.headers["host"] == "models.example.com"
    assert sent.extensions["sni_hostname"] == "models.example.com"


def test_a_configured_provider_is_looked_up_once_for_the_config_and_the_call(monkeypatch, private_network, resolves, wire):
    from routers import ai

    async def settings(_user):
        return {"text_provider": "p1", "text_model": "m"}

    async def load(_user, _provider_id):
        return {"id": "p1", "user": "u1", "kind": "anthropic-compatible", "base_url": PROVIDER_URL, "encrypted_key": "e", "key_iv": "i"}

    monkeypatch.setattr(ai, "_load_settings", settings)
    monkeypatch.setattr(ai, "_load_provider", load)
    monkeypatch.setattr(ai, "decrypt", lambda *_a: "test-key")
    resolves.answers["models.example.com"] = [PUBLIC]
    wire.respond = lambda request: httpx.Response(200, json=MESSAGES_REPLY)

    async def go():
        cfg = await ai._active_text_config(_provider_user())
        return await ai._call_complete(
            cfg["kind"], cfg["model"], cfg["api_key"], cfg["base_url"] or None,
            system="s", messages=[], destination=cfg.get("destination"),
        )

    assert asyncio.run(go()) == "PONG"
    assert resolves.asked == ["models.example.com"]
    assert [r.url.host for r in wire.sent] == [PUBLIC]


def test_testing_a_provider_looks_it_up_once(client, monkeypatch, private_network, resolves, wire):
    from routers import ai

    async def user(_request):
        return _provider_user()

    async def load(_user, _provider_id):
        return {"id": "p1", "user": "u1", "kind": "anthropic-compatible", "base_url": PROVIDER_URL,
                "encrypted_key": "e", "key_iv": "i", "models_cache": ["m"]}

    monkeypatch.setattr(ai, "current_user", user)
    monkeypatch.setattr(ai, "_load_provider", load)
    monkeypatch.setattr(ai, "decrypt", lambda *_a: "test-key")
    resolves.answers["models.example.com"] = [PUBLIC]
    wire.respond = lambda request: httpx.Response(200, json=MESSAGES_REPLY)
    res = client.post("/api/ai/providers/p1/test")
    assert res.status_code == 200, res.text
    assert resolves.asked == ["models.example.com"]


def test_a_refused_address_falls_through_to_the_next_checked_one(private_network, resolves, wire):
    from routers import ai

    resolves.answers["models.example.com"] = [PUBLIC, PUBLIC_2]

    def respond(request):
        if request.url.host == PUBLIC:
            raise httpx.ConnectError("connection refused")
        return httpx.Response(200, json=MESSAGES_REPLY)

    wire.respond = respond
    text = asyncio.run(ai._call_complete("anthropic-compatible", "m", "test-key", PROVIDER_URL, system="s", messages=[]))
    assert text == "PONG"
    assert [r.url.host for r in wire.sent] == [PUBLIC, PUBLIC_2]


def test_a_client_that_follows_redirects_checks_every_hop(private_network, resolves, wire):
    resolves.answers["papers.example.com"] = [PUBLIC]
    wire.respond = _redirect("http://127.0.0.1:8090/api/admins", status=302)

    async def go():
        async with destinations.client(follow_redirects=True) as http:
            await http.get("https://papers.example.com/p")

    with pytest.raises(TypedError) as err:
        asyncio.run(go())
    assert err.value.code == "destination_denied"
    assert [r.url.host for r in wire.sent] == [PUBLIC]


def test_a_chosen_provider_on_a_denied_address_is_refused_in_design_practice(monkeypatch, private_network):
    from routers import sd_practice

    async def load(_user, _provider_id):
        return {"id": "p1", "user": "u1", "kind": "openai-compatible", "base_url": "http://169.254.169.254/v1",
                "encrypted_key": "e", "key_iv": "i"}

    monkeypatch.setattr(sd_practice, "_load_provider", load)
    monkeypatch.setattr(sd_practice, "decrypt", lambda *_a: "test-key")
    with pytest.raises(TypedError) as err:
        asyncio.run(sd_practice._resolve_text_cfg(_provider_user(), "p1", "m"))
    assert err.value.code == "destination_denied"


# ---- the paper fetch ---------------------------------------------------------------------------


@pytest.mark.parametrize("gate", ["", "enabled"])
def test_the_paper_fetch_never_reaches_a_private_address(private_network, resolves, wire, gate):
    from routers import ai

    private_network(gate)
    resolves.answers["papers.example.com"] = [PUBLIC]
    resolves.answers["intranet.example.com"] = ["10.0.0.5"]
    assert asyncio.run(ai._fetch_paper_text("http://10.0.0.5/paper.pdf")) is None
    assert wire.sent == []
    wire.respond = _redirect("https://intranet.example.com/paper.pdf", status=302)
    assert asyncio.run(ai._fetch_paper_text("https://papers.example.com/paper.pdf")) is None
    assert [r.url.host for r in wire.sent] == [PUBLIC]


def test_the_paper_fetch_follows_public_redirects_by_name(private_network, resolves, wire):
    from routers import ai

    resolves.answers["doi.example.org"] = [PUBLIC]
    resolves.answers["papers.example.com"] = [PUBLIC_2]

    def respond(request):
        if request.headers["host"] == "doi.example.org":
            return httpx.Response(302, headers={"Location": "https://papers.example.com/abs"})
        if request.url.path == "/abs":
            return httpx.Response(302, headers={"Location": "/full"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<p>Paper text</p>")

    wire.respond = respond
    assert asyncio.run(ai._fetch_paper_text("https://doi.example.org/10.1/x")) == "Paper text"
    assert [(r.url.host, r.headers["host"], r.url.path) for r in wire.sent] == [
        (PUBLIC, "doi.example.org", "/10.1/x"),
        (PUBLIC_2, "papers.example.com", "/abs"),
        (PUBLIC_2, "papers.example.com", "/full"),
    ]


def test_the_paper_fetch_stops_after_5_redirects(private_network, resolves, wire):
    from routers import ai

    resolves.answers["papers.example.com"] = [PUBLIC]
    wire.respond = lambda request: httpx.Response(302, headers={"Location": f"{request.url.path}x"})
    assert asyncio.run(ai._fetch_paper_text("https://papers.example.com/p")) is None
    assert len(wire.sent) == 6


# ---- TLS checks the name, not the pinned address ------------------------------------------------


def _self_signed(name: str, directory) -> tuple[str, str]:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID

    key = ec.generate_private_key(ec.SECP256R1())
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=5))
        .not_valid_after(now + datetime.timedelta(hours=1))
        .add_extension(x509.SubjectAlternativeName([x509.DNSName(name)]), critical=False)
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .sign(key, hashes.SHA256())
    )
    cert_path, key_path = directory / "cert.pem", directory / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    )
    return str(cert_path), str(key_path)


@pytest.mark.parametrize("name, verified", [("models.test", True), ("other.test", False)])
def test_a_pinned_tls_connection_checks_the_certificate_against_the_name(tmp_path, monkeypatch, resolves, name, verified):
    cert, key = _self_signed("models.test", tmp_path)
    seen: dict[str, str] = {}
    server_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    server_context.load_cert_chain(cert, key)
    server_context.sni_callback = lambda _sock, sni, _ctx: seen.update(sni=sni)
    client_context = ssl.create_default_context(cafile=cert)
    monkeypatch.setattr(destinations, "inner_transport", lambda host: httpx.AsyncHTTPTransport(verify=client_context))

    async def handle(reader, writer):
        try:
            seen["request"] = (await reader.readuntil(b"\r\n\r\n")).decode()
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
            await writer.drain()
        except (ConnectionError, asyncio.IncompleteReadError, ssl.SSLError):
            pass
        finally:
            writer.close()

    async def go():
        server = await asyncio.start_server(handle, "127.0.0.1", 0, ssl=server_context)
        port = server.sockets[0].getsockname()[1]
        pinned = destinations.Destination(name, port, (ipaddress.ip_address("127.0.0.1"),))
        try:
            async with destinations.client(pinned) as http:
                response = await http.get(f"https://{name}:{port}/v1/models")
                return port, response.text
        finally:
            server.close()

    if verified:
        port, text = asyncio.run(go())
        assert text == "ok"
        assert seen["sni"] == "models.test"
        assert f"host: models.test:{port}" in seen["request"].lower()
    else:
        with pytest.raises(httpx.ConnectError):
            asyncio.run(go())
    assert resolves.asked == []
