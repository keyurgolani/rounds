"""Where an AI provider base URL may point (ROUNDS-00A-L01, D3).

A provider base URL is account data that the runner connects to, so it
can't name the runner's own neighborhood. These answer 403
``destination_denied``:

- a scheme other than ``http`` or ``https``, or no host;
- loopback, link-local, unspecified, multicast, reserved, and other
  non-public addresses;
- cloud metadata addresses;
- service names: single-label hosts and the ``localhost``,
  ``.localhost``, ``.internal``, ``.svc``, and ``.cluster.local``
  suffixes;
- private networks (RFC 1918, RFC 6598 shared space, IPv6 ULA), unless
  ``ROUNDS_GATE_PROVIDER_PRIVATE_NETWORK`` is ``enabled`` for a model
  server on the operator's LAN.

A name is checked as written and then by every address it resolves to.
A name that doesn't resolve is denied too.

``vet`` does that with one lookup and returns the checked addresses.
Every outbound call to a provider, or to a paper URL, goes through a
``client``: an httpx client whose transport connects only to a vetted
address, keeping the name for the Host header and TLS, so the
connection can't land somewhere the lookup didn't check. A host the
caller didn't vet first is vetted on its first request, once per
client. Redirects are off unless the caller turns them on, and then
every hop is vetted the same way.

TODO(ROUNDS-14-L02): #73's provider invocation owns outbound policy.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Iterable
from urllib.parse import urlsplit

import httpx

from app import gates
from app.errors import TypedError

GATE = "PROVIDER_PRIVATE_NETWORK"
RESOLVE_TIMEOUT_S = 5
UNRESOLVED = "This provider address doesn't resolve."

Address = ipaddress.IPv4Address | ipaddress.IPv6Address

# Always denied, whatever the gate says.
METADATA_ADDRESSES = frozenset(
    ipaddress.ip_address(a)
    for a in (
        "169.254.169.254",
        "169.254.170.2",
        "169.254.170.23",
        "100.100.100.200",
        "168.63.129.16",
        "fd00:ec2::254",
        "fd00:ec2::23",
    )
)
# Allowed only while the gate is enabled.
PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(n)
    for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "fc00::/7")
)
SERVICE_SUFFIXES = (".localhost", ".internal", ".svc", ".cluster.local")
NAT64_PREFIX = ipaddress.ip_network("64:ff9b::/96")

Resolver = Callable[[str, int], Awaitable[Iterable[str]]]


def _deny(detail: str | None = None) -> TypedError:
    return TypedError("destination_denied", detail)


def private_network_allowed() -> bool:
    return gates.value(GATE) == "enabled"


def _unwrap(address: Address) -> Address:
    """The IPv4 address an IPv4-mapped, 6to4, or NAT64 IPv6 address
    carries, so it's judged as that IPv4 address."""
    if isinstance(address, ipaddress.IPv6Address):
        embedded = address.ipv4_mapped or address.sixtofour
        if embedded is not None:
            return embedded
        if address in NAT64_PREFIX:
            return ipaddress.IPv4Address(int(address) & 0xFFFFFFFF)
    return address


def address_allowed(address: Address, private_ok: bool) -> bool:
    address = _unwrap(address)
    if address in METADATA_ADDRESSES:
        return False
    if any(address in net for net in PRIVATE_NETWORKS if net.version == address.version):
        return private_ok
    if isinstance(address, ipaddress.IPv6Address) and address.is_site_local:
        return False
    return address.is_global and not address.is_multicast


def _host_and_port(base_url: str) -> tuple[str, int]:
    try:
        parts = urlsplit(base_url.strip())
        port = parts.port
    except ValueError:
        raise _deny() from None
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise _deny()
    host = parts.hostname.rstrip(".").lower()
    if not host:
        raise _deny()
    return host, port or (443 if parts.scheme == "https" else 80)


def _literal(host: str) -> Address | None:
    try:
        return ipaddress.ip_address(host)
    except ValueError:
        return None


def check_static(base_url: str, private_ok: bool | None = None) -> tuple[str, int, Address | None]:
    """The checks that need no lookup. Returns the host, the port, and
    the address when the host is an IP literal."""
    allowed_private = private_network_allowed() if private_ok is None else private_ok
    host, port = _host_and_port(base_url)
    literal = _literal(host)
    if literal is not None:
        if not address_allowed(literal, allowed_private):
            raise _deny()
        return host, port, literal
    if "." not in host or host == "localhost" or host.endswith(SERVICE_SUFFIXES):
        raise _deny()
    return host, port, None


async def _system_resolve(host: str, port: int) -> list[str]:
    loop = asyncio.get_running_loop()
    infos = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return [info[4][0] for info in infos]


resolve: Resolver = _system_resolve


@dataclass(frozen=True)
class Destination:
    """A host and port whose every address passed the checks, from one
    lookup."""

    host: str
    port: int
    addresses: tuple[Address, ...]


async def vet(url: str | None, private_ok: bool | None = None) -> Destination | None:
    """The checked destination of ``url``, from one lookup, or None for an
    empty URL, which means the provider's public default. Raises 403
    ``destination_denied`` unless every check passes."""
    if not url or not url.strip():
        return None
    allowed_private = private_network_allowed() if private_ok is None else private_ok
    host, port, literal = check_static(url, allowed_private)
    if literal is not None:
        return Destination(host, port, (literal,))
    try:
        found = await asyncio.wait_for(resolve(host, port), RESOLVE_TIMEOUT_S)
    except (OSError, asyncio.TimeoutError, UnicodeError):
        raise _deny(UNRESOLVED) from None
    addresses = []
    for raw in found:
        try:
            addresses.append(ipaddress.ip_address(str(raw).split("%", 1)[0]))
        except ValueError:
            raise _deny() from None
    if not addresses:
        raise _deny(UNRESOLVED)
    if not all(address_allowed(a, allowed_private) for a in addresses):
        raise _deny()
    return Destination(host, port, tuple(dict.fromkeys(addresses)))


async def check(base_url: str | None) -> None:
    """Deny ``base_url`` unless every check passes. An empty base URL
    means the provider's public default and passes."""
    await vet(base_url)


def _vetted_for(destination: Destination | None, url: str | None) -> bool:
    if destination is None or not url or not url.strip():
        return False
    try:
        return _host_and_port(url) == (destination.host, destination.port)
    except TypedError:
        return False


async def vetted(url: str | None, destination: Destination | None = None) -> Destination | None:
    """``destination`` when it was vetted for ``url``'s host and port,
    otherwise a fresh ``vet``, so a caller that already vetted the URL
    doesn't look it up again."""
    if _vetted_for(destination, url):
        return destination
    return await vet(url)


def inner_transport(host: str) -> httpx.AsyncBaseTransport:
    """The transport that carries one host's connections. Each host gets
    its own pool, so a connection set up for one name never serves
    another."""
    return httpx.AsyncHTTPTransport()


class PinnedTransport(httpx.AsyncBaseTransport):
    """Sends each request to a vetted address of its host: one the caller
    vetted, or one this transport vets on the host's first request. The
    request goes out with the name in its Host header, and TLS checks
    the certificate against the name. An address that refuses the
    connection falls through to the next vetted one. The client's own
    request keeps its URL, so a relative redirect resolves against the
    name, not the address."""

    def __init__(self, known: Iterable[Destination] = (), private_ok: bool | None = None) -> None:
        self._vetted = {(d.host, d.port): d for d in known}
        self._private_ok = private_ok
        self._inner: dict[str, httpx.AsyncBaseTransport] = {}

    async def _destination(self, url: httpx.URL) -> Destination:
        key = _host_and_port(str(url))
        destination = self._vetted.get(key)
        if destination is None:
            destination = await vet(str(url), self._private_ok)
            if destination is None:
                raise _deny()
            self._vetted[key] = destination
        return destination

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        url = request.url
        destination = await self._destination(url)
        inner = self._inner.get(destination.host)
        if inner is None:
            inner = self._inner[destination.host] = inner_transport(destination.host)
        extensions = dict(request.extensions)
        if url.scheme == "https":
            extensions["sni_hostname"] = destination.host
        last = len(destination.addresses) - 1
        for index, address in enumerate(destination.addresses):
            pinned = httpx.Request(
                request.method,
                url.copy_with(host=str(address)),
                headers=request.headers,
                stream=request.stream,
                extensions=extensions,
            )
            try:
                return await inner.handle_async_request(pinned)
            except httpx.ConnectError:
                if index == last:
                    raise
        raise _deny()  # unreachable: a vetted destination has an address

    async def aclose(self) -> None:
        for inner in self._inner.values():
            await inner.aclose()


def client(
    *known: Destination | None,
    private_ok: bool | None = None,
    follow_redirects: bool = False,
    **kwargs: Any,
) -> httpx.AsyncClient:
    """An httpx client for outbound calls that connects only to vetted
    addresses. ``known`` destinations were vetted already and need no
    further lookup; any other host is vetted once, on its first request.
    ``private_ok`` overrides the private-network gate (the paper fetch
    passes False). Redirects stay off unless ``follow_redirects``; each
    hop is vetted either way. With its own transport, the client ignores
    proxy settings in the environment."""
    transport = PinnedTransport([d for d in known if d is not None], private_ok)
    return httpx.AsyncClient(transport=transport, follow_redirects=follow_redirects, **kwargs)
