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

TODO(ROUNDS-14-L02): #73's provider invocation owns outbound policy,
including pinning the checked address for the connection itself.
"""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from typing import Awaitable, Callable, Iterable
from urllib.parse import urlsplit

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


async def check(base_url: str | None) -> None:
    """Deny ``base_url`` unless every check passes. An empty base URL
    means the provider's public default and passes."""
    if not base_url or not base_url.strip():
        return
    private_ok = private_network_allowed()
    host, port, literal = check_static(base_url, private_ok)
    if literal is not None:
        return
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
    if not all(address_allowed(a, private_ok) for a in addresses):
        raise _deny()
