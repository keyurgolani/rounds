"""The address the share resolver counts by (ROUNDS-00B-L04,
app/client_ip.py): a trusted proxy's X-Real-IP, or the peer itself, and a
setting that can't be read trusts no proxy."""
from __future__ import annotations

import logging

import pytest

from app import client_ip

REAL_IP = b"x-real-ip"


def _headers(*values: str) -> list[tuple[bytes, bytes]]:
    return [(b"host", b"rounds.test")] + [(REAL_IP, v.encode("latin-1")) for v in values]


def test_the_default_trusts_loopback_and_rfc1918():
    assert client_ip.DEFAULT_CIDRS == ("127.0.0.0/8", "::1/128", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
    for peer in ("127.0.0.1", "::1", "10.1.2.3", "172.20.0.5", "192.168.1.9"):
        assert client_ip.client_address(peer, _headers("203.0.113.7"), {}) == "203.0.113.7", peer


@pytest.mark.parametrize("peer", ["203.0.113.50", "172.32.0.1", "100.64.0.1", "fd00::1", "2001:db8::1"])
def test_an_untrusted_peer_is_the_client_whatever_it_sends(peer):
    assert client_ip.client_address(peer, _headers("198.51.100.1"), {}) == peer


def test_a_trusted_peer_without_the_header_is_itself():
    assert client_ip.client_address("10.0.0.9", _headers(), {}) == "10.0.0.9"


@pytest.mark.parametrize("values", [("203.0.113.7", "198.51.100.1"), ("203.0.113.7, 198.51.100.1",), ("nope",), ("",)])
def test_a_trusted_peer_that_names_no_one_readable_address_is_itself(values):
    assert client_ip.client_address("10.0.0.9", _headers(*values), {}) == "10.0.0.9"


def test_the_header_name_matches_in_any_case():
    headers = [(b"X-Real-IP", b"203.0.113.7")]
    assert client_ip.client_address("10.0.0.9", headers, {}) == "203.0.113.7"


def test_ipv4_mapped_addresses_are_ipv4():
    assert client_ip.client_address("::ffff:10.0.0.9", _headers("::ffff:203.0.113.7"), {}) == "203.0.113.7"
    assert client_ip.client_address("::ffff:203.0.113.50", _headers("198.51.100.1"), {}) == "203.0.113.50"


@pytest.mark.parametrize("peer", [None, "", "not-an-address", "unix:/tmp/sock"])
def test_a_peer_that_is_not_an_address_has_none(peer):
    assert client_ip.client_address(peer, _headers("203.0.113.7"), {}) is None


def test_an_operator_list_replaces_the_default():
    env = {client_ip.ENV: "198.51.100.0/24, 2001:db8::/32"}
    assert client_ip.client_address("198.51.100.20", _headers("203.0.113.7"), env) == "203.0.113.7"
    assert client_ip.client_address("2001:db8::5", _headers("203.0.113.7"), env) == "203.0.113.7"
    # The default ranges no longer count.
    assert client_ip.client_address("10.0.0.9", _headers("203.0.113.7"), env) == "10.0.0.9"


def test_none_trusts_no_proxy():
    env = {client_ip.ENV: "none"}
    assert client_ip.trusted_networks(env) == ()
    assert client_ip.client_address("127.0.0.1", _headers("203.0.113.7"), env) == "127.0.0.1"


@pytest.mark.parametrize("raw", ["10.0.0.0/8,", "10.0.0.1/8", "10.0.0.0/33", "ten", "10.0.0.0/8;192.168.0.0/16"])
def test_a_setting_that_cant_be_read_trusts_no_proxy_and_logs_without_the_value(raw, caplog):
    client_ip._parsed.clear()
    env = {client_ip.ENV: raw}
    with caplog.at_level(logging.ERROR, logger="app.client_ip"):
        assert client_ip.trusted_networks(env) == ()
        assert client_ip.client_address("10.0.0.9", _headers("203.0.113.7"), env) == "10.0.0.9"
        client_ip.trusted_networks(env)
    errors = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(errors) == 1
    assert raw not in errors[0].getMessage()


def test_an_empty_setting_is_the_default():
    assert client_ip.trusted_networks({client_ip.ENV: "  "}) == client_ip.trusted_networks({})
