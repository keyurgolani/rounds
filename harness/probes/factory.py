"""Two-account factory and fixture graph.

Generates all credentials per run (never the hosted demo password), signs
up account A and account B, and seeds one owned row in every account-scoped
collection for each account. The seeded rows are the targets the probes
prove are isolated. Content collections that ship empty (take_home
assignments) get one fixture row via the admin token so the dependent
user-owned collections can be exercised.
"""
from __future__ import annotations

import hashlib
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


# A Legacy Artifact Snapshot's fields, for the fixture row and the create
# probes: a resume source, an empty design, and a small markup document.
SNAPSHOT_MARKUP = (
    b'<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="utf-8" />\n  <title>Resume</title>\n</head>\n'
    b'<body>\n<article data-resume-page="true"></article>\n</body>\n</html>'
)


def snapshot_fields(source_id: str) -> dict[str, Any]:
    return {
        "source_kind": "resume",
        "source_id": source_id,
        "source_updated": _DATE,
        "template_id": "modern",
        "template_fallback": False,
        "design": {},
        "data": {"personalInfo": {"fullName": ""}, "experience": [], "education": [], "skills": [],
                 "projects": [], "publications": [], "profiles": []},
        "content_checksum": "sha256:" + hashlib.sha256(SNAPSHOT_MARKUP).hexdigest(),
        "materializer_digest": "sha256:" + hashlib.sha256(b"harness materializer").hexdigest(),
        "sanitizer_version": "1.0.0",
        "font_families": ["inter"],
        "size_bytes": len(SNAPSHOT_MARKUP),
    }


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


def seed_account(pb: PBClient, acct: Account, content: dict[str, str], admin_token: str) -> None:
    """Create one owned row in every account-scoped collection for `acct`.

    Most rows are created with the account's own token, which also confirms
    the owner create path works under the create rule: a rejected owner create
    stops the run. ``resume_share_views`` is seeded with the admin token
    instead, because its create and update rules are superuser-only (null).
    """
    uid = acct.user_id
    tok = acct.token
    tag = acct.tag
    ids = acct.ids

    def mk(collection: str, payload: dict[str, Any]) -> str:
        rec = _must(pb.create(collection, tok, {"user": uid, **payload}), f"seed {collection}/{tag}")
        ids[collection] = rec["id"]
        return rec["id"]

    def mk_admin(collection: str, payload: dict[str, Any]) -> str:
        rec = _must(pb.create(collection, admin_token, {"user": uid, **payload}), f"seed {collection}/{tag}")
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
    mk_admin("resume_share_views", {"link": ids["resume_share_links"]})
    # Only a PocketBase hook writes snapshots (ROUNDS-00A-L04), so the
    # fixture row, with its markup file, goes in with the admin token.
    rec = _must(
        pb.create_with_file(
            "legacy_artifact_snapshots",
            admin_token,
            {"user": uid, **snapshot_fields(resume)},
            "markup",
            "snapshot.html",
            SNAPSHOT_MARKUP,
            "text/html",
        ),
        f"seed legacy_artifact_snapshots/{tag}",
    )
    ids["legacy_artifact_snapshots"] = rec["id"]

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


def fresh_payload(
    collection: str,
    owner_id: str,
    a: Account,
    b: Account,
    content: dict[str, str],
    suffix: str,
) -> dict[str, Any]:
    """A complete, valid, non-colliding create payload for `collection`.

    Used by the create probes (anonymous, foreign-owner, server-only, and the
    superuser view insert) and the oversized-input probe, which need a body
    that passes field, relation, and uniqueness validation so that the only
    thing left to decide the request is the createRule or the field-size check.
    ``owner_id`` is the ``user`` value: the deny probes use a no-rows account so
    there is no per-user uniqueness collision, and relations point at account
    `a`'s seeded rows (they only need to exist). Junctions pair one of `a`'s endpoints with one of `b`'s so
    the (parent, child) pair is novel and does not collide with a seeded row.
    Unique scalar fields carry ``suffix`` so repeated runs do not collide.

    This lists the same required fields as ``seed_account``; keep the two in
    step. The harness run exercises both, so a drift shows up as a failed
    probe rather than a silent gap.
    """
    s = suffix
    base: dict[str, Any] = {"user": owner_id}
    extra: dict[str, Any] = {
        "campaigns": {"name": "probe", "slug": f"probe-{s}"},
        "applications": {"company": "Acme", "role": "Engineer", "campaign": a.ids["campaigns"]},
        "interview_rounds": {"application": a.ids["applications"], "round_type": "technical"},
        "user_progress": {"question_type": "coding", "question_slug": f"probe-{s}"},
        "user_preferences": {"theme": "light"},
        "offers": {"application": a.ids["applications"], "status": "pending"},
        "code_drafts": {"campaign": a.ids["campaigns"], "question": f"probe-{s}", "language": "python", "code": "x=1"},
        "todos": {"campaign": a.ids["campaigns"], "body": "probe"},
        "resumes": {"name": "probe", "slug": f"probe-{s}"},
        "resume_variants": {"resume": a.ids["resumes"], "name": "variant"},
        "resume_versions": {"resume": a.ids["resumes"]},
        "resume_share_links": {"resume": a.ids["resumes"], "token": f"probe-{s}"},
        "resume_share_views": {"link": a.ids["resume_share_links"]},
        # No markup file: only the create probe uses it, and the null create
        # rule refuses the request before any field is read.
        "legacy_artifact_snapshots": snapshot_fields(a.ids["resumes"]),
        "ai_providers": {"kind": "openai", "label": "provider"},
        "ai_settings": {},
        "ai_coding_drafts": {"round": content["round"], "file_path": f"probe-{s}.py", "contents": "x=1"},
        "ai_coding_attempts": {"round": content["round"], "status": "in-progress", "current_checkpoint": 0},
        "take_home_drafts": {"assignment": content["assignment"], "file_path": f"probe-{s}.py", "contents": "x=1"},
        "take_home_attempts": {"assignment": content["assignment"], "status": "in-progress"},
        "question_timers": {"question_type": "coding", "question_slug": f"probe-{s}", "accumulated_ms": 0},
        "experience_jobs": {"company": "Acme", "role": "Engineer", "start_date": _DATE},
        "experience_projects": {"title": "project", "start_date": _DATE},
        "experience_anecdotes": {"title": "anecdote", "date": _DATE},
        "experience_bullets": {"title": "bullet", "date": _DATE},
        "exp_job_projects": {"parent": a.ids["experience_jobs"], "child": b.ids["experience_projects"]},
        "exp_job_anecdotes": {"parent": a.ids["experience_jobs"], "child": b.ids["experience_anecdotes"]},
        "exp_job_bullets": {"parent": a.ids["experience_jobs"], "child": b.ids["experience_bullets"]},
        "exp_project_anecdotes": {"parent": a.ids["experience_projects"], "child": b.ids["experience_anecdotes"]},
        "exp_project_bullets": {"parent": a.ids["experience_projects"], "child": b.ids["experience_bullets"]},
        "exp_anecdote_bullets": {"parent": a.ids["experience_anecdotes"], "child": b.ids["experience_bullets"]},
    }
    if collection not in extra:
        raise RuntimeError(f"fresh_payload: no recipe for {collection}")
    base.update(extra[collection])
    return base
