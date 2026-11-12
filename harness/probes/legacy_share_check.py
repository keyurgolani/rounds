"""Harness check for older share links on the stack (ROUNDS-00B-L06 stage 1).

Three phases:

``legacy-shares-fixture``
  Offline, with the pinned binary: a pb_data shaped like 62d4eae (only the
  migrations that sort before 1700006000) in a volume of its own, holding
  older links for two accounts: one per state the journeys below use, one
  on another account's resume with views, real views with viewer hashes and
  user agents, and resumes the materializer renders. The fixture's ids and
  values go to the state folder only.
``legacy-shares``
  PocketBase started on that volume runs every later migration before its
  first request. Both runner replicas reach it through the recorder, nginx
  is up, snapshot creation is on, and the materializer is up.
  - every fixture link value, and as many random ones, gets byte for byte
    the same answer on every path, for every caller: the older read path
    through nginx and at each replica, the resolver through nginx and at each
    replica (as given and as a capability bearer), the /r/<value> page, and
    PocketBase's own API, as an anonymous caller, the owner, and another
    account; the owner's new link resolves (receipt
    isolation.share-legacy.replaced);
  - the owner's list holds its older links and never the one on another
    account's resume; Get a new link gives a bearer that resolves on both
    replicas; a second press, a replay, and a replaced link answer
    already-issued with the same capability; another account's link, a link
    turned off for good, a mismatched target, and a quarantined link get one
    not-found; the snapshot carries its source's update times;
  - revoking the new link, then resolving it at once on both replicas, gets
    the unknown answer, and deleting the resume revokes its variant's new
    link (receipt isolation.share-chain.capability-revoked);
  - every way a capability fails to resolve gets one not-found with the
    share headers (receipt isolation.share-resolver.not-found.uniform);
  - REST shows the quarantined link and its views to nobody;
  - every public share request reaches PocketBase only as the share
    resolver's own login and identity (receipt
    isolation.share-public.resolver-identity).
``legacy-shares-scan``
  No fixture link value, viewer hash, or user agent is in any service log
  or in that pb_data. The scan passes over the every-value check's own
  tagged requests.

The direct calls to a replica name a client of their own, as the share
secrets phases do, and the calls through nginx stay under its backstop.
Fixture values stay in the state folder and in memory; printed lines and
receipts name checks, statuses, and counts only.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import logscan
import recorder
from admission_check import Checks, admin_token, call, uuid7, wait_up
from pbclient import PBClient
from receipts import Receipt, ReceiptWriter
from share_secrets_check import (
    BEARER,
    FRONTEND_URL,
    POCKETBASE_URL,
    RD02_DIR,
    REPLICAS,
    named_client,
    random_bearer,
    raw,
    resolve,
    shape,
)

PHASES = ("legacy-shares-fixture", "legacy-shares", "legacy-shares-scan")
PB_BIN = Path(os.environ.get("PB_BIN", "/pbbin/pocketbase"))
MIGRATIONS = Path(os.environ.get("PB_MIGRATIONS_DIR", "/pb_migrations"))
SEEDS_DIR = os.environ.get("PB_SEEDS_DIR", "")
PB_DATA = Path(os.environ.get("PB_DATA_DIR", "/pb_data"))
STATE = Path(os.environ.get("LEGACY_SHARES_STATE", "/state/legacy-shares.json"))
SCAN_DIR = Path(os.environ.get("LEGACY_SHARES_SCAN_DIR", "/state/legacy-scan"))
RECORDER_LOG = os.environ.get("RECORDER_LOG", recorder.DEFAULT_LOG)
# 62d4eae's last migration sorts before this one.
BEFORE_R0 = "1700006000"
OLDER_PATH = "/api/share/by-token/"
LINKS_PATH = "/api/collections/resume_share_links/records"
VIEWS_PATH = "/api/collections/resume_share_views/records"
NOT_FOUND = b'{"detail":"Not found."}'
# The resolver's PocketBase calls (backend/app/share_resolver_client.py).
RESOLVER_LOGIN = "/api/collections/share_resolvers/auth-with-password"
RESOLVER_LOOKUP = "/api/rounds/share/lookup"
# Marks every fixture viewer value carries, so a scan can find any left.
IP_MARK = "olderviewerhash"
AGENT_MARK = "OlderFixtureAgent"
# nginx's backstop takes a burst of 20 resolves, then 2 a second.
NGINX_PACE_S = 0.6
# The every-value check's requests to PocketBase name themselves, and the
# scan passes over the check's own tagged requests.
PROBE_AGENT = "rounds-harness/legacy-shares-every-value"


def rid(tag: str) -> str:
    out = ("lx" + tag + "0" * 15)[:15]
    assert re.fullmatch(r"[a-z0-9]{15}", out), tag
    return out


UO, UT = rid("uo"), rid("ut")
RO, RT = rid("ro"), rid("rt")
VO = rid("vo")
# name -> (id, owner, fields)
LINKS = {
    "resume": (rid("lr"), UO, {"resume": RO}),
    "variant": (rid("lv"), UO, {"variant": VO}),
    "password": (rid("lp"), UO, {"resume": RO, "is_password": 1}),
    "expiry": (rid("le"), UO, {"resume": RO, "expires_at": "2030-01-01 00:00:00.000Z"}),
    "foreign": (rid("lf"), UO, {"resume": RT}),
    "other": (rid("lo"), UT, {"resume": RT}),
}
VIEWED = ("resume", "foreign")


# ---- legacy-shares-fixture --------------------------------------------------------------


def _insert(conn: sqlite3.Connection, table: str, **cols: Any) -> None:
    cols.setdefault("created", "2024-01-01 00:00:00.000Z")
    cols.setdefault("updated", "2024-01-01 00:00:00.000Z")
    names = ", ".join(f'"{k}"' for k in cols)
    conn.execute(f'INSERT INTO "{table}" ({names}) VALUES ({", ".join("?" for _ in cols)})', list(cols.values()))


def plant(db: Path, renderable: dict) -> dict:
    """Two accounts, their resumes and a variant, the older links and their
    views, written straight to SQLite as 62d4eae kept them."""
    state: dict[str, Any] = {"links": {}, "views": {}, "hashes": [], "agents": [], "accounts": {}}
    conn = sqlite3.connect(str(db))
    try:
        for uid, tag in ((UO, "owner"), (UT, "other")):
            email = f"lx-{tag}-{secrets.token_hex(4)}@harness.invalid"
            _insert(conn, "users", id=uid, email=email, username=f"lx{tag}{secrets.token_hex(3)}",
                    tokenKey=secrets.token_hex(16), passwordHash="x")
            state["accounts"][tag] = {"id": uid, "email": email}
        design = json.dumps(renderable.get("design") or {})
        data = json.dumps(renderable.get("data") or {})
        template = renderable.get("template_id") or ""
        _insert(conn, "resumes", id=RO, user=UO, name="Owner resume", slug="lx-owner", template_id=template,
                design=design, data=data)
        _insert(conn, "resumes", id=RT, user=UT, name="Other resume", slug="lx-other", template_id=template,
                design=design, data=data)
        _insert(conn, "resume_variants", id=VO, user=UO, resume=RO, name="For Acme", data=data)
        for name, (link_id, owner, fields) in LINKS.items():
            value = secrets.token_urlsafe(16)
            row = {"resume": "", "variant": "", "is_password": 0, "password_hash": "", "expires_at": "", **fields}
            _insert(conn, "resume_share_links", id=link_id, user=owner, token=value, **row)
            state["links"][name] = {"id": link_id, "value": value}
        for name in VIEWED:
            link_id, owner, _ = LINKS[name]
            for n in range(2):
                view_id = rid(f"w{name[0]}{n}")
                ip = f"{IP_MARK}{secrets.token_hex(8)}"
                agent = f"Mozilla/5.0 ({AGENT_MARK} {secrets.token_hex(4)})"
                _insert(conn, "resume_share_views", id=view_id, user=owner, link=link_id, viewer_ip_hash=ip,
                        user_agent=agent, viewed_at=f"2024-02-0{n + 1} 10:00:00.000Z")
                state["views"].setdefault(name, []).append(view_id)
                state["hashes"].append(ip)
                state["agents"].append(agent)
        conn.commit()
    finally:
        conn.close()
    state["ids"] = {"owner_resume": RO, "other_resume": RT, "variant": VO}
    return state


def run_fixture() -> int:
    c = Checks()
    work = Path(tempfile.mkdtemp(prefix="legacy-fixture-"))
    try:
        old = work / "migrations"
        old.mkdir()
        for path in sorted(MIGRATIONS.glob("*.js")):
            if path.name < BEFORE_R0:
                text = path.read_text()
                if SEEDS_DIR:
                    text = text.replace("/pb_seeds/", SEEDS_DIR.rstrip("/") + "/")
                (old / path.name).write_text(text)
        env = {"PATH": "/usr/bin:/bin", "PB_ADMIN_EMAIL": os.environ.get("PB_ADMIN_EMAIL", ""),
               "PB_ADMIN_PASSWORD": os.environ.get("PB_ADMIN_PASSWORD", "")}
        up = subprocess.run([str(PB_BIN), "migrate", "up", f"--dir={PB_DATA}", f"--migrationsDir={old}"],
                            capture_output=True, text=True, timeout=300, env=env)
        last = sorted(p.name for p in old.glob("*.js"))[-1]
        conn = sqlite3.connect((PB_DATA / "data.db").resolve().as_uri() + "?mode=ro", uri=True)
        try:
            applied = conn.execute("SELECT 1 FROM _migrations WHERE file = ?", (last,)).fetchone() is not None
            newer = conn.execute("SELECT COUNT(*) FROM _migrations WHERE file >= ? AND file LIKE '17%.js'",
                                 (BEFORE_R0,)).fetchone()[0]
        finally:
            conn.close()
        if not c.check("legacy-shares.fixture.shaped-like-62d4eae", up.returncode == 0 and applied and newer == 0,
                       (up.stdout + up.stderr)[-400:]):
            return 1
        renderable = json.loads((RD02_DIR / "base-and-link-in-text.json").read_text())["input"]
        state = plant(PB_DATA / "data.db", renderable)
        STATE.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(STATE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump(state, f)
        c.check("legacy-shares.fixture.planted", len(state["links"]) == len(LINKS), "")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"legacy-shares-fixture: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


# ---- legacy-shares --------------------------------------------------------------------------


def receipt(writer: ReceiptWriter, case: str, surface: str, actor: str, ok: bool, expected: int, observed: int,
            detail: str = "") -> None:
    writer.write(Receipt(case, surface, "read", actor, expected, observed, ok, 0, "" if ok else detail))


def via_nginx() -> bool:
    return bool(FRONTEND_URL) and os.environ.get("LEGACY_SHARES_NO_NGINX", "") != "1"


def paced_resolve(value: str) -> tuple[int, bytes, dict[str, str]]:
    time.sleep(NGINX_PACE_S)
    return resolve(FRONTEND_URL, value)


def every_resolver(value: str) -> list[tuple[int, bytes, tuple]]:
    """The resolver's answer for ``value`` at each replica, and through nginx."""
    out = [shape(resolve(base, value, client=named_client())) for base in REPLICAS]
    if via_nginx():
        out.append(shape(paced_resolve(value)))
    return out


def uniform(answers: list) -> bool:
    return bool(answers) and all(a == answers[0] for a in answers)


def sign_in(pb: PBClient, admin: str, acct: dict) -> str:
    """Give a fixture account a password, as the superuser, and sign in."""
    password = "Hx" + secrets.token_hex(16)
    set_pw = pb.update("users", acct["id"], {"password": password, "passwordConfirm": password}, admin)
    if set_pw.status != 200:
        raise RuntimeError(f"setting a fixture password failed: status={set_pw.status}")
    auth = pb.auth_password(acct["email"], password)
    if auth.status != 200 or not isinstance(auth.body, dict):
        raise RuntimeError(f"fixture sign-in failed: status={auth.status}")
    return auth.body["token"]


def get_new_link(token: str, body: dict, key: str) -> tuple[int, Any]:
    base = FRONTEND_URL if via_nginx() else REPLICAS[0]
    status, answer, _ = call(base, "POST", "/api/share", token, body, {"Idempotency-Key": key}, timeout=60)
    return status, answer


def older_list(token: str) -> dict[str, dict]:
    base = FRONTEND_URL if via_nginx() else REPLICAS[0]
    status, answer, _ = call(base, "GET", "/api/share", token)
    if status != 200 or not isinstance(answer, dict) or not isinstance(answer.get("legacy"), list):
        raise RuntimeError(f"the older links list failed: status={status}")
    return {row["id"]: row for row in answer["legacy"]}


def check_uniform(c: Checks, writer: ReceiptWriter, pb: PBClient, state: dict, owner: str, other: str,
                  rec_start: int) -> tuple[bool, str]:
    """Every value on every path: one answer per path and caller, for the
    fixture's values and random ones alike."""
    values = [link["value"] for link in state["links"].values()]
    values += [secrets.token_urlsafe(16) for _ in values]
    problems: list[str] = []

    for base in REPLICAS:
        before = recorder.log_length(RECORDER_LOG)
        answers = [raw(base, "GET", OLDER_PATH + v, headers={"X-Real-IP": named_client()})[:2] for v in values]
        if not uniform(answers) or answers[0][0] != 404:
            problems.append(f"replica older read status={answers[0][0]} uniform={uniform(answers)}")
        if recorder.log_length(RECORDER_LOG) != before:
            problems.append("the replica's older read reached PocketBase")
    if via_nginx():
        answers = [raw(FRONTEND_URL, "GET", OLDER_PATH + v) for v in values]
        if not uniform([(s, b) for s, b, _ in answers]) or answers[0][:2] != (404, NOT_FOUND):
            problems.append(f"nginx older read status={answers[0][0]}")
        pages = [raw(FRONTEND_URL, "GET", "/r/" + v)[:2] for v in values]
        if not uniform(pages) or pages[0][0] != 200:
            problems.append(f"older page status={pages[0][0]} uniform={uniform(pages)}")

    resolved = [a for v in values for a in every_resolver(v) + every_resolver("sd1_" + v)]
    if not uniform(resolved) or resolved[0][:2] != (404, NOT_FOUND):
        problems.append(f"resolver status={resolved[0][0]} uniform={uniform(resolved)}")

    # PocketBase itself, not through nginx, as the scan expects.
    for label, token in (("anonymous", None), ("owner", owner), ("other", other)):
        by_filter = [_rest(f"{LINKS_PATH}?filter=" + _q(f"token='{v}'"), token) for v in values]
        by_param = [_rest(f"{LINKS_PATH}?token=" + _q(v), token) for v in values]
        for kind, got in (("filter", by_filter), ("param", by_param)):
            if not uniform(got):
                problems.append(f"REST {kind} as {label} differs by value")
    c.check("legacy-shares.every-value.one-answer-per-path", not problems, "; ".join(problems))
    return not problems, "; ".join(problems)


def _rest(path: str, token: str | None) -> tuple[int, bytes]:
    return raw(POCKETBASE_URL, "GET", path, token, headers={"User-Agent": PROBE_AGENT})[:2]


def _q(text: str) -> str:
    import urllib.parse

    return urllib.parse.quote(text, safe="")


def resolves_everywhere(bearer: str) -> bool:
    for base in REPLICAS:
        if resolve(base, bearer, client=named_client())[0] != 200:
            return False
    return not via_nginx() or paced_resolve(bearer)[0] == 200


def check_journeys(c: Checks, writer: ReceiptWriter, pb: PBClient, admin: str, state: dict, owner: str,
                   other: str) -> dict:
    links = {name: link["id"] for name, link in state["links"].items()}
    out: dict[str, Any] = {"bearers": []}

    mine = older_list(owner)
    theirs = older_list(other)
    c.check("legacy-shares.list.owner-sees-its-own",
            {links["resume"], links["variant"], links["password"], links["expiry"]} == set(mine)
            and mine[links["resume"]]["status"] == "migrated" and mine[links["password"]]["status"] == "revoked_unverified"
            and links["foreign"] not in mine, repr(sorted((k, v["status"]) for k, v in mine.items())))
    c.check("legacy-shares.list.other-sees-its-own", set(theirs) == {links["other"]}, repr(sorted(theirs)))
    c.check("legacy-shares.list.holds-no-value", not any(v["value"] in json.dumps(mine) for v in state["links"].values()),
            "a link value is in the list")

    key = uuid7()
    status, first = get_new_link(owner, {"legacy_link_id": links["resume"]}, key)
    bearer = first.get("token") if isinstance(first, dict) else None
    ok = status == 201 and isinstance(bearer, str) and BEARER.fullmatch(bearer) is not None
    c.check("legacy-shares.new-link.issued-once", ok, f"status={status}")
    if not ok:
        return out
    out["bearers"].append(bearer)
    cap = first["capability_id"]
    out["capability"] = cap
    c.check("legacy-shares.new-link.shares-the-same-resume", (first.get("scope") or {}).get("resume_id") == state["ids"]["owner_resume"],
            repr(first.get("scope")))
    out["resolved_before_revoke"] = resolves_everywhere(bearer)
    c.check("legacy-shares.new-link.resolves-on-every-replica", out["resolved_before_revoke"], "")
    again = [get_new_link(owner, {"legacy_link_id": links["resume"]}, key),
             get_new_link(owner, {"legacy_link_id": links["resume"]}, uuid7())]
    c.check("legacy-shares.new-link.second-press-and-replay-answer-the-first",
            all(isinstance(b, dict) and b.get("secret_delivery") == "already-issued" and b.get("capability_id") == cap
                and "token" not in b for _s, b in again), repr([s for s, _ in again]))
    replaced = older_list(owner)[links["resume"]]
    c.check("legacy-shares.new-link.marks-the-older-one-replaced", replaced.get("replaced_by") == cap,
            repr(replaced.get("replaced_by")))

    refusals = [
        get_new_link(owner, {"legacy_link_id": links["other"]}, uuid7()),
        get_new_link(owner, {"legacy_link_id": links["password"]}, uuid7()),
        get_new_link(owner, {"legacy_link_id": links["variant"], "resume_id": state["ids"]["owner_resume"]}, uuid7()),
        get_new_link(owner, {"legacy_link_id": links["foreign"]}, uuid7()),
    ]
    bodies = [json.dumps({k: v for k, v in (b or {}).items() if k != "correlation_id"}, sort_keys=True)
              for _s, b in refusals]
    c.check("legacy-shares.new-link.refusals-are-one-not-found",
            all(s == 404 for s, _ in refusals) and uniform(bodies), repr([s for s, _ in refusals]))

    snap = _snapshot_of(pb, admin, cap)
    resume = pb.get(f"/api/collections/resumes/records/{state['ids']['owner_resume']}", admin).body or {}
    c.check("legacy-shares.new-link.snapshot-carries-the-source-time",
            snap.get("source_kind") == "resume" and snap.get("source_updated") == resume.get("updated"), "")

    # Revoked, then resolved at once on both replicas.
    revoke_base = FRONTEND_URL if via_nginx() else REPLICAS[0]
    r_status, _, _ = call(revoke_base, "POST", f"/api/share/capabilities/{cap}/revoke", owner, {})
    out["revoked"] = [shape(resolve(base, bearer, client=named_client())) for base in REPLICAS]
    revoked_ok = r_status == 200 and all(a[:2] == (404, NOT_FOUND) for a in out["revoked"])

    # The variant's new link, then its resume deleted.
    status, second = get_new_link(owner, {"legacy_link_id": links["variant"]}, uuid7())
    b2 = second.get("token") if isinstance(second, dict) else None
    variant_ok = status == 201 and isinstance(b2, str)
    if variant_ok:
        out["bearers"].append(b2)
        snap2 = _snapshot_of(pb, admin, second["capability_id"])
        variant = pb.get(f"/api/collections/resume_variants/records/{state['ids']['variant']}", admin).body or {}
        c.check("legacy-shares.new-link.variant-snapshot-carries-both-times",
                snap2.get("source_kind") == "variant" and snap2.get("source_updated") == variant.get("updated")
                and snap2.get("parent_updated") == resume.get("updated"), "")
        variant_ok = resolves_everywhere(b2)
        deleted = pb.delete("resumes", state["ids"]["owner_resume"], owner)
        out["deleted"] = [shape(resolve(base, b2, client=named_client())) for base in REPLICAS]
        variant_ok = variant_ok and deleted.status == 204 and all(a[:2] == (404, NOT_FOUND) for a in out["deleted"])
    c.check("legacy-shares.revoke.resolves-nothing-at-once", revoked_ok, f"revoke={r_status}")
    c.check("legacy-shares.delete.revokes-the-variants-new-link", variant_ok, f"status={status}")
    receipt(writer, "isolation.share-chain.capability-revoked", "share:resolver", "share_bearer",
            revoked_ok and variant_ok and out["resolved_before_revoke"], 404,
            out["revoked"][0][0] if out["revoked"] else 0, f"revoke={r_status} variant={variant_ok}")
    return out


def _snapshot_of(pb: PBClient, admin: str, cap: str) -> dict:
    capability = pb.get(f"/api/collections/share_capabilities/records/{cap}", admin).body or {}
    snap = capability.get("snapshot") if isinstance(capability, dict) else None
    if not snap:
        return {}
    got = pb.get(f"/api/collections/legacy_artifact_snapshots/records/{snap}", admin).body
    return got if isinstance(got, dict) else {}


def check_not_found(c: Checks, writer: ReceiptWriter, state: dict, journey: dict) -> None:
    """Whatever stops a capability resolving: one answer, with the headers."""
    older_value = state["links"]["resume"]["value"]
    answers = every_resolver(random_bearer()) + every_resolver("x") + every_resolver(older_value) \
        + every_resolver("sd1_" + older_value) + journey.get("revoked", []) + journey.get("deleted", [])
    ok = uniform(answers) and answers[0][:2] == (404, NOT_FOUND) and journey.get("resolved_before_revoke") is True
    c.check("legacy-shares.not-found.one-answer-with-the-headers", ok, f"answers={len(answers)}")
    receipt(writer, "isolation.share-resolver.not-found.uniform", "share:resolver", "share_bearer", ok, 404,
            answers[0][0] if answers else 0, f"uniform={uniform(answers)}")


def check_quarantined_hidden(c: Checks, state: dict, owner: str, other: str) -> None:
    rest = PBClient(FRONTEND_URL if via_nginx() else POCKETBASE_URL)
    link = state["links"]["foreign"]["id"]
    views = state["views"]["foreign"]
    seen = []
    for token in (None, owner, other):
        seen.append(rest.get(f"{LINKS_PATH}/{link}", token).status)
        seen += [rest.get(f"{VIEWS_PATH}/{v}", token).status for v in views]
        listed = rest.get(f"{LINKS_PATH}?filter=" + _q(f"id='{link}'"), token)
        seen.append(len((listed.body or {}).get("items") or []) if listed.status == 200 else 0)
        held = rest.get("/api/collections/relation_quarantine/records", token)
        seen.append(len((held.body or {}).get("items") or []) if held.status == 200 else 0)
    c.check("legacy-shares.quarantined.shown-to-nobody", all(s in (0, 404) for s in seen), repr(seen))


def check_resolver_identity(c: Checks, writer: ReceiptWriter, start: int, end: int) -> None:
    """Every call PocketBase got while only public share requests ran (the
    every-value checks), from the recorder: the resolver's login, with no
    token, and its lookups, as its service identity, and nothing else."""
    lines = recorder.read_log(RECORDER_LOG, start)[: max(0, end - start)]
    allowed = all((line["path"] == RESOLVER_LOGIN and line["auth"] == "none")
                  or (line["path"] == RESOLVER_LOOKUP and line["auth"] == "service") for line in lines)
    looked_up = any(line["path"] == RESOLVER_LOOKUP and line["auth"] == "service" for line in lines)
    ok = allowed and looked_up
    c.check("legacy-shares.public.only-the-resolvers-identity", ok,
            f"lines={len(lines)} classes={sorted({(line['path'], line['auth']) for line in lines})}")
    receipt(writer, "isolation.share-public.resolver-identity", "share:upstream", "anonymous", ok, 0,
            sum(1 for line in lines if not ((line["path"] == RESOLVER_LOGIN and line["auth"] == "none")
                                            or (line["path"] == RESOLVER_LOOKUP and line["auth"] == "service"))),
            f"looked_up={looked_up}")


def run_stack(writer: ReceiptWriter) -> int:
    c = Checks()
    state = json.loads(STATE.read_text())
    pb = PBClient(POCKETBASE_URL)
    pb.wait_healthy()
    for base in REPLICAS:
        if not wait_up(base):
            raise RuntimeError("the older links phase needs both runner replicas up")
    if via_nginx():
        front = PBClient(FRONTEND_URL)
        front.wait_healthy()
    admin = admin_token(pb)
    owner = sign_in(pb, admin, state["accounts"]["owner"])
    other = sign_in(pb, admin, state["accounts"]["other"])

    rec_start = recorder.log_length(RECORDER_LOG)
    uniform_ok, why = check_uniform(c, writer, pb, state, owner, other, rec_start)
    rec_end = recorder.log_length(RECORDER_LOG)
    journey = check_journeys(c, writer, pb, admin, state, owner, other)
    check_not_found(c, writer, state, journey)
    check_quarantined_hidden(c, state, owner, other)
    replaced_ok = uniform_ok and journey.get("resolved_before_revoke") is True
    receipt(writer, "isolation.share-legacy.replaced", "share:legacy", "share_bearer", replaced_ok, 404,
            404 if uniform_ok else 0, why or "the owner's new link didn't resolve")
    check_resolver_identity(c, writer, rec_start, rec_end)

    # The scan reads the bearers this phase issued too.
    state["issued"] = journey.get("bearers", [])
    fd = os.open(STATE, os.O_WRONLY | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(state, f)
    print(f"legacy-shares: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


# ---- legacy-shares-scan ---------------------------------------------------------------------


def run_scan() -> int:
    c = Checks()
    state = json.loads(STATE.read_text())
    values = tuple([link["value"] for link in state["links"].values()] + state["hashes"] + state["agents"])
    hits, where = 0, []
    for path in sorted(SCAN_DIR.glob("*.log")):
        found = logscan.scan_text(path.read_text(errors="replace"), path.name, values).literals
        hits += found
        if found:
            where.append(path.stem)
    c.check("legacy-shares.scan.logs-hold-no-fixture-value", hits == 0, f"{hits} found in {', '.join(where)}")
    in_data = own = 0
    tarball = SCAN_DIR / "pb_data.tar"
    if tarball.exists():
        work = Path(tempfile.mkdtemp(prefix="legacy-scan-"))
        try:
            import tarfile

            with tarfile.open(tarball) as tar:
                tar.extractall(work, filter="data")
            for db in work.rglob("*.db"):
                found, passed = scan_db(db, values)
                in_data += found
                own += passed
        finally:
            shutil.rmtree(work, ignore_errors=True)
    c.check("legacy-shares.scan.pb-data-holds-no-fixture-value", tarball.exists() and in_data == 0,
            f"tarball={tarball.exists()} found={in_data} own_requests_passed_over={own}")
    print(f"legacy-shares-scan: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


def _own_request(table: str, record: dict[str, Any]) -> bool:
    """Whether a row belongs to one of the every-value check's own tagged
    requests."""
    if table != "_logs":
        return False
    try:
        data = json.loads(record.get("data") or "{}")
    except (TypeError, ValueError):
        return False
    return isinstance(data, dict) and data.get("userAgent") == PROBE_AGENT


def scan_db(db: Path, values: tuple[str, ...]) -> tuple[int, int]:
    """Every text value of every table in ``db``: the fixture values found,
    and how many rows were the every-value check's own tagged requests."""
    found = passed = 0
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    try:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
        for table in tables:
            cur = con.execute('SELECT * FROM "' + table.replace('"', '""') + '"')
            cols = [d[0] for d in cur.description]
            for row in cur:
                if _own_request(table, dict(zip(cols, row))):
                    passed += 1
                    continue
                for value in row:
                    if isinstance(value, bytes):
                        value = value.decode("utf-8", "replace")
                    if isinstance(value, str):
                        found += logscan.scan_text(value, f"{db.name}:{table}", values).literals
    finally:
        con.close()
    return found, passed


def main(phase: str, writer: ReceiptWriter | None = None) -> int:
    if phase == "legacy-shares-fixture":
        return run_fixture()
    if phase == "legacy-shares":
        assert writer is not None
        return run_stack(writer)
    if phase == "legacy-shares-scan":
        return run_scan()
    print(f"unknown phase {phase!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else ""))
