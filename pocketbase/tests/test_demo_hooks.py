"""The demo account's containment hooks (ROUNDS-00B-L07 stage 1).

pocketbase/pb_hooks/demo.js runs under node with PocketBase's globals
faked: the demo gate and its alias, the boot lock, the sign-in refusal
with the demo off, the users field lock, and the refusal of share links
and AI providers, credentials, models, and settings a demo account would
own. demo.pb.js's registrations are checked too. #9's harness runs the
same hooks on the real PocketBase (harness/probes/demo_check.py).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / "pocketbase" / "pb_hooks"

RUNNER = r"""
const path = require("path");
const [hooksDir, raw] = process.argv.slice(1);
globalThis.__hooks = hooksDir;
class ApiError extends Error {
  constructor(status, message, data) { super(message); this.status = status; this.data = data; }
}
globalThis.BadRequestError = class BadRequestError extends ApiError { constructor(m, d) { super(400, m, d); } };
globalThis.ForbiddenError = class ForbiddenError extends ApiError { constructor(m, d) { super(403, m, d); } };
globalThis.UnauthorizedError = class UnauthorizedError extends ApiError { constructor(m, d) { super(401, m, d); } };
globalThis.ValidationError = class ValidationError { constructor(code, message) { this.code = code; this.message = message; } };
globalThis.$apis = { requestInfo: (ctx) => ctx.info };
let draws = 0;
globalThis.$security = { randomString: (n) => { draws += 1; return ("r" + draws).padEnd(n, "x"); } };
const demo = require(path.join(hooksDir, "demo.js"));

function record(fields, original) {
  const data = Object.assign({ calls: [] }, fields || {});
  return {
    id: data.id || "",
    getBool: (name) => data[name] === true,
    getString: (name) => (typeof data[name] === "string" ? data[name] : ""),
    setPassword: (password) => { data.calls.push("setPassword:" + password.length); },
    refreshTokenKey: () => { data.calls.push("refreshTokenKey"); },
    originalCopy: () => record(original || {}),
    data,
  };
}

function db(step) {
  const users = {};
  Object.entries(step.users || {}).forEach(([id, f]) => { users[id] = record(Object.assign({ id }, f)); });
  const providers = {};
  Object.entries(step.providers || {}).forEach(([id, f]) => { providers[id] = record(Object.assign({ id }, f)); });
  const saves = [];
  const dao = {
    findRecordsByFilter: (name, filter) => {
      if (step.failQuery) throw new Error("no such table: _collections");
      if (name !== "users" || filter !== "is_demo = true") throw new Error("unexpected query");
      return Object.values(users).filter((u) => u.getBool("is_demo"));
    },
    findRecordById: (name, id) => {
      const table = name === "users" ? users : name === "ai_providers" ? providers : {};
      if (!table[id]) throw new Error("sql: no rows in result set");
      return table[id];
    },
    saveRecord: (r) => {
      if (step.failSave) throw new Error("save failed");
      saves.push(r.id);
    },
  };
  return { users, saves, dao };
}

function outcome(fn) {
  try {
    fn();
    return { allowed: true };
  } catch (err) {
    if (err.status) {
      const data = err.data && err.data.demo ? { demo: { code: err.data.demo.code, message: err.data.demo.message } } : err.data;
      return { status: err.status, message: err.message, data: data === undefined ? null : data };
    }
    return { error: err.message };
  }
}

const ctx = (step) => ({ info: { admin: step.superuser ? { id: "admin" } : null, data: step.data || {} } });

const results = JSON.parse(raw).map((step) => {
  const store = db(step);
  globalThis.$app = { dao: () => store.dao };
  switch (step.call) {
    case "enabled":
      return demo.enabled(step.env);
    case "lockAll": {
      const out = demo.lockAll(store.dao, step.env);
      const calls = {};
      Object.entries(store.users).forEach(([id, u]) => { calls[id] = u.data.calls; });
      return { out, calls, saves: store.saves };
    }
    case "guardSignIn":
      return outcome(() => demo.guardSignIn({ record: step.record === null ? null : record(step.record) }, step.env));
    case "guardAccountUpdate":
      return outcome(() => demo.guardAccountUpdate({
        httpContext: ctx(step), record: record(step.fields, step.original), uploadedFiles: step.uploaded || {},
      }));
    case "guardAccountDelete":
      return outcome(() => demo.guardAccountDelete({ httpContext: ctx(step), record: record(step.record) }));
    case "guardEmailChange":
      return outcome(() => demo.guardEmailChange({ httpContext: ctx(step), record: record(step.record) }));
    case "guardContainedRequest":
      return outcome(() => demo.guardContainedRequest({
        httpContext: ctx(step), record: record(step.fields, step.original),
      }));
    case "guardContainedModel":
      // The model hook reads through the event's own dao, never $app's.
      globalThis.$app = { dao: () => { throw new Error("used $app.dao()"); } };
      return outcome(() => demo.guardContainedModel({ dao: store.dao, model: record(step.fields) }));
    case "constants":
      return { profile: demo.PROFILE_FIELDS, contained: demo.CONTAINED, chars: demo.PASSWORD_CHARS };
    default:
      throw new Error("unknown call " + step.call);
  }
});
process.stdout.write(JSON.stringify(results));
"""

OFF: dict = {}
ON = {"ROUNDS_ENABLE_DEMO": "true"}
DEMO = {"is_demo": True}
STANDARD = {"is_demo": False}
SIGN_IN_FAILED = {"status": 400, "message": "Failed to authenticate.", "data": None}
NOT_PERMITTED = {"status": 403, "message": "Not available in the demo.",
                 "data": {"demo": {"code": "demo_not_permitted", "message": "Not available in the demo."}}}


def run(*steps: dict) -> list:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run([node, "-e", RUNNER, str(HOOKS), json.dumps(list(steps))], capture_output=True, text=True,
                         timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


# ---- the gate --------------------------------------------------------------------------------------


@pytest.mark.parametrize("env, on", [
    ({}, False),
    ({"ROUNDS_ENABLE_DEMO": "true"}, True),
    ({"ROUNDS_ENABLE_DEMO": " YES "}, True),
    ({"ROUNDS_ENABLE_DEMO": "false"}, False),
    ({"ROUNDS_ENABLE_DEMO": "enabled"}, False),
    ({"ROUNDS_GATE_DEMO": "enabled"}, True),
    ({"ROUNDS_GATE_DEMO": "disabled", "ROUNDS_ENABLE_DEMO": "true"}, False),
    ({"ROUNDS_GATE_DEMO": "on"}, False),
])
def test_the_demo_is_off_unless_an_operator_turns_it_on(env, on):
    assert run({"call": "enabled", "env": env}) == [on]


# ---- 1. the boot lock --------------------------------------------------------------------------------


def test_with_the_demo_off_every_demo_account_gets_a_random_password_and_a_new_token_key():
    (result,) = run({"call": "lockAll", "env": OFF,
                     "users": {"demo00000000001": DEMO, "demo00000000002": DEMO, "user00000000001": STANDARD}})
    assert result["out"] == {"demo": "disabled", "locked": 2, "failed": 0}
    for account in ("demo00000000001", "demo00000000002"):
        assert result["calls"][account] == ["setPassword:48", "refreshTokenKey"]
    assert result["calls"]["user00000000001"] == []
    assert sorted(result["saves"]) == ["demo00000000001", "demo00000000002"]


def test_with_the_demo_on_the_boot_lock_changes_nothing():
    (result,) = run({"call": "lockAll", "env": ON, "users": {"demo00000000001": DEMO}})
    assert result == {"out": {"demo": "enabled"}, "calls": {"demo00000000001": []}, "saves": []}


def test_before_the_first_migration_the_boot_lock_reports_not_ready():
    (result,) = run({"call": "lockAll", "env": OFF, "failQuery": True})
    assert result["out"] == {"demo": "disabled", "code": "not_ready"}


def test_a_failed_save_is_counted_and_the_start_goes_on():
    (result,) = run({"call": "lockAll", "env": OFF, "failSave": True, "users": {"demo00000000001": DEMO}})
    assert result["out"] == {"demo": "disabled", "locked": 0, "failed": 1}


# ---- 2. sign-in -------------------------------------------------------------------------------------


def test_with_the_demo_off_a_demo_sign_in_fails_as_a_wrong_password_does():
    assert run(
        {"call": "guardSignIn", "env": OFF, "record": DEMO},
        {"call": "guardSignIn", "env": {"ROUNDS_GATE_DEMO": "nonsense"}, "record": DEMO},
    ) == [SIGN_IN_FAILED, SIGN_IN_FAILED]


def test_standard_accounts_and_the_demo_when_on_sign_in():
    assert run(
        {"call": "guardSignIn", "env": OFF, "record": STANDARD},
        {"call": "guardSignIn", "env": OFF, "record": None},
        {"call": "guardSignIn", "env": ON, "record": DEMO},
    ) == [{"allowed": True}] * 3


# ---- 3. the demo account's own record ------------------------------------------------------------


@pytest.mark.parametrize("data", [
    {"password": "a-new-password-1", "passwordConfirm": "a-new-password-1", "oldPassword": "the-old-one-123"},
    {"email": "someone@example.test"},
    {"username": "someone"},
    {"verified": False},
    {"emailVisibility": True},
    {"is_demo": False},
    {"name": "Visitor", "password": "a-new-password-1"},
])
def test_a_demo_caller_changes_nothing_but_its_profile(data):
    assert run({"call": "guardAccountUpdate", "fields": DEMO, "original": DEMO, "data": data}) == [NOT_PERMITTED]


def test_a_demo_caller_updates_its_name_bio_target_and_avatar():
    assert run(
        {"call": "guardAccountUpdate", "fields": DEMO, "original": DEMO,
         "data": {"name": "Visitor", "bio": "Trying it out", "target": "Staff engineer"}},
        {"call": "guardAccountUpdate", "fields": DEMO, "original": DEMO, "data": {}, "uploaded": {"avatar": [{}]}},
        {"call": "guardAccountUpdate", "fields": DEMO, "original": DEMO, "data": {"avatar-": "old.png"}},
    ) == [{"allowed": True}] * 3


def test_the_field_lock_holds_only_demo_callers_and_never_a_superuser():
    password = {"password": "a-new-password-1", "passwordConfirm": "a-new-password-1"}
    assert run(
        {"call": "guardAccountUpdate", "fields": STANDARD, "original": STANDARD, "data": password},
        {"call": "guardAccountUpdate", "fields": DEMO, "original": DEMO, "data": password, "superuser": True},
        {"call": "guardAccountUpdate", "fields": DEMO, "original": DEMO, "data": {"email": "a@example.test"},
         "uploaded": {"avatar": [{}]}, "superuser": True},
    ) == [{"allowed": True}] * 3


def test_an_uploaded_file_outside_the_profile_is_refused():
    assert run({"call": "guardAccountUpdate", "fields": DEMO, "original": DEMO, "data": {},
                "uploaded": {"attachments": [{}]}}) == [NOT_PERMITTED]


def test_a_demo_caller_cant_delete_its_account_or_change_its_email():
    assert run(
        {"call": "guardAccountDelete", "record": DEMO},
        {"call": "guardEmailChange", "record": DEMO},
    ) == [NOT_PERMITTED, NOT_PERMITTED]
    assert run(
        {"call": "guardAccountDelete", "record": DEMO, "superuser": True},
        {"call": "guardAccountDelete", "record": STANDARD},
        {"call": "guardEmailChange", "record": STANDARD},
    ) == [{"allowed": True}] * 3


# ---- 4. what a demo account may not own ---------------------------------------------------------------

USERS = {"demo00000000001": DEMO, "user00000000001": STANDARD}
PROVIDERS = {"prov00000000001": {"user": "demo00000000001"}, "prov00000000002": {"user": "user00000000001"}}


def test_no_client_writes_a_row_a_demo_account_would_own():
    assert run(
        {"call": "guardContainedRequest", "users": USERS, "fields": {"user": "demo00000000001"}},
        {"call": "guardContainedRequest", "users": USERS, "fields": {"user": "demo00000000001"}, "superuser": True},
        # An update of a row it already owns, whatever the new owner says.
        {"call": "guardContainedRequest", "users": USERS, "fields": {"user": "user00000000001"},
         "original": {"user": "demo00000000001"}},
        # A row keyed by its provider, as #73's credentials and models are.
        {"call": "guardContainedRequest", "users": USERS, "providers": PROVIDERS,
         "fields": {"provider": "prov00000000001"}},
    ) == [NOT_PERMITTED] * 4


def test_standard_accounts_write_their_rows():
    assert run(
        {"call": "guardContainedRequest", "users": USERS, "fields": {"user": "user00000000001"}},
        {"call": "guardContainedRequest", "users": USERS, "providers": PROVIDERS,
         "fields": {"provider": "prov00000000002"}},
        # An owner that doesn't exist is the rules' and relations' to refuse.
        {"call": "guardContainedRequest", "users": USERS, "fields": {"user": "gone00000000001"}},
        {"call": "guardContainedRequest", "users": USERS, "fields": {}},
    ) == [{"allowed": True}] * 4


def test_no_other_writer_saves_a_row_a_demo_account_would_own():
    assert run(
        {"call": "guardContainedModel", "users": USERS, "fields": {"user": "demo00000000001"}},
        {"call": "guardContainedModel", "users": USERS, "providers": PROVIDERS, "fields": {"provider": "prov00000000001"}},
        {"call": "guardContainedModel", "users": USERS, "fields": {"user": "user00000000001"}},
    ) == [{"error": "demo_not_permitted"}, {"error": "demo_not_permitted"}, {"allowed": True}]


def test_the_constants_are_the_bodys():
    (constants,) = run({"call": "constants"})
    assert constants == {
        "profile": ["name", "bio", "target", "avatar"],
        "contained": ["resume_share_links", "share_capabilities", "ai_providers", "ai_credentials",
                      "ai_provider_models", "ai_settings"],
        "chars": 48,
    }


# ---- registration --------------------------------------------------------------------------------------

REGISTRATION = r"""
const path = require("path");
const [hooksDir] = process.argv.slice(1);
const seen = [];
globalThis.__hooks = hooksDir;
for (const name of ["onAfterBootstrap", "onRecordBeforeAuthWithPasswordRequest", "onRecordBeforeAuthWithOAuth2Request",
                    "onRecordBeforeUpdateRequest", "onRecordBeforeDeleteRequest", "onRecordBeforeRequestEmailChangeRequest",
                    "onRecordBeforeCreateRequest", "onModelBeforeCreate", "onModelBeforeUpdate"]) {
  globalThis[name] = (fn, ...tags) => seen.push({ name, tags });
}
require(path.join(hooksDir, "demo.pb.js"));
process.stdout.write(JSON.stringify(seen));
"""

CONTAINED = ["resume_share_links", "share_capabilities", "ai_providers", "ai_credentials", "ai_provider_models",
             "ai_settings"]


def test_demo_pb_js_registers_each_hook_on_its_collections():
    node = shutil.which("node")
    assert node
    res = subprocess.run([node, "-e", REGISTRATION, str(HOOKS)], capture_output=True, text=True, timeout=60, check=True)
    assert json.loads(res.stdout) == [
        {"name": "onAfterBootstrap", "tags": []},
        {"name": "onRecordBeforeAuthWithPasswordRequest", "tags": ["users"]},
        {"name": "onRecordBeforeAuthWithOAuth2Request", "tags": ["users"]},
        {"name": "onRecordBeforeUpdateRequest", "tags": ["users"]},
        {"name": "onRecordBeforeDeleteRequest", "tags": ["users"]},
        {"name": "onRecordBeforeRequestEmailChangeRequest", "tags": ["users"]},
        {"name": "onRecordBeforeCreateRequest", "tags": CONTAINED},
        {"name": "onRecordBeforeUpdateRequest", "tags": CONTAINED},
        {"name": "onModelBeforeCreate", "tags": CONTAINED},
        {"name": "onModelBeforeUpdate", "tags": CONTAINED},
    ]


def test_each_handler_reads_the_demo_gate_itself():
    # PocketBase runs every handler in its own context, so none shares a
    # value read elsewhere (test_hooks.py holds the signup hook to the same).
    source = (HOOKS / "demo.pb.js").read_text()
    assert "function " not in source
    for name in ("ROUNDS_GATE_DEMO", "ROUNDS_ENABLE_DEMO"):
        assert source.count(f'$os.getenv("{name}")') == 3, name
    assert len(re.findall(r"require\(`\$\{__hooks\}/demo\.js`\)", source)) == 10


def test_the_demo_module_is_not_auto_loaded_as_a_hook_file():
    # PocketBase loads only *.pb.js files, so demo.js stays a require target.
    assert (HOOKS / "demo.js").exists() and not (HOOKS / "demo.js").name.endswith(".pb.js")
