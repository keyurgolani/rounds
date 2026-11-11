"""The share resolver's login and throttle in pb_hooks/share_secrets.js
(ROUNDS-00B-L04).

The decisions under node, on an in-memory store with the PocketBase
store's contract (share_secrets_runner.cjs): the three throttle counters
with their limits, windows, and order, the prune, the share-resolver record
following its secret, its exact-name login, and the guard that refuses the
record on every route but its own. A real PocketBase runs the store in the
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
require(path.join(hooksDir, "share_secrets.pb.js"));
process.stdout.write(JSON.stringify(seen));
"""


def test_share_secrets_pb_js_registers_its_three_hooks():
    node = shutil.which("node")
    assert node
    res = subprocess.run([node, "-e", REGISTRATION, str(HOOKS)], capture_output=True, text=True, timeout=60,
                         check=True)
    assert json.loads(res.stdout) == [
        {"name": "onAfterBootstrap", "tags": []},
        {"name": "onRecordBeforeAuthWithPasswordRequest", "tags": ["share_resolvers"]},
        {"name": "routerUse", "tags": []},
    ]


def test_each_handler_requires_the_module_itself():
    # PocketBase runs every handler in its own context, so none shares a
    # value read elsewhere.
    source = (HOOKS / "share_secrets.pb.js").read_text()
    assert "function " not in source
    assert len(re.findall(r"require\(`\$\{__hooks\}/share_secrets\.js`\)", source)) == 3


def test_the_module_is_not_auto_loaded_as_a_hook_file():
    # PocketBase loads only *.pb.js files, so share_secrets.js stays a
    # require target.
    assert (HOOKS / "share_secrets.js").exists() and not (HOOKS / "share_secrets.js").name.endswith(".pb.js")
