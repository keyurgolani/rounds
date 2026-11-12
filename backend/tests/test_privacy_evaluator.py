"""The privacy evaluators against the shared vectors (ROUNDS-14-L01).

The same vector files drive frontend/src/privacy/__tests__/evaluator.test.ts,
so both evaluators answer every case the same way. The vectors and policy
files are the copies scripts/conformance/run.mjs --write keeps beside the
evaluator.
"""
from __future__ import annotations

import copy
import ipaddress
import json
import time
from pathlib import Path

import pytest

from app import destinations
from app.privacy import evaluator

VECTORS = Path(evaluator.__file__).resolve().parent / "vectors"


def _cases():
    out = []
    for path in sorted(VECTORS.glob("*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        for case in doc["cases"]:
            out.append(pytest.param(case, id=f'{doc["suite"]}:{case["id"]}'))
    return out


def _registry(patch):
    reg = copy.deepcopy(evaluator.PURPOSES)
    for purpose in reg["purposes"]:
        purpose.update(copy.deepcopy(patch.get(purpose["id"], {})))
    return reg


def _text(pieces):
    return "".join("".join(p) if isinstance(p, list) else p for p in pieces)


def _call(case):
    args = case["args"]
    call = case["call"]
    if call == "evaluate_sink":
        return evaluator.evaluate_sink(args["field_id"], args["sink"], args.get("context"))
    if call == "evaluate_egress":
        registry = _registry(case["registryPatch"]) if "registryPatch" in case else None
        return evaluator.evaluate_egress(args["purpose"], args["field_ids"], args.get("endpoint"), args.get("location"),
                                         args.get("consent"), args.get("context"), registry=registry)
    if call == "evaluate_retention":
        return evaluator.evaluate_retention(args["row_id"], args["value"], args["anchor"], args.get("context"))
    if call == "classify_destination":
        return evaluator.classify_destination(args["host"], args["port"], args["addresses"], args.get("settings"))
    if call == "detect_secret":
        return evaluator.detect_secret(_text(args["pieces"]))
    if call == "parse_private_endpoints":
        try:
            entries = evaluator.parse_private_endpoints(args["value"])
        except ValueError as err:
            return {"error": str(err)}
        return {"entries": [{"network": str(e["network"]), "port": e["port"]} for e in entries]}
    raise AssertionError(f"unknown call {call}")


@pytest.mark.parametrize("case", _cases())
def test_vector(case):
    got = _call(case)
    want = case["expect"]
    if want is None or got is None:
        assert got == want
        return
    if "error" in want:
        assert "error" in got, got
        assert want["error"] in got["error"]
        return
    for key, value in want.items():
        assert got.get(key) == value, f"{key}: got {got.get(key)!r}, want {value!r}"


def test_every_class_and_sink_has_a_matrix_vector():
    doc = json.loads((VECTORS / "matrix.json").read_text(encoding="utf-8"))
    ids = {c["id"] for c in doc["cases"]}
    for cell in evaluator.POLICY["matrix"]["cells"]:
        assert cell["id"] in ids, cell["id"]
    assert len(evaluator.POLICY["matrix"]["cells"]) == 40


SAMPLES = evaluator.SECRET_PATTERNS


@pytest.mark.parametrize("sample", SAMPLES["fixtures"], ids=lambda s: s["pattern"])
def test_secret_fixture_flags_offsets_only(sample):
    secret = "".join(sample["parts"])
    text = sample["before"] + secret + sample["after"]
    got = evaluator.detect_secret(text)
    assert got is not None and got["code"] == "secret-detected"
    start = len(sample["before"])
    assert {"pattern": sample["pattern"], "start": start, "end": start + len(secret)} in got["findings"]
    assert secret not in json.dumps(got)


@pytest.mark.parametrize("sample", SAMPLES["nearMisses"], ids=lambda s: s["pattern"])
def test_secret_near_miss_passes(sample):
    text = sample["before"] + "".join(sample["parts"]) + sample["after"]
    got = evaluator.detect_secret(text)
    assert got is None or all(f["pattern"] != sample["pattern"] for f in got["findings"])


def test_every_pattern_has_a_fixture_and_a_near_miss():
    ids = {p["id"] for p in SAMPLES["patterns"]}
    assert ids == {s["pattern"] for s in SAMPLES["fixtures"]}
    assert ids == {s["pattern"] for s in SAMPLES["nearMisses"]}


# Ranges the policy refuses and R0 lets through. R0's own table is
# ROUNDS-14-L02's to replace, so they stay named here until then.
STRICTER_THAN_R0 = {"::/96", "::ffff:0:0:0/96", "5f00::/16"}
# Ranges whose R0 answer depends on the CPython point release, through
# ipaddress's is_global; the policy refuses them on every release. CPython
# still calls 5f00::/16 (RFC 9602) global, and a later release may not.
RELEASE_DEPENDENT = {"3fff::/20", "64:ff9b:1::/48", "5f00::/16"}
# IANA's special-purpose address registries.
SPECIAL_PURPOSE = [
    "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24",
    "192.0.0.0/29", "192.0.0.8/32", "192.0.0.9/32", "192.0.0.10/32", "192.0.0.170/32", "192.0.0.171/32", "192.0.2.0/24",
    "192.31.196.0/24", "192.52.193.0/24", "192.88.99.0/24", "192.168.0.0/16", "192.175.48.0/24", "198.18.0.0/15",
    "198.51.100.0/24", "203.0.113.0/24", "224.0.0.0/4", "240.0.0.0/4", "255.255.255.255/32",
    "::1/128", "::/128", "::ffff:0:0/96", "64:ff9b::/96", "64:ff9b:1::/48", "100::/64", "2001::/23", "2001::/32",
    "2001:1::1/128", "2001:1::2/128", "2001:1::3/128", "2001:2::/48", "2001:3::/32", "2001:4:112::/48", "2001:20::/28",
    "2001:30::/28", "2001:db8::/32", "2002::/16", "2620:4f:8000::/48", "3fff::/20", "5f00::/16", "fc00::/7", "fe80::/10",
]
PUBLIC = ["8.8.8.8", "104.18.6.192", "2606:4700::6812:6c0", "2a00:1450:4001:80b::200e"]
# IANA's globally reachable exceptions inside 192.0.0.0/24 and 2001::/23,
# which the policy refuses whole and R0 lets through.
GLOBAL_EXCEPTIONS = ["192.0.0.9/32", "192.0.0.10/32", "2001:1::1/128", "2001:1::2/128", "2001:3::/32", "2001:4:112::/48", "2001:20::/28", "2001:30::/28"]


def _samples(network):
    net = ipaddress.ip_network(network)
    if net.num_addresses <= 2:
        return [net.network_address]
    return [net.network_address + 1, net.network_address + net.num_addresses // 2, net.broadcast_address - 1]


def _policy_allows(address):
    """The policy's answer with the best settings an operator could give:
    the gate on and the address itself listed, when it can be."""
    text = str(address)
    entry = f"[{text}]:443" if address.version == 6 else f"{text}:443"
    try:
        evaluator.parse_private_endpoints(entry)
        settings = {"gate": "enabled", "allowlist": entry}
    except ValueError:
        settings = None
    return evaluator.classify_destination("models.example.com", 443, [text], settings)["decision"] == "allow"


def _policy_lists():
    loc = evaluator.POLICY["locations"]
    never = loc["never"]
    return never["loopback"] + never["linkLocal"] + never["unspecified"] + never["metadata"] + loc["nonPublic"]


def test_destination_lists_match_the_runner():
    """The policy's never and private lists are the ones the runner's
    destination check refuses or gates today (ROUNDS-00A-L01). Over samples
    of IANA's special-purpose ranges and the policy's own lists, a sampled
    address the policy refuses, R0 refuses, outside the ranges named here.
    The policy also refuses the globally reachable exceptions inside
    192.0.0.0/24 and 2001::/23, with their ranges, which R0 allows."""
    loc = evaluator.POLICY["locations"]
    assert sorted(map(str, destinations.METADATA_ADDRESSES)) == sorted(str(ipaddress.ip_address(a)) for a in loc["never"]["metadata"])
    assert [str(n) for n in destinations.PRIVATE_NETWORKS] == loc["privateNetworks"]
    assert list(destinations.SERVICE_SUFFIXES) == loc["never"]["serviceSuffixes"]
    assert STRICTER_THAN_R0 | RELEASE_DEPENDENT <= set(loc["nonPublic"])
    for net in _policy_lists():
        for sample in _samples(net):
            assert not _policy_allows(sample), (net, str(sample))
    named = STRICTER_THAN_R0 | RELEASE_DEPENDENT | set(GLOBAL_EXCEPTIONS)
    for net in SPECIAL_PURPOSE + _policy_lists():
        if net in named:
            continue
        for sample in _samples(net):
            if not _policy_allows(sample):
                assert not destinations.address_allowed(sample, True), (net, str(sample))
    # 5f00::/16 is in both sets on purpose: the R0 check skips it, so a CPython that starts refusing it needs no test change.
    for net in STRICTER_THAN_R0 - RELEASE_DEPENDENT:
        assert any(destinations.address_allowed(s, True) for s in _samples(net)), f"R0 refuses {net} now; drop it from STRICTER_THAN_R0"


def test_the_policy_allows_no_address_the_runner_refuses():
    """The other direction: over the same samples, a sampled address the
    policy allows, R0 allows too."""
    allowed = 0
    for net in SPECIAL_PURPOSE + _policy_lists():
        for sample in _samples(net):
            if _policy_allows(sample):
                allowed += 1
                assert destinations.address_allowed(sample, True), (net, str(sample))
    for text in PUBLIC:
        assert _policy_allows(ipaddress.ip_address(text)) and destinations.address_allowed(ipaddress.ip_address(text), False), text
    assert allowed > 0


def test_the_policy_refuses_the_globally_reachable_exceptions_r0_allows():
    for net in GLOBAL_EXCEPTIONS:
        inside = [ipaddress.ip_network(r) for r in ("192.0.0.0/24", "2001::/23")]
        assert any(r.version == ipaddress.ip_network(net).version and ipaddress.ip_network(net).subnet_of(r) for r in inside), net
        for sample in _samples(net):
            assert not _policy_allows(sample), (net, str(sample))
            assert destinations.address_allowed(sample, True), (net, str(sample))


def test_versions_name_every_policy_version():
    assert evaluator.VERSIONS == {"privacy": "privacy@1", "retention": "retention@1", "redaction": "redaction@1", "consent": "consent@1"}


def test_a_refused_entry_never_appears_in_its_message():
    doc = json.loads((VECTORS / "settings.json").read_text(encoding="utf-8"))
    for case in doc["cases"]:
        if "error" not in case["expect"]:
            continue
        with pytest.raises(ValueError) as raised:
            evaluator.parse_private_endpoints(case["args"]["value"])
        for item in case["args"]["value"].split(","):
            assert not item.strip() or item.strip() not in str(raised.value), case["id"]


CAP = evaluator.MAX_CODE_POINTS


def _fill(unit, n=CAP):
    return (unit * (n // len(unit) + 1))[:n]


# Texts that made the earlier JWT and PEM patterns quadratic, and the
# other runs a pattern could backtrack over, each at the cap.
ADVERSARIAL = {
    "jwt-heads": lambda: _fill("eyJ"),
    "jwt-long-runs": lambda: _fill(" eyJ" + "A" * 8200),
    "pem-headers": lambda: _fill("-----BEGIN "),
    "pem-words": lambda: "-----BEGIN " + _fill("A ", CAP - 11),
    "bearer-spaces": lambda: "Bearer" + _fill(" ", CAP - 6),
    "short-keys": lambda: _fill("sk-AAAAAAAAAAAAAAAAAAA "),
}


@pytest.mark.parametrize("name", sorted(ADVERSARIAL))
def test_detect_secret_stays_linear_at_the_cap(name):
    text = ADVERSARIAL[name]()
    assert len(text) == CAP
    started = time.perf_counter()
    evaluator.detect_secret(text)
    assert time.perf_counter() - started < 2.0, name


def test_detect_secret_reads_up_to_the_cap_and_refuses_past_it():
    sample = next(s for s in SAMPLES["fixtures"] if s["pattern"] == "groq-key")
    secret = "".join(sample["parts"])
    got = evaluator.detect_secret(" " * (CAP - len(secret)) + secret)
    assert got == {"code": "secret-detected", "findings": [{"pattern": "groq-key", "start": CAP - len(secret), "end": CAP}]}
    assert evaluator.detect_secret(" " * CAP + secret) == {"code": "text-too-long", "findings": []}


@pytest.mark.parametrize("value", [42, b"bytes", ["text"], {"text": "a"}])
def test_detect_secret_refuses_a_value_that_isnt_text(value):
    assert evaluator.detect_secret(value) == {"code": "input-invalid", "findings": []}


def test_detect_secret_passes_no_text():
    assert evaluator.detect_secret(None) is None
    assert evaluator.detect_secret("") is None


def test_descendants_keep_map_order_and_the_callers_column():
    got = evaluator.descendants("pb:resume_variants.data#/personalInfo")
    assert got[0].startswith("pb:resume_variants.data#/personalInfo/")
    assert "pb:resume_variants.data#/personalInfo/email" in got
    assert evaluator.descendants("pb:ai_coding_rounds.checkpoints")[:2] == [
        "pb:ai_coding_rounds.checkpoints#/*/*/hidden_files", "pb:ai_coding_rounds.checkpoints#/*/*/test_command"]
    assert evaluator.descendants("storage:pocketbase_auth") == []
    assert evaluator.descendants("pb:offers.id") == []
