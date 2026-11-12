"""Harness check for the demo account's containment (ROUNDS-00B-L07 stage 1).

Two phases on the real PocketBase:

- ``demo-on``: PocketBase runs with ``ROUNDS_ENABLE_DEMO=true``, as a
  hosted demo does, with the runner up. The seeded demo account signs in,
  and so does a demo account a superuser makes. That caller changes its
  profile but not its password, email, username, or verification, can't
  delete itself or ask for an email change, and can't create a share link,
  an AI provider, or AI settings, through PocketBase or the runner, while a
  standard account still can. With the runners at
  ``ROUNDS_GATE_DEMO_EXECUTION``'s default since phase 3c, the deployment
  verifier's demo check passes through nginx: the seeded demo account's
  code run is refused before anything runs (ROUNDS-00B-L07). It saves that
  account and its token to ``/state`` for the next phase.
- ``demo-off``: after PocketBase restarts with the demo gate at its
  default, both demo accounts' sign-ins get the answer a wrong password
  gets, and so does a demo account whose password a superuser has just
  set, so the sign-in refusal holds without the boot lock. The token from
  before the restart is refused, and so is a token the boot lock never
  rotated: a standard account's from the earlier phase, after a superuser
  makes it a demo account. Nothing answers under ``/api/rounds/demo/`` but
  what an unknown route gets, and a standard account still signs in.

Prints one PASS/FAIL line per check and exits non-zero on any failure.
"""
from __future__ import annotations

import json
import os
import secrets
import sys
from pathlib import Path

import factory
import verify_deployment as vd
from admission_check import Checks, admin_token, call, uuid7
from pbclient import PBClient

POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://pocketbase:8090")
RUNNER_URL = os.environ.get("RUNNER_URL", "http://runner:8000")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://frontend").rstrip("/")
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
    locked = ("email", "username", "verified", "is_demo")
    before = {k: (pb.view("users", d.user_id, admin).body or {}).get(k) for k in locked}
    refused = {
        "password-change": pb.update("users", d.user_id, {"oldPassword": d.password, "password": new_password,
                                                   "passwordConfirm": new_password}, d.token),
        "email": pb.update("users", d.user_id, {"email": factory.make_account("other").email}, d.token),
        "username": pb.update("users", d.user_id, {"username": "visitor" + secrets.token_hex(4)}, d.token),
        "verified": pb.update("users", d.user_id, {"verified": False}, d.token),
        "delete": pb.delete("users", d.user_id, d.token),
    }
    email_change = call(POCKETBASE_URL, "POST", "/api/collections/users/request-email-change", d.token,
                        {"newEmail": factory.make_account("other").email})
    still = pb.auth_password(d.email, d.password)
    after = {k: (pb.view("users", d.user_id, admin).body or {}).get(k) for k in locked}
    # PocketBase itself refuses a record email change by anyone but a
    # superuser (400) before the demo hook sees it; every other refusal is
    # the demo hook's.
    c.check("demo.on.the-account-fields-and-the-account-stay",
            all(_not_permitted(r.status, r.body) for k, r in refused.items() if k != "email")
            and refused["email"].status in (400, 403)
            and _not_permitted(email_change[0], email_change[1]) and still.status == 200 and after == before,
            " ".join(f"{k}={r.status}" for k, r in refused.items()) + f" email-change={email_change[0]}"
            f" sign-in={still.status} unchanged={after == before}")

    # What a demo account may not own, through PocketBase and the runner.
    resume = pb.create("resumes", d.token, {"user": d.user_id, "name": "demo resume", "slug": "demo-" + secrets.token_hex(4)})
    resume_id = (resume.body or {}).get("id", "")
    direct = {
        "resume_share_links": pb.create("resume_share_links", d.token, {"user": d.user_id, "resume": resume_id}),
        "ai_providers": pb.create("ai_providers", d.token, {"user": d.user_id, "kind": "openai", "label": "demo"}),
        "ai_settings": pb.create("ai_settings", d.token, {"user": d.user_id}),
    }
    # Since ROUNDS-00B-L06 no client creates a share link row, so PocketBase
    # refuses the demo account's before the demo hook sees it; the other two
    # are the demo hook's own refusal.
    link = direct.pop("resume_share_links")
    c.check("demo.on.no-share-link-provider-or-settings-row-through-pocketbase",
            resume.status == 200 and link.status in (400, 403)
            and all(_not_permitted(r.status, r.body) for r in direct.values()),
            f"resume={resume.status} resume_share_links={link.status} "
            + " ".join(f"{k}={r.status}" for k, r in direct.items()))
    direct["resume_share_links"] = link
    # A share link is CreateShare (ROUNDS-00B-L04), which makes none for a
    # demo account, whatever it answers; the no-row counts below hold it.
    share = call(RUNNER_URL, "POST", "/api/share", d.token, {"resume_id": resume_id}, {"Idempotency-Key": uuid7()})[:2]
    through = {
        "provider": call(RUNNER_URL, "POST", "/api/ai/providers", d.token,
                         {"kind": "openai", "label": "demo", "key": "harness-key-not-a-secret"})[:2],
        "settings": call(RUNNER_URL, "PUT", "/api/ai/settings", d.token, {"text_model": "harness-model"})[:2],
    }
    left = {name: _count(pb, admin, name, d.user_id) for name in [*direct, "share_capabilities"]}
    # The runner passes PocketBase's refusal on, code included.
    c.check("demo.on.no-share-link-provider-or-settings-row-through-the-runner",
            all(status == 403 and NOT_PERMITTED["code"] in json.dumps(body) for status, body in through.values())
            and share[0] != 201 and "token" not in json.dumps(share[1] or {})
            and all(n == 0 for n in left.values()),
            f"share={share[0]} " + " ".join(f"{k}={v[0]}" for k, v in through.items()) + f" rows={left}")

    # The demo's code runs, at their default since phase 3c: the deployment
    # verifier's own check, through nginx as an operator runs it.
    code_run = vd.check_demo_code_runs(FRONTEND_URL)
    c.check("demo.on.the-demo-accounts-code-run-is-refused-through-nginx", code_run.passed, code_run.detail)

    # A standard account is held to none of it.
    s = _standard(pb, admin)
    s.token = (pb.auth_password(s.email, s.password).body or {}).get("token", "")
    own = pb.create("ai_settings", s.token, {"user": s.user_id})
    moved = pb.update("users", s.user_id, {"oldPassword": s.password, "password": new_password,
                                           "passwordConfirm": new_password}, s.token)
    c.check("demo.on.a-standard-account-is-held-to-none-of-it", own.status == 200 and moved.status == 200,
            f"settings={own.status} password-change={moved.status}")

    # A standard account and its token, which the next phase makes a demo
    # account after the restart, so the boot lock never rotates it.
    f = _standard(pb, admin)
    f.token = (pb.auth_password(f.email, f.password).body or {}).get("token", "")

    # Signups are off in the next phase, so it signs in with these.
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({"email": d.email, "password": d.password, "token": d.token, "id": d.user_id,
                                 "standard": {"email": s.email, "password": new_password},
                                 "flipped": {"id": f.user_id, "token": f.token}}))


def run_off(c: Checks, pb: PBClient, admin: str) -> None:
    saved = json.loads(STATE.read_text())
    accounts = {"seeded": (factory._DEMO_EMAIL, factory._DEMO_PASSWORD), "made": (saved["email"], saved["password"])}
    for name, (email, password) in accounts.items():
        right = pb.auth_password(email, password)
        wrong = pb.auth_password(email, _wrong_password())
        c.check(f"demo.off.the-{name}-demo-account-fails-as-a-wrong-password",
                right.status == 400 and (right.status, right.body) == (wrong.status, wrong.body),
                f"status={right.status} same-as-wrong={(right.status, right.body) == (wrong.status, wrong.body)}")
    # A password a superuser sets now, after the boot lock ran: only the
    # sign-in refusal stands between it and a session.
    known = factory.make_account("demo").password
    reset = pb.update("users", saved["id"], {"password": known, "passwordConfirm": known}, admin)
    right = pb.auth_password(saved["email"], known)
    wrong = pb.auth_password(saved["email"], _wrong_password())
    c.check("demo.off.a-just-set-demo-password-fails-as-a-wrong-password",
            reset.status == 200 and right.status == 400 and (right.status, right.body) == (wrong.status, wrong.body),
            f"reset={reset.status} status={right.status}"
            f" same-as-wrong={(right.status, right.body) == (wrong.status, wrong.body)}")
    refreshed = call(POCKETBASE_URL, "POST", "/api/collections/users/auth-refresh", saved["token"])
    c.check("demo.off.a-token-from-before-the-start-is-refused", refreshed[0] == 401, f"status={refreshed[0]}")
    # A live token the boot lock never rotated, once its account is a demo
    # account: refused on refresh and on any other request.
    flipped = saved["flipped"]
    before = call(POCKETBASE_URL, "GET", "/api/collections/todos/records", flipped["token"])[0]
    made_demo = pb.update("users", flipped["id"], {"is_demo": True}, admin)
    after = {
        "refresh": call(POCKETBASE_URL, "POST", "/api/collections/users/auth-refresh", flipped["token"])[0],
        "list": call(POCKETBASE_URL, "GET", "/api/collections/todos/records", flipped["token"])[0],
    }
    c.check("demo.off.a-demo-token-the-lock-missed-holds-no-session",
            before == 200 and made_demo.status == 200 and after["refresh"] == 401 and after["list"] == 401,
            f"before={before} made-demo={made_demo.status} " + " ".join(f"{k}={v}" for k, v in after.items()))
    # Each demo route answers as a route that doesn't exist does.
    unknown = "/api/rounds/no-such-route-" + secrets.token_hex(4)
    routes = {
        "status": ("GET", "/api/rounds/demo", None, None),
        "start": ("POST", "/api/rounds/demo/sessions", None, {}),
        "end": ("POST", "/api/rounds/demo/sessions/end", saved["token"], {}),
    }
    answers = {name: (call(POCKETBASE_URL, method, path, token, body)[0],
                      call(POCKETBASE_URL, method, unknown, token, body)[0])
               for name, (method, path, token, body) in routes.items()}
    c.check("demo.off.no-demo-route-answers",
            all(got == control and got in (404, 405) for got, control in answers.values())
            and answers["status"][0] == 404,
            " ".join(f"{k}={got}/{control}" for k, (got, control) in answers.items()))
    signed = pb.auth_password(saved["standard"]["email"], saved["standard"]["password"])
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
