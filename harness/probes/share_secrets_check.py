"""Harness check for one-time share links (ROUNDS-00B-L04).

Three phases, on the real PocketBase with snapshot creation and share
capability resolution on, the materializer up, both runner replicas, and
nginx:

``share-secrets``
  - CreateShare through nginx shows the bearer once; the same key answers
    already-issued with the same capability and no bearer, as it is and
    after the source changes; Rotate recovers a lost create, and a repeated
    rotate key answers already-issued;
  - 10 rotations at one version, across both replicas: one new bearer, and
    the old one resolves nothing on either replica;
  - a revoked or an expired capability can't be rotated; a demo account's
    create is #4's ineligible;
  - a password mismatch, no password, and a password that could never match
    answer exactly as an unknown bearer does (receipt
    isolation.share-resolver.password.uniform);
  - password tries are limited per client and bearer; 1,000 random
    well-formed bearers from one client, under three key ids, get the
    uniform not-found until the client's limit, then 429; once throttled, a live bearer and an unknown
    one get the same 429 (receipt isolation.share-resolver.throttle.independent);
  - a client can't spread its count with its own X-Real-IP through nginx,
    and nginx's backstop answers a burst with 429.
``share-secrets-down``
  PocketBase stopped: a live bearer gets the same not-found as an unknown one.
``share-secrets-scan``
  The launcher puts every service's log and a pb_data tarball in the state
  folder, which is never uploaded. No issued bearer (raw, URL-encoded, or
  base64) or password (raw, or its SHA-1, SHA-256, or MD5) is in any of
  them, and no log line for a share resolve or the share page carries this
  probe's address (receipts isolation.logs.share-secret.absent and
  isolation.logs.share-client-address.absent).

The runners trust X-Real-IP from this network's addresses, as they do from
nginx, so the direct calls to a replica name a test client of their own and
keep the probe's own count for the calls through nginx.

Bearers and passwords stay in the state folder and in memory; receipts and
printed lines name checks, statuses, and counts only.
"""
from __future__ import annotations

import base64
import hashlib
import io
import itertools
import json
import os
import re
import secrets
import socket
import sys
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import factory
import logscan
from admission_check import Checks, account, admin_token, call, demo_account, uuid7, wait_up
from pbclient import PBClient
from receipts import Receipt, ReceiptWriter

POCKETBASE_URL = os.environ.get("POCKETBASE_URL", "http://pocketbase:8090")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://frontend").rstrip("/")
REPLICAS = [u.strip().rstrip("/") for u in os.environ.get("RUNNER_URLS", "http://runner:8000").split(",") if u.strip()]
RD02_DIR = Path(os.environ.get("RD02_DIR", "/rd02"))
STATE = Path(os.environ.get("SHARE_STATE_PATH", "/state/share-secrets.json"))
SCAN_DIR = Path(os.environ.get("SHARE_SCAN_DIR", "/state/share-scan"))
RESOLVE = "/api/share/resolve"
CREATE = "/api/share"
CAPABILITIES = "/api/share/capabilities"
BEARER = re.compile(r"sd1_[A-Za-z0-9_-]{22}")
RESOLVER_HEADERS = ("cache-control", "x-robots-tag", "referrer-policy", "x-content-type-options",
                    "x-frame-options", "content-security-policy")
IP_LIMIT = 60
PASSWORD_LIMIT = 10
PHASES = ("share-secrets", "share-secrets-down", "share-secrets-scan")
# A log line for a share capability resolve or its page.
SHARE_LINE = re.compile(r'"(?:POST /api/share/resolve|(?:GET|HEAD) /r(?:\?\S*)?) HTTP')


# ---- calls ----------------------------------------------------------------------------------------------


def raw(base: str, method: str, path: str, token: str | None = None, body: Any = None,
        headers: dict[str, str] | None = None, timeout: float = 30) -> tuple[int, bytes, dict[str, str]]:
    """Status, raw body, and lowercased headers, for byte comparisons."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    sent = {"Accept": "application/json", **(headers or {})}
    if data is not None:
        sent["Content-Type"] = "application/json"
    if token:
        sent["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base + path, data=data, headers=sent, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read(), {k.lower(): v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as err:
        return err.code, err.read(), {k.lower(): v for k, v in err.headers.items()}


def resolve(base: str, token: str, password: str | None = None, client: str | None = None):
    body: dict[str, str] = {"token": token}
    if password is not None:
        body["password"] = password
    return raw(base, "POST", RESOLVE, body=body, headers={"X-Real-IP": client} if client else None)


def shape(answer: tuple[int, bytes, dict[str, str]]) -> tuple[int, bytes, tuple]:
    """What a uniform answer must share: status, bytes, and the share headers."""
    status, body, headers = answer
    return status, body, tuple(headers.get(h) for h in RESOLVER_HEADERS)


def random_bearer(key: str = "sd1") -> str:
    """A well-formed bearer no capability has, under ``key``."""
    return key + "_" + base64.urlsafe_b64encode(secrets.token_bytes(16)).rstrip(b"=").decode("ascii")


# The key ids the flood mixes: the current one, and two the format allows
# that resolve nothing but count the same.
KEY_IDS = ("sd1", "sd7", "sd999")


_clients = itertools.count(1)


def named_client() -> str:
    """A documentation-range address, a new one each call, for a direct call
    to name as its client. A run's PocketBase starts empty, so none has a
    count yet."""
    return f"198.51.100.{next(_clients)}"


def create_share(token: str, resume_id: str, key: str, password: str | None = None) -> tuple[int, Any]:
    payload: dict[str, str] = {"resume_id": resume_id}
    if password is not None:
        payload["password"] = password
    status, body, _ = call(FRONTEND_URL, "POST", CREATE, token, payload, {"Idempotency-Key": key}, timeout=60)
    return status, body


def rotate(base: str, token: str, cid: str, version: int, key: str) -> tuple[int, Any]:
    status, body, _ = call(base, "POST", f"{CAPABILITIES}/{cid}/rotate", token,
                           {"expected_capability_version": version}, {"Idempotency-Key": key}, timeout=60)
    return status, body


def issued(status: int, body: Any, want: int) -> bool:
    return (status == want and isinstance(body, dict) and body.get("secret_delivery") == "issued"
            and isinstance(body.get("token"), str) and BEARER.fullmatch(body["token"]) is not None)


def fields_of(body: Any) -> dict:
    if not isinstance(body, dict):
        return {}
    return {k: body.get(k) for k in ("capability_id", "scope", "state", "expires_at", "capability_version")}


def probe_address(host: str) -> str:
    """The address this container reaches ``host`` from."""
    name = urllib.parse.urlparse(host).hostname or host
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect((name, 80))
        return s.getsockname()[0]


def wait_routed() -> None:
    for base in REPLICAS:
        if not wait_up(base):
            raise RuntimeError("the share secrets phase needs both runner replicas up")
    front = PBClient(FRONTEND_URL)
    front.wait_healthy()
    front.wait_for(CAPABILITIES, lambda r: r.status == 401)


def renderable_resume(pb: PBClient, acct: factory.Account, slug: str) -> dict:
    """A resume the materializer renders: RD-02's base input."""
    given = json.loads((RD02_DIR / "base-and-link-in-text.json").read_text())["input"]
    made = pb.create("resumes", acct.token, {
        "user": acct.user_id, "name": slug, "slug": slug, "template_id": given.get("template_id") or "",
        "design": given.get("design"), "data": given.get("data"),
    })
    if made.status != 200 or not isinstance(made.body, dict):
        raise RuntimeError(f"resume {slug} create failed: status={made.status}")
    return made.body


class Secrets:
    """Every bearer and password the phase issues, for the scan, and the
    writer's redactor, so no receipt can carry one."""

    def __init__(self, writer: ReceiptWriter) -> None:
        self.writer = writer
        self.tokens: list[str] = []
        self.passwords: list[str] = []

    def token(self, value: Any) -> Any:
        if isinstance(value, str) and value not in self.tokens:
            self.tokens.append(value)
            self.writer.register_secret(value, "share-bearer")
        return value

    def password(self, value: str) -> str:
        self.passwords.append(value)
        self.writer.register_secret(value, "share-password")
        return value


def receipt(writer: ReceiptWriter, case: str, ok: bool, expected: int, observed: int, detail: str = "") -> None:
    writer.write(Receipt(case, "share:resolver" if "resolver" in case else "logs:share", "resolve", "share_bearer",
                         expected, observed, ok, 0, "" if ok else detail))


# ---- share-secrets ------------------------------------------------------------------------------------------


def run_create_and_rotate(c: Checks, pb: PBClient, admin: str, a: factory.Account, s: Secrets) -> dict:
    src = renderable_resume(pb, a, "share-secrets-" + secrets.token_hex(3))
    key = uuid7()
    status, first = create_share(a.token, src["id"], key)
    s.token(first.get("token") if isinstance(first, dict) else None)
    c.check("share.create.issued-once", issued(status, first, 201), f"status={status}")
    again_status, again = create_share(a.token, src["id"], key)
    c.check("share.create.retry-is-already-issued",
            again_status == 200 and isinstance(again, dict) and again.get("secret_delivery") == "already-issued"
            and "token" not in again and fields_of(again) == fields_of(first), f"status={again_status}")
    edited = pb.update("resumes", src["id"], {"name": src["name"] + " edited"}, a.token)
    later_status, later = create_share(a.token, src["id"], key)
    c.check("share.create.retry-after-a-source-edit-is-already-issued",
            edited.status == 200 and later_status == 200 and isinstance(later, dict)
            and later.get("secret_delivery") == "already-issued" and "token" not in later
            and fields_of(later) == fields_of(first), f"edit={edited.status} status={later_status}")

    # The first answer was lost: Rotate gets a link that works, and the lost one stops.
    cid = first.get("capability_id") if isinstance(first, dict) else ""
    version = later.get("capability_version") if isinstance(later, dict) else 0
    rkey = uuid7()
    r_status, turned = rotate(FRONTEND_URL, a.token, cid, version, rkey)
    s.token(turned.get("token") if isinstance(turned, dict) else None)
    client = named_client()
    new_ok = issued(r_status, turned, 200) and resolve(REPLICAS[0], turned["token"], client=client)[0] == 200
    lost = resolve(REPLICAS[-1], first.get("token", random_bearer()), client=client)[0] if isinstance(first, dict) else 0
    c.check("share.rotate.recovers-a-lost-create", new_ok and lost == 404, f"rotate={r_status} lost={lost}")
    dup_status, dup = rotate(FRONTEND_URL, a.token, cid, version, rkey)
    c.check("share.rotate.same-key-is-already-issued",
            dup_status == 200 and isinstance(dup, dict) and dup.get("secret_delivery") == "already-issued"
            and "token" not in dup and dup.get("capability_version") == version + 1, f"status={dup_status}")
    return {"capability_id": cid, "token": turned.get("token") if isinstance(turned, dict) else ""}


def run_concurrent_rotations(c: Checks, pb: PBClient, a: factory.Account, s: Secrets) -> None:
    src = renderable_resume(pb, a, "share-concurrent-" + secrets.token_hex(3))
    status, made = create_share(a.token, src["id"], uuid7())
    old = s.token(made.get("token")) if isinstance(made, dict) else ""
    cid = made.get("capability_id") if isinstance(made, dict) else ""
    answers: list[tuple[int, Any]] = []
    lock = threading.Lock()

    def one(i: int) -> None:
        got = rotate(REPLICAS[i % len(REPLICAS)], a.token, cid, 1, uuid7())
        with lock:
            answers.append(got)

    threads = [threading.Thread(target=one, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    winners = [body for st, body in answers if issued(st, body, 200)]
    for body in winners:
        s.token(body["token"])
    conflicts = [st for st, body in answers
                 if st == 409 and isinstance(body, dict) and body.get("code") == "capability_version_conflict"]
    client = named_client()
    old_dead = all(resolve(base, old, client=client)[0] == 404 for base in REPLICAS)
    new_live = len(winners) == 1 and all(resolve(base, winners[0]["token"], client=client)[0] == 200 for base in REPLICAS)
    c.check("share.rotate.ten-at-once-make-one-bearer",
            status == 201 and len(winners) == 1 and len(conflicts) == 9 and old_dead and new_live,
            f"create={status} issued={len(winners)} conflicts={len(conflicts)} old_dead={old_dead} new_live={new_live}")


def run_closed_rotations(c: Checks, pb: PBClient, admin: str, a: factory.Account, demo: factory.Account,
                         s: Secrets) -> None:
    made = []
    for n in range(2):
        src = renderable_resume(pb, a, f"share-closed-{n}-" + secrets.token_hex(3))
        _, body = create_share(a.token, src["id"], uuid7())
        s.token(body.get("token") if isinstance(body, dict) else None)
        made.append(body if isinstance(body, dict) else {})
    revoked, expired = made
    rv, _, _ = call(FRONTEND_URL, "POST", f"{CAPABILITIES}/{revoked.get('capability_id')}/revoke", a.token, {})
    past = time.strftime("%Y-%m-%d %H:%M:%S.000Z", time.gmtime(time.time() - 60))
    ex = pb.update("share_capabilities", expired.get("capability_id", ""), {"expires_at": past}, admin)
    r1 = rotate(FRONTEND_URL, a.token, revoked.get("capability_id", ""), 2, uuid7())
    r2 = rotate(FRONTEND_URL, a.token, expired.get("capability_id", ""), 1, uuid7())
    c.check("share.rotate.revoked-and-expired-are-refused",
            rv == 200 and ex.status == 200
            and r1[0] == 409 and isinstance(r1[1], dict) and r1[1].get("code") == "capability_revoked"
            and r2[0] == 409 and isinstance(r2[1], dict) and r2[1].get("code") == "capability_expired",
            f"revoke={rv} expire={ex.status} revoked={r1[0]} expired={r2[0]}")

    demo_src = renderable_resume(pb, demo, "share-demo-" + secrets.token_hex(3))
    d_status, d_body = create_share(demo.token, demo_src["id"], uuid7())
    c.check("share.create.demo-account-is-ineligible",
            d_status == 200 and d_body == {"status": "ineligible", "reason": "demo_account"}, f"status={d_status}")


def run_password_uniform(c: Checks, pb: PBClient, a: factory.Account, s: Secrets, writer: ReceiptWriter) -> dict:
    src = renderable_resume(pb, a, "share-password-" + secrets.token_hex(3))
    password = s.password("harness-share-pw-" + secrets.token_hex(8))
    status, made = create_share(a.token, src["id"], uuid7(), password)
    token = s.token(made.get("token")) if isinstance(made, dict) else random_bearer()
    unknown = shape(resolve(FRONTEND_URL, random_bearer()))
    tries = {
        "no password": shape(resolve(FRONTEND_URL, token)),
        "a wrong password": shape(resolve(FRONTEND_URL, token, "not-the-password-" + secrets.token_hex(4))),
        "a password that could never match": shape(resolve(FRONTEND_URL, token, "x" * 200)),
        "an unknown bearer with a password": shape(resolve(FRONTEND_URL, random_bearer(), password)),
        "a bearer under another key id": shape(resolve(FRONTEND_URL, random_bearer("sd7"), password)),
    }
    right = resolve(FRONTEND_URL, token, password)
    differ = [name for name, got in tries.items() if got != unknown]
    ok = status == 201 and unknown[0] == 404 and not differ and right[0] == 200
    c.check("share.resolve.password-mismatch-is-the-unknown-answer", ok,
            f"create={status} right={right[0]} differ={','.join(differ) or 'none'}")
    receipt(writer, "isolation.share-resolver.password.uniform", ok, 404, unknown[0],
            f"right={right[0]} differ={','.join(differ) or 'none'}")
    # The protected bearer stays for the limit check below.
    return {"token": token, "password": password, "not_found": base64.b64encode(unknown[1]).decode("ascii"),
            "headers": list(unknown[2])}


def run_limits(c: Checks, pb: PBClient, a: factory.Account, protected: dict, live: str, s: Secrets,
               writer: ReceiptWriter) -> None:
    base = REPLICAS[0]
    # Password tries: 10 per client and bearer, then 429 even for the right one.
    tries_client = named_client()
    wrong = [resolve(base, protected["token"], "wrong-" + secrets.token_hex(6), tries_client)[0]
             for _ in range(PASSWORD_LIMIT)]
    eleventh = resolve(base, protected["token"], protected["password"], tries_client)
    c.check("share.resolve.password-tries-are-limited-per-client-and-bearer",
            wrong == [404] * PASSWORD_LIMIT and eleventh[0] == 429, f"wrong={sorted(set(wrong))} next={eleventh[0]}")

    # 1,000 random well-formed bearers from one client, under three key ids:
    # every one counts.
    flood = REPLICAS[-1]
    client = named_client()
    baseline = shape(resolve(flood, random_bearer(), client=named_client()))
    answers = [shape(resolve(flood, random_bearer(KEY_IDS[i % len(KEY_IDS)]), client=client)) for i in range(1000)]
    head = answers[:IP_LIMIT]
    first_429 = next((i for i, got in enumerate(answers) if got[0] == 429), None)
    c.check("share.resolve.a-thousand-random-bearers-meet-the-limit",
            all(got == baseline for got in head) and first_429 == IP_LIMIT
            and all(got[0] in (404, 429) for got in answers) and all(got == baseline for got in answers if got[0] == 404),
            f"first_429={first_429} statuses={sorted({got[0] for got in answers})}")

    # Throttled, a live bearer gets exactly what an unknown one gets.
    live_answer = resolve(flood, live, client=client)
    unknown_answer = resolve(flood, random_bearer(), client=client)
    fresh = resolve(flood, live, client=named_client())
    same = (live_answer[0] == unknown_answer[0] == 429 and live_answer[1] == unknown_answer[1]
            and "retry-after" in live_answer[2] and "retry-after" in unknown_answer[2])
    ok = same and fresh[0] == 200
    c.check("share.resolve.throttled-answer-ignores-the-bearer", ok,
            f"live={live_answer[0]} unknown={unknown_answer[0]} fresh={fresh[0]}")
    receipt(writer, "isolation.share-resolver.throttle.independent", ok, 429, live_answer[0],
            f"live={live_answer[0]} unknown={unknown_answer[0]} fresh={fresh[0]}")


def run_through_nginx(c: Checks) -> None:
    # A client's own X-Real-IP never reaches the runner past nginx, so its
    # resolves all count as one client: the runner's 429 comes, with its
    # window's wait, within the limit.
    seen = None
    # Twice the limit and one more, in case the window that the earlier
    # resolves started ends partway.
    for n in range(2 * IP_LIMIT + 1):
        status, _, headers = resolve(FRONTEND_URL, random_bearer(), client=named_client())
        if status == 429:
            seen = (n, headers.get("retry-after"))
            break
        time.sleep(0.6)
    wait = int(seen[1]) if seen and seen[1] and seen[1].isdigit() else 0
    c.check("share.resolve.a-spoofed-real-ip-is-ignored-through-nginx", seen is not None and wait > 1,
            f"throttled_at={seen[0] if seen else None} retry_after={wait}")

    # nginx's backstop answers a burst itself.
    out: list[tuple[int, str | None]] = []
    lock = threading.Lock()

    def one() -> None:
        status, _, headers = resolve(FRONTEND_URL, random_bearer())
        with lock:
            out.append((status, headers.get("retry-after")))

    threads = [threading.Thread(target=one) for _ in range(40)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    c.check("share.resolve.nginx-backstop-answers-a-burst", any(st == 429 and ra == "1" for st, ra in out),
            f"statuses={sorted({st for st, _ in out})}")


def run_secrets(writer: ReceiptWriter) -> int:
    c = Checks()
    pb = PBClient(POCKETBASE_URL, timeout=30)
    pb.wait_healthy()
    wait_routed()
    admin = admin_token(pb)
    s = Secrets(writer)
    a = account(pb, "secrets-a")
    demo = demo_account(pb, admin)
    for acct in (a, demo):
        writer.register_secret(acct.password, f"password:{acct.tag}")
        writer.register_secret(acct.token, f"token:{acct.tag}")

    protected = run_password_uniform(c, pb, a, s, writer)
    recovered = run_create_and_rotate(c, pb, admin, a, s)
    run_concurrent_rotations(c, pb, a, s)
    run_closed_rotations(c, pb, admin, a, demo, s)
    run_limits(c, pb, a, protected, recovered["token"], s, writer)
    run_through_nginx(c)

    # The share page, and one request outside the share routes for the
    # address scan's control.
    page = raw(FRONTEND_URL, "GET", "/r", headers={"Accept": "text/html"})
    home = raw(FRONTEND_URL, "GET", "/", headers={"Accept": "text/html"})
    c.check("share.page.served", page[0] == 200 and home[0] == 200, f"page={page[0]} home={home[0]}")

    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps({
        "tokens": s.tokens, "passwords": s.passwords, "live": recovered["token"],
        "not_found": protected["not_found"], "headers": protected["headers"],
        "probe_ip": probe_address(FRONTEND_URL),
    }))
    os.chmod(STATE, 0o600)
    print(f"share-secrets: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


# ---- share-secrets-down ---------------------------------------------------------------------------------------


def run_down() -> int:
    c = Checks()
    state = json.loads(STATE.read_text())
    want = (404, base64.b64decode(state["not_found"]), tuple(state["headers"]))
    got = shape(resolve(FRONTEND_URL, state["live"]))
    c.check("share.resolve.pocketbase-down-is-the-unknown-answer", got == want, f"status={got[0]}")
    print(f"share-secrets-down: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


# ---- share-secrets-scan ----------------------------------------------------------------------------------------


def literals(tokens: list[str], passwords: list[str]) -> tuple[str, ...]:
    """Every form an issued bearer or password could be logged in."""
    out: list[str] = []
    for t in tokens:
        raw_bytes = t.encode("ascii")
        out += [t, urllib.parse.quote(t, safe=""), base64.b64encode(raw_bytes).decode(),
                base64.b64encode(raw_bytes).decode().rstrip("="), base64.urlsafe_b64encode(raw_bytes).decode().rstrip("=")]
    for p in passwords:
        b = p.encode("utf-8")
        out += [p, urllib.parse.quote(p, safe=""), hashlib.sha1(b).hexdigest(), hashlib.sha256(b).hexdigest(),
                hashlib.md5(b).hexdigest()]
    return tuple(dict.fromkeys(v for v in out if v))


def tar_hits(path: Path, values: tuple[str, ...]) -> int:
    """How many of ``values`` appear in any file inside a tarball, as bytes."""
    hits = 0
    needles = [v.encode("utf-8") for v in values]
    with tarfile.open(path) as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            data = tar.extractfile(member).read()  # type: ignore[union-attr]
            hits += sum(data.count(n) for n in needles)
    return hits


def address_lines(text: str, address: str) -> tuple[int, int]:
    """(share lines that carry ``address``, other lines that do)."""
    share = other = 0
    pattern = re.compile(r"(?<![0-9.])" + re.escape(address) + r"(?![0-9])")
    for line in text.splitlines():
        if pattern.search(line):
            if SHARE_LINE.search(line):
                share += 1
            else:
                other += 1
    return share, other


def run_scan(writer: ReceiptWriter) -> int:
    c = Checks()
    state = json.loads(STATE.read_text())
    values = literals(state["tokens"], state["passwords"])
    logs = sorted(SCAN_DIR.glob("*.log"))
    found = logscan.Findings()
    for path in logs:
        logscan.scan_text(path.read_text(errors="replace"), path.name, values, found)
    tarball = SCAN_DIR / "pb_data.tar"
    in_data = tar_hits(tarball, values) if tarball.exists() else -1

    # The control: the same scan finds a value written on purpose to a
    # scratch log here, outside the uploaded folder.
    planted = random_bearer()
    with tempfile.TemporaryDirectory() as scratch:
        log = Path(scratch) / "planted.log"
        log.write_text(f"scratch line {planted}\n")
        control = logscan.scan_text(log.read_text(), "planted", literals([planted], []))
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            info = tarfile.TarInfo("planted.db")
            data = f"row {planted}".encode()
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        tar_path = Path(scratch) / "planted.tar"
        tar_path.write_bytes(buf.getvalue())
        control_tar = tar_hits(tar_path, literals([planted], []))
    ok = (len(logs) >= 4 and found.literals == 0 and in_data == 0 and control.literals > 0 and control_tar > 0
          and len(state["tokens"]) > 0 and len(state["passwords"]) > 0)
    c.check("share.logs.no-bearer-or-password-anywhere", ok,
            f"logs={len(logs)} found={found.literals} pb_data={in_data} control={control.literals}/{control_tar}")
    receipt(writer, "isolation.logs.share-secret.absent", ok, 0, found.literals + max(in_data, 0),
            f"logs={len(logs)} found={found.literals} pb_data={in_data}")

    # No log line for a share resolve or the share page has this probe's
    # address; the control is the frontend's line for the probe's other
    # request, which has it.
    address = state["probe_ip"]
    share_lines = other_lines = 0
    for path in logs:
        s, o = address_lines(path.read_text(errors="replace"), address)
        share_lines += s
        if path.name.startswith("frontend"):
            other_lines += o
    ok = share_lines == 0 and other_lines > 0
    c.check("share.logs.no-client-address-for-a-share-request", ok,
            f"share_lines={share_lines} control_lines={other_lines}")
    receipt(writer, "isolation.logs.share-client-address.absent", ok, 0, share_lines,
            f"share_lines={share_lines} control_lines={other_lines}")
    print(f"share-secrets-scan: {c.passed} passed, {c.failed} failed")
    return 1 if c.failed else 0


def main(phase: str, writer: ReceiptWriter) -> int:
    if phase == "share-secrets":
        return run_secrets(writer)
    if phase == "share-secrets-down":
        return run_down()
    if phase == "share-secrets-scan":
        return run_scan(writer)
    print(f"unknown phase {phase!r}", file=sys.stderr)
    return 2
