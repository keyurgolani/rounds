"""Two-account factory and fixture graph.

Generates all credentials per run (never the hosted demo password), signs
up account A and account B, and seeds one owned row in every account-scoped
collection for each account. The seeded rows are the targets the probes
prove are isolated. Content collections that ship empty (take_home
assignments) get one fixture row via the admin token so the dependent
user-owned collections can be exercised.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass, field
from typing import Any

from pbclient import PBClient, Response

# Guard: the hosted demo credential must never be used by the factory.
_DEMO_PASSWORD = "RoundsDemo123!"
_DEMO_EMAIL = "demo@rounds.keyurgolani.name"

_DATE = "2020-01-01 00:00:00.000Z"


@dataclass
class Account:
    tag: str
    email: str
    password: str
    user_id: str = ""
    token: str = ""
    ids: dict[str, str] = field(default_factory=dict)


def _gen_password() -> str:
    pw = "Hx" + secrets.token_hex(16) + "!9"
    if pw == _DEMO_PASSWORD:  # unreachable; defensive
        raise RuntimeError("generated the demo password")
    return pw


def make_account(tag: str) -> Account:
    email = f"harness-{tag}-{secrets.token_hex(6)}@harness.invalid"
    if email == _DEMO_EMAIL:
        raise RuntimeError("generated the demo email")
    return Account(tag=tag, email=email, password=_gen_password())


def _must(resp: Response, what: str) -> dict[str, Any]:
    if resp.status not in (200, 201) or not isinstance(resp.body, dict):
        raise RuntimeError(f"{what} failed: status={resp.status} body={resp.body!r}")
    return resp.body


def register(pb: PBClient, acct: Account) -> None:
    if acct.password == _DEMO_PASSWORD:
        raise RuntimeError("refusing to sign up with the demo password")
    rec = _must(pb.signup(acct.email, acct.password), f"signup {acct.tag}")
    acct.user_id = rec["id"]
    auth = _must(pb.auth_password(acct.email, acct.password), f"auth {acct.tag}")
    acct.token = auth["token"]


def ensure_content_fixtures(pb: PBClient, admin_token: str) -> dict[str, str]:
    """Create content rows that ship empty so dependents can be seeded.

    Uses the admin token: these are shared author/seed-owned content rows,
    not account-scoped rows. The seeded ai_coding round already exists from
    its content migration, so only take_home needs a fixture.
    """
    out: dict[str, str] = {}
    existing = pb.listing("take_home_assignments", token=admin_token, params={"perPage": 1})
    items = (existing.body or {}).get("items") or []
    if items:
        out["assignment"] = items[0]["id"]
    else:
        rec = _must(
            pb.create(
                "take_home_assignments",
                admin_token,
                {
                    "slug": "harness-fixture",
                    "title": "Harness Fixture",
                    "language": "python",
                    "entrypoint": "true",
                    "ai_policy": "off",
                },
            ),
            "take_home assignment fixture",
        )
        out["assignment"] = rec["id"]

    rounds = pb.listing("ai_coding_rounds", token=admin_token, params={"perPage": 1})
    r_items = (rounds.body or {}).get("items") or []
    if not r_items:
        raise RuntimeError("no ai_coding_rounds seeded; cannot seed ai_coding fixtures")
    out["round"] = r_items[0]["id"]
    return out


def seed_account(pb: PBClient, acct: Account, content: dict[str, str]) -> None:
    """Create one owned row in every account-scoped collection for `acct`."""
    uid = acct.user_id
    tok = acct.token
    tag = acct.tag
    ids = acct.ids

    def mk(collection: str, payload: dict[str, Any]) -> str:
        rec = _must(pb.create(collection, tok, {"user": uid, **payload}), f"seed {collection}/{tag}")
        ids[collection] = rec["id"]
        return rec["id"]

    campaign = mk("campaigns", {"name": f"{tag} campaign", "slug": f"{tag}-campaign"})
    application = mk("applications", {"company": "Acme", "role": "Engineer", "campaign": campaign})
    mk("interview_rounds", {"application": application, "round_type": "technical", "campaign": campaign})
    mk("user_progress", {"question_type": "coding", "question_slug": "two-sum"})
    mk("user_preferences", {"theme": "light"})
    mk("offers", {"application": application, "status": "pending"})
    mk("code_drafts", {"campaign": campaign, "question": "two-sum", "language": "python", "code": "x=1"})
    mk("todos", {"campaign": campaign, "body": "a todo"})

    resume = mk("resumes", {"name": f"{tag} resume", "slug": f"{tag}-resume"})
    variant = mk("resume_variants", {"resume": resume, "name": "variant"})
    mk("resume_versions", {"resume": resume, "data": {}})
    mk("resume_share_links", {"resume": resume, "token": secrets.token_urlsafe(16)})
    mk("resume_share_views", {"link": ids["resume_share_links"]})

    mk("ai_providers", {"kind": "openai", "label": "provider"})
    mk("ai_settings", {})

    mk("ai_coding_drafts", {"round": content["round"], "file_path": "a.py", "contents": "x=1"})
    mk("ai_coding_attempts", {"round": content["round"], "status": "in-progress", "current_checkpoint": 0})

    mk("take_home_drafts", {"assignment": content["assignment"], "file_path": "a.py", "contents": "x=1"})
    mk("take_home_attempts", {"assignment": content["assignment"], "status": "in-progress"})

    mk("question_timers", {"question_type": "coding", "question_slug": "two-sum", "accumulated_ms": 0})

    job = mk("experience_jobs", {"company": "Acme", "role": "Engineer", "start_date": _DATE})
    project = mk("experience_projects", {"title": "project", "start_date": _DATE})
    anecdote = mk("experience_anecdotes", {"title": "anecdote", "date": _DATE})
    bullet = mk("experience_bullets", {"title": "bullet", "date": _DATE})

    mk("exp_job_projects", {"parent": job, "child": project})
    mk("exp_job_anecdotes", {"parent": job, "child": anecdote})
    mk("exp_job_bullets", {"parent": job, "child": bullet})
    mk("exp_project_anecdotes", {"parent": project, "child": anecdote})
    mk("exp_project_bullets", {"parent": project, "child": bullet})
    mk("exp_anecdote_bullets", {"parent": anecdote, "child": bullet})

    # users: the account's own record id, for the users isolation probes.
    ids["users"] = uid
