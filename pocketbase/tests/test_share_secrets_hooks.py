"""The share resolver's login and throttle in pb_hooks/share_secrets.js
(ROUNDS-00B-L04).

The decisions under node, on an in-memory store with the PocketBase
store's contract (share_secrets_runner.cjs): the three throttle counters
with their limits, windows, and order, the prune, the share-resolver record
following its secret, its exact-name login, and the guard that refuses the
record on every route but its own. Then the lookup route, which counts
before it reads, and CreateShare's and RotateShareBearer's routes: one
transaction each that keeps nothing when it refuses, a kept result with no
digest or verifier, a retry that replays it, and one winner of any number
of rotations at a version. A real PocketBase runs the store in the
harness."""
from __future__ import annotations

import itertools
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
HOOKS = HERE.parent / "pb_hooks"
RUNNER = HERE / "share_secrets_runner.cjs"

T0 = 1_800_000_000
SECRET = "test-resolver-secret-placeholder-0123456789"
_keys = itertools.count(1)


def run(*steps: dict) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run([node, str(RUNNER), str(HOOKS)], input=json.dumps({"steps": list(steps)}),
                         capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def key() -> str:
    return format(next(_keys), "064x")


def resolve(ip: str, day: str, now: int, pw: str | None = None) -> dict:
    entries = [{"scope": "ip_minute", "key": ip}]
    if pw is not None:
        entries.append({"scope": "pw_15m", "key": pw})
    entries.append({"scope": "digest_day", "key": day})
    return {"call": "throttle", "entries": entries, "now": now}


# ---- the profile -------------------------------------------------------------


def test_the_limits_windows_and_order_are_pinned():
    (c,) = run({"call": "constants"})["results"]
    assert c["limits"] == {
        "ip_minute": {"limit": 60, "window_s": 60},
        "pw_15m": {"limit": 10, "window_s": 900},
        "digest_day": {"limit": 100, "window_s": 86400},
    }
    assert c["order"] == ["ip_minute", "pw_15m", "digest_day"]
    assert c["prune"] == [100, 86400]
    assert c["names"] == ["share_resolvers", "share-resolver", "share_throttle"]
    assert c["routes"] == [{"method": "POST", "path": "/api/rounds/share/lookup"}]


def test_the_hooks_and_the_runner_agree():
    (c,) = run({"call": "constants"})["results"]
    client = (ROOT / "backend" / "app" / "share_resolver_client.py").read_text()
    secrets_py = (ROOT / "backend" / "app" / "share_secrets.py").read_text()
    env, low, high = c["secret"]
    assert f'SECRET_ENV = "{env}"' in client
    assert f"SECRET_MIN_CHARS = {low}" in client and f"SECRET_MAX_CHARS = {high}" in client
    collection, username, _ = c["names"]
    assert f'COLLECTION = "{collection}"' in client and f'USERNAME = "{username}"' in client
    assert f'LOOKUP_PATH = "{c["routes"][0]["path"]}"' in client
    assert 'SCOPES = ("ip_minute", "pw_15m", "digest_day")' in client
    for scope in c["order"]:
        assert f'"{scope}"' in secrets_py


# ---- the throttle ------------------------------------------------------------


def test_a_client_gets_60_resolves_a_minute_then_waits_for_its_window():
    ip = key()
    steps = [resolve(ip, key(), T0 + i % 50) for i in range(61)]
    steps.append(resolve(ip, key(), T0 + 59))
    steps.append(resolve(ip, key(), T0 + 60))
    out = run(*steps)["results"]
    assert all(o == {"throttled": False, "retry_after": 0} for o in out[:60])
    assert out[60] == {"throttled": True, "retry_after": 60 - 10}
    assert out[61] == {"throttled": True, "retry_after": 1}
    # A new window.
    assert out[62] == {"throttled": False, "retry_after": 0}


def test_a_thousand_random_bearers_from_one_client_trip_its_limit():
    ip = key()
    out = run(*(resolve(ip, key(), T0 + i // 100) for i in range(1000)))["results"]
    assert [o["throttled"] for o in out] == [False] * 60 + [True] * 940


def test_a_client_over_its_minute_adds_no_other_counter():
    ip = key()
    days = [key() for _ in range(62)]
    pw = key()
    out = run(*(resolve(ip, d, T0) for d in days[:60]), resolve(ip, days[60], T0, pw=pw), resolve(ip, days[61], T0))
    assert out["results"][60]["throttled"] and out["results"][61]["throttled"]
    held = {row["key"] for row in out["counters"]}
    assert ip in held and set(days[:60]) <= held
    assert days[60] not in held and days[61] not in held and pw not in held


def test_password_tries_are_10_per_15_minutes_per_client_and_bearer():
    ip, other_ip, day, other_day = key(), key(), key(), key()
    pw, pw_other_bearer, pw_other_client = key(), key(), key()
    steps = [resolve(ip, day, T0 + 60 * i, pw=pw) for i in range(11)]
    steps += [
        resolve(ip, other_day, T0 + 600, pw=pw_other_bearer),
        resolve(other_ip, day, T0 + 600, pw=pw_other_client),
        resolve(ip, day, T0 + 900, pw=pw),
    ]
    out = run(*steps)["results"]
    assert [o["throttled"] for o in out[:10]] == [False] * 10
    assert out[10] == {"throttled": True, "retry_after": 900 - 600}
    # Another bearer from the same client, and the same bearer from another
    # client, have their own tries.
    assert out[11]["throttled"] is False and out[12]["throttled"] is False
    # The window ends 15 minutes after the first try.
    assert out[13]["throttled"] is False


def test_a_bearer_gets_100_resolves_a_day_from_any_client():
    day = key()
    steps = [resolve(key(), day, T0 + i) for i in range(101)]
    steps.append(resolve(key(), day, T0 + 86_399))
    steps.append(resolve(key(), day, T0 + 86_400))
    out = run(*steps)["results"]
    assert [o["throttled"] for o in out[:100]] == [False] * 100
    assert out[100] == {"throttled": True, "retry_after": 86_400 - 100}
    assert out[101] == {"throttled": True, "retry_after": 1}
    assert out[102]["throttled"] is False


def test_the_answer_reads_only_the_counters():
    # The throttle takes no lookup result, so a live bearer and a random one
    # with the same counters get the same answers.
    a = [resolve("a" * 64, "c" * 64, T0 + i) for i in range(70)]
    b = [resolve("a" * 64, "c" * 64, T0 + i) for i in range(70)]
    assert run(*a)["results"] == run(*b)["results"]


def test_a_window_starts_again_when_the_clock_moves_back():
    ip = key()
    out = run(*(resolve(ip, key(), T0) for _ in range(61)), resolve(ip, key(), T0 - 5))["results"]
    assert out[60]["throttled"] is True
    assert out[61]["throttled"] is False


def test_retry_after_is_at_least_one_whole_second():
    ip = key()
    out = run(*(resolve(ip, key(), T0) for _ in range(60)), resolve(ip, key(), T0 + 59))["results"]
    assert out[60] == {"throttled": True, "retry_after": 1}


@pytest.mark.parametrize(
    "entries",
    [
        None,
        [],
        [{"scope": "ip_minute", "key": "1" * 64}],
        [{"scope": "digest_day", "key": "1" * 64}, {"scope": "ip_minute", "key": "2" * 64}],
        [{"scope": "ip_minute", "key": "1" * 64}, {"scope": "pw_15m", "key": "2" * 64}],
        [{"scope": "pw_15m", "key": "1" * 64}, {"scope": "ip_minute", "key": "2" * 64},
         {"scope": "digest_day", "key": "3" * 64}],
        [{"scope": "ip_minute", "key": "1" * 64}, {"scope": "pw_15m", "key": "2" * 64},
         {"scope": "digest_day", "key": "3" * 64}, {"scope": "digest_day", "key": "4" * 64}],
        [{"scope": "ip_minute", "key": "1" * 64}, {"scope": "digest_day", "key": "1" * 64}],
        [{"scope": "ip_minute", "key": "1" * 63}, {"scope": "digest_day", "key": "2" * 64}],
        [{"scope": "ip_minute", "key": "A" * 64}, {"scope": "digest_day", "key": "2" * 64}],
        [{"scope": "ip_minute", "key": "1" * 64, "count": 0}, {"scope": "digest_day", "key": "2" * 64}],
        [{"scope": "ip_hour", "key": "1" * 64}, {"scope": "digest_day", "key": "2" * 64}],
        [["ip_minute", "1" * 64], ["digest_day", "2" * 64]],
    ],
    ids=["none", "empty", "one", "wrong-order", "no-day", "password-first", "four", "same-key", "short-key",
         "upper-key", "extra-field", "unknown-scope", "pairs"],
)
def test_only_the_three_counters_in_order_are_taken(entries):
    (out,) = run({"call": "checkThrottle", "input": entries})["results"]
    assert out is None


def test_the_checked_counters_are_copied_as_given():
    entries = [{"scope": "ip_minute", "key": "1" * 64}, {"scope": "pw_15m", "key": "2" * 64},
               {"scope": "digest_day", "key": "3" * 64}]
    (out,) = run({"call": "checkThrottle", "input": entries})["results"]
    assert out == entries


def test_prune_removes_at_most_100_counters_over_a_day_old_oldest_first():
    old = [{"key": key(), "scope": "digest_day", "window_start": T0 - 86_401 - i, "count": 1} for i in range(150)]
    fresh = [{"key": key(), "scope": "ip_minute", "window_start": T0 - 86_399, "count": 3}]
    steps = [{"call": "seedCounter", "row": r} for r in old + fresh]
    out = run(*steps, {"call": "prune", "now": T0})
    assert out["results"][-1] == 100
    held = {row["key"] for row in out["counters"]}
    # The oldest go first; the fresh one stays.
    assert held == {r["key"] for r in old[:50]} | {fresh[0]["key"]}
    out = run(*steps, {"call": "prune", "now": T0}, {"call": "prune", "now": T0})
    assert out["results"][-1] == 50
    assert [row["key"] for row in out["counters"]] == [fresh[0]["key"]]


def test_the_pocketbase_store_keeps_one_row_per_counter():
    ip, day = key(), key()
    runs = [{"entries": [{"scope": "ip_minute", "key": ip}, {"scope": "digest_day", "key": day}], "now": T0 + i}
            for i in range(3)]
    (out,) = run({"call": "pbStore", "runs": runs, "pruneAt": T0 + 86_401})["results"]
    assert out["out"] == [{"throttled": False, "retry_after": 0}] * 3
    # Both windows started at T0, so a day and a second later both go.
    assert out["pruned"] == 2 and out["rows"] == []
    filters = {(c["filter"], c["limit"]) for c in out["calls"]}
    assert filters == {("key = {:key}", 1), ("window_start < {:cutoff}", 100)}


def test_the_pocketbase_store_counts_up_within_a_window():
    ip, day = key(), key()
    runs = [{"entries": [{"scope": "ip_minute", "key": ip}, {"scope": "digest_day", "key": day}], "now": T0 + i}
            for i in range(3)]
    (out,) = run({"call": "pbStore", "runs": runs})["results"]
    assert sorted((r["scope"], r["count"], r["window_start"]) for r in out["rows"]) == [
        ("digest_day", 3, T0), ("ip_minute", 3, T0)]


# ---- the share-resolver record -----------------------------------------------


@pytest.mark.parametrize(
    "existing, secret, did, password",
    [
        (None, SECRET, "created", SECRET),
        ({"username": "share-resolver", "password": SECRET}, SECRET, "unchanged", SECRET),
        ({"username": "share-resolver", "password": "o" * 40}, SECRET, "updated", SECRET),
        (None, "", "skipped", None),
        (None, "short", "skipped", None),
        ({"username": "share-resolver", "password": SECRET}, "", "disabled", "r" * 64),
        ({"username": "share-resolver", "password": SECRET}, " " + SECRET, "disabled", "r" * 64),
        (None, "x" * 72, "created", "x" * 72),
        (None, "x" * 73, "skipped", None),
        (None, "test resolver secret with spaces 0123456789", "skipped", None),
    ],
    ids=["created", "unchanged", "updated", "unset", "short", "unset-later", "whitespace", "longest", "too-long",
         "inner-space"],
)
def test_the_resolver_record_follows_the_secret(existing, secret, did, password):
    (out,) = run({"call": "ensureResolver", "existing": existing, "secret": secret})["results"]
    assert out["did"] == did
    if password is None:
        assert out["records"] == []
    else:
        assert out["records"] == [{"username": "share-resolver", "password": password}]


def test_bootstrap_waits_for_the_collection_the_migration_makes():
    (out,) = run({"call": "bootstrapResolver", "collection": False, "secret": SECRET})["results"]
    assert out["did"] == "absent" and out["records"] == []
    (out,) = run({"call": "bootstrapResolver", "collection": True, "secret": SECRET})["results"]
    assert out["did"] == "created"
    assert out["records"] == [{"username": "share-resolver", "password": SECRET}]


def test_bootstrap_never_logs_the_secret():
    for secret in (SECRET, "short-but-secret-value"):
        (out,) = run({"call": "bootstrapResolver", "collection": True, "secret": secret})["results"]
        assert out["logs"] and all(secret not in line for line in out["logs"])


@pytest.mark.parametrize(
    "existing, identity, secret, did, password",
    [
        (None, "share-resolver", SECRET, "created", SECRET),
        ({"username": "share-resolver", "password": "o" * 40}, "share-resolver", SECRET, "updated", SECRET),
        ({"username": "share-resolver", "password": SECRET}, "share-resolver", SECRET, "unchanged", SECRET),
        ({"username": "share-resolver", "password": SECRET}, "share-resolver", "", "disabled", "r" * 64),
        (None, "someone-else", SECRET, None, None),
    ],
    ids=["first-login", "rotated", "same", "unset", "other-identity"],
)
def test_a_login_syncs_the_resolver_first_and_checks_the_record_as_it_is_now(existing, identity, secret, did,
                                                                              password):
    (out,) = run({"call": "syncResolverForLogin", "existing": existing, "identity": identity,
                  "secret": secret})["results"]
    assert out["did"] == did
    if password is None:
        assert out["record"] is None and out["records"] == ([existing] if existing else [])
    else:
        assert out["record"] == {"username": "share-resolver", "password": password}


@pytest.mark.parametrize(
    "segment",
    ["Share_Resolvers", "SHARE_RESOLVERS", "share_resolvérs", "c0llection0id00", None],
    ids=["another-case", "upper-case", "outside-the-name-alphabet", "the-collection-id", "no-request"],
)
def test_the_resolver_login_answers_only_its_exact_collection_name(segment):
    existing = {"username": "share-resolver", "password": "o" * 40}
    (out,) = run({"call": "syncResolverForLogin", "existing": existing, "identity": "share-resolver",
                  "secret": SECRET, "segment": segment})["results"]
    # The uniform 404, before the record follows the secret or is checked.
    assert out == {"not_found": True, "records": [existing]}


RESOLVER = {"collection": "share_resolvers", "username": "share-resolver"}
USER = {"collection": "users", "username": "someone"}


@pytest.mark.parametrize(
    "method, path",
    [
        ("GET", "/api/collections/:collection/records"),
        ("GET", "/api/collections/:collection/records/:id"),
        ("POST", "/api/collections/:collection/records"),
        ("PATCH", "/api/collections/:collection/records/:id"),
        ("DELETE", "/api/collections/:collection/records/:id"),
        ("POST", "/api/collections/:collection/auth-refresh"),
        ("POST", "/api/realtime"),
        ("POST", "/api/files/token"),
        ("GET", "/api/files/:collection/:recordId/:filename"),
        ("GET", "/api/health"),
        ("POST", "/api/rounds/admission/admit"),
        ("POST", "/api/rounds/legacy-snapshots"),
        ("GET", "/api/rounds/share/lookup"),
        ("POST", "/api/rounds/share/lookup/"),
        ("POST", "/API/ROUNDS/SHARE/LOOKUP"),
    ],
)
def test_the_resolver_record_is_refused_on_every_route_but_its_lookup(method, path):
    (out,) = run({"call": "guardResolverRequest", "principal": RESOLVER, "method": method, "path": path})["results"]
    assert out["allowed"] is False and out["forbidden"] is True
    # One content-free line: no route, id, or name.
    assert [json.loads(line) for line in out["logs"]] == [
        {"v": "obs/v1", "event": "share_resolver", "service": "pocketbase", "outcome": "refused"}]


def test_the_resolver_record_reaches_its_lookup_route():
    (out,) = run({"call": "guardResolverRequest", "principal": RESOLVER, "method": "POST",
                  "path": "/api/rounds/share/lookup"})["results"]
    assert out == {"allowed": True, "logs": []}


@pytest.mark.parametrize("principal", [None, USER], ids=["anonymous", "account"])
@pytest.mark.parametrize("path", ["/api/collections/:collection/records", "/api/rounds/share/lookup"])
def test_the_guard_leaves_every_other_caller_alone(principal, path):
    (out,) = run({"call": "guardResolverRequest", "principal": principal, "method": "POST", "path": path})["results"]
    assert out == {"allowed": True, "logs": []}


# ---- registration --------------------------------------------------------------

REGISTRATION = r"""
const path = require("path");
const [hooksDir] = process.argv.slice(1);
const seen = [];
globalThis.__hooks = hooksDir;
for (const name of ["onAfterBootstrap", "routerUse", "onRecordBeforeAuthWithPasswordRequest"]) {
  globalThis[name] = (fn, ...tags) => seen.push({ name, tags });
}
globalThis.$apis = { requireRecordAuth: (...collections) => ({ auth: collections }) };
globalThis.routerAdd = (method, route, fn, ...middlewares) => seen.push({ name: "routerAdd", method, route, middlewares });
require(path.join(hooksDir, "share_secrets.pb.js"));
process.stdout.write(JSON.stringify(seen));
"""


def test_share_secrets_pb_js_registers_its_hooks_and_routes():
    node = shutil.which("node")
    assert node
    res = subprocess.run([node, "-e", REGISTRATION, str(HOOKS)], capture_output=True, text=True, timeout=60,
                         check=True)
    as_resolver = [{"auth": ["share_resolvers"]}]
    as_account = [{"auth": ["users"]}]
    assert json.loads(res.stdout) == [
        {"name": "onAfterBootstrap", "tags": []},
        {"name": "onRecordBeforeAuthWithPasswordRequest", "tags": ["share_resolvers"]},
        # The lookup takes only share-resolver; the commands only an account.
        {"name": "routerAdd", "method": "POST", "route": "/api/rounds/share/lookup", "middlewares": as_resolver},
        {"name": "routerAdd", "method": "POST", "route": "/api/rounds/share/commands", "middlewares": as_account},
        {"name": "routerAdd", "method": "POST", "route": "/api/rounds/share/capabilities", "middlewares": as_account},
        {"name": "routerAdd", "method": "POST", "route": "/api/rounds/share/capabilities/:id/rotate",
         "middlewares": as_account},
        {"name": "routerUse", "tags": []},
    ]


def test_each_handler_requires_the_module_itself():
    # PocketBase runs every handler in its own context, so none shares a
    # value read elsewhere.
    source = (HOOKS / "share_secrets.pb.js").read_text()
    assert "function " not in source
    assert len(re.findall(r"require\(`\$\{__hooks\}/share_secrets\.js`\)", source)) == 7


def test_the_module_is_not_auto_loaded_as_a_hook_file():
    # PocketBase loads only *.pb.js files, so share_secrets.js stays a
    # require target.
    assert (HOOKS / "share_secrets.js").exists() and not (HOOKS / "share_secrets.js").name.endswith(".pb.js")


# ---- the share commands and the lookup route (ROUNDS-00B-L04 part 2) ---------------------------------

V = "share-secrets/v1"
LOOKUP_V = "share-lookup/v1"
ACCOUNT, OTHER = "acct00000000001", "acct00000000002"
KEY, SNAP_KEY, SNAP_KEY_2, KEY_2 = (f"0190f000-0000-7000-8000-00000000000{n}" for n in (1, 2, 3, 4))
FP, FP_2 = "a" * 64, "b" * 64
D1, D2, D3, D9 = "1" * 64, "2" * 64, "3" * 64, "9" * 64
PW1 = "pw1$argon2id$v=19$m=19456,t=2,p=1$c2FsdHNhbHRzYWx0c2FsdA$" + "A" * 43
CAP = "capaaaaaaaaaaa1"


def run_with(state: dict | None, *steps: dict) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    program = {"steps": list(steps), "world": state or {}}
    res = subprocess.run([node, str(RUNNER), str(HOOKS)], input=json.dumps(program), capture_output=True,
                         text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def shared() -> dict:
    return {"snapshots": {
        "snapresumeaaaa1": {"user": ACCOUNT, "source_kind": "resume", "source_id": "resumeaaaaaaaa1"},
        "snapvariantaaa1": {"user": ACCOUNT, "source_kind": "variant", "source_id": "variantaaaaaaa1"},
        "snapotheraccnt1": {"user": OTHER, "source_kind": "resume", "source_id": "resumebbbbbbbb1"},
    }}


def with_capability(**over) -> dict:
    state = shared()
    row = {"user": ACCOUNT, "snapshot": "snapresumeaaaa1", "status": "active", "expires_at": "2027-02-09 12:00:00.000Z",
           "capability_version": 1, "bearer_digest": D1, "digest_key_version": 1, "password_policy_ref": PW1,
           "purpose": "For recruiters", "revoked_reason": "", "revoked_at": "", "created": "2026-11-10 12:00:00.000Z"}
    row.update(over)
    state["capabilities"] = {CAP: row}
    return state


def begin(**over) -> dict:
    data = {"command_id": KEY, "operation": "share_create", "fingerprint": FP, "snapshot": SNAP_KEY}
    data.update(over)
    return {"call": "begin", "input": data}


def create(**over) -> dict:
    data = {"command_id": KEY, "fingerprint": FP, "snapshot_id": "snapresumeaaaa1", "purpose": None,
            "expires_at": None, "password_policy_ref": "", "bearer_digest": D1, "digest_key_version": 1}
    data.update(over)
    return {"call": "createShare", "input": data}


def rotate(account: str = ACCOUNT, cid: str = CAP, **over) -> dict:
    data = {"command_id": KEY, "fingerprint": FP, "expected_capability_version": 1, "bearer_digest": D9,
            "digest_key_version": 1}
    data.update(over)
    return {"call": "rotateShare", "account": account, "id": cid, "input": data}


def test_begin_records_the_command_and_keeps_its_first_snapshot_key():
    out = run_with(shared(), begin(), begin(snapshot=SNAP_KEY_2))
    first, again = (r["value"] for r in out["results"])
    assert first == {"status": 200, "body": {"v": V, "verdict": "new", "snapshot_command_id": SNAP_KEY}}
    # A retry gets the key its first attempt kept, so its snapshot replays.
    assert again == {"status": 200, "body": {"v": V, "verdict": "retry", "snapshot_command_id": SNAP_KEY}}
    (row,) = out["world"]["commands"]
    assert (row["account"], row["operation"], row["state"]) == (ACCOUNT, "share_create", "in_flight")
    assert row["share_snapshot_command"] == SNAP_KEY


def test_a_completed_command_answers_its_kept_result_before_anything_runs():
    out = run_with(shared(), begin(), create(), begin())
    made, replay = out["results"][1]["value"], out["results"][2]["value"]
    assert replay == {"status": 200, "body": {"v": V, "verdict": "replay", "result": made["body"]["result"]}}
    assert "setSnapshot" not in out["results"][2]["calls"]


@pytest.mark.parametrize("change", [{"fingerprint": FP_2}, {"operation": "share_rotate", "snapshot": None}])
def test_a_key_used_for_another_request_is_a_mismatch(change):
    out = run_with(shared(), begin(), begin(**change))
    assert out["results"][1]["value"] == {"status": 409, "body": {"v": V, "error": "idempotency_mismatch"}}


def test_create_makes_one_capability_and_keeps_a_result_with_no_secret():
    out = run_with(shared(), begin(), create(password_policy_ref=PW1))
    made = out["results"][1]["value"]
    assert (made["status"], made["body"]["delivery"]) == (201, "issued")
    result = made["body"]["result"]
    assert result["status"] == 201
    assert list(result["body"]) == ["capability_id", "scope", "state", "expires_at", "capability_version"]
    assert result["body"]["scope"] == {"target_kind": "legacy_artifact_snapshot", "resume_id": "resumeaaaaaaaa1",
                                       "projection_version": 1}
    assert (result["body"]["state"], result["body"]["capability_version"]) == ("active", 1)
    (row,) = out["world"]["commands"]
    assert (row["state"], row["result"]) == ("completed", result)
    (cap,) = out["world"]["capabilities"].values()
    assert (cap["bearer_digest"], cap["password_policy_ref"]) == (D1, PW1)
    kept = json.dumps(out["world"]["commands"])
    assert D1 not in kept and PW1 not in kept


def test_a_variant_share_names_its_variant():
    out = run_with(shared(), begin(), create(snapshot_id="snapvariantaaa1"))
    scope = out["results"][1]["value"]["body"]["result"]["body"]["scope"]
    assert scope == {"target_kind": "legacy_artifact_snapshot", "variant_id": "variantaaaaaaa1", "projection_version": 1}


def test_a_retry_of_a_completed_create_is_already_issued_and_makes_nothing():
    out = run_with(shared(), begin(), create(), create(bearer_digest=D2))
    first, again = out["results"][1]["value"], out["results"][2]
    assert again["value"] == {"status": 200, "body": {"v": V, "delivery": "already_issued",
                                                      "result": first["body"]["result"]}}
    assert "createCapability" not in again["calls"]
    assert len(out["world"]["capabilities"]) == 1


@pytest.mark.parametrize("over, status, code", [
    ({"snapshot_id": "snapotheraccnt1"}, 404, "not_found"),
    ({"snapshot_id": "snapmissingaaa1"}, 404, "not_found"),
    ({"password_policy_ref": "plain-text"}, 400, "invalid_request"),
])
def test_a_create_that_makes_nothing_keeps_nothing(over, status, code):
    out = run_with(shared(), create(**over))
    assert out["results"][0]["value"] == {"status": status, "body": {"v": V, "error": code}}
    assert out["world"]["commands"] == [] and out["world"]["capabilities"] == {}


def test_a_create_under_a_key_begun_for_another_request_is_refused():
    out = run_with(shared(), begin(), create(fingerprint=FP_2))
    assert out["results"][1]["value"] == {"status": 409, "body": {"v": V, "error": "idempotency_mismatch"}}
    assert out["world"]["capabilities"] == {}


def test_a_write_that_fails_keeps_nothing_and_throws_for_the_route_to_answer():
    state = dict(shared(), failCreate=True)
    out = run_with(state, create())
    assert "database is locked" in out["results"][0]["threw"]
    assert out["world"]["commands"] == [] and out["world"]["capabilities"] == {}


def test_a_digest_another_capability_holds_fails_the_write_and_keeps_nothing():
    out = run_with(with_capability(), create(command_id=KEY_2))
    assert "UNIQUE" in out["results"][0]["threw"]
    assert out["world"]["commands"] == [] and list(out["world"]["capabilities"]) == [CAP]


def test_rotate_swaps_the_digest_raises_the_version_and_keeps_a_result_with_no_secret():
    out = run_with(with_capability(), rotate())
    res = out["results"][0]["value"]
    assert (res["status"], res["body"]["delivery"]) == (200, "issued")
    assert res["body"]["result"] == {"status": 200, "body": {
        "capability_id": CAP, "state": "active", "expires_at": "2027-02-09 12:00:00.000Z", "capability_version": 2}}
    cap = out["world"]["capabilities"][CAP]
    assert (cap["bearer_digest"], cap["capability_version"], cap["password_policy_ref"]) == (D9, 2, PW1)
    kept = json.dumps(out["world"]["commands"])
    assert D9 not in kept and D1 not in kept and PW1 not in kept


def test_of_two_rotations_at_one_version_one_swaps_and_the_other_conflicts():
    out = run_with(with_capability(), rotate(bearer_digest=D2), rotate(command_id=KEY_2, bearer_digest=D3))
    first, second = (r["value"] for r in out["results"])
    assert first["status"] == 200
    assert second == {"status": 409, "body": {"v": V, "error": "capability_version_conflict"}}
    assert out["world"]["capabilities"][CAP]["bearer_digest"] == D2
    assert [c["command_id"] for c in out["world"]["commands"]] == [KEY]


def test_a_retried_rotation_is_already_issued_and_swaps_nothing_again():
    out = run_with(with_capability(), rotate(bearer_digest=D2), rotate(bearer_digest=D3))
    first, again = out["results"][0]["value"], out["results"][1]
    assert again["value"] == {"status": 200, "body": {"v": V, "delivery": "already_issued",
                                                      "result": first["body"]["result"]}}
    assert "rotateBearer" not in again["calls"]
    cap = out["world"]["capabilities"][CAP]
    assert (cap["bearer_digest"], cap["capability_version"]) == (D2, 2)


@pytest.mark.parametrize("over, account, status, code", [
    ({"status": "revoked", "revoked_reason": "owner", "revoked_at": "2026-11-11 00:00:00.000Z",
      "capability_version": 2}, ACCOUNT, 409, "capability_revoked"),
    ({"expires_at": "2026-11-01 00:00:00.000Z"}, ACCOUNT, 409, "capability_expired"),
    ({}, OTHER, 404, "not_found"),
])
def test_a_rotation_that_cannot_happen_keeps_nothing(over, account, status, code):
    state = with_capability(**over)
    out = run_with(state, rotate(account=account))
    assert out["results"][0]["value"] == {"status": status, "body": {"v": V, "error": code}}
    assert out["world"]["commands"] == []
    assert out["world"]["capabilities"] == state["capabilities"]


def test_a_rotation_under_another_key_version_is_invalid():
    out = run_with(with_capability(), rotate(digest_key_version=2))
    assert out["results"][0]["value"] == {"status": 400, "body": {"v": V, "error": "invalid_request"}}


def _lookup(now: int, digest: str = D1, capabilities: dict | None = None, pw: bool = False) -> dict:
    throttle = [{"scope": "ip_minute", "key": "c" * 64}]
    if pw:
        throttle.append({"scope": "pw_15m", "key": "d" * 64})
    throttle.append({"scope": "digest_day", "key": "e" * 64})
    return {"call": "lookup", "now": now, "capabilities": capabilities or {},
            "input": {"digest": digest, "throttle": throttle}}


FIELDS = {"id": CAP, "status": "active", "expires_at": "2027-02-09 12:00:00.000Z", "capability_version": 1,
          "snapshot": "snapresumeaaaa1", "password_policy_ref": "", "markup": "<p>x</p>"}


def test_the_lookup_answers_the_lookup_fields_or_null():
    out = run(_lookup(T0, D1, {D1: FIELDS}), _lookup(T0 + 1, D2, {D1: FIELDS}))
    found, missing = out["results"]
    assert found == {"out": {"status": 200, "body": {"v": LOOKUP_V, "throttled": False, "capability": FIELDS}},
                     "asked": [D1]}
    assert missing["out"]["body"] == {"v": LOOKUP_V, "throttled": False, "capability": None}


def test_a_throttled_lookup_reads_no_capability():
    seeded = {"call": "seedCounter", "row": {"key": "c" * 64, "scope": "ip_minute", "window_start": T0, "count": 60}}
    out = run(seeded, _lookup(T0 + 10, D1, {D1: FIELDS}))
    res = out["results"][1]
    assert res == {"out": {"status": 200, "body": {"v": LOOKUP_V, "throttled": True, "retry_after": 50}},
                   "asked": []}


def test_each_lookup_prunes_old_counters():
    old = {"call": "seedCounter", "row": {"key": "f" * 64, "scope": "digest_day", "window_start": T0, "count": 3}}
    out = run(old, _lookup(T0 + 2 * 24 * 3600))
    assert "f" * 64 not in [row["key"] for row in out["counters"]]


@pytest.mark.parametrize("data", [
    {"digest": D1},
    {"digest": "x", "throttle": [{"scope": "ip_minute", "key": "c" * 64}, {"scope": "digest_day", "key": "e" * 64}]},
    {"digest": D1, "throttle": [{"scope": "digest_day", "key": "e" * 64}]},
    {"digest": D1, "throttle": [{"scope": "ip_minute", "key": "c" * 64}, {"scope": "digest_day", "key": "e" * 64}],
     "token": "sd1_x"},
    None, [], "digest",
])
def test_the_lookup_takes_only_a_digest_and_its_counters(data):
    (res,) = run({"call": "checkLookup", "input": data})["results"]
    assert res is None


@pytest.mark.parametrize("data, ok", [
    ({"command_id": KEY, "operation": "share_create", "fingerprint": FP, "snapshot_command_id": SNAP_KEY}, True),
    ({"command_id": KEY, "operation": "share_rotate", "fingerprint": FP}, True),
    ({"command_id": KEY, "operation": "share_create", "fingerprint": FP}, False),
    ({"command_id": KEY, "operation": "share_create", "fingerprint": FP, "snapshot_command_id": KEY}, False),
    ({"command_id": KEY, "operation": "share_rotate", "fingerprint": FP, "snapshot_command_id": SNAP_KEY}, False),
    ({"command_id": KEY, "operation": "snapshot_create", "fingerprint": FP}, False),
    ({"command_id": "not-a-uuid", "operation": "share_rotate", "fingerprint": FP}, False),
    ({"command_id": KEY, "operation": "share_rotate", "fingerprint": "F" * 64}, False),
    ({"command_id": KEY, "operation": "share_rotate", "fingerprint": FP, "token": "sd1_x"}, False),
])
def test_begin_takes_only_its_own_fields(data, ok):
    (res,) = run({"call": "checkBegin", "input": data})["results"]
    assert (res is not None) is ok


CREATE_BODY = {"command_id": KEY, "fingerprint": FP, "snapshot_id": "snapresumeaaaa1", "purpose": None,
               "expires_at": None, "password_policy_ref": "", "bearer_digest": D1, "digest_key_version": 1}


@pytest.mark.parametrize("over", [
    {"token": "sd1_AbCdEfGhIjKlMnOpQrStUv"}, {"password": "correct horse"}, {"bearer_digest": "sd1_x"},
    {"snapshot_id": "SNAP"}, {"digest_key_version": 0}, {"digest_key_version": "1"}, {"password_policy_ref": 5},
    {"password_policy_ref": "x" * 513}, {"purpose": "x" * 401}, {"command_id": "x"},
])
def test_create_takes_only_its_own_fields_and_never_a_bearer_or_password(over):
    (res,) = run({"call": "checkCreate", "input": dict(CREATE_BODY, **over)})["results"]
    assert res is None


def test_a_well_formed_create_is_taken():
    (res,) = run({"call": "checkCreate", "input": CREATE_BODY})["results"]
    assert res == CREATE_BODY


ROTATE_BODY = {"command_id": KEY, "fingerprint": FP, "expected_capability_version": 1, "bearer_digest": D9,
               "digest_key_version": 1}


@pytest.mark.parametrize("over", [
    {"token": "sd1_AbCdEfGhIjKlMnOpQrStUv"}, {"expected_capability_version": 0},
    {"expected_capability_version": 1.5}, {"expected_capability_version": "1"}, {"bearer_digest": "x"},
])
def test_rotate_takes_only_its_own_fields(over):
    (res,) = run({"call": "checkRotate", "input": dict(ROTATE_BODY, **over)})["results"]
    assert res is None


RESOLVER = {"collection": "share_resolvers", "username": "share-resolver"}
ACCOUNT_RECORD = {"collection": "users", "username": "ada", "id": ACCOUNT}
RUNNER_KEY = "test-runner-key-placeholder-0123456789"
LOOKUP_BODY = {"digest": D1, "throttle": [{"scope": "ip_minute", "key": "c" * 64},
                                          {"scope": "digest_day", "key": "e" * 64}]}


@pytest.mark.parametrize("principal", [None, ACCOUNT_RECORD, {"collection": "share_resolvers", "username": "other"},
                                       {"collection": "Share_Resolvers", "username": "share-resolver"}])
def test_the_lookup_route_answers_only_share_resolver(principal):
    (res,) = run({"call": "handle", "handler": "handleLookup", "principal": principal, "data": LOOKUP_BODY})["results"]
    assert res["threw"] == "ForbiddenError"


def test_the_lookup_route_refuses_a_malformed_body():
    (res,) = run({"call": "handle", "handler": "handleLookup", "principal": RESOLVER,
                  "data": {"digest": D1}})["results"]
    assert res["answer"] == {"status": 400, "body": {"v": LOOKUP_V, "error": "invalid_request"}}


@pytest.mark.parametrize("handler", ["handleBegin", "handleCreate", "handleRotate"])
def test_the_command_routes_need_a_signed_in_account(handler):
    (res,) = run({"call": "handle", "handler": handler, "principal": None, "data": {}})["results"]
    assert res["threw"] == "UnauthorizedError"


@pytest.mark.parametrize("handler", ["handleBegin", "handleCreate", "handleRotate"])
@pytest.mark.parametrize("runner_key, sent, status, code", [
    ("", RUNNER_KEY, 503, "unconfigured"),
    (RUNNER_KEY, None, 403, "forbidden"),
    (RUNNER_KEY, "another-runner-key-placeholder-0123456789", 403, "forbidden"),
])
def test_the_command_routes_need_the_runner_key(handler, runner_key, sent, status, code):
    headers = {} if sent is None else {"x_rounds_admission_key": sent}
    (res,) = run({"call": "handle", "handler": handler, "principal": ACCOUNT_RECORD, "data": {},
                  "runnerKey": runner_key, "headers": headers, "params": {"id": CAP}})["results"]
    assert res["answer"] == {"status": status, "body": {"v": V, "error": code}}


@pytest.mark.parametrize("handler", ["handleBegin", "handleCreate", "handleRotate"])
def test_the_command_routes_refuse_a_malformed_body_before_any_write(handler):
    (res,) = run({"call": "handle", "handler": handler, "principal": ACCOUNT_RECORD, "data": {"token": "sd1_x"},
                  "runnerKey": RUNNER_KEY, "headers": {"x_rounds_admission_key": RUNNER_KEY},
                  "params": {"id": CAP}})["results"]
    assert res["answer"] == {"status": 400, "body": {"v": V, "error": "invalid_request"}}


def test_rotate_with_a_malformed_id_is_not_found_before_any_write():
    (res,) = run({"call": "handle", "handler": "handleRotate", "principal": ACCOUNT_RECORD, "data": ROTATE_BODY,
                  "runnerKey": RUNNER_KEY, "headers": {"x_rounds_admission_key": RUNNER_KEY},
                  "params": {"id": "CAPAAAAAAAAAAA1"}})["results"]
    assert res["answer"] == {"status": 404, "body": {"v": V, "error": "not_found"}}
