"""AI provider base URL destinations (ROUNDS-00A-L01, D3).

Loopback, link-local, metadata, other non-public addresses, and service
names answer 403 ``destination_denied``. Private networks do too unless
``ROUNDS_GATE_PROVIDER_PRIVATE_NETWORK`` is enabled."""
from __future__ import annotations

import asyncio
import ipaddress
import socket

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
