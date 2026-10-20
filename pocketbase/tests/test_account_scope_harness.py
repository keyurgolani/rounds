"""Unit tests for the account-scope harness logic (ROUNDS-00B-L01).

Covers policy.load validation, the rule read-back's exact comparison
(including null vs "" and the users manageRule), and the verdict's
pass/fail decisions. These run in the backend gate via
``pytest ../pocketbase/tests``; the full two-account run lives in the
Finch/Docker harness.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

PROBES = Path(__file__).resolve().parents[1].parent / "harness" / "probes"
sys.path.insert(0, str(PROBES))

import factory  # noqa: E402
import families  # noqa: E402
import policy  # noqa: E402
import run  # noqa: E402
from pbclient import Response  # noqa: E402
from receipts import Receipt  # noqa: E402

ENFORCED = "account-scope.view.cross-account.denied"
# A synthetic family name that is never a real, implemented family. Stage 3
# closes the last open gap, so the pending-handling tests use this name to
# exercise the verdict logic without depending on a still-open real family.
PENDING = "account-scope.synthetic.pending"


def minimal_doc() -> dict:
    return {
        "version": "v1",
        "contract": "account-scope",
        "deny_contract": {"view": {"status": 404}},
        "probe_families": {
            ENFORCED: {"status": "enforced", "deny_key": "view", "operation": "view", "actor": "authenticated-other"},
            PENDING: {"status": "pending", "deny_key": "view", "operation": "create", "actor": "authenticated-other"},
        },
        "collections": {
            "campaigns": {
                "current_rules": {"list": "user = @request.auth.id"},
                "probes": [ENFORCED, PENDING],
            }
        },
    }


def write_receipts(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def receipt(probe_id: str, collection: str, passed: bool = True) -> dict:
    return {
        "probe_id": probe_id,
        "collection": collection,
        "operation": "view",
        "actor": "authenticated-other",
        "expected_status": 404,
        "observed_status": 404 if passed else 200,
        "passed": passed,
        "request_time_ms": 1,
    }


def baseline_rows() -> list[dict]:
    return [receipt(ENFORCED, "campaigns"), receipt(run.READBACK_PROBE, "campaigns")]


# --------------------------------------------------------------------------
# policy.load
# --------------------------------------------------------------------------


def _write_policy(tmp_path: Path, doc: dict) -> Path:
    p = tmp_path / "policy.json"
    p.write_text(json.dumps(doc))
    return p


def test_load_accepts_the_minimal_valid_policy(tmp_path):
    doc = policy.load(_write_policy(tmp_path, minimal_doc()))
    assert doc["version"] == "v1"


def test_load_rejects_unknown_version(tmp_path):
    d = minimal_doc()
    d["version"] = "v2"
    with pytest.raises(policy.PolicyError, match="unsupported policy version"):
        policy.load(_write_policy(tmp_path, d))


def test_load_rejects_unknown_family_status(tmp_path):
    d = minimal_doc()
    d["probe_families"][ENFORCED]["status"] = "maybe"
    with pytest.raises(policy.PolicyError, match="unknown status"):
        policy.load(_write_policy(tmp_path, d))


def test_load_rejects_a_collection_referencing_an_undeclared_family(tmp_path):
    d = minimal_doc()
    d["collections"]["campaigns"]["probes"].append("account-scope.make-believe")
    with pytest.raises(policy.PolicyError, match="undeclared probe family"):
        policy.load(_write_policy(tmp_path, d))


def test_enforced_and_pending_pairs_split_by_status():
    d = minimal_doc()
    assert policy.enforced_pairs(d) == [("campaigns", ENFORCED)]
    assert policy.pending_pairs(d) == [("campaigns", PENDING)]


def test_committed_policy_loads_and_covers_every_denial_cell():
    doc = policy.load(run.os.environ.get("POLICY_PATH", str(
        Path(__file__).resolve().parents[1].parent / "docs" / "security" / "account-scope.v1.json")))
    # Every enforced family the committed policy references has an
    # implementation, and every pending one does not.
    fam = doc["probe_families"]
    for name, row in doc["collections"].items():
        for pid in row["probes"]:
            if fam[pid]["status"] == "enforced":
                assert pid in families.IMPLEMENTED_FAMILIES, pid
            else:
                assert pid not in families.IMPLEMENTED_FAMILIES, pid


# --------------------------------------------------------------------------
# run_verdict
# --------------------------------------------------------------------------


def test_verdict_passes_when_every_enforced_result_and_readback_pass(tmp_path):
    path = tmp_path / "r.jsonl"
    write_receipts(path, baseline_rows())
    assert run.run_verdict(minimal_doc(), str(path)) == 0


def test_verdict_fails_on_a_missing_enforced_result(tmp_path):
    path = tmp_path / "r.jsonl"
    write_receipts(path, [receipt(run.READBACK_PROBE, "campaigns")])
    assert run.run_verdict(minimal_doc(), str(path)) == 1


def test_verdict_fails_on_a_failed_enforced_result(tmp_path):
    path = tmp_path / "r.jsonl"
    write_receipts(path, [receipt(ENFORCED, "campaigns", passed=False), receipt(run.READBACK_PROBE, "campaigns")])
    assert run.run_verdict(minimal_doc(), str(path)) == 1


def test_verdict_fails_on_a_missing_readback(tmp_path):
    path = tmp_path / "r.jsonl"
    write_receipts(path, [receipt(ENFORCED, "campaigns")])
    assert run.run_verdict(minimal_doc(), str(path)) == 1


def test_verdict_fails_when_a_pending_family_produces_a_receipt(tmp_path):
    path = tmp_path / "r.jsonl"
    write_receipts(path, baseline_rows() + [receipt(PENDING, "campaigns")])
    assert run.run_verdict(minimal_doc(), str(path)) == 1


def test_verdict_fails_when_a_pending_family_is_implemented(tmp_path, monkeypatch):
    path = tmp_path / "r.jsonl"
    write_receipts(path, baseline_rows())
    monkeypatch.setattr(families, "IMPLEMENTED_FAMILIES", families.IMPLEMENTED_FAMILIES | {PENDING})
    assert run.run_verdict(minimal_doc(), str(path)) == 1


def test_verdict_fails_on_a_stray_receipt_for_an_unknown_family(tmp_path):
    path = tmp_path / "r.jsonl"
    write_receipts(path, baseline_rows() + [receipt("account-scope.not-a-real-family", "campaigns")])
    assert run.run_verdict(minimal_doc(), str(path)) == 1


# --------------------------------------------------------------------------
# _readback
# --------------------------------------------------------------------------


@dataclass
class _Resp:
    status: int
    body: Any
    elapsed_ms: int = 1


class FakePB:
    def __init__(self, collections: list[dict]):
        self._collections = collections

    def collections_meta(self, admin_token: str) -> _Resp:
        return _Resp(200, {"items": self._collections})


class CapturingWriter:
    def __init__(self):
        self.receipts: list[Receipt] = []

    def write(self, r: Receipt) -> None:
        self.receipts.append(r)


def _readback_once(current_rules: dict, live_rules: dict) -> Receipt:
    doc = {"collections": {"c": {"current_rules": current_rules}}}
    live = {"name": "c", **live_rules}
    writer = CapturingWriter()
    run._readback(FakePB([live]), doc, "admin", writer)
    assert len(writer.receipts) == 1
    return writer.receipts[0]


def test_readback_passes_when_live_rules_match_exactly():
    r = _readback_once(
        {"list": "user = @request.auth.id", "create": '@request.auth.id != ""'},
        {"listRule": "user = @request.auth.id", "createRule": '@request.auth.id != ""'},
    )
    assert r.passed and r.detail == ""


def test_readback_distinguishes_null_from_empty_string():
    # Policy says create is "" (anyone); PocketBase reports null (superusers).
    r = _readback_once({"create": ""}, {"createRule": None})
    assert not r.passed and "create" in r.detail


def test_readback_flags_a_loosened_rule():
    r = _readback_once({"update": "user = @request.auth.id"}, {"updateRule": ""})
    assert not r.passed and "update" in r.detail


def test_readback_checks_the_users_manage_rule_under_options():
    # PocketBase 0.22 nests an auth collection's manageRule under options.
    passing = _readback_once({"manage": None}, {"options": {"manageRule": None}})
    assert passing.passed
    failing = _readback_once({"manage": None}, {"options": {"manageRule": "id = @request.auth.id"}})
    assert not failing.passed and "manage" in failing.detail
    # manageRule missing entirely (not an auth collection) is also a mismatch.
    absent = _readback_once({"manage": None}, {})
    assert not absent.passed and "manage" in absent.detail


def test_readback_flags_a_missing_collection():
    doc = {"collections": {"c": {"current_rules": {"list": "x"}}}}
    writer = CapturingWriter()
    run._readback(FakePB([]), doc, "admin", writer)
    assert not writer.receipts[0].passed and "collection-missing" in writer.receipts[0].detail


# --------------------------------------------------------------------------
# factory.fresh_payload and the create-anonymous / oversized probes
# --------------------------------------------------------------------------

STANDARD_COLLECTIONS = [
    "campaigns", "applications", "interview_rounds", "user_progress",
    "user_preferences", "offers", "code_drafts", "todos", "resumes",
    "resume_variants", "resume_versions", "resume_share_links",
    "resume_share_views", "ai_providers", "ai_settings", "ai_coding_drafts",
    "ai_coding_attempts", "take_home_drafts", "take_home_attempts",
    "question_timers", "experience_jobs", "experience_projects",
    "experience_anecdotes", "experience_bullets", "exp_job_projects",
    "exp_job_anecdotes", "exp_job_bullets", "exp_project_anecdotes",
    "exp_project_bullets", "exp_anecdote_bullets",
]


def _default_policy_path() -> str:
    return str(Path(__file__).resolve().parents[1].parent / "docs" / "security" / "account-scope.v1.json")


def _acct(tag: str) -> "factory.Account":
    a = factory.Account(tag=tag, email=f"{tag}@x", password="pw")
    a.user_id = f"uid-{tag}"
    for c in STANDARD_COLLECTIONS:
        a.ids[c] = f"{tag}-{c}-id"
    a.ids["users"] = a.user_id
    return a


def test_fresh_payload_has_a_recipe_for_every_standard_collection():
    a, b = _acct("a"), _acct("b")
    content = {"round": "round-id", "assignment": "assignment-id"}
    policy_collections = {
        n for n in policy.load(_default_policy_path())["collections"] if n != "users"
    }
    assert set(STANDARD_COLLECTIONS) == policy_collections
    for name in STANDARD_COLLECTIONS:
        payload = factory.fresh_payload(name, "owner-id", a, b, content, "sfx")
        assert payload["user"] == "owner-id"
        assert isinstance(payload, dict)


def test_fresh_payload_pairs_junctions_across_accounts_to_avoid_collisions():
    a, b = _acct("a"), _acct("b")
    content = {"round": "round-id", "assignment": "assignment-id"}
    p = factory.fresh_payload("exp_job_projects", "owner-id", a, b, content, "sfx")
    assert p["parent"] == a.ids["experience_jobs"]
    assert p["child"] == b.ids["experience_projects"]


def test_fresh_payload_rejects_an_unknown_collection():
    a, b = _acct("a"), _acct("b")
    content = {"round": "round-id", "assignment": "assignment-id"}
    with pytest.raises(RuntimeError, match="no recipe"):
        factory.fresh_payload("not_a_collection", "owner-id", a, b, content, "sfx")


class _CreatePB:
    def __init__(self, status: int, body: Any):
        self._status, self._body = status, body
        self.calls = []

    def create(self, collection, token, payload):
        self.calls.append((collection, token))
        return Response(status=self._status, body=self._body, elapsed_ms=1)


def test_create_anonymous_passes_only_on_a_rule_denial_with_empty_data():
    pb = _CreatePB(400, {"code": 400, "message": "Failed to create record.", "data": {}})
    r = families.create_anonymous_denied(pb, "campaigns", {"user": "x"}, 400)
    assert r.passed and pb.calls == [("campaigns", None)]


def test_create_anonymous_fails_on_a_field_validation_400():
    # A validation 400 (populated data) must not count: the rule was not reached.
    pb = _CreatePB(400, {"data": {"slug": {"code": "validation_required"}}})
    r = families.create_anonymous_denied(pb, "campaigns", {"user": "x"}, 400)
    assert not r.passed and "slug" in r.detail


def test_oversized_passes_only_on_a_json_size_error_for_the_field():
    good = _CreatePB(400, {"data": {"data": {"code": "validation_json_size_limit"}}})
    assert families.oversized_input_rejected(good, "resumes", "tok", {"user": "x"}, "data", 400).passed
    wrong = _CreatePB(400, {"data": {"name": {"code": "validation_required"}}})
    assert not families.oversized_input_rejected(wrong, "resumes", "tok", {"user": "x"}, "data", 400).passed
    created = _CreatePB(200, {"id": "rec"})
    assert not families.oversized_input_rejected(created, "resumes", "tok", {"user": "x"}, "data", 400).passed


# --------------------------------------------------------------------------
# stage-3 create/update ownership families
# --------------------------------------------------------------------------


class _ProbePB:
    """Configurable fake PocketBase for the ownership probe functions.

    ``update`` may be a single Response or a list consumed in order (the
    accept probe issues two updates). ``listing`` is used for the superuser
    owner-count check.
    """

    def __init__(self, *, create=None, update=None, view=None, listing=None):
        self._create, self._update, self._view, self._listing = create, update, view, listing
        self.calls: list[tuple] = []

    def create(self, collection, token, payload):
        self.calls.append(("create", collection, token, dict(payload) if payload else payload))
        return self._create

    def update(self, collection, record_id, payload, token=None):
        self.calls.append(("update", collection, record_id, token, dict(payload)))
        if isinstance(self._update, list):
            return self._update.pop(0)
        return self._update

    def view(self, collection, record_id, token=None):
        self.calls.append(("view", collection, record_id, token))
        return self._view

    def listing(self, collection, token=None, params=None):
        self.calls.append(("listing", collection, token, params))
        return self._listing


def _count(total):
    return Response(200, {"items": [], "totalItems": total}, 1)


def test_foreign_owner_denied_passes_on_empty_data_and_no_planted_row():
    pb = _ProbePB(create=Response(400, {"message": "Failed to create record.", "data": {}}, 1),
                  listing=_count(0))
    r = families.create_foreign_owner_denied(pb, "campaigns", "b-token", {"user": "uid-c"}, "admin", "uid-c", 400)
    assert r.passed
    # The caller is the authenticated account, not anonymous.
    assert pb.calls[0][:3] == ("create", "campaigns", "b-token")


def test_foreign_owner_denied_fails_if_a_row_was_planted():
    pb = _ProbePB(create=Response(400, {"data": {}}, 1), listing=_count(1))
    r = families.create_foreign_owner_denied(pb, "campaigns", "b-token", {"user": "uid-c"}, "admin", "uid-c", 400)
    assert not r.passed and "rows_under_owner=1" in r.detail


def test_foreign_owner_denied_fails_on_a_validation_400_with_populated_data():
    pb = _ProbePB(create=Response(400, {"data": {"slug": {"code": "validation_required"}}}, 1), listing=_count(0))
    r = families.create_foreign_owner_denied(pb, "campaigns", "b-token", {"user": "uid-c"}, "admin", "uid-c", 400)
    assert not r.passed and "slug" in r.detail


def test_reassign_denied_passes_when_denied_and_owner_unchanged():
    pb = _ProbePB(update=Response(404, {}, 1), view=Response(200, {"id": "x", "user": "uid-a"}, 1))
    r = families.update_reassign_denied(pb, "campaigns", "rec", "uid-b", "a-token", "admin", "uid-a", 404)
    assert r.passed


def test_reassign_denied_fails_when_the_owner_actually_changed():
    # The pre-migration rule lets the reassign through: status is not the deny
    # status and the owner is now the other account.
    pb = _ProbePB(update=Response(200, {"id": "x", "user": "uid-b"}, 1), view=Response(200, {"id": "x", "user": "uid-b"}, 1))
    r = families.update_reassign_denied(pb, "campaigns", "rec", "uid-b", "a-token", "admin", "uid-a", 404)
    assert not r.passed


def test_update_own_accepted_passes_when_both_client_shapes_succeed():
    pb = _ProbePB(update=[Response(200, {"id": "x"}, 1), Response(200, {"id": "x"}, 1)])
    r = families.update_own_accepted(pb, "campaigns", "rec", "uid-b", "b-token", 200)
    assert r.passed
    # Shape one omits user; shape two resends the owner's own id.
    assert pb.calls[0][4] == {} and pb.calls[1][4] == {"user": "uid-b"}


def test_update_own_accepted_fails_if_either_shape_is_rejected():
    pb = _ProbePB(update=[Response(200, {"id": "x"}, 1), Response(404, {}, 1)])
    r = families.update_own_accepted(pb, "campaigns", "rec", "uid-b", "b-token", 200)
    assert not r.passed and "resend=404" in r.detail


def test_server_only_create_denied_passes_on_forbidden_and_no_planted_row():
    pb = _ProbePB(create=Response(403, {"message": "Only superusers can perform this action."}, 1), listing=_count(0))
    r = families.create_server_only_denied(pb, "resume_share_views", "b-token", {"user": "uid-c"}, "admin", "uid-c", 403)
    assert r.passed


def test_server_only_update_denied_passes_when_forbidden_but_still_readable():
    pb = _ProbePB(update=Response(403, {}, 1), view=Response(200, {"id": "x"}, 1))
    r = families.update_server_only_denied(pb, "resume_share_views", "rec", "a-token", 403)
    assert r.passed


def test_server_only_update_denied_fails_if_the_update_went_through():
    pb = _ProbePB(update=Response(200, {"id": "x"}, 1), view=Response(200, {"id": "x"}, 1))
    r = families.update_server_only_denied(pb, "resume_share_views", "rec", "a-token", 403)
    assert not r.passed


def test_superuser_create_accepted_passes_on_success_and_fails_on_forbidden():
    ok = _ProbePB(create=Response(200, {"id": "view"}, 1))
    assert families.create_superuser_accepted(ok, "resume_share_views", "admin", {"user": "uid-a"}, 200).passed
    denied = _ProbePB(create=Response(403, {}, 1))
    assert not families.create_superuser_accepted(denied, "resume_share_views", "admin", {"user": "uid-a"}, 200).passed
