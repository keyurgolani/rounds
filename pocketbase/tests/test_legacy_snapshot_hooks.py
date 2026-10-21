"""Legacy Artifact Snapshot creation in pb_hooks/legacy_snapshots.js
(ROUNDS-00A-L04, PR 2).

The command's decisions under node, on an in-memory store with the
PocketBase store's contract (legacy_snapshots_runner.cjs): the gate, the
request check, replay of a completed command before any lookup, one 404
for a missing or another account's source, conflict on a stale
``expected_updated``, the demo and parent checks, the materializer's
answers checked against their SHA-256 and size, reuse inside one source,
the per-account quota, the command completed in the same transaction as
the record, and nothing written on any failure. Then the dry-run scan's
report. The harness runs the same functions on a real PocketBase.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
HOOKS = HERE.parent / "pb_hooks"
RUNNER = HERE / "legacy_snapshots_runner.cjs"

A = {"id": "acct00000000001", "demo": False}
B = {"id": "acct00000000002", "demo": False}
DEMO = {"id": "acct00000000003", "demo": True}
K1 = "0190f000-0000-7000-8000-000000000001"
K2 = "0190f000-0000-7000-8000-000000000002"
T1 = "2026-10-20 10:00:00.000Z"
T2 = "2026-10-20 10:05:00.000Z"
MARKUP = "<!DOCTYPE html><html><head><meta charset=\"utf-8\"></head><body><p>Resume é</p></body></html>"
OK = {"ok": {"markup": MARKUP, "template_id": "modern", "font_families": ["inter"]}}
QUOTA = {"snapshots": 500, "bytes": 200 * 1024 * 1024}


def run(steps: list[dict], state: dict | None = None) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run(
        [node, str(RUNNER), str(HOOKS)],
        input=json.dumps({"state": state or base_state(), "steps": steps}),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def base_state() -> dict:
    return {
        "users": {A["id"]: {}, B["id"]: {}, DEMO["id"]: {"is_demo": True}},
        "resumes": {
            "resumeaaaaaaaa1": {"user": A["id"], "updated": T1, "template_id": "classic",
                                "design": {"colors": {"primary": "#112233"}}, "data": {"personalInfo": {"fullName": "A"}}},
            "resumebbbbbbbb1": {"user": B["id"], "updated": T1, "template_id": "modern", "design": {}, "data": {}},
            "resumedemodemo1": {"user": DEMO["id"], "updated": T1, "template_id": "modern", "design": {}, "data": {}},
        },
        "variants": {
            "variantaaaaaaa1": {"user": A["id"], "updated": T1, "resume": "resumeaaaaaaaa1",
                                "data": {"personalInfo": {"fullName": "A variant"}}},
            # A variant whose parent belongs to another account, as a legacy
            # row written before relation authorization could be.
            "variantforeign1": {"user": A["id"], "updated": T1, "resume": "resumebbbbbbbb1", "data": {}},
            "variantorphan01": {"user": A["id"], "updated": T1, "resume": "resumegone00001", "data": {}},
        },
    }


def create(account=A, kind="resume", source="resumeaaaaaaaa1", expected=T1, command=K1, materializer=None,
           **extra) -> dict:
    data = {"source_kind": kind, "source_id": source, "expected_updated": expected}
    if command is not None:
        data["command_id"] = command
    step = {"op": "create", "account": account, "data": data, "materializer": materializer or [OK]}
    step.update(extra)
    return step


def admit(account=A, command=K1, operation="snapshot_create") -> dict:
    return {"op": "admit", "account": account, "command_id": command, "operation": operation}


def sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def only(out: dict) -> dict:
    (result,) = out["results"]
    return result


# ---- the gate and the request ------------------------------------------------


def test_gate_off_answers_route_disabled_and_writes_nothing():
    out = run([admit(), create(gateOn=False)])
    result = out["results"][1]
    assert result["out"] == {"status": 503, "body": {"v": "legacy-snapshot/v1", "error": "route_disabled"}}
    assert result["calls"] == []
    assert out["state"]["snapshots"] == [] and out["state"]["files"] == []
    assert out["state"]["commands"][0]["state"] == "in_flight"


@pytest.mark.parametrize("data", [
    {"source_kind": "resume", "source_id": "resumeaaaaaaaa1"},
    {"source_kind": "resume", "source_id": "resumeaaaaaaaa1", "expected_updated": T1, "html": "<p>x</p>"},
    {"source_kind": "draft", "source_id": "resumeaaaaaaaa1", "expected_updated": T1},
    {"source_kind": "resume", "source_id": "RESUME", "expected_updated": T1},
    {"source_kind": "resume", "source_id": "resumeaaaaaaaa1", "expected_updated": "yesterday"},
    {"source_kind": "resume", "source_id": "resumeaaaaaaaa1", "expected_updated": T1, "command_id": "not-a-key"},
    {"source_kind": "resume", "source_id": "resumeaaaaaaaa1", "expected_updated": T1, "template_id": "modern"},
    {"source_kind": "resume", "source_id": "resumeaaaaaaaa1", "expected_updated": T1, "design": {}},
])
def test_a_malformed_request_is_refused_before_any_lookup(data):
    out = run([{"op": "create", "account": A, "data": data, "materializer": [OK]}])
    result = only(out)
    assert result["out"] == {"status": 400, "body": {"v": "legacy-snapshot/v1", "error": "invalid_request"}}
    assert result["calls"] == []


# ---- ownership and conflict --------------------------------------------------


def test_another_accounts_source_answers_exactly_like_a_missing_one():
    out = run([
        create(account=B, source="resumeaaaaaaaa1", command=None),
        create(account=B, source="resumezzzzzzzz1", command=None),
        create(account=B, kind="variant", source="variantaaaaaaa1", command=None),
    ])
    foreign, missing, foreign_variant = (r["out"] for r in out["results"])
    assert foreign == missing == foreign_variant == {"status": 404, "body": {"v": "legacy-snapshot/v1", "error": "not_found"}}
    assert all(r["calls"] == [] for r in out["results"])
    assert out["state"]["snapshots"] == []


def test_a_stale_expected_updated_is_a_conflict_and_writes_nothing():
    out = run([admit(), create(expected=T2)])
    result = out["results"][1]
    assert result["out"] == {"status": 409, "body": {"status": "conflict", "snapshot_id": None, "content_checksum": None}}
    assert result["calls"] == []
    assert out["state"]["snapshots"] == []
    # Left for the runner's finish, so a same-key retry runs again.
    assert out["state"]["commands"][0]["state"] == "in_flight"


def test_a_change_while_the_materializer_ran_is_a_conflict_too():
    step = create(changeDuringMaterialize={"table": "resumes", "id": "resumeaaaaaaaa1", "set": {"updated": T2}})
    out = run([admit(), step])
    result = out["results"][1]
    assert result["out"]["status"] == 409
    assert out["state"]["snapshots"] == [] and out["state"]["files"] == []
    assert out["state"]["commands"][0]["state"] == "in_flight"


# ---- ineligible -----------------------------------------------------------------


def _ineligible(reason: str) -> dict:
    return {"status": 200, "body": {"status": "ineligible", "snapshot_id": None, "content_checksum": None,
                                    "reason": reason}}


def test_a_demo_account_is_ineligible_and_its_command_completes():
    out = run([admit(account=DEMO), create(account=DEMO, source="resumedemodemo1")])
    result = out["results"][1]
    assert result["out"] == _ineligible("demo_account")
    assert result["calls"] == []
    (command,) = out["state"]["commands"]
    assert command["state"] == "completed" and command["result"] == _ineligible("demo_account")
    assert out["state"]["snapshots"] == []


@pytest.mark.parametrize("variant", ["variantforeign1", "variantorphan01"])
def test_a_variant_whose_parent_is_missing_or_another_accounts_is_parent_invalid(variant):
    out = run([admit(), create(kind="variant", source=variant)])
    result = out["results"][1]
    assert result["out"] == _ineligible("parent_invalid")
    assert result["calls"] == []
    assert out["state"]["snapshots"] == []


@pytest.mark.parametrize("reason", ["design_out_of_domain", "data_malformed", "data_too_large", "markup_unsafe"])
def test_the_materializers_ineligible_reasons_complete_the_command(reason):
    answer = {"status": 200, "body": {"status": "ineligible", "reason": reason, "sanitizer_version": "1.0.0"}}
    out = run([admit(), create(materializer=[answer])])
    result = out["results"][1]
    assert result["out"] == _ineligible(reason)
    assert out["state"]["commands"][0]["result"] == _ineligible(reason)
    assert out["state"]["snapshots"] == []


def test_a_body_the_materializer_refuses_as_too_large_is_data_too_large():
    out = run([create(materializer=[{"status": 413, "body": {"error": "body_too_large"}}], command=None)])
    assert only(out)["out"] == _ineligible("data_too_large")


# ---- the materializer unavailable ---------------------------------------------------


@pytest.mark.parametrize("answer", [
    "throw",
    {"status": 500, "body": {"error": "materialize_failed"}},
    {"status": 200, "body": None},
    {"status": 200, "body": {"status": "ineligible", "reason": "a reason it never gives"}},
    {"ok": {"markup": MARKUP, "override": {"content_checksum": "sha256:" + "0" * 64}}},
    {"ok": {"markup": MARKUP, "override": {"size_bytes": 3}}},
    {"ok": {"markup": MARKUP, "override": {"template_id": "../modern"}}},
    {"ok": {"markup": MARKUP, "override": {"font_families": ["Comic Sans"]}}},
    {"ok": {"markup": MARKUP, "override": {"materializer_digest": "v1"}}},
    {"ok": {"markup": MARKUP, "override": {"design": []}}},
])
def test_a_materializer_error_or_an_answer_off_contract_writes_nothing(answer):
    out = run([admit(), create(materializer=[answer])])
    result = out["results"][1]
    assert result["out"] == {"status": 503, "body": {"v": "legacy-snapshot/v1", "error": "materializer_unavailable"}}
    assert out["state"]["snapshots"] == [] and out["state"]["files"] == []
    assert out["state"]["commands"][0]["state"] == "in_flight"


# ---- created and reused ------------------------------------------------------------


def test_an_owner_creates_a_snapshot_built_only_from_server_reads():
    out = run([admit(), create()])
    result = out["results"][1]
    assert result["out"]["status"] == 201
    body = result["out"]["body"]
    assert body["status"] == "created" and body["content_checksum"] == sha256(MARKUP)
    # The materializer got the resume's own stored template, design, and data.
    assert result["calls"] == [{"template_id": "classic", "design": {"colors": {"primary": "#112233"}},
                                "data": {"personalInfo": {"fullName": "A"}}}]
    (snap,) = out["state"]["snapshots"]
    assert snap["id"] == body["snapshot_id"]
    assert snap["user"] == A["id"] and snap["source_kind"] == "resume" and snap["source_id"] == "resumeaaaaaaaa1"
    assert snap["source_updated"] == T1 and snap["parent_id"] == "" and snap["parent_updated"] == ""
    assert snap["size_bytes"] == len(MARKUP.encode("utf-8"))
    assert snap["markup_sha256"] == hashlib.sha256(MARKUP.encode("utf-8")).hexdigest()
    (command,) = out["state"]["commands"]
    assert command["state"] == "completed" and command["result"] == result["out"]


def test_a_variant_renders_with_its_parents_template_and_design_and_records_the_parent():
    out = run([create(kind="variant", source="variantaaaaaaa1", command=None)])
    result = only(out)
    assert result["out"]["status"] == 201
    assert result["calls"] == [{"template_id": "classic", "design": {"colors": {"primary": "#112233"}},
                                "data": {"personalInfo": {"fullName": "A variant"}}}]
    (snap,) = out["state"]["snapshots"]
    assert (snap["parent_id"], snap["parent_updated"]) == ("resumeaaaaaaaa1", T1)


def test_a_replayed_command_returns_its_result_before_any_lookup():
    first = run([admit(), create()])
    created = first["results"][1]["out"]
    state = first["state"]
    # The source is gone and the materializer would fail: the replay still
    # answers the stored result and calls nothing.
    del state["resumes"]["resumeaaaaaaaa1"]
    out = run([create(materializer=["throw"])], state=state)
    result = only(out)
    assert result["out"] == created
    assert result["calls"] == []
    assert len(out["state"]["snapshots"]) == 1


def test_the_same_inputs_under_a_new_key_are_reused_with_the_same_checksum():
    out = run([admit(), create(), admit(command=K2), create(command=K2)])
    created, reused = out["results"][1]["out"], out["results"][3]["out"]
    assert reused["status"] == 200 and reused["body"]["status"] == "reused"
    assert reused["body"]["snapshot_id"] == created["body"]["snapshot_id"]
    assert reused["body"]["content_checksum"] == created["body"]["content_checksum"]
    assert len(out["state"]["snapshots"]) == 1
    assert [c["state"] for c in out["state"]["commands"]] == ["completed", "completed"]


def test_a_variant_matching_its_parents_markup_gets_its_own_snapshot():
    out = run([create(command=None), create(kind="variant", source="variantaaaaaaa1", command=None)])
    first, second = (r["out"] for r in out["results"])
    assert first["status"] == second["status"] == 201
    assert first["body"]["snapshot_id"] != second["body"]["snapshot_id"]
    assert first["body"]["content_checksum"] == second["body"]["content_checksum"]
    assert [s["source_kind"] for s in out["state"]["snapshots"]] == ["resume", "variant"]


def test_a_new_materializer_digest_creates_a_new_snapshot():
    other = {"ok": {"markup": MARKUP, "digest": "sha256:" + "e" * 64}}
    out = run([create(command=None), create(command=None, materializer=[other])])
    assert [r["out"]["status"] for r in out["results"]] == [201, 201]
    assert len(out["state"]["snapshots"]) == 2


def test_without_a_command_id_the_snapshot_is_still_created_and_nothing_completes():
    out = run([create(command=None)])
    assert only(out)["out"]["status"] == 201
    assert out["state"]["commands"] == []


# ---- quota and failure ------------------------------------------------------------


def _full_state(count: int, size: int) -> dict:
    state = base_state()
    state["snapshots"] = [
        {"id": f"old{i:012d}", "user": A["id"], "source_kind": "resume", "source_id": f"src{i:012d}",
         "content_checksum": "sha256:" + "1" * 64, "materializer_digest": "sha256:" + "2" * 64, "size_bytes": size}
        for i in range(count)
    ]
    return state


@pytest.mark.parametrize("count,size", [(QUOTA["snapshots"], 1), (1, QUOTA["bytes"])])
def test_an_account_at_its_quota_is_refused_and_nothing_is_written(count, size):
    state = _full_state(count, size)
    out = run([admit(), create()], state=state)
    result = out["results"][1]
    assert result["out"] == {"status": 429, "body": {"v": "legacy-snapshot/v1", "error": "snapshot_quota_exceeded"}}
    assert len(out["state"]["snapshots"]) == count
    assert out["state"]["commands"][0]["state"] == "in_flight"


def test_another_accounts_snapshots_dont_count_against_the_quota():
    state = _full_state(QUOTA["snapshots"], 1)
    for row in state["snapshots"]:
        row["user"] = B["id"]
    out = run([create(command=None)], state=state)
    assert only(out)["out"]["status"] == 201


def test_a_failed_save_rolls_back_the_command_and_discards_the_file():
    out = run([admit(), create(failSave=True)])
    result = out["results"][1]
    assert result["out"] == {"status": 503, "body": {"v": "legacy-snapshot/v1", "error": "unavailable"}}
    assert out["state"]["snapshots"] == [] and out["state"]["files"] == []
    assert out["state"]["commands"][0]["state"] == "in_flight"
    assert len(result["discarded"]) == 1


# ---- metrics ----------------------------------------------------------------------


def test_metric_lines_carry_outcomes_and_sizes_never_ids_or_content():
    out = run([admit(), create(), create(account=B, command=None)])
    lines = [json.dumps(line) for r in out["results"][1:] for line in r["logs"]]
    assert any('"outcome": "created"' in line for line in lines)
    assert any('"outcome": "not_found"' in line for line in lines)
    for line in lines:
        for secret in (A["id"], B["id"], "resumeaaaaaaaa1", K1, "Resume", "#112233"):
            assert secret not in line, line


# ---- helpers --------------------------------------------------------------------------


@pytest.mark.parametrize("text", ["", "abc", "é", "€", "😀", "a\ud800b", "\udc00", "mixed é€😀 text"])
def test_utf8_length_matches_the_encoded_bytes(text):
    (result,) = run([{"op": "utf8Length", "text": text}])["results"]
    assert result["ours"] == result["node"]


def test_canonical_json_matches_pythons_sorted_compact_form():
    value = {"b": [1, {"z": True, "a": None}], "a": "x", "c": {"y": 2, "x": "é"}}
    (got,) = run([{"op": "canonical", "value": value}])["results"]
    assert got == json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


# ---- the scan ------------------------------------------------------------------------


def scan(state: dict, answers: list, commit: str = "abc1234") -> dict:
    return only(run([{"op": "scan", "materializer": answers, "commit": commit}], state=state))


def test_the_scan_counts_by_reason_and_pseudonymous_account_and_writes_nothing():
    design_off = {"status": 200, "body": {"status": "ineligible", "reason": "design_out_of_domain",
                                          "materializer_digest": "sha256:" + "d" * 64, "sanitizer_version": "1.0.0"}}
    # Calls go in id order: resumes, then variants.
    result = scan(base_state(), [OK, design_off, OK])
    report = result["report"]
    assert report["schema"] == "legacy-snapshot-scan/v1"
    assert report["commit"] == "abc1234"
    assert report["materializer_digest"] == "sha256:" + "d" * 64
    assert report["totals"] == {"sources": 6, "resumes": 3, "variants": 3, "eligible": 2, "ineligible": 4,
                                "unavailable": 0}
    assert report["by_reason"]["demo_account"] == 1
    assert report["by_reason"]["parent_invalid"] == 2
    assert report["by_reason"]["design_out_of_domain"] == 1
    assert report["complete"] is True
    assert sorted(report["accounts"]) == ["acct-01", "acct-02", "acct-03"]
    text = json.dumps(report)
    for raw in (A["id"], B["id"], DEMO["id"], "resumeaaaaaaaa1", "variantaaaaaaa1", "Resume"):
        assert raw not in text


def test_the_scan_report_carries_its_own_checksum_and_repeats_exactly():
    first = scan(base_state(), [OK])["report"]
    second = scan(base_state(), [OK])["report"]
    assert first == second
    body = {k: v for k, v in first.items() if k != "checksum"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert first["checksum"] == sha256(canonical)


def test_a_scan_with_the_materializer_unavailable_is_incomplete():
    report = scan(base_state(), ["throw"])["report"]
    assert report["complete"] is False
    assert report["totals"]["unavailable"] == report["totals"]["sources"] - 3
