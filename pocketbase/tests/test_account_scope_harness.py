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
import re
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
    def __init__(self, status: int, body: Any, owner_rows: int = 0):
        self._status, self._body = status, body
        self.owner_rows = owner_rows
        self.calls = []

    def create(self, collection, token, payload):
        self.calls.append((collection, token))
        return Response(status=self._status, body=self._body, elapsed_ms=1)

    def listing(self, collection, token=None, params=None):
        # The superuser's owner-count read.
        return Response(status=200, body={"items": [], "totalItems": self.owner_rows}, elapsed_ms=1)


def test_create_anonymous_passes_only_on_a_rule_denial_with_empty_data():
    pb = _CreatePB(400, {"code": 400, "message": "Failed to create record.", "data": {}})
    r = families.create_anonymous_denied(pb, "campaigns", {"user": "x"}, "admin", "uid-c", 400)
    assert r.passed and pb.calls == [("campaigns", None)]


def test_create_anonymous_fails_on_a_field_validation_400():
    # A validation 400 (populated data) must not count: the rule was not reached.
    pb = _CreatePB(400, {"data": {"slug": {"code": "validation_required"}}})
    r = families.create_anonymous_denied(pb, "campaigns", {"user": "x"}, "admin", "uid-c", 400)
    assert not r.passed and "slug" in r.detail


def test_create_anonymous_fails_if_a_row_was_left_under_the_owner():
    pb = _CreatePB(400, {"data": {}}, owner_rows=1)
    r = families.create_anonymous_denied(pb, "campaigns", {"user": "x"}, "admin", "uid-c", 400)
    assert not r.passed and "rows_under_owner=1" in r.detail


def _oversized(pb):
    return families.oversized_input_rejected(pb, "resumes", "tok", {"user": "x"}, "data", "admin", "uid-a", 400)


def test_oversized_passes_only_on_a_json_size_error_for_the_field():
    good = _CreatePB(400, {"data": {"data": {"code": "validation_json_size_limit"}}}, owner_rows=1)
    assert _oversized(good).passed
    wrong = _CreatePB(400, {"data": {"name": {"code": "validation_required"}}}, owner_rows=1)
    assert not _oversized(wrong).passed
    created = _CreatePB(200, {"id": "rec"}, owner_rows=1)
    assert not _oversized(created).passed


class _CountingCreatePB(_CreatePB):
    """The owner's row count rises after the create, as if it was written."""

    def __init__(self, status, body, counts):
        super().__init__(status, body)
        self._counts = list(counts)

    def listing(self, collection, token=None, params=None):
        return Response(status=200, body={"items": [], "totalItems": self._counts.pop(0)}, elapsed_ms=1)


def test_oversized_fails_if_the_owners_row_count_changed():
    pb = _CountingCreatePB(400, {"data": {"data": {"code": "validation_json_size_limit"}}}, counts=[1, 2])
    r = _oversized(pb)
    assert not r.passed and "rows_before=1 rows_after=2" in r.detail


class _SignupPB:
    def __init__(self, signup_status, accounts, listing_status=200):
        self.signup_status, self.accounts, self.listing_status = signup_status, accounts, listing_status
        self.filters = []

    def signup(self, email, password):
        return Response(self.signup_status, {"code": self.signup_status, "message": "x", "data": {}}, 1)

    def listing(self, collection, token=None, params=None):
        self.filters.append((collection, token, (params or {}).get("filter", "")))
        return Response(self.listing_status, {"items": [], "totalItems": self.accounts}, 1)


def test_disabled_signup_passes_only_when_no_account_is_left():
    ok = _SignupPB(400, accounts=0)
    r = families.signup_disabled_denied(ok, "admin", 400)
    assert r.passed and ok.filters[0][:2] == ("users", "admin") and "@harness.invalid" in ok.filters[0][2]
    assert not families.signup_disabled_denied(_SignupPB(400, accounts=1), "admin", 400).passed
    assert not families.signup_disabled_denied(_SignupPB(400, accounts=0, listing_status=500), "admin", 400).passed
    assert not families.signup_disabled_denied(_SignupPB(200, accounts=0), "admin", 400).passed


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


def test_foreign_owner_denied_fails_when_the_superuser_listing_errors():
    # The create was denied correctly, but the no-row-planted check couldn't
    # run: that must fail the probe, not pass it on a count of zero.
    pb = _ProbePB(create=Response(400, {"data": {}}, 1), listing=Response(500, {"message": "x"}, 1))
    r = families.create_foreign_owner_denied(pb, "campaigns", "b-token", {"user": "uid-c"}, "admin", "uid-c", 400)
    assert not r.passed and "listing status=500" in r.detail


def test_foreign_owner_denied_fails_when_the_listing_is_not_a_page():
    pb = _ProbePB(create=Response(400, {"data": {}}, 1), listing=Response(200, None, 1))
    r = families.create_foreign_owner_denied(pb, "campaigns", "b-token", {"user": "uid-c"}, "admin", "uid-c", 400)
    assert not r.passed and "rows_under_owner=unknown" in r.detail


def test_server_only_create_denied_fails_when_the_superuser_listing_errors():
    pb = _ProbePB(create=Response(403, {}, 1), listing=Response(401, {"message": "x"}, 1))
    r = families.create_server_only_denied(pb, "resume_share_views", "b-token", {"user": "uid-c"}, "admin", "uid-c", 403)
    assert not r.passed and "listing status=401" in r.detail


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


# --------------------------------------------------------------------------
# stage-4 enumeration, inference, replay, and degraded families
# --------------------------------------------------------------------------


class _StatefulPB:
    """A fake PocketBase holding one record per (collection, id), so the
    owner's before/after snapshot and foreign-versus-missing answers are real
    comparisons. `leak` makes a named operation succeed on a foreign record."""

    NOT_FOUND = {"code": 404, "message": "The requested resource wasn't found.", "data": {}}

    def __init__(self, records: dict, owner_token: str, leak: str = ""):
        self.records = {k: dict(v) for k, v in records.items()}
        self.owner_token = owner_token
        self.leak = leak

    def _find(self, collection, record_id):
        return self.records.get((collection, record_id))

    def view(self, collection, record_id, token=None):
        rec = self._find(collection, record_id)
        if rec is None or (token != self.owner_token and self.leak != "view"):
            return Response(404, dict(self.NOT_FOUND), 1)
        return Response(200, dict(rec), 1)

    def update(self, collection, record_id, payload, token=None):
        rec = self._find(collection, record_id)
        if rec is None or (token != self.owner_token and self.leak != "update"):
            return Response(404, dict(self.NOT_FOUND), 1)
        rec["updated"] = rec.get("updated", "") + "+"
        return Response(200, dict(rec), 1)

    def delete(self, collection, record_id, token=None):
        rec = self._find(collection, record_id)
        if rec is None or (token != self.owner_token and self.leak != "delete"):
            return Response(404, dict(self.NOT_FOUND), 1)
        del self.records[(collection, record_id)]
        return Response(204, None, 1)

    def listing(self, collection, token=None, params=None):
        flt = (params or {}).get("filter", "")
        items = []
        if self.leak == "list":
            items = [dict(r) for (c, rid), r in self.records.items() if c == collection and rid in flt]
        return Response(200, {"items": items, "totalItems": len(items)}, 1)


def _accounts():
    a, b = _acct("a"), _acct("b")
    a.token, b.token = "a-token", "b-token"
    return a, b


def _pb_with_a_record(leak=""):
    a, b = _accounts()
    pb = _StatefulPB({("campaigns", a.ids["campaigns"]): {"id": a.ids["campaigns"], "user": a.user_id, "updated": "t0"}},
                     owner_token=a.token, leak=leak)
    return pb, a, b


@pytest.mark.parametrize("fn,leak", [
    (families.update_cross_account_denied, "update"),
    (families.delete_cross_account_denied, "delete"),
])
def test_a_denied_write_passes_only_if_the_record_is_unchanged(fn, leak):
    pb, a, b = _pb_with_a_record()
    assert fn(pb, "campaigns", a, b, 404).passed
    leaky, a, b = _pb_with_a_record(leak=leak)
    r = fn(leaky, "campaigns", a, b, 404)
    assert not r.passed and "unchanged=False" in r.detail


class _ViewSeq(_ProbePB):
    """Answers views in order, so a probe's before and after reads can differ."""

    def __init__(self, views, **kw):
        super().__init__(**kw)
        self._views = list(views)

    def view(self, collection, record_id, token=None):
        self.calls.append(("view", collection, record_id, token))
        return self._views.pop(0)


def test_reassign_denied_fails_when_another_field_changed():
    pb = _ViewSeq([Response(200, {"id": "x", "user": "uid-a", "name": "old"}, 1),
                   Response(200, {"id": "x", "user": "uid-a", "name": "new"}, 1)],
                  update=Response(404, {}, 1))
    r = families.update_reassign_denied(pb, "campaigns", "rec", "uid-b", "a-token", "admin", "uid-a", 404)
    assert not r.passed and "unchanged=False" in r.detail


def test_server_only_update_denied_fails_when_the_row_changed():
    pb = _ViewSeq([Response(200, {"id": "x", "updated": "t0"}, 1), Response(200, {"id": "x", "updated": "t1"}, 1)],
                  update=Response(403, {}, 1))
    r = families.update_server_only_denied(pb, "resume_share_views", "rec", "a-token", 403)
    assert not r.passed and "unchanged=False" in r.detail


def test_list_filter_isolated_passes_when_filters_return_nothing():
    pb, a, b = _pb_with_a_record()
    assert families.list_filter_isolated(pb, "campaigns", a, b, 200).passed


def test_list_filter_isolated_fails_when_a_filter_returns_a_foreign_row():
    pb, a, b = _pb_with_a_record(leak="list")
    r = families.list_filter_isolated(pb, "campaigns", a, b, 200)
    assert not r.passed and "rows=1" in r.detail


@pytest.mark.parametrize("fn,op", [
    (families.view_foreign_or_missing, "view"),
    (families.update_foreign_or_missing, "update"),
    (families.delete_foreign_or_missing, "delete"),
])
def test_foreign_and_missing_records_must_answer_alike(fn, op):
    pb, a, b = _pb_with_a_record()
    assert fn(pb, "campaigns", a, b, 404).passed
    leaky, a, b = _pb_with_a_record(leak=op)
    assert not fn(leaky, "campaigns", a, b, 404).passed


def test_foreign_or_missing_fails_when_the_bodies_differ():
    pb, a, b = _pb_with_a_record()
    real_view = pb.view

    def view(collection, record_id, token=None):
        resp = real_view(collection, record_id, token)
        if record_id != a.ids["campaigns"] and resp.status == 404:
            return Response(404, {"code": 404, "message": "Missing.", "data": {}}, 1)
        return resp

    pb.view = view
    r = families.view_foreign_or_missing(pb, "campaigns", a, b, 404)
    assert not r.passed and "same_body=False" in r.detail


def test_missing_record_ids_are_well_formed_and_fresh():
    ids = {families.missing_record_id() for _ in range(50)}
    assert len(ids) == 50 and all(re.fullmatch(r"[a-z0-9]{15}", i) for i in ids)


def test_replayed_denied_create_passes_when_every_copy_is_denied():
    pb = _ProbePB(create=Response(400, {"message": "Failed to create record.", "data": {}}, 1), listing=_count(0))
    r = families.create_replayed_denied(pb, "campaigns", "b-token", {"user": "uid-c"}, "admin", "uid-c", 400)
    assert r.passed and sum(1 for c in pb.calls if c[0] == "create") == 3


def test_replayed_denied_create_fails_when_a_later_copy_gets_through():
    responses = [Response(400, {"data": {}}, 1), Response(400, {"data": {}}, 1), Response(200, {"id": "x"}, 1)]

    class _Seq(_ProbePB):
        def create(self, collection, token, payload):
            self.calls.append(("create", collection, token, dict(payload)))
            return responses.pop(0)

    pb = _Seq(listing=_count(1))
    r = families.create_replayed_denied(pb, "campaigns", "b-token", {"user": "uid-c"}, "admin", "uid-c", 400)
    assert not r.passed and "statuses=[400, 400, 200]" in r.detail


def test_nonexistent_owner_denied_compares_status_and_rows_only():
    # A validation body (the named user does not exist) still passes: only the
    # status and the row count are compared; the body is a #13 exception.
    pb = _ProbePB(create=Response(400, {"data": {"user": {"code": "validation_missing_rel_records"}}}, 1),
                  listing=_count(0))
    assert families.create_nonexistent_owner_denied(pb, "campaigns", "b-token", {"user": "m"}, "admin", "m", 400).passed
    leaked = _ProbePB(create=Response(400, {"data": {}}, 1), listing=_count(1))
    assert not families.create_nonexistent_owner_denied(leaked, "campaigns", "b-token", {"user": "m"}, "admin", "m", 400).passed


class _FrontendPB:
    def __init__(self, resp):
        self.resp, self.calls = resp, []

    def post(self, path, body, token=None):
        self.calls.append((path, token))
        return self.resp


def test_degraded_runner_passes_only_on_the_typed_auth_unavailable():
    ok = _FrontendPB(Response(503, {"code": "auth_unavailable", "detail": "x", "correlation_id": "c"}, 1))
    r = families.runner_fails_closed_without_pocketbase(ok, "take_home_attempts", 503)
    assert r.passed and ok.calls[0][0] == "/api/take-home/submit"
    for bad in (Response(500, {"detail": "Internal Server Error"}, 1), Response(200, {"id": "x"}, 1),
                Response(503, {"code": "route_disabled"}, 1)):
        assert not families.runner_fails_closed_without_pocketbase(_FrontendPB(bad), "take_home_attempts", 503).passed


# --------------------------------------------------------------------------
# verdict: deployment checks and receipt shape
# --------------------------------------------------------------------------


DEPLOY_CHECK = "deployment.proxy.admin-ui.denied"


def _doc_with_deploy_check():
    d = minimal_doc()
    d["deployment_checks"] = {DEPLOY_CHECK: {"guarantee": "g"}}
    return d


def test_verdict_requires_a_passing_receipt_for_each_deployment_check(tmp_path):
    path = tmp_path / "r.jsonl"
    write_receipts(path, baseline_rows())
    assert run.run_verdict(_doc_with_deploy_check(), str(path)) == 1  # missing
    write_receipts(path, baseline_rows() + [receipt(DEPLOY_CHECK, "/_/", passed=False)])
    assert run.run_verdict(_doc_with_deploy_check(), str(path)) == 1  # failed
    write_receipts(path, baseline_rows() + [receipt(DEPLOY_CHECK, "/_/")])
    assert run.run_verdict(_doc_with_deploy_check(), str(path)) == 0


def test_verdict_fails_when_receipts_have_different_fields(tmp_path):
    path = tmp_path / "r.jsonl"
    odd = receipt(ENFORCED, "campaigns")
    odd["extra"] = "x"
    write_receipts(path, [odd, receipt(run.READBACK_PROBE, "campaigns")])
    assert run.run_verdict(minimal_doc(), str(path)) == 1


# --------------------------------------------------------------------------
# the committed policy: coverage per actor, operation, and resource state
# --------------------------------------------------------------------------


def test_every_collection_covers_each_actor_operation_and_resource_state():
    doc = policy.load(_default_policy_path())
    reads = {
        "account-scope.list.cross-account.isolated", "account-scope.list.anonymous.isolated",
        "account-scope.list.filter.isolated", "account-scope.view.cross-account.denied",
        "account-scope.view.anonymous.denied", "account-scope.view.foreign-or-missing.indistinguishable",
        "account-scope.delete.cross-account.denied", "account-scope.delete.anonymous.denied",
        "account-scope.delete.foreign-or-missing.indistinguishable",
    }
    owned_writes = {
        "account-scope.create.anonymous.denied", "account-scope.create.foreign-owner.denied",
        "account-scope.create.nonexistent-owner.denied", "account-scope.create.replayed-denied.denied",
        "account-scope.update.cross-account.denied", "account-scope.update.anonymous.denied",
        "account-scope.update.foreign-or-missing.indistinguishable", "account-scope.update.reassign-owner.denied",
        "account-scope.update.own.accepted",
    }
    server_only = {"account-scope.create.server-only.denied", "account-scope.update.server-only.denied",
                   "account-scope.create.superuser.accepted"}
    for name, row in doc["collections"].items():
        probes = set(row["probes"])
        assert reads <= probes, (name, sorted(reads - probes))
        if name == "resume_share_views":
            assert server_only <= probes, name
        elif name != "users":
            assert owned_writes <= probes, (name, sorted(owned_writes - probes))


def test_no_collection_keeps_the_old_any_signed_in_create_rule():
    doc = policy.load(_default_policy_path())
    for name, row in doc["collections"].items():
        assert row["current_rules"].get("create") != '@request.auth.id != ""', name


def test_open_exceptions_name_their_closing_leaf():
    doc = policy.load(_default_policy_path())
    ids = {e["id"] for e in doc["open_exceptions"]}
    assert {"timing", "error-shapes", "owner-id-create-shape"} <= ids
    assert all(e["closed_by"].startswith("ROUNDS-") for e in doc["open_exceptions"])
