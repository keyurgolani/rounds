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


def test_destination_lists_match_the_runner():
    """The policy's never and private lists are the ones the runner's
    destination check refuses or gates today (ROUNDS-00A-L01)."""
    loc = evaluator.POLICY["locations"]
    assert sorted(map(str, destinations.METADATA_ADDRESSES)) == sorted(str(ipaddress.ip_address(a)) for a in loc["never"]["metadata"])
    assert [str(n) for n in destinations.PRIVATE_NETWORKS] == loc["privateNetworks"]
    assert list(destinations.SERVICE_SUFFIXES) == loc["never"]["serviceSuffixes"]
    for net in loc["never"]["loopback"] + loc["never"]["linkLocal"] + loc["never"]["unspecified"] + loc["nonPublic"]:
        sample = ipaddress.ip_network(net).network_address + (1 if ipaddress.ip_network(net).num_addresses > 2 else 0)
        assert not destinations.address_allowed(sample, True), net


def test_versions_name_every_policy_version():
    assert evaluator.VERSIONS == {"privacy": "privacy@1", "retention": "retention@1", "redaction": "redaction@1", "consent": "consent@1"}
