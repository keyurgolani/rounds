"""The client address the share resolver's throttle counts by
(ROUNDS-00B-L04).

The runner sits behind nginx, so a request's peer is usually the proxy. A
peer inside ``ROUNDS_TRUSTED_PROXY_CIDRS`` is a proxy, and the one address
its ``X-Real-IP`` names is the client. Any other peer is the client itself,
whatever headers it sends. Unset, the list is loopback and the RFC 1918
ranges, where the bundled nginx sits in every launcher. An operator whose
front proxy sits elsewhere sets the list (comma-separated CIDRs), or
``none`` to trust no proxy. A list that can't be read trusts no proxy and
logs one error, so a typo never lets a client name its own address.
"""
from __future__ import annotations

import ipaddress
import logging
import os
from typing import Iterable, Mapping

_log = logging.getLogger(__name__)

ENV = "ROUNDS_TRUSTED_PROXY_CIDRS"
DEFAULT_CIDRS = ("127.0.0.0/8", "::1/128", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
HEADER = b"x-real-ip"

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address
IPNetwork = ipaddress.IPv4Network | ipaddress.IPv6Network

_parsed: dict[str, tuple[IPNetwork, ...]] = {}


def _networks(raw: str) -> tuple[IPNetwork, ...] | None:
    if raw.strip().lower() == "none":
        return ()
    out = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            return None
        try:
            out.append(ipaddress.ip_network(part, strict=True))
        except ValueError:
            return None
    return tuple(out)


def trusted_networks(environ: Mapping[str, str] | None = None) -> tuple[IPNetwork, ...]:
    """The proxies whose ``X-Real-IP`` counts."""
    env = os.environ if environ is None else environ
    raw = (env.get(ENV) or "").strip()
    if not raw:
        raw = ",".join(DEFAULT_CIDRS)
    if raw not in _parsed:
        networks = _networks(raw)
        if networks is None:
            # Never the value: it names the deployment's network.
            _log.error("%s can't be read, so no proxy is trusted until it is fixed.", ENV)
            networks = ()
        _parsed[raw] = networks
    return _parsed[raw]


def _address(value: object) -> IPAddress | None:
    if not isinstance(value, str):
        return None
    try:
        ip = ipaddress.ip_address(value.strip())
    except ValueError:
        return None
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped is not None:
        return ip.ipv4_mapped
    return ip


def client_address(
    peer: str | None,
    headers: Iterable[tuple[bytes, bytes]],
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """The address to count a request by: the peer, or, when the peer is a
    trusted proxy that sent exactly one readable ``X-Real-IP``, that
    address. None when the peer isn't an address."""
    peer_ip = _address(peer)
    if peer_ip is None:
        return None
    if not any(peer_ip in network for network in trusted_networks(environ)):
        return str(peer_ip)
    named = [value for name, value in headers if name.lower() == HEADER]
    if len(named) != 1:
        return str(peer_ip)
    forwarded = _address(named[0].decode("latin-1"))
    return str(forwarded) if forwarded is not None else str(peer_ip)
