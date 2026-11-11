"""Harness check for Share Capabilities (ROUNDS-00B-L03 stage 2).

One phase, ``share-capabilities``, on the real PocketBase with both runner
replicas and nginx up and signups still on:

- an owner lists their capabilities and revokes one through nginx and the
  runner: only their own rows, only the owner fields, the same answer
  again, and another account's capability answered like a missing one,
  with nothing changed;
- deleting a resume or a variant that has been shared succeeds, with an
  active capability and with only a revoked one: the active one is
  revoked, a revoked one stays as it was, and the snapshots stay;
- a resume delete that reaches a shared variant revokes that variant's
  capability too;
- PocketBase refuses to delete a snapshot a capability names, the
  superuser's delete included;
- the superuser can't move a capability to another snapshot or account,
  change its checksum, lengthen it, or reopen a revoked one;
- deleting an account with active and revoked capabilities succeeds and
  leaves none of its capabilities or snapshots.

The superuser seeds the snapshots and capabilities, through the same model
hooks and owner triggers every writer meets; nothing creates a capability
any other way until #12.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import os
import secrets
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import factory
from admission_check import Checks, account, admin_token, call, wait_up
from pbclient import PBClient

POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://pocketbase:8090")
RUNNER_URL = os.environ.get("RUNNER_URL", "http://runner:8000")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://frontend").rstrip("/")
ROUTE = "/api/share/capabilities"
OWNER_FIELDS = {"id", "status", "revoked_reason", "purpose", "expires_at", "created", "revoked_at"}
NOT_FOUND = {"detail": "Not found.", "code": "not_found"}
CAPS = "share_capabilities"
SNAPSHOTS = "legacy_artifact_snapshots"


class Seed:
    """The rows one check seeds for an account, by the superuser where only
    a hook may write."""

    def __init__(self, pb: PBClient, admin: str, acct: factory.Account) -> None:
        self.pb, self.admin, self.acct = pb, admin, acct

    def _made(self, resp, what: str) -> str:
        if resp.status != 200 or not isinstance(resp.body, dict) or not resp.body.get("id"):
            raise RuntimeError(f"{what} failed: status={resp.status} body={resp.body!r}")
        return resp.body["id"]

    def resume(self) -> str:
        return self._made(self.pb.create("resumes", self.acct.token, {
            "user": self.acct.user_id, "name": "shared resume", "slug": "shared-" + secrets.token_hex(4),
        }), "resume create")

    def variant(self, resume_id: str) -> str:
        return self._made(self.pb.create("resume_variants", self.acct.token, {
            "user": self.acct.user_id, "resume": resume_id, "name": "shared variant",
        }), "variant create")

    def snapshot(self, kind: str, source_id: str) -> str:
        fields = {"user": self.acct.user_id, **factory.snapshot_fields(source_id), "source_kind": kind}
        return self._made(self.pb.create_with_file(SNAPSHOTS, self.admin, fields, "markup", "snapshot.html",
                                                   factory.SNAPSHOT_MARKUP, "text/html"), "snapshot seed")

    def capability(self, snapshot_id: str) -> str:
        return self._made(self.pb.create(CAPS, self.admin, {"user": self.acct.user_id,
                                                            **factory.capability_fields(snapshot_id)}),
                          "capability seed")


def _row(pb: PBClient, admin: str, collection: str, record_id: str) -> dict[str, Any] | None:
    got = pb.view(collection, record_id, admin)
    return got.body if got.status == 200 and isinstance(got.body, dict) else None


def _count(pb: PBClient, admin: str, collection: str, user_id: str) -> int:
    resp = pb.listing(collection, admin, {"filter": f'user = "{user_id}"', "perPage": 1})
    return int((resp.body or {}).get("totalItems", -1)) if resp.status == 200 else -1


def _strip(body: Any) -> Any:
    return {k: v for k, v in body.items() if k != "correlation_id"} if isinstance(body, dict) else body


def _eventually(read: Callable[[], Any], ok: Callable[[Any], bool], tries: int = 20, delay: float = 0.25) -> Any:
    """``read()`` until ``ok`` accepts it, or the last answer."""
    got = read()
    for _ in range(tries):
        if ok(got):
            break
        time.sleep(delay)
        got = read()
    return got


def _revoke(token: str, capability_id: str) -> tuple[int, Any]:
    status, body, _ = call(FRONTEND_URL, "POST", f"{ROUTE}/{capability_id}/revoke", token, {})
    return status, body


def _state(row: dict[str, Any] | None) -> tuple:
    if row is None:
        return ("gone",)
    return (row.get("status"), row.get("revoked_reason"), row.get("capability_version"))


def _wait_routed() -> None:
    if not wait_up(RUNNER_URL):
        raise RuntimeError("the share capability phase needs the runner up")
    frontend = PBClient(FRONTEND_URL)
    frontend.wait_healthy()
    frontend.wait_for(ROUTE, lambda r: r.status == 401 and isinstance(r.body, dict)
                      and r.body.get("code") == "unauthenticated")


def run_owner_routes(c: Checks, pb: PBClient, admin: str, a: factory.Account, b: factory.Account) -> None:
    sa, sb = Seed(pb, admin, a), Seed(pb, admin, b)
    cap_a = sa.capability(sa.snapshot("resume", sa.resume()))
    cap_b = sb.capability(sb.snapshot("resume", sb.resume()))

    listed = {name: call(FRONTEND_URL, "GET", ROUTE, acct.token)[:2] for name, acct in (("a", a), ("b", b))}
    c.check("share.capability.list.owner-only-owner-fields",
            all(status == 200 and isinstance(body, list) for status, body in listed.values())
            and [i.get("id") for i in listed["a"][1]] == [cap_a] and [i.get("id") for i in listed["b"][1]] == [cap_b]
            and all(set(i) == OWNER_FIELDS for _, body in listed.values() for i in body),
            " ".join(f"{k}={v[0]}" for k, v in listed.items()))

    first, again = _revoke(a.token, cap_a), _revoke(a.token, cap_a)
    row = _row(pb, admin, CAPS, cap_a)
    c.check("share.capability.revoke.once-and-again-the-same",
            first[0] == 200 and again[0] == 200 and first[1] == again[1]
            and (first[1] or {}).get("status") == "revoked" and (first[1] or {}).get("revoked_reason") == "owner"
            and _state(row) == ("revoked", "owner", 2),
            f"first={first[0]} again={again[0]} same={first[1] == again[1]} row={_state(row)}")

    before = _row(pb, admin, CAPS, cap_b)
    foreign = _revoke(a.token, cap_b)
    missing = _revoke(a.token, "z" * 15)
    after = _row(pb, admin, CAPS, cap_b)
    c.check("share.capability.revoke.another-accounts-like-a-missing-one",
            foreign[0] == missing[0] == 404 and _strip(foreign[1]) == _strip(missing[1]) == NOT_FOUND
            and before is not None and before == after,
            f"foreign={foreign[0]} missing={missing[0]} unchanged={before == after}")


def run_source_deletes(c: Checks, pb: PBClient, admin: str, a: factory.Account) -> str:
    """The resume and variant deletes; answers a snapshot a revoked
    capability still names, for the snapshot check."""
    s = Seed(pb, admin, a)

    def case(name: str, delete: tuple[str, str], snapshot: str, capability: str, want: tuple,
             also_gone: tuple[str, str] | None = None) -> None:
        deleted = pb.delete(delete[0], delete[1], a.token)
        row = _eventually(lambda: _row(pb, admin, CAPS, capability), lambda r: _state(r) == want)
        kept = _row(pb, admin, SNAPSHOTS, snapshot) is not None
        gone = also_gone is None or _row(pb, admin, also_gone[0], also_gone[1]) is None
        c.check(f"share.capability.source-delete.{name}",
                deleted.status == 204 and _state(row) == want and kept and gone,
                f"delete={deleted.status} capability={_state(row)} snapshot-kept={kept} cascade={gone}")

    # A resume with an active capability: revoked, snapshot kept.
    r1 = s.resume()
    s1 = s.snapshot("resume", r1)
    case("resume-with-an-active-capability", ("resumes", r1), s1, s.capability(s1), ("revoked", "source_deleted", 2))

    # A resume with only a revoked capability: left as it was.
    r2 = s.resume()
    s2 = s.snapshot("resume", r2)
    c2 = s.capability(s2)
    _revoke(a.token, c2)
    case("resume-with-a-revoked-capability", ("resumes", r2), s2, c2, ("revoked", "owner", 2))

    # A resume delete that reaches its shared variant.
    r3 = s.resume()
    v3 = s.variant(r3)
    s3 = s.snapshot("variant", v3)
    case("resume-reaching-a-shared-variant", ("resumes", r3), s3, s.capability(s3), ("revoked", "source_deleted", 2),
         also_gone=("resume_variants", v3))

    # A variant deleted on its own, with an active and with a revoked capability.
    r4 = s.resume()
    v4 = s.variant(r4)
    s4 = s.snapshot("variant", v4)
    case("variant-with-an-active-capability", ("resume_variants", v4), s4, s.capability(s4),
         ("revoked", "source_deleted", 2))
    v5 = s.variant(r4)
    s5 = s.snapshot("variant", v5)
    c5 = s.capability(s5)
    _revoke(a.token, c5)
    case("variant-with-a-revoked-capability", ("resume_variants", v5), s5, c5, ("revoked", "owner", 2))
    c.check("share.capability.source-delete.the-parent-resume-stays", _row(pb, admin, "resumes", r4) is not None)
    return s2


def run_snapshot_guard(c: Checks, pb: PBClient, admin: str, snapshot: str) -> None:
    refused = pb.delete(SNAPSHOTS, snapshot, admin)
    c.check("share.capability.named-snapshot-delete.refused",
            refused.status == 400 and _row(pb, admin, SNAPSHOTS, snapshot) is not None,
            f"delete={refused.status}")


def run_superuser_changes(c: Checks, pb: PBClient, admin: str, a: factory.Account, b: factory.Account) -> None:
    sb = Seed(pb, admin, b)
    resume = sb.resume()
    snapshot = sb.snapshot("resume", resume)
    other = sb.snapshot("variant", sb.variant(resume))
    active = sb.capability(snapshot)
    revoked = sb.capability(snapshot)
    _revoke(b.token, revoked)
    longer = (datetime.now(timezone.utc) + timedelta(days=200)).strftime("%Y-%m-%d %H:%M:%S.000Z")
    changes = {
        "another-snapshot": (active, {"snapshot": other}),
        "another-account": (active, {"user": a.user_id}),
        "another-checksum": (active, {"target_checksum": "sha256:" + "0" * 64}),
        "a-later-expiry": (active, {"expires_at": longer}),
        "a-reopen": (revoked, {"status": "active", "revoked_reason": "", "revoked_at": "",
                               "capability_version": 3}),
    }
    before = {cid: _row(pb, admin, CAPS, cid) for cid in (active, revoked)}
    answers = {name: pb.update(CAPS, cid, change, admin).status for name, (cid, change) in changes.items()}
    after = {cid: _row(pb, admin, CAPS, cid) for cid in (active, revoked)}
    # The model hook refuses with 400; a move to another account meets #10's
    # relation check first, which answers like a missing record.
    c.check("share.capability.superuser-change.refused",
            all(400 <= status < 500 for status in answers.values()) and before == after and None not in after.values(),
            " ".join(f"{k}={v}" for k, v in answers.items()) + f" unchanged={before == after}")


def run_account_delete(c: Checks, pb: PBClient, admin: str) -> None:
    d = account(pb, "share-delete")
    s = Seed(pb, admin, d)
    snapshot = s.snapshot("resume", s.resume())
    s.capability(snapshot)
    _revoke(d.token, s.capability(snapshot))
    held = (_count(pb, admin, CAPS, d.user_id), _count(pb, admin, SNAPSHOTS, d.user_id))
    deleted = pb.delete("users", d.user_id, d.token)
    left = (_count(pb, admin, CAPS, d.user_id), _count(pb, admin, SNAPSHOTS, d.user_id))
    c.check("share.capability.account-delete.leaves-nothing",
            held == (2, 1) and deleted.status == 204 and left == (0, 0) and _row(pb, admin, "users", d.user_id) is None,
            f"held={held} delete={deleted.status} left={left}")


def main() -> int:
    c = Checks()
    pb = PBClient(POCKETBASE_URL)
    pb.wait_healthy()
    _wait_routed()
    admin = admin_token(pb)
    a, b = account(pb, "share-a"), account(pb, "share-b")
    run_owner_routes(c, pb, admin, a, b)
    named = run_source_deletes(c, pb, admin, a)
    run_snapshot_guard(c, pb, admin, named)
    run_superuser_changes(c, pb, admin, a, b)
    run_account_delete(c, pb, admin)
    print(f"share-capabilities: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main())
