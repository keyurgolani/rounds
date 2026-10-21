"""Harness check for the demo account's containment (ROUNDS-00B-L07 stage 1).

Two phases on the real PocketBase:

- ``demo-on``: PocketBase runs with ``ROUNDS_ENABLE_DEMO=true``, as a
  hosted demo does, with the runner up. The seeded demo account signs in,
  and so does a demo account a superuser makes. That caller changes its
  profile but not its password, email, username, or verification, can't
  delete itself or ask for an email change, and can't create a share link,
  an AI provider, or AI settings, through PocketBase or the runner, while a
  standard account still can. It saves that account and its token to
  ``/state`` for the next phase.
- ``demo-off``: after PocketBase restarts with the demo gate at its
  default, both demo accounts' sign-ins get the answer a wrong password
  gets, the token from before the restart is refused, and a standard
  account still signs in.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
from pathlib import Path

import factory
from admission_check import Checks, admin_token, call
from pbclient import PBClient

POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://pocketbase:8090")
RUNNER_URL = os.environ.get("RUNNER_URL", "http://runner:8000")
STATE = Path(os.environ.get("DEMO_STATE_PATH", "/state/demo.json"))
NOT_PERMITTED = {"code": "demo_not_permitted", "message": "Not available in the demo."}


def _wrong_password() -> str:
    return "Wrong" + secrets.token_hex(12) + "!1"


def _not_permitted(status: int, body) -> bool:
    return status == 403 and ((body or {}).get("data") or {}).get("demo") == NOT_PERMITTED


def _count(pb: PBClient, admin: str, collection: str, user_id: str) -> int:
    resp = pb.listing(collection, admin, {"filter": f'user = "{user_id}"', "perPage": 1})
    return int((resp.body or {}).get("totalItems", -1)) if resp.status == 200 else -1


def _standard(pb: PBClient, admin: str) -> factory.Account:
    """A standard account a superuser makes, since signups may be off."""
    acct = factory.make_account("standard")
    created = pb.create("users", admin, {"email": acct.email, "password": acct.password,
                                         "passwordConfirm": acct.password})
    if created.status != 200:
        raise RuntimeError(f"standard account create failed: status={created.status}")
    acct.user_id = created.body["id"]
    return acct


def _demo(pb: PBClient, admin: str) -> factory.Account:
    acct = factory.make_account("demo")
    created = pb.create("users", admin, {"email": acct.email, "password": acct.password,
                                         "passwordConfirm": acct.password, "is_demo": True})
    if created.status != 200:
        raise RuntimeError(f"demo account create failed: status={created.status}")
    acct.user_id = created.body["id"]
    return acct


def run_on(c: Checks, pb: PBClient, admin: str) -> None:
    seeded = pb.auth_password(factory._DEMO_EMAIL, factory._DEMO_PASSWORD)
    c.check("demo.on.the-seeded-demo-account-signs-in", seeded.status == 200, f"status={seeded.status}")
    d = _demo(pb, admin)
    signed = pb.auth_password(d.email, d.password)
    d.token = (signed.body or {}).get("token", "")
    c.check("demo.on.a-demo-account-signs-in", signed.status == 200 and bool(d.token), f"status={signed.status}")

    # The account's own record: its profile changes, nothing else does.
    profile = pb.update("users", d.user_id, {"name": "Visitor", "bio": "Trying it", "target": "Staff"}, d.token)
    c.check("demo.on.the-profile-changes", profile.status == 200 and (profile.body or {}).get("name") == "Visitor",
            f"status={profile.status}")
    new_password = factory.make_account("demo").password
    refused = {
        "password": pb.update("users", d.user_id, {"oldPassword": d.password, "password": new_password,
                                                   "passwordConfirm": new_password}, d.token),
        "email": pb.update("users", d.user_id, {"email": factory.make_account("other").email}, d.token),
        "username": pb.update("users", d.user_id, {"username": "visitor" + secrets.token_hex(4)}, d.token),
        "verified": pb.update("users", d.user_id, {"verified": False}, d.token),
        "delete": pb.delete("users", d.user_id, d.token),
    }
    email_change = call(POCKETBASE_URL, "POST", "/api/collections/users/request-email-change", d.token,
                        {"newEmail": factory.make_account("other").email})
    still = pb.auth_password(d.email, d.password)
    c.check("demo.on.the-account-fields-and-the-account-stay",
            all(_not_permitted(r.status, r.body) for r in refused.values())
            and _not_permitted(email_change[0], email_change[1]) and still.status == 200,
            " ".join(f"{k}={r.status}" for k, r in refused.items()) + f" email-change={email_change[0]}"
            f" sign-in={still.status}")

    # What a demo account may not own, through PocketBase and the runner.
    resume = pb.create("resumes", d.token, {"user": d.user_id, "name": "demo resume", "slug": "demo-" + secrets.token_hex(4)})
    resume_id = (resume.body or {}).get("id", "")
    direct = {
        "resume_share_links": pb.create("resume_share_links", d.token, {"user": d.user_id, "resume": resume_id,
                                                                        "token": secrets.token_urlsafe(16)}),
        "ai_providers": pb.create("ai_providers", d.token, {"user": d.user_id, "kind": "openai", "label": "demo"}),
        "ai_settings": pb.create("ai_settings", d.token, {"user": d.user_id}),
    }
    c.check("demo.on.no-share-link-provider-or-settings-row-through-pocketbase",
            resume.status == 200 and all(_not_permitted(r.status, r.body) for r in direct.values()),
            f"resume={resume.status} " + " ".join(f"{k}={r.status}" for k, r in direct.items()))
    through = {
        "share": call(RUNNER_URL, "POST", "/api/share", d.token, {"resume_id": resume_id})[0],
        "provider": call(RUNNER_URL, "POST", "/api/ai/providers", d.token,
                         {"kind": "openai", "label": "demo", "key": "harness-key-not-a-secret"})[0],
        "settings": call(RUNNER_URL, "PUT", "/api/ai/settings", d.token, {"text_model": "harness-model"})[0],
    }
    left = {name: _count(pb, admin, name, d.user_id) for name in direct}
    c.check("demo.on.no-share-link-provider-or-settings-row-through-the-runner",
            all(status == 403 for status in through.values()) and all(n == 0 for n in left.values()),
            " ".join(f"{k}={v}" for k, v in through.items()) + f" rows={left}")

    # A standard account is held to none of it.
    s = _standard(pb, admin)
    s.token = (pb.auth_password(s.email, s.password).body or {}).get("token", "")
    own = pb.create("ai_settings", s.token, {"user": s.user_id})
    moved = pb.update("users", s.user_id, {"oldPassword": s.password, "password": new_password,
                                           "passwordConfirm": new_password}, s.token)
    c.check("demo.on.a-standard-account-is-held-to-none-of-it", own.status == 200 and moved.status == 200,
            f"settings={own.status} password={moved.status}")

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"email": d.email, "password": d.password, "token": d.token, "id": d.user_id}))


def run_off(c: Checks, pb: PBClient, admin: str) -> None:
    saved = json.loads(STATE.read_text())
    accounts = {"seeded": (factory._DEMO_EMAIL, factory._DEMO_PASSWORD), "made": (saved["email"], saved["password"])}
    for name, (email, password) in accounts.items():
        right = pb.auth_password(email, password)
        wrong = pb.auth_password(email, _wrong_password())
        c.check(f"demo.off.the-{name}-demo-account-fails-as-a-wrong-password",
                right.status == 400 and (right.status, right.body) == (wrong.status, wrong.body),
                f"status={right.status} same-as-wrong={(right.status, right.body) == (wrong.status, wrong.body)}")
    refreshed = call(POCKETBASE_URL, "POST", "/api/collections/users/auth-refresh", saved["token"])
    c.check("demo.off.a-token-from-before-the-start-is-refused", refreshed[0] == 401, f"status={refreshed[0]}")
    s = _standard(pb, admin)
    signed = pb.auth_password(s.email, s.password)
    c.check("demo.off.a-standard-account-signs-in", signed.status == 200, f"status={signed.status}")


def main(phase: str) -> int:
    c = Checks()
    pb = PBClient(POCKETBASE_URL)
    pb.wait_healthy()
    admin = admin_token(pb)
    (run_on if phase == "demo-on" else run_off)(c, pb, admin)
    print(f"{phase}: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "demo-on"))
