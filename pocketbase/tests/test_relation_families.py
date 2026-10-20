"""Unit tests for the typed-relation harness families (ROUNDS-00B-L02).

These drive the five relation endpoint family functions in
``harness/probes/families.py`` with fake PocketBase clients, the same way
``test_account_scope_harness.py`` drives the stage-3/4 families. They pin the
pass/fail contract each family enforces:

  * a create or update that points a typed relation at a foreign target is a
    clean rule-shaped denial (the deny-contract status, empty ``data``) that
    leaves the owner's rows untouched;
  * a foreign target and a nonexistent target are denied with the same status
    and the same parsed body, so the answer never reveals the target exists;
  * an empty ``relation_endpoints`` list fails the probe rather than passing
    vacuously, so a collection that should declare endpoints cannot go dark.

The predicate's own decision logic is covered against the real hook module in
``test_relation_endpoints_hooks.py``; here the PocketBase client is faked.
"""
from __future__ import annotations

import sys
from pathlib import Path

PROBES = Path(__file__).resolve().parents[1].parent / "harness" / "probes"
if str(PROBES) not in sys.path:
    sys.path.insert(0, str(PROBES))

import factory  # noqa: E402
import families  # noqa: E402
from pbclient import Response  # noqa: E402

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

CONTENT = {"round": "round-id", "assignment": "assignment-id"}
NOT_FOUND = {"code": 404, "message": "The requested resource wasn't found.", "data": {}}
DENIED = {"code": 400, "message": "Failed to create record.", "data": {}}
TODO_EP = [{"field": "campaign", "target": "campaigns"}]
VARIANT_EP = [{"field": "application", "target": "applications"},
              {"field": "resume", "target": "resumes"}]


def _acct(tag: str) -> "factory.Account":
    a = factory.Account(tag=tag, email=f"{tag}@x", password="pw")
    a.user_id = f"uid-{tag}"
    a.token = f"{tag}-token"
    for c in STANDARD_COLLECTIONS:
        a.ids[c] = f"{tag}-{c}-id"
    a.ids["users"] = a.user_id
    return a


def _accounts():
    return _acct("a"), _acct("b")


# --------------------------------------------------------------------------
# create families
# --------------------------------------------------------------------------


class _RelCreatePB:
    """Answers create with a fixed (or sequenced) response; the superuser
    owner-count listing returns ``owner_rows`` (an int, or a list consumed in
    order to model a before/after change)."""

    def __init__(self, create, owner_rows=0):
        self._create = create
        self._owner_rows = owner_rows
        self.calls: list[tuple] = []

    def create(self, collection, token, payload):
        self.calls.append(("create", collection, token, dict(payload)))
        if isinstance(self._create, list):
            return self._create.pop(0)
        return self._create

    def listing(self, collection, token=None, params=None):
        self.calls.append(("listing", collection, token, params))
        total = self._owner_rows.pop(0) if isinstance(self._owner_rows, list) else self._owner_rows
        return Response(200, {"items": [], "totalItems": total}, 1)


def test_create_relation_foreign_denied_passes_on_a_clean_rule_denial():
    a, b = _accounts()
    pb = _RelCreatePB(Response(400, dict(DENIED), 1), owner_rows=0)
    r = families.create_relation_foreign_denied(pb, "todos", TODO_EP, b, a, CONTENT, "admin", 400)
    assert r.passed and r.detail == ""
    # The create is the caller's own token, and the relation points at a's row.
    create = next(c for c in pb.calls if c[0] == "create")
    assert create[1:3] == ("todos", "b-token")
    assert create[3]["campaign"] == a.ids["campaigns"]
    assert create[3]["user"] == b.user_id


def test_create_relation_foreign_denied_fails_when_the_row_was_created():
    a, b = _accounts()
    pb = _RelCreatePB(Response(200, {"id": "new"}, 1), owner_rows=[0, 1])
    r = families.create_relation_foreign_denied(pb, "todos", TODO_EP, b, a, CONTENT, "admin", 400)
    assert not r.passed and "status=200" in r.detail and "rows=0->1" in r.detail


def test_create_relation_foreign_denied_fails_on_a_validation_body():
    # A populated `data` means a field check fired, not the endpoint predicate.
    a, b = _accounts()
    pb = _RelCreatePB(Response(400, {"data": {"campaign": {"code": "validation_required"}}}, 1))
    r = families.create_relation_foreign_denied(pb, "todos", TODO_EP, b, a, CONTENT, "admin", 400)
    assert not r.passed and "campaign" in r.detail


def test_create_relation_foreign_denied_fails_on_empty_endpoints():
    a, b = _accounts()
    pb = _RelCreatePB(Response(400, dict(DENIED), 1))
    r = families.create_relation_foreign_denied(pb, "question_timers", [], b, a, CONTENT, "admin", 400)
    assert not r.passed and "no relation endpoints" in r.detail
    # With nothing to point, the family must not have touched the API.
    assert pb.calls == []


def test_create_relation_foreign_denied_checks_every_endpoint():
    a, b = _accounts()
    # The first endpoint is denied cleanly, the second leaks through.
    pb = _RelCreatePB([Response(400, dict(DENIED), 1), Response(200, {"id": "new"}, 1)],
                      owner_rows=[0, 0, 0, 1])
    r = families.create_relation_foreign_denied(pb, "resume_variants", VARIANT_EP, b, a, CONTENT, "admin", 400)
    assert not r.passed and "field=resume" in r.detail and "field=application" not in r.detail


def test_create_relation_superuser_denied_uses_the_admin_token():
    a, b = _accounts()
    pb = _RelCreatePB(Response(400, dict(DENIED), 1), owner_rows=0)
    r = families.create_relation_superuser_denied(pb, "todos", TODO_EP, a, b, CONTENT, "admin", 400)
    assert r.passed and r.actor == "superuser"
    create = next(c for c in pb.calls if c[0] == "create")
    # The admin creates an a-owned row pointing at b's record.
    assert create[2] == "admin"
    assert create[3]["user"] == a.user_id and create[3]["campaign"] == b.ids["campaigns"]


def test_create_relation_indistinguishable_passes_when_foreign_and_missing_match():
    a, b = _accounts()
    pb = _RelCreatePB([Response(400, dict(DENIED), 1), Response(400, dict(DENIED), 1)])
    r = families.create_relation_foreign_or_missing_indistinguishable(pb, "todos", TODO_EP, b, a, CONTENT, 400)
    assert r.passed and r.detail == ""


def test_create_relation_indistinguishable_fails_when_bodies_differ():
    a, b = _accounts()
    # Same status, but the foreign answer carries a different body than missing.
    pb = _RelCreatePB([Response(400, {"code": 400, "message": "Foreign.", "data": {}}, 1),
                       Response(400, dict(DENIED), 1)])
    r = families.create_relation_foreign_or_missing_indistinguishable(pb, "todos", TODO_EP, b, a, CONTENT, 400)
    assert not r.passed and "same_body=False" in r.detail


def test_create_relation_indistinguishable_fails_on_the_wrong_status():
    a, b = _accounts()
    pb = _RelCreatePB([Response(200, {"id": "x"}, 1), Response(200, {"id": "y"}, 1)])
    r = families.create_relation_foreign_or_missing_indistinguishable(pb, "todos", TODO_EP, b, a, CONTENT, 400)
    assert not r.passed and "foreign=200" in r.detail


# --------------------------------------------------------------------------
# update families
# --------------------------------------------------------------------------


class _RelUpdatePB:
    """A one-row fake: ``view`` reports the current body, ``update`` returns a
    fixed (or sequenced) response and, when ``mutate`` is set, a successful
    update changes what ``view`` reports afterwards."""

    def __init__(self, row: dict, update, mutate: bool = False):
        self._row = dict(row)
        self._update = update
        self._mutate = mutate
        self.calls: list[tuple] = []

    def view(self, collection, record_id, token=None):
        self.calls.append(("view", collection, record_id, token))
        return Response(200, dict(self._row), 1)

    def update(self, collection, record_id, payload, token=None):
        self.calls.append(("update", collection, record_id, token, dict(payload)))
        resp = self._update.pop(0) if isinstance(self._update, list) else self._update
        if resp.status == 200 and self._mutate:
            self._row.update(payload)
        return resp


def _todo_row(a):
    return {"id": a.ids["todos"], "user": a.user_id, "campaign": a.ids["campaigns"]}


def test_update_relation_foreign_denied_passes_on_not_found_and_unchanged():
    a, b = _accounts()
    pb = _RelUpdatePB(_todo_row(b), Response(404, dict(NOT_FOUND), 1))
    r = families.update_relation_foreign_denied(pb, "todos", TODO_EP, b, a, 404)
    assert r.passed and r.detail == ""
    upd = next(c for c in pb.calls if c[0] == "update")
    assert upd[3] == "b-token" and upd[4] == {"campaign": a.ids["campaigns"]}


def test_update_relation_foreign_denied_fails_when_the_repoint_went_through():
    a, b = _accounts()
    pb = _RelUpdatePB(_todo_row(b), Response(200, {"id": "x"}, 1), mutate=True)
    r = families.update_relation_foreign_denied(pb, "todos", TODO_EP, b, a, 404)
    assert not r.passed and "unchanged=False" in r.detail


def test_update_relation_foreign_denied_fails_on_a_validation_body():
    a, b = _accounts()
    pb = _RelUpdatePB(_todo_row(b), Response(404, {"code": 404, "message": "x", "data": {"campaign": {}}}, 1))
    r = families.update_relation_foreign_denied(pb, "todos", TODO_EP, b, a, 404)
    assert not r.passed and "data=['campaign']" in r.detail


def test_update_relation_foreign_denied_fails_on_empty_endpoints():
    a, b = _accounts()
    pb = _RelUpdatePB(_todo_row(b), Response(404, dict(NOT_FOUND), 1))
    r = families.update_relation_foreign_denied(pb, "question_timers", [], b, a, 404)
    assert not r.passed and "no relation endpoints" in r.detail
    assert pb.calls == []


def test_update_relation_indistinguishable_passes_when_foreign_and_missing_match():
    a, b = _accounts()
    pb = _RelUpdatePB(_todo_row(b), [Response(404, dict(NOT_FOUND), 1), Response(404, dict(NOT_FOUND), 1)])
    r = families.update_relation_foreign_or_missing_indistinguishable(pb, "todos", TODO_EP, b, a, 404)
    assert r.passed and r.detail == ""


def test_update_relation_indistinguishable_fails_when_bodies_differ():
    a, b = _accounts()
    pb = _RelUpdatePB(_todo_row(b),
                      [Response(404, {"code": 404, "message": "Foreign.", "data": {}}, 1),
                       Response(404, dict(NOT_FOUND), 1)])
    r = families.update_relation_foreign_or_missing_indistinguishable(pb, "todos", TODO_EP, b, a, 404)
    assert not r.passed and "same_body=False" in r.detail
