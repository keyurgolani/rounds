"""Share capabilities in pb_hooks/share_capabilities.js (ROUNDS-00B-L03
stage 2).

The decisions under node, on an in-memory store with the PocketBase store's
contract (share_capabilities_runner.cjs): create_capability's argument checks
before any read and its one answer for a missing, another account's, or
ineligible snapshot; lookup_capability's one answer for every state that
doesn't resolve; what a row may hold and how it may change, for any writer;
the owner's list and revoke; a source delete revokes and keeps the snapshots
and never fails; an account delete removes the account's capabilities first.
Then share_capabilities.pb.js's registrations. The PocketBase store itself
runs natively and in #9's harness.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
HOOKS = HERE.parent / "pb_hooks"
RUNNER = HERE / "share_capabilities_runner.cjs"

DAY = 24 * 60 * 60 * 1000
NOW = int(datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc).timestamp() * 1000)

A = "acct00000000001"
B = "acct00000000002"
DEMO = "acct00000000003"
D1, D2, D3, D9 = "1" * 64, "2" * 64, "3" * 64, "9" * 64

MARKUP_A = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Resume</title></head><body><p>Ada é</p></body></html>'
MARKUP_V = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Resume</title></head><body><p>Ada, backend</p></body></html>'
MARKUP_B = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Resume</title></head><body><p>Bea</p></body></html>'
MARKUP_D = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Resume</title></head><body><p>Demo</p></body></html>'

OWNER_FIELDS = ["id", "status", "revoked_reason", "purpose", "expires_at", "created", "revoked_at"]
LOOKUP_FIELDS = ["id", "status", "expires_at", "capability_version", "snapshot", "password_policy_ref", "markup"]


def fmt(ms: int) -> str:
    """PocketBase 0.22's datetime text, as formatDate writes it."""
    when = datetime.fromtimestamp(ms // 1000, tz=timezone.utc)
    return when.strftime("%Y-%m-%d %H:%M:%S") + f".{ms % 1000:03d}Z"


def checksum(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def snap(user: str, kind: str, source: str, markup: str) -> dict:
    return {"user": user, "source_kind": kind, "source_id": source, "content_checksum": checksum(markup),
            "markup": "snapshot_abc.html", "markup_text": markup}


def base_state() -> dict:
    return {
        "users": {A: {}, B: {}, DEMO: {"is_demo": True}},
        "resumes": {
            "resumeaaaaaaaa1": {"user": A, "name": "Ada's resume"},
            "resumebbbbbbbb1": {"user": B, "name": "Bea's resume"},
            "resumedemodemo1": {"user": DEMO, "name": "Demo resume"},
        },
        "variants": {"variantaaaaaaa1": {"user": A, "name": "Backend roles", "resume": "resumeaaaaaaaa1"}},
        "snapshots": {
            "snapresumeaaaa1": snap(A, "resume", "resumeaaaaaaaa1", MARKUP_A),
            "snapvariantaaa1": snap(A, "variant", "variantaaaaaaa1", MARKUP_V),
            "snapresumebbbb1": snap(B, "resume", "resumebbbbbbbb1", MARKUP_B),
            "snapdemodemo001": snap(DEMO, "resume", "resumedemodemo1", MARKUP_D),
        },
        "capabilities": {},
    }


def cap_row(cid: str, owner: str, snapshot_id: str, digest: str, state: dict, **over) -> dict:
    row = {
        "id": cid, "user": owner, "target_kind": "legacy_artifact_snapshot", "snapshot": snapshot_id,
        "target_checksum": state["snapshots"][snapshot_id]["content_checksum"], "purpose": "For recruiters",
        "expires_at": fmt(NOW + 30 * DAY), "password_policy_ref": "", "view_policy": "disabled",
        "capability_version": 1, "status": "active", "revoked_at": "", "revoked_reason": "",
        "projection_version": 1, "bearer_digest": digest, "digest_key_version": 1, "created": fmt(NOW - DAY),
    }
    row.update(over)
    return row


def shared_state(**over) -> dict:
    """A's resume shared once, with digest D1."""
    state = base_state()
    state["capabilities"]["capaaaaaaaaaaa1"] = cap_row("capaaaaaaaaaaa1", A, "snapresumeaaaa1", D1, state, **over)
    return state


def run(steps: list[dict], state: dict | None = None) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run(
        [node, str(RUNNER), str(HOOKS)],
        input=json.dumps({"state": state or base_state(), "now": NOW, "steps": steps}),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def create_input(**over) -> dict:
    data = {"owner": A, "snapshot_id": "snapresumeaaaa1", "purpose": None, "expires_at": None,
            "password_policy_ref": None, "bearer_digest": D1, "digest_key_version": 1}
    data.update(over)
    return data


# ---- constants and dates ---------------------------------------------------------------------------------


def test_the_contract_constants():
    (res,) = run([{"call": "constants"}])["results"]
    c = res["value"]
    assert c["VERSION"] == "share-capability/v1"
    assert (c["KIND"], c["PROJECTION_VERSION"], c["VIEW_POLICY"]) == ("legacy_artifact_snapshot", 1, "disabled")
    assert (c["DEFAULT_DAYS"], c["MAX_DAYS"], c["PURPOSE_MAX"], c["LIST_LIMIT"]) == (90, 365, 80, 200)
    assert c["OWNER_FIELDS"] == OWNER_FIELDS
    assert c["LOOKUP_FIELDS"] == LOOKUP_FIELDS
    # Every stored field is either fixed at create or one of the moves an
    # update may make, nothing in both.
    assert not set(c["FIXED"]) & set(c["MUTABLE"])
    assert set(c["FIXED"]) | set(c["MUTABLE"]) == {
        "user", "target_kind", "snapshot", "target_checksum", "purpose", "expires_at", "password_policy_ref",
        "view_policy", "capability_version", "status", "revoked_at", "revoked_reason", "projection_version",
        "bearer_digest", "digest_key_version",
    }


@pytest.mark.parametrize("text, ms", [
    ("2026-11-11 12:00:00.000Z", NOW),
    ("2026-11-11T12:00:00Z", NOW),
    ("2026-11-11 12:00:00.5Z", NOW + 500),
    ("2026-11-11 12:00:00.123456Z", NOW + 123),
])
def test_dates_parse_from_pocketbase_text(text, ms):
    (res,) = run([{"call": "parseDate", "value": text}])["results"]
    assert res["value"] == ms


@pytest.mark.parametrize("text", ["2026-02-30 00:00:00.000Z", "2026-11-11 24:00:00.000Z", "2026-11-11", "",
                                  "2026-11-11 12:00:00.000+01:00", 1794398400000, None])
def test_anything_else_is_not_a_date(text):
    (res,) = run([{"call": "parseDate", "value": text}])["results"]
    assert res["value"] is None


def test_dates_format_as_pocketbase_stores_them():
    (res,) = run([{"call": "formatDate", "ms": NOW + 7}])["results"]
    assert res["value"] == "2026-11-11 12:00:00.007Z" == fmt(NOW + 7)


@pytest.mark.parametrize("name, purpose", [
    ("Ada's resume", "Ada's resume"),
    ("  padded\tname\n ", "padded name"),
    ("x" * 81, "x" * 80),
    ("😀" * 81, "😀" * 80),
    ("", "Shared resume"),
    ("\u0000\u0001", "Shared resume"),
    (None, "Shared resume"),
])
def test_the_default_purpose_is_the_source_name_cut_to_80(name, purpose):
    (res,) = run([{"call": "defaultPurpose", "name": name}])["results"]
    assert res["value"] == purpose


# ---- create_capability -------------------------------------------------------------------------------


def test_a_capability_takes_the_defaults_and_answers_only_the_owner_fields():
    out = run([{"call": "create", "input": create_input()}])
    (res,) = out["results"]
    assert res["value"]["status"] == "created"
    view = res["value"]["capability"]
    assert list(view) == OWNER_FIELDS
    (stored,) = out["state"]["capabilities"].values()
    assert stored == {
        "id": view["id"], "created": fmt(NOW), "user": A, "target_kind": "legacy_artifact_snapshot",
        "snapshot": "snapresumeaaaa1", "target_checksum": checksum(MARKUP_A), "purpose": "Ada's resume",
        "expires_at": fmt(NOW + 90 * DAY), "password_policy_ref": "", "view_policy": "disabled",
        "capability_version": 1, "status": "active", "revoked_at": "", "revoked_reason": "",
        "projection_version": 1, "bearer_digest": D1, "digest_key_version": 1,
    }
    assert view == {k: stored[k] for k in OWNER_FIELDS}


def test_a_variant_snapshot_defaults_to_the_variant_name():
    out = run([{"call": "create", "input": create_input(snapshot_id="snapvariantaaa1")}])
    assert out["results"][0]["value"]["capability"]["purpose"] == "Backend roles"


def test_create_keeps_a_purpose_expiry_and_verifier_given_to_it():
    out = run([{"call": "create", "input": create_input(
        purpose="  Acme application ", expires_at=fmt(NOW + 365 * DAY), password_policy_ref="pw1$placeholder$verifier",
        digest_key_version=2)}])
    (stored,) = out["state"]["capabilities"].values()
    assert (stored["purpose"], stored["expires_at"], stored["password_policy_ref"], stored["digest_key_version"]) == (
        "Acme application", fmt(NOW + 365 * DAY), "pw1$placeholder$verifier", 2)


@pytest.mark.parametrize("over", [
    {"expires_at": fmt(NOW + 60 * 1000)},
    {"expires_at": fmt(NOW + 365 * DAY)},
    {"purpose": "x" * 80},
    {"purpose": "😀" * 80},
    {"password_policy_ref": "!" * 512},
    {"digest_key_version": 999},
])
def test_the_bounds_themselves_are_accepted(over):
    (res,) = run([{"call": "create", "input": create_input(**over)}])["results"]
    assert res["value"]["status"] == "created", res


BAD_ARGUMENTS = [
    ("arguments", {"target_kind": "artifact_revision"}),
    ("arguments", {"user": B}),
    ("owner", {"owner": "acct1"}),
    ("owner", {"owner": None}),
    ("snapshot_id", {"snapshot_id": "SNAPRESUMEAAAA1"}),
    ("snapshot_id", {"snapshot_id": ["snapresumeaaaa1"]}),
    ("purpose", {"purpose": "x" * 81}),
    ("purpose", {"purpose": "line\nbreak"}),
    ("purpose", {"purpose": "   "}),
    ("purpose", {"purpose": 7}),
    ("expires_at", {"expires_at": fmt(NOW)}),
    ("expires_at", {"expires_at": fmt(NOW - 1)}),
    ("expires_at", {"expires_at": fmt(NOW + 59 * 1000)}),
    ("expires_at", {"expires_at": fmt(NOW + 365 * DAY + 1)}),
    ("expires_at", {"expires_at": "2026-02-30 00:00:00.000Z"}),
    ("expires_at", {"expires_at": "next week"}),
    ("expires_at", {"expires_at": NOW + DAY}),
    ("password_policy_ref", {"password_policy_ref": "has space"}),
    ("password_policy_ref", {"password_policy_ref": "x" * 513}),
    ("password_policy_ref", {"password_policy_ref": 5}),
    ("bearer_digest", {"bearer_digest": "A" * 64}),
    ("bearer_digest", {"bearer_digest": "1" * 63}),
    ("bearer_digest", {"bearer_digest": None}),
    ("digest_key_version", {"digest_key_version": 0}),
    ("digest_key_version", {"digest_key_version": 1000}),
    ("digest_key_version", {"digest_key_version": 1.5}),
    ("digest_key_version", {"digest_key_version": "1"}),
]


@pytest.mark.parametrize("field, over", BAD_ARGUMENTS)
def test_a_bad_argument_is_refused_before_any_read_and_writes_nothing(field, over):
    out = run([{"call": "create", "input": create_input(**over)}])
    (res,) = out["results"]
    assert res["value"] == {"status": "invalid", "field": field}
    assert res["calls"] == []
    assert out["state"]["capabilities"] == {}


def _unavailable_cases():
    def drop_source(s):
        del s["resumes"]["resumeaaaaaaaa1"]

    def move_source(s):
        s["resumes"]["resumeaaaaaaaa1"]["user"] = B

    def drop_markup(s):
        del s["snapshots"]["snapresumeaaaa1"]["markup_text"]

    def bad_checksum(s):
        s["snapshots"]["snapresumeaaaa1"]["content_checksum"] = "md5:abc"

    return {
        "missing": ({"snapshot_id": "snapmissingaaa1"}, None),
        "another account's": ({"snapshot_id": "snapresumebbbb1"}, None),
        "demo account": ({"owner": DEMO, "snapshot_id": "snapdemodemo001"}, None),
        "source deleted": ({}, drop_source),
        "source moved": ({}, move_source),
        "markup missing": ({}, drop_markup),
        "checksum malformed": ({}, bad_checksum),
    }


@pytest.mark.parametrize("case", sorted(_unavailable_cases()))
def test_a_missing_foreign_or_ineligible_snapshot_gets_one_answer_and_writes_nothing(case):
    over, mutate = _unavailable_cases()[case]
    state = base_state()
    if mutate:
        mutate(state)
    out = run([{"call": "create", "input": create_input(**over)}], state)
    (res,) = out["results"]
    assert res["value"] == {"status": "share-unavailable"}
    assert "insert" not in res["calls"]
    assert out["state"]["capabilities"] == {}


def test_a_digest_already_taken_fails_the_write_and_keeps_the_store():
    state = shared_state()
    out = run([{"call": "create", "input": create_input()}], state)
    (res,) = out["results"]
    assert "UNIQUE" in res["threw"]
    assert out["state"]["capabilities"] == state["capabilities"]


# ---- lookup_capability -------------------------------------------------------------------------------


def test_an_active_capability_resolves_to_the_lookup_fields_and_the_markup():
    out = run([{"call": "lookup", "digest": D1}], shared_state())
    (res,) = out["results"]
    assert res["value"]["reason"] == "available"
    cap = res["value"]["capability"]
    assert list(cap) == LOOKUP_FIELDS
    assert cap == {"id": "capaaaaaaaaaaa1", "status": "active", "expires_at": fmt(NOW + 30 * DAY),
                   "capability_version": 1, "snapshot": "snapresumeaaaa1", "password_policy_ref": "",
                   "markup": MARKUP_A}


def _miss_cases():
    def edit(field, value):
        return lambda s: s["capabilities"]["capaaaaaaaaaaa1"].update({field: value})

    def snapshot_edit(field, value):
        return lambda s: s["snapshots"]["snapresumeaaaa1"].update({field: value})

    def drop(table, key):
        return lambda s: s[table].pop(key)

    return {
        "unknown": (D9, None, "unknown"),
        "revoked": (D1, edit("status", "revoked"), "revoked"),
        "expired now": (D1, edit("expires_at", fmt(NOW)), "expired"),
        "expired before": (D1, edit("expires_at", fmt(NOW - 1)), "expired"),
        "unreadable expiry": (D1, edit("expires_at", ""), "expired"),
        "other kind": (D1, edit("target_kind", "artifact_revision"), "unsupported"),
        "other projection": (D1, edit("projection_version", 2), "unsupported"),
        "views counted": (D1, edit("view_policy", "counted"), "unsupported"),
        "snapshot gone": (D1, drop("snapshots", "snapresumeaaaa1"), "snapshot"),
        "cross-account snapshot": (D1, snapshot_edit("user", B), "snapshot"),
        "checksum mismatch": (D1, edit("target_checksum", checksum("other")), "checksum"),
        "source deleted": (D1, drop("resumes", "resumeaaaaaaaa1"), "source"),
        "source moved": (D1, lambda s: s["resumes"]["resumeaaaaaaaa1"].update(user=B), "source"),
        "markup gone": (D1, lambda s: s["snapshots"]["snapresumeaaaa1"].pop("markup_text"), "markup"),
        "markup changed": (D1, snapshot_edit("markup_text", MARKUP_A + " "), "markup"),
    }


@pytest.mark.parametrize("case", sorted(_miss_cases()))
def test_every_state_that_does_not_resolve_answers_the_same_null(case):
    digest, mutate, reason = _miss_cases()[case]
    state = shared_state()
    if mutate:
        mutate(state)
    (res,) = run([{"call": "lookup", "digest": digest}], state)["results"]
    assert res["value"] == {"capability": None, "reason": reason}
    # One read by digest, as for a capability that resolves.
    assert res["calls"].count("byDigest") == 1


@pytest.mark.parametrize("digest", ["", "g" * 64, "1" * 63, "1" * 65, "A" * 64, None, 123])
def test_a_malformed_digest_is_answered_before_any_read(digest):
    (res,) = run([{"call": "lookup", "digest": digest}], shared_state())["results"]
    assert res["value"] == {"capability": None, "reason": "malformed"}
    assert res["calls"] == []


@pytest.mark.parametrize("failure", ["failStore", "failMarkup"])
def test_a_store_failure_is_thrown_for_the_caller_to_answer_as_degraded(failure):
    (res,) = run([{"call": "lookup", "digest": D1, "options": {failure: True}}], shared_state())["results"]
    assert "unavailable" in res["threw"]


def test_after_a_revoke_the_next_lookup_is_null():
    out = run([
        {"call": "lookup", "digest": D1},
        {"call": "revoke", "caller": A, "id": "capaaaaaaaaaaa1"},
        {"call": "lookup", "digest": D1},
    ], shared_state())
    first, _, after = out["results"]
    assert first["value"]["reason"] == "available"
    assert after["value"] == {"capability": None, "reason": "revoked"}


# ---- what a row may hold: create ----------------------------------------------------------------------


def _row(**over) -> dict:
    state = base_state()
    return cap_row("capaaaaaaaaaaa1", A, "snapresumeaaaa1", D1, state, **over)


SNAP_A = {"id": "snapresumeaaaa1", "user": A, "content_checksum": checksum(MARKUP_A)}


def test_a_well_formed_row_may_be_stored():
    (res,) = run([{"call": "screenCreate", "row": _row(), "snapshot": SNAP_A}])["results"]
    assert res["value"] is None


@pytest.mark.parametrize("over, snapshot, reason", [
    ({"user": "x"}, SNAP_A, "user"),
    ({"target_kind": "artifact_revision"}, SNAP_A, "target_kind"),
    ({}, None, "snapshot"),
    ({}, dict(SNAP_A, user=B), "snapshot"),
    ({}, dict(SNAP_A, id="snapresumebbbb1"), "snapshot"),
    ({"target_checksum": checksum("other")}, SNAP_A, "target_checksum"),
    ({"purpose": ""}, SNAP_A, "purpose"),
    ({"purpose": " padded"}, SNAP_A, "purpose"),
    ({"purpose": "x" * 81}, SNAP_A, "purpose"),
    ({"expires_at": fmt(NOW)}, SNAP_A, "expires_at"),
    ({"expires_at": fmt(NOW + 365 * DAY + 1)}, SNAP_A, "expires_at"),
    ({"password_policy_ref": "has space"}, SNAP_A, "password_policy_ref"),
    ({"view_policy": "counted"}, SNAP_A, "view_policy"),
    ({"capability_version": 2}, SNAP_A, "capability_version"),
    ({"status": "revoked"}, SNAP_A, "status"),
    ({"revoked_reason": "owner"}, SNAP_A, "revoked"),
    ({"revoked_at": fmt(NOW)}, SNAP_A, "revoked"),
    ({"projection_version": 2}, SNAP_A, "projection_version"),
    ({"bearer_digest": "x"}, SNAP_A, "bearer_digest"),
    ({"digest_key_version": 0}, SNAP_A, "digest_key_version"),
])
def test_a_row_that_breaks_a_create_rule_is_refused(over, snapshot, reason):
    (res,) = run([{"call": "screenCreate", "row": _row(**over), "snapshot": snapshot}])["results"]
    assert res["value"] == reason


# ---- how a row may change: update ---------------------------------------------------------------------


REVOKE = {"status": "revoked", "revoked_at": fmt(NOW), "revoked_reason": "owner", "capability_version": 2}


@pytest.mark.parametrize("change", [
    {},
    {"capability_version": 2, "bearer_digest": D2},
    {"capability_version": 2},
    {"expires_at": fmt(NOW + DAY)},
    REVOKE,
    dict(REVOKE, revoked_reason="source_deleted"),
    dict(REVOKE, capability_version=2, bearer_digest=D2),
])
def test_the_moves_an_active_capability_may_make(change):
    before = _row()
    (res,) = run([{"call": "screenUpdate", "before": before, "after": dict(before, **change)}])["results"]
    assert res["value"] is None


@pytest.mark.parametrize("change, reason", [
    ({"user": B}, "user"),
    ({"target_kind": "artifact_revision"}, "target_kind"),
    ({"snapshot": "snapvariantaaa1"}, "snapshot"),
    ({"target_checksum": checksum("other")}, "target_checksum"),
    ({"purpose": "Renamed"}, "purpose"),
    ({"password_policy_ref": "pw1$other"}, "password_policy_ref"),
    ({"view_policy": "counted"}, "view_policy"),
    ({"projection_version": 2}, "projection_version"),
    ({"digest_key_version": 2}, "digest_key_version"),
    ({"capability_version": 0}, "capability_version"),
    ({"bearer_digest": D2}, "bearer_digest"),
    ({"capability_version": 2, "bearer_digest": "x"}, "bearer_digest"),
    ({"expires_at": fmt(NOW + 31 * DAY)}, "expires_at"),
    ({"expires_at": ""}, "expires_at"),
    (dict(REVOKE, capability_version=1), "capability_version"),
    (dict(REVOKE, revoked_reason=""), "revoked"),
    (dict(REVOKE, revoked_reason="expired"), "revoked"),
    (dict(REVOKE, revoked_at=""), "revoked"),
    ({"revoked_reason": "owner"}, "revoked"),
    ({"status": "paused"}, "status"),
])
def test_any_other_change_to_an_active_capability_is_refused(change, reason):
    before = _row()
    (res,) = run([{"call": "screenUpdate", "before": before, "after": dict(before, **change)}])["results"]
    assert res["value"] == reason


@pytest.mark.parametrize("change", [
    {"status": "active", "revoked_at": "", "revoked_reason": "", "capability_version": 3},
    {"capability_version": 3},
    {"capability_version": 3, "bearer_digest": D2},
    {"expires_at": fmt(NOW + DAY)},
    {"revoked_reason": "source_deleted"},
    {"revoked_at": fmt(NOW + 1)},
])
def test_a_revoked_capability_never_changes_again(change):
    before = _row(**REVOKE)
    (res,) = run([{"call": "screenUpdate", "before": before, "after": dict(before, **change)}])["results"]
    assert res["value"] == "revoked"


def test_saving_a_revoked_capability_unchanged_is_allowed():
    before = _row(**REVOKE)
    (res,) = run([{"call": "screenUpdate", "before": before, "after": dict(before)}])["results"]
    assert res["value"] is None


# ---- the owner's list and revoke ------------------------------------------------------------------------


def _owned_state() -> dict:
    state = base_state()
    caps = state["capabilities"]
    caps["capaaaaaaaaaaa1"] = cap_row("capaaaaaaaaaaa1", A, "snapresumeaaaa1", D1, state, created=fmt(NOW - 3 * DAY))
    caps["capaaaaaaaaaaa2"] = cap_row("capaaaaaaaaaaa2", A, "snapvariantaaa1", D2, state, created=fmt(NOW - DAY),
                                      password_policy_ref="pw1$placeholder$verifier")
    caps["capbbbbbbbbbbb1"] = cap_row("capbbbbbbbbbbb1", B, "snapresumebbbb1", D3, state, created=fmt(NOW))
    return state


def test_the_owner_list_has_only_the_callers_rows_newest_first_and_only_the_owner_fields():
    (res,) = run([{"call": "list", "caller": A}], _owned_state())["results"]
    assert res["value"]["status"] == 200
    items = res["value"]["body"]["items"]
    assert [i["id"] for i in items] == ["capaaaaaaaaaaa2", "capaaaaaaaaaaa1"]
    assert all(list(i) == OWNER_FIELDS for i in items)
    text = json.dumps(res["value"])
    for secret in (D1, D2, D3, "pw1$placeholder$verifier", "snapresumeaaaa1", A, B):
        assert secret not in text


def test_a_caller_with_no_capabilities_or_no_account_lists_none():
    out = run([{"call": "list", "caller": DEMO}, {"call": "list", "caller": "not-an-id"}], _owned_state())
    assert [r["value"]["body"]["items"] for r in out["results"]] == [[], []]


def test_revoke_records_the_reason_raises_the_version_and_keeps_the_row():
    out = run([{"call": "revoke", "caller": A, "id": "capaaaaaaaaaaa1"}], _owned_state())
    (res,) = out["results"]
    assert res["value"]["status"] == 200
    assert res["value"]["body"]["changed"] is True
    assert res["value"]["body"]["capability"]["status"] == "revoked"
    row = out["state"]["capabilities"]["capaaaaaaaaaaa1"]
    assert (row["status"], row["revoked_reason"], row["revoked_at"], row["capability_version"]) == (
        "revoked", "owner", fmt(NOW), 2)
    assert row["bearer_digest"] == D1 and row["snapshot"] == "snapresumeaaaa1"


def test_revoking_again_answers_the_same_and_writes_nothing():
    first = run([{"call": "revoke", "caller": A, "id": "capaaaaaaaaaaa1"}], _owned_state())
    again = run([{"call": "revoke", "caller": A, "id": "capaaaaaaaaaaa1", "now": NOW + DAY}], first["state"])
    (res,) = again["results"]
    assert res["value"]["body"]["changed"] is False
    assert res["value"]["body"]["capability"] == first["results"][0]["value"]["body"]["capability"]
    assert "update" not in res["calls"]
    assert again["state"] == first["state"]


@pytest.mark.parametrize("caller, cid", [
    (B, "capaaaaaaaaaaa1"),
    (A, "capmissingaaaa1"),
    (A, "CAPAAAAAAAAAAA1"),
    (A, "../capaaaaaaaaa"),
    (A, ""),
    (DEMO, "capaaaaaaaaaaa1"),
])
def test_another_accounts_capability_answers_like_a_missing_one_and_stays(caller, cid):
    state = _owned_state()
    out = run([{"call": "revoke", "caller": caller, "id": cid}], state)
    (res,) = out["results"]
    assert res["value"] == {"status": 404, "body": {"v": "share-capability/v1", "error": "not_found"}}
    assert "update" not in res["calls"]
    assert out["state"] == state


# ---- deletes: the source, then the account ---------------------------------------------------------------


def _source_state() -> dict:
    """A's resume shared twice (one revoked by the owner), its variant
    shared once, and B's resume shared once."""
    state = base_state()
    caps = state["capabilities"]
    caps["capresumeactive"] = cap_row("capresumeactive", A, "snapresumeaaaa1", D1, state)
    caps["capresumerevokd"] = cap_row("capresumerevokd", A, "snapresumeaaaa1", D2, state, **REVOKE)
    caps["capvariantactiv"] = cap_row("capvariantactiv", A, "snapvariantaaa1", D3, state)
    caps["capotheraccount"] = cap_row("capotheraccount", B, "snapresumebbbb1", D9, state)
    return state


def test_a_deleted_resume_revokes_its_active_capability_and_keeps_its_snapshots():
    state = _source_state()
    del state["resumes"]["resumeaaaaaaaa1"]  # the delete has committed
    out = run([{"call": "revokeForSource", "kind": "resume", "id": "resumeaaaaaaaa1"}], state)
    (res,) = out["results"]
    assert res["value"] == {"revoked": 1}
    caps = out["state"]["capabilities"]
    active = caps["capresumeactive"]
    assert (active["status"], active["revoked_reason"], active["revoked_at"], active["capability_version"]) == (
        "revoked", "source_deleted", fmt(NOW), 2)
    # A capability the owner had already revoked keeps its own reason.
    assert caps["capresumerevokd"] == state["capabilities"]["capresumerevokd"]
    # The variant's goes when its own delete fires; another account's never.
    assert caps["capvariantactiv"]["status"] == "active"
    assert caps["capotheraccount"]["status"] == "active"
    # Every snapshot stays, so each capability still names what it granted.
    assert out["state"]["snapshots"] == state["snapshots"]
    assert {c["snapshot"] for c in caps.values()} <= set(out["state"]["snapshots"])


def test_a_deleted_variant_revokes_its_capability_too():
    state = _source_state()
    del state["variants"]["variantaaaaaaa1"]
    out = run([{"call": "revokeForSource", "kind": "variant", "id": "variantaaaaaaa1"}], state)
    assert out["results"][0]["value"] == {"revoked": 1}
    assert out["state"]["capabilities"]["capvariantactiv"]["revoked_reason"] == "source_deleted"
    assert out["state"]["snapshots"] == state["snapshots"]


def test_a_source_with_only_a_revoked_capability_changes_nothing():
    state = _source_state()
    del state["capabilities"]["capresumeactive"]
    out = run([{"call": "revokeForSource", "kind": "resume", "id": "resumeaaaaaaaa1"}], state)
    (res,) = out["results"]
    assert res["value"] == {"revoked": 0}
    assert "update" not in res["calls"]
    assert out["state"] == state


@pytest.mark.parametrize("kind, sid", [("resume", "resumenotshared"), ("version", "resumeaaaaaaaa1"),
                                       ("resume", "BAD")])
def test_a_source_with_no_capability_or_an_odd_one_revokes_nothing(kind, sid):
    state = _source_state()
    out = run([{"call": "revokeForSource", "kind": kind, "id": sid}], state)
    assert out["results"][0]["value"] == {"revoked": 0}
    assert out["state"] == state


def test_a_failed_revoke_leaves_the_store_as_it_was():
    state = _source_state()
    out = run([{"call": "revokeForSource", "kind": "resume", "id": "resumeaaaaaaaa1",
                "options": {"failUpdate": True}}], state)
    assert "busy" in out["results"][0]["threw"]
    assert out["state"] == state


@pytest.mark.parametrize("kind", ["resume", "variant"])
def test_the_source_delete_hook_never_throws_so_the_delete_always_finishes(kind):
    # PocketBase 0.22 runs it after the delete commits; a throw would only
    # turn a finished delete into an error. lookup refuses the capability
    # anyway, since its source is gone.
    out = run([{"call": "onSourceDeleted", "kind": kind, "id": "resumeaaaaaaaa1"}])
    (res,) = out["results"]
    assert "threw" not in res
    assert {"level": "error", "line": {"v": "obs/v1", "event": "share_capability", "service": "pocketbase",
                                       "outcome": "revoke_failed", "reason": "source_deleted"}} in out["logs"]


def test_an_account_delete_removes_only_that_accounts_capabilities():
    state = _source_state()
    out = run([{"call": "deleteForAccount", "user": A}], state)
    assert out["results"][0]["value"] == {"deleted": 3}
    assert list(out["state"]["capabilities"]) == ["capotheraccount"]
    assert out["state"]["snapshots"] == state["snapshots"]


def test_a_failure_while_deleting_an_accounts_capabilities_fails_the_account_delete():
    # It runs inside the account delete's transaction: throwing undoes it
    # all, where carrying on would leave the cascade to fail on a snapshot.
    (res,) = run([{"call": "onAccountDelete", "id": A}])["results"]
    assert "locked" in res["threw"]


# ---- the model hooks, as PocketBase calls them ----------------------------------------------------------


def test_the_create_hook_accepts_a_well_formed_row_and_refuses_a_foreign_snapshot():
    snapshot = {"id": "snapresumeaaaa1", "user": A, "source_kind": "resume", "source_id": "resumeaaaaaaaa1",
                "content_checksum": checksum(MARKUP_A), "markup": "snapshot_abc.html"}
    out = run([
        {"call": "guardCreate", "row": _row(), "snapshot": snapshot},
        {"call": "guardCreate", "row": _row(), "snapshot": dict(snapshot, user=B)},
        {"call": "guardCreate", "row": _row(), "snapshot": None},
    ])
    ok, foreign, missing = out["results"]
    assert "threw" not in ok
    assert foreign["threw"] == missing["threw"] == "share capability refused: snapshot"


def test_the_update_hook_refuses_a_retarget():
    before = _row()
    (res,) = run([{"call": "guardUpdate", "original": before, "row": dict(before, snapshot="snapvariantaaa1")}])["results"]
    assert res["threw"] == "share capability refused: snapshot"


def test_hook_logs_carry_no_id_owner_digest_purpose_or_content():
    state = _source_state()
    out = run([
        {"call": "guardCreate", "row": _row(), "snapshot": None},
        {"call": "guardUpdate", "original": _row(), "row": dict(_row(), user=B)},
        {"call": "onSourceDeleted", "kind": "resume", "id": "resumeaaaaaaaa1"},
        {"call": "onAccountDelete", "id": A},
        {"call": "create", "input": create_input(snapshot_id="snapresumebbbb1")},
    ], state)
    text = json.dumps(out["logs"])
    planted = [A, B, D1, D2, D3, D9, "capaaaaaaaaaaa1", "snapresumeaaaa1", "snapresumebbbb1", "resumeaaaaaaaa1",
               "For recruiters", "Ada"]
    assert out["logs"], "expected the hooks to log"
    for value in planted:
        assert value not in text, value


# ---- registration ------------------------------------------------------------------------------------------


REGISTRATION = r"""
const path = require("path");
const [hooksDir] = process.argv.slice(1);
const seen = [];
globalThis.__hooks = hooksDir;
globalThis.$apis = { requireRecordAuth: (...names) => ({ requireRecordAuth: names }) };
globalThis.routerAdd = (method, route, handler, ...middlewares) => seen.push({ name: "routerAdd", method, route, middlewares });
for (const name of ["onModelBeforeCreate", "onModelBeforeUpdate", "onModelAfterDelete", "onModelBeforeDelete"]) {
  globalThis[name] = (fn, ...tags) => seen.push({ name, tags });
}
require(path.join(hooksDir, "share_capabilities.pb.js"));
process.stdout.write(JSON.stringify(seen));
"""


def test_share_capabilities_pb_js_registers_the_owner_routes_and_the_model_hooks():
    node = shutil.which("node")
    assert node
    res = subprocess.run([node, "-e", REGISTRATION, str(HOOKS)], capture_output=True, text=True, timeout=60, check=True)
    owner_only = [{"requireRecordAuth": ["users"]}]
    assert json.loads(res.stdout) == [
        {"name": "routerAdd", "method": "GET", "route": "/api/rounds/share/capabilities", "middlewares": owner_only},
        {"name": "routerAdd", "method": "POST", "route": "/api/rounds/share/capabilities/:id/revoke",
         "middlewares": owner_only},
        {"name": "onModelBeforeCreate", "tags": ["share_capabilities"]},
        {"name": "onModelBeforeUpdate", "tags": ["share_capabilities"]},
        {"name": "onModelAfterDelete", "tags": ["resumes"]},
        {"name": "onModelAfterDelete", "tags": ["resume_variants"]},
        {"name": "onModelBeforeDelete", "tags": ["users"]},
    ]


def test_each_handler_requires_the_module_itself_and_it_is_not_a_hook_file():
    source = (HOOKS / "share_capabilities.pb.js").read_text()
    assert "function " not in source
    assert len(re.findall(r"require\(`\$\{__hooks\}/share_capabilities\.js`\)", source)) == 7
    assert (HOOKS / "share_capabilities.js").exists()
    assert not (HOOKS / "share_capabilities.js").name.endswith(".pb.js")
