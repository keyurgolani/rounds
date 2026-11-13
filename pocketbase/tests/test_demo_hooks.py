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
import time
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
// What the hooks log, for the "logged" step.
const logs = [];
console.log = (line) => { logs.push(JSON.parse(line)); };
const demo = require(path.join(hooksDir, "demo.js"));

function record(fields, original) {
  const data = Object.assign({ calls: [] }, fields || {});
  return {
    id: data.id || "",
    tableName: () => data.table || "",
    getBool: (name) => data[name] === true,
    getString: (name) => (typeof data[name] === "string" ? data[name] : ""),
    // A file field's names, as PocketBase reads them: a string is one name.
    getStringSlice: (name) => (typeof data[name] === "string" && data[name] ? [data[name]] : []),
    setPassword: (password) => { data.calls.push("setPassword:" + password.length); },
    refreshTokenKey: () => { data.calls.push("refreshTokenKey"); },
    // PocketBase's original copy keeps the record's collection.
    originalCopy: () => record(Object.assign({ table: data.table }, original || {})),
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
      if (step.failQuery) throw new Error(step.failQuery === true ? "no such table: users" : step.failQuery);
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

const ctx = (step) => ({
  info: {
    admin: step.superuser ? { id: "admin" } : null,
    data: step.data || {},
    authRecord: step.auth === undefined || step.auth === null ? null : record(step.auth),
  },
});
// A contained row: its collection defaults to ai_settings.
const row = (step, fields) => Object.assign({ table: step.table || "ai_settings" }, fields || {});

function exec(step) {
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
    case "guardPasswordOnly":
      // A sign-in event: the record it would sign in to, if any, and the
      // request's own session, if it carried one.
      return outcome(() => demo.guardPasswordOnly({
        httpContext: ctx(step), record: step.record ? record(step.record) : null,
      }, step.env));
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
        httpContext: ctx(step), record: record(row(step, step.fields), step.original),
      }));
    case "guardContainedModel":
      // The model hook reads through the event's own dao, never $app's.
      globalThis.$app = { dao: () => { throw new Error("used $app.dao()"); } };
      return outcome(() => demo.guardContainedModel({ dao: store.dao, model: record(row(step, step.fields)) }));
    case "guardSession":
      return outcome(() => demo.guardSession(ctx(step), step.env));
    case "lockFailed":
      return demo.lockFailed(step.out);
    case "constants":
      return {
        profile: demo.PROFILE_FIELDS, contained: demo.CONTAINED, chars: demo.PASSWORD_CHARS, owners: demo.OWNERS,
        seeded: demo.SEEDED_PROFILE, reset: demo.RESET, reset_extra: demo.RESET_EXTRA,
        not_demo_writable: demo.NOT_DEMO_WRITABLE, kept: demo.KEPT,
      };
    case "logged": {
      logs.length = 0;
      const result = exec(step.step);
      return { result, logs: logs.slice() };
    }
    default:
      throw new Error("unknown call " + step.call);
  }
}
process.stdout.write(JSON.stringify(JSON.parse(raw).map(exec)));
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


def test_any_other_query_failure_is_query_failed_not_not_ready():
    (result,) = run({"call": "lockAll", "env": OFF, "failQuery": "database is locked"})
    assert result["out"] == {"demo": "disabled", "code": "query_failed"}


def test_a_lock_that_couldnt_finish_is_logged_as_an_error():
    assert run(
        {"call": "lockFailed", "out": {"demo": "disabled", "code": "query_failed"}},
        {"call": "lockFailed", "out": {"demo": "disabled", "locked": 1, "failed": 1}},
        {"call": "lockFailed", "out": {"demo": "disabled", "locked": 2, "failed": 0}},
        {"call": "lockFailed", "out": {"demo": "disabled", "code": "not_ready"}},
        {"call": "lockFailed", "out": {"demo": "enabled"}},
    ) == [True, True, False, False, False]


def test_a_failed_save_is_counted_and_the_start_goes_on():
    (result,) = run({"call": "lockAll", "env": OFF, "failSave": True, "users": {"demo00000000001": DEMO}})
    assert result["out"] == {"demo": "disabled", "locked": 0, "failed": 1}


# ---- 2. sign-in -------------------------------------------------------------------------------------


def test_the_demo_account_signs_in_with_its_password_only():
    # On or off: any other sign-in to a demo account, or from a demo
    # session, gets the answer a failed sign-in gets.
    assert run(
        {"call": "guardPasswordOnly", "env": ON, "record": DEMO},
        {"call": "guardPasswordOnly", "env": OFF, "record": DEMO},
        {"call": "guardPasswordOnly", "env": ON, "record": None, "auth": DEMO},
        {"call": "guardPasswordOnly", "env": ON, "record": STANDARD, "auth": DEMO},
    ) == [SIGN_IN_FAILED] * 4


def test_other_accounts_keep_their_other_sign_in_methods():
    assert run(
        {"call": "guardPasswordOnly", "env": ON, "record": STANDARD},
        {"call": "guardPasswordOnly", "env": OFF, "record": STANDARD, "auth": STANDARD},
        {"call": "guardPasswordOnly", "env": ON, "record": None},
    ) == [{"allowed": True}] * 3


# demo.pb.js's own sign-in registrations, driven as PocketBase calls them,
# so a hook wired to the wrong guard, or not at all, fails here too.
SIGN_IN_HOOKS = r"""
const path = require("path");
const [hooksDir, raw] = process.argv.slice(1);
globalThis.__hooks = hooksDir;
class ApiError extends Error { constructor(s, m) { super(m); this.status = s; } }
globalThis.BadRequestError = class extends ApiError { constructor(m) { super(400, m); } };
globalThis.ForbiddenError = class extends ApiError { constructor(m) { super(403, m); } };
globalThis.UnauthorizedError = class extends ApiError { constructor(m) { super(401, m); } };
globalThis.ValidationError = class { constructor(c, m) { this.code = c; this.message = m; } };
globalThis.$apis = { requestInfo: (c) => c.info };
console.log = () => {};
let env = {};
globalThis.$os = { getenv: (name) => env[name] || "" };
const hooks = {};
for (const name of ["onAfterBootstrap", "routerUse", "onRecordBeforeAuthWithPasswordRequest",
                    "onRecordBeforeAuthWithOAuth2Request", "onRecordBeforeUpdateRequest",
                    "onRecordBeforeDeleteRequest", "onRecordBeforeRequestEmailChangeRequest",
                    "onRecordBeforeCreateRequest", "onModelBeforeCreate", "onModelBeforeUpdate",
                    "routerAdd", "cronAdd"]) {
  globalThis[name] = (fn) => { (hooks[name] = hooks[name] || []).push(fn); };
}
require(path.join(hooksDir, "demo.pb.js"));
const rec = (f) => ({ getBool: (k) => f[k] === true, getString: () => "" });
process.stdout.write(JSON.stringify(JSON.parse(raw).map((step) => {
  env = step.env;
  try {
    (hooks[step.hook] || []).forEach((fn) => fn({
      record: step.record ? rec(step.record) : null,
      httpContext: { info: { authRecord: step.auth ? rec(step.auth) : null } },
    }));
    return "allowed";
  } catch (err) {
    return err.message;
  }
})));
"""
PASSWORD_HOOK = "onRecordBeforeAuthWithPasswordRequest"
# PocketBase 0.22's hook for every other way to sign in to a users record.
OTHER_SIGN_IN_HOOK = "onRecordBeforeAuthWithOAuth2Request"


def sign_in_run(*steps: dict) -> list:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run([node, "-e", SIGN_IN_HOOKS, str(HOOKS), json.dumps(list(steps))], capture_output=True,
                         text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def test_the_registered_sign_in_hooks_hold_the_demo_account_to_its_password():
    failed = SIGN_IN_FAILED["message"]
    assert sign_in_run(
        {"hook": OTHER_SIGN_IN_HOOK, "env": ON, "record": DEMO},
        {"hook": OTHER_SIGN_IN_HOOK, "env": OFF, "record": DEMO},
        {"hook": OTHER_SIGN_IN_HOOK, "env": ON, "record": None, "auth": DEMO},
        {"hook": OTHER_SIGN_IN_HOOK, "env": ON, "record": STANDARD, "auth": DEMO},
        {"hook": PASSWORD_HOOK, "env": OFF, "record": DEMO},
    ) == [failed] * 5
    assert sign_in_run(
        {"hook": PASSWORD_HOOK, "env": ON, "record": DEMO},
        {"hook": OTHER_SIGN_IN_HOOK, "env": ON, "record": STANDARD},
        {"hook": OTHER_SIGN_IN_HOOK, "env": OFF, "record": STANDARD, "auth": STANDARD},
        {"hook": OTHER_SIGN_IN_HOOK, "env": ON, "record": None},
    ) == ["allowed"] * 4


def test_with_the_demo_off_a_demo_sign_in_fails_as_a_wrong_password_does():
    assert run(
        {"call": "guardSignIn", "env": OFF, "record": DEMO},
        {"call": "guardSignIn", "env": {"ROUNDS_GATE_DEMO": "nonsense"}, "record": DEMO},
    ) == [SIGN_IN_FAILED, SIGN_IN_FAILED]


NO_SESSION = {"status": 401, "message": "The request requires valid record authorization token to be set.",
              "data": None}


def test_with_the_demo_off_no_request_a_demo_token_authenticates_goes_through():
    # A token from before the start, even if the boot lock never rotated it.
    assert run(
        {"call": "guardSession", "env": OFF, "auth": DEMO},
        {"call": "guardSession", "env": {"ROUNDS_GATE_DEMO": "nonsense"}, "auth": DEMO},
    ) == [NO_SESSION, NO_SESSION]


def test_standard_sessions_anonymous_requests_and_the_demo_when_on_go_through():
    assert run(
        {"call": "guardSession", "env": OFF, "auth": STANDARD},
        {"call": "guardSession", "env": OFF, "auth": None},
        {"call": "guardSession", "env": OFF, "auth": None, "superuser": True},
        {"call": "guardSession", "env": ON, "auth": DEMO},
    ) == [{"allowed": True}] * 4


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
])
def test_a_demo_caller_changes_nothing_but_its_profile(data):
    assert run({"call": "guardAccountUpdate", "fields": DEMO, "original": DEMO, "data": data}) == [NOT_PERMITTED]


def test_a_demo_caller_changing_its_demo_flag_gets_the_admission_answer_whichever_hook_runs_first():
    # The record carries the change, as PocketBase's update request does.
    assert run({"call": "guardAccountUpdate", "fields": STANDARD, "original": DEMO, "data": {"is_demo": False}}) == [
        {"status": 400, "message": "These account fields can't be changed.", "data": None}
    ]


LOCKED = {"status": 400, "message": "These account fields can't be changed.", "data": None}
# 1700000600_demo_user.js's seeded profile, and one that differs from it.
SEEDED = {"name": "Rounds Demo", "bio": "Disposable hosted demo account. Changes reset on logout.",
          "target": "Explore Rounds"}
SEEDED_DEMO = dict(DEMO, **SEEDED)
OTHER_DEMO = dict(DEMO, name="Visitor", bio="", target="")


# Each step's `fields` is the record as PocketBase would save it, and
# `original` the record as stored.
@pytest.mark.parametrize("original, data, saved", [
    (SEEDED_DEMO, {"name": "Visitor"}, dict(SEEDED_DEMO, name="Visitor")),
    (SEEDED_DEMO, {"bio": ""}, dict(SEEDED_DEMO, bio="")),
    (SEEDED_DEMO, {"target": None}, dict(SEEDED_DEMO, target="")),
    (SEEDED_DEMO, dict(SEEDED, name="Visitor"), dict(SEEDED_DEMO, name="Visitor")),
    # A form the request data doesn't show: the record as it would save.
    (SEEDED_DEMO, {}, dict(SEEDED_DEMO, name="Visitor")),
    # Beside another key, the profile's answer comes first.
    (SEEDED_DEMO, {"name": "Visitor", "password": "a-new-password-1"}, dict(SEEDED_DEMO, name="Visitor")),
    # A modifier or an upload under a profile field's name, on a record
    # that doesn't hold the seeded profile.
    (OTHER_DEMO, {"name+": "x"}, OTHER_DEMO),
    (OTHER_DEMO, {"+name": "x"}, OTHER_DEMO),
    (OTHER_DEMO, {"bio-": "x"}, OTHER_DEMO),
    (OTHER_DEMO, {"target": "Explore Rounds"}, dict(OTHER_DEMO, target="Explore Rounds")),
])
def test_a_demo_caller_cant_change_its_name_bio_or_target_in_any_form(original, data, saved):
    assert run({"call": "guardAccountUpdate", "fields": saved, "original": original, "data": data}) == [LOCKED]


def test_an_upload_under_a_profile_fields_name_is_held_to_the_profile_lock():
    assert run({"call": "guardAccountUpdate", "fields": OTHER_DEMO, "original": OTHER_DEMO, "data": {},
                "uploaded": {"target": [{}]}}) == [LOCKED]


def test_a_request_leaving_exactly_the_seeded_profile_goes_through():
    # What the sign-out reset sends today, on a record that holds the
    # seeded profile or one that doesn't.
    assert run(
        {"call": "guardAccountUpdate", "fields": SEEDED_DEMO, "original": SEEDED_DEMO, "data": dict(SEEDED)},
        {"call": "guardAccountUpdate", "fields": SEEDED_DEMO, "original": OTHER_DEMO, "data": dict(SEEDED)},
        {"call": "guardAccountUpdate", "fields": SEEDED_DEMO, "original": SEEDED_DEMO, "data": {"name": "Rounds Demo"}},
        {"call": "guardAccountUpdate", "fields": SEEDED_DEMO, "original": SEEDED_DEMO, "data": {"name+": "x"}},
    ) == [{"allowed": True}] * 4


def test_the_profile_lock_answers_as_the_other_locked_fields_do_whichever_hook_runs_first():
    flag = dict(SEEDED_DEMO, name="Visitor", is_demo=False)
    file = dict(SEEDED_DEMO, name="Visitor", avatar="face.png")
    assert run(
        {"call": "guardAccountUpdate", "fields": flag, "original": SEEDED_DEMO, "data": {"name": "Visitor", "is_demo": False}},
        {"call": "guardAccountUpdate", "fields": file, "original": SEEDED_DEMO, "data": {"name": "Visitor", "avatar": "face.png"}},
        {"call": "guardAccountUpdate", "fields": dict(SEEDED_DEMO, name="Visitor"), "original": SEEDED_DEMO,
         "data": {"name": "Visitor"}},
    ) == [LOCKED] * 3


def test_the_profile_lock_holds_only_demo_callers_and_never_a_superuser():
    standard = dict(STANDARD, **SEEDED)
    assert run(
        {"call": "guardAccountUpdate", "fields": dict(standard, name="Visitor"), "original": standard,
         "data": {"name": "Visitor"}},
        {"call": "guardAccountUpdate", "fields": dict(SEEDED_DEMO, name="Visitor"), "original": SEEDED_DEMO,
         "data": {"name": "Visitor"}, "superuser": True},
    ) == [{"allowed": True}] * 2


def test_the_profile_lock_logs_nothing():
    (result,) = run({"call": "logged", "step": {"call": "guardAccountUpdate", "fields": dict(SEEDED_DEMO, name="Visitor"),
                                                "original": SEEDED_DEMO, "data": {"name": "Visitor"}}})
    assert result == {"result": LOCKED, "logs": []}


def test_the_seeded_profile_is_the_migrations():
    (constants,) = run({"call": "constants"})
    migration = (ROOT / "pocketbase" / "pb_migrations" / "1700000600_demo_user.js").read_text()
    for field, value in constants["seeded"].items():
        assert f'demo.set("{field}", {json.dumps(value)});' in migration, field
    assert constants["seeded"] == SEEDED


def test_a_demo_caller_cant_change_its_profile_file():
    # In any form, alone or beside its text fields, with profile_files.js's
    # answer whichever users update hook PocketBase runs first.
    stored = dict(DEMO, avatar="face.png")
    steps = [
        {"call": "guardAccountUpdate", "fields": DEMO, "original": DEMO, "data": {}, "uploaded": {"avatar": [{}]}},
        {"call": "guardAccountUpdate", "fields": stored, "original": stored, "data": {"avatar-": "face.png"}},
        {"call": "guardAccountUpdate", "fields": stored, "original": stored, "data": {"avatar+": "face.png"}},
        {"call": "guardAccountUpdate", "fields": stored, "original": stored, "data": {"avatar": ""}},
        {"call": "guardAccountUpdate", "fields": stored, "original": stored, "data": {"avatar": None}},
        {"call": "guardAccountUpdate", "fields": DEMO, "original": DEMO, "data": {"name": "Visitor", "avatar": "face.png"}},
        # The record as it would save, whatever the request named.
        {"call": "guardAccountUpdate", "fields": DEMO, "original": stored, "data": {"name": "Visitor"}},
    ]
    assert run(*steps) == [LOCKED] * len(steps)


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
        {"call": "guardContainedRequest", "users": USERS, "providers": PROVIDERS, "table": "ai_credentials",
         "fields": {"provider": "prov00000000001"}},
    ) == [NOT_PERMITTED] * 4


def test_standard_accounts_write_their_rows():
    assert run(
        {"call": "guardContainedRequest", "users": USERS, "fields": {"user": "user00000000001"}},
        {"call": "guardContainedRequest", "users": USERS, "providers": PROVIDERS, "table": "ai_provider_models",
         "fields": {"provider": "prov00000000002"}},
        # An owner that doesn't exist is the rules' and relations' to refuse.
        {"call": "guardContainedRequest", "users": USERS, "fields": {"user": "gone00000000001"}},
        {"call": "guardContainedRequest", "users": USERS, "fields": {}},
    ) == [{"allowed": True}] * 4


def test_no_other_writer_saves_a_row_a_demo_account_would_own():
    assert run(
        {"call": "guardContainedModel", "users": USERS, "fields": {"user": "demo00000000001"}},
        {"call": "guardContainedModel", "users": USERS, "providers": PROVIDERS, "table": "ai_credentials",
         "fields": {"provider": "prov00000000001"}},
        {"call": "guardContainedModel", "users": USERS, "fields": {"user": "user00000000001"}},
    ) == [{"error": "demo_not_permitted"}, {"error": "demo_not_permitted"}, {"allowed": True}]


def test_a_collection_with_no_owner_entry_is_refused_outright():
    assert run(
        {"call": "guardContainedRequest", "users": USERS, "table": "not_mapped", "fields": {"user": "user00000000001"}},
        {"call": "guardContainedModel", "users": USERS, "table": "not_mapped", "fields": {"user": "user00000000001"}},
    ) == [NOT_PERMITTED, {"error": "demo_not_permitted"}]


def test_the_constants_are_the_bodys():
    (constants,) = run({"call": "constants"})
    assert constants == {
        "profile": ["name", "bio", "target"],
        "contained": ["resume_share_links", "share_capabilities", "ai_providers", "ai_credentials",
                      "ai_provider_models", "ai_settings"],
        "chars": 48,
        "owners": {
            "resume_share_links": {"field": "user"},
            "share_capabilities": {"field": "user"},
            "ai_providers": {"field": "user"},
            "ai_credentials": {"via": "provider"},
            "ai_provider_models": {"via": "provider"},
            "ai_settings": {"field": "user"},
        },
        "seeded": SEEDED,
        "reset": [
            "exp_anecdote_bullets", "exp_project_bullets", "exp_project_anecdotes", "exp_job_bullets",
            "exp_job_anecdotes", "exp_job_projects",
            "experience_bullets", "experience_anecdotes", "experience_projects", "experience_jobs",
            "resume_versions", "resume_variants", "resumes",
            "ai_coding_attempts", "take_home_attempts", "ai_coding_drafts", "take_home_drafts", "question_timers",
            "todos", "code_drafts", "offers", "interview_rounds", "user_progress", "user_preferences", "applications",
            "campaigns",
        ],
        "reset_extra": ["execution_jobs", "execution_envelopes", "admission_commands", "external_auths"],
        "not_demo_writable": ["resume_share_views", "legacy_artifact_snapshots"],
        "kept": ["admission_commands", "admission_counters", "admission_leases"],
    }


def test_each_denial_logs_one_line_without_an_id_or_a_value():
    line = {"v": "obs/v1", "event": "demo_denied", "service": "pocketbase"}
    results = run(
        {"call": "logged", "step": {"call": "guardSignIn", "env": OFF, "record": DEMO}},
        {"call": "logged", "step": {"call": "guardAccountUpdate", "fields": DEMO, "original": DEMO,
                                    "data": {"email": "someone@example.test"}}},
        {"call": "logged", "step": {"call": "guardAccountDelete", "record": DEMO}},
        {"call": "logged", "step": {"call": "guardEmailChange", "record": DEMO}},
        {"call": "logged", "step": {"call": "guardContainedRequest", "users": USERS,
                                    "fields": {"user": "demo00000000001", "table": "ai_providers"}}},
        {"call": "logged", "step": {"call": "guardContainedModel", "users": USERS,
                                    "fields": {"user": "demo00000000001", "table": "ai_settings"}}},
        {"call": "logged", "step": {"call": "guardPasswordOnly", "env": ON, "record": DEMO}},
        {"call": "logged", "step": {"call": "guardPasswordOnly", "env": OFF, "record": None, "auth": DEMO}},
    )
    assert [r["logs"] for r in results] == [
        [dict(line, code="demo_off", on="sign_in", collection="users")],
        [dict(line, code="demo_not_permitted", on="update", collection="users")],
        [dict(line, code="demo_not_permitted", on="delete", collection="users")],
        [dict(line, code="demo_not_permitted", on="email_change", collection="users")],
        [dict(line, code="demo_not_permitted", on="save", collection="ai_providers")],
        [dict(line, code="demo_not_permitted", on="model_save", collection="ai_settings")],
        [dict(line, code="demo_not_permitted", on="sign_in", collection="users")],
        [dict(line, code="demo_off", on="sign_in", collection="users")],
    ]
    assert "demo00000000001" not in json.dumps(results[4]["logs"] + results[5]["logs"])


def test_an_allowed_write_logs_nothing():
    results = run(
        {"call": "logged", "step": {"call": "guardSignIn", "env": ON, "record": DEMO}},
        {"call": "logged", "step": {"call": "guardAccountUpdate", "fields": SEEDED_DEMO, "original": SEEDED_DEMO,
                                    "data": dict(SEEDED)}},
        {"call": "logged", "step": {"call": "guardContainedModel", "users": USERS,
                                    "fields": {"user": "user00000000001", "table": "ai_settings"}}},
        {"call": "logged", "step": {"call": "guardPasswordOnly", "env": ON, "record": STANDARD}},
    )
    assert [r["result"] for r in results] == [{"allowed": True}] * 4
    assert [r["logs"] for r in results] == [[], [], [], []]


# Collections the OWNERS map names before their leaf adds them. The leaf
# that adds one confirms its entry here and drops it from this set.
NOT_YET = {"ai_credentials", "ai_provider_models"}


def _collection_blocks() -> dict[str, str]:
    """Each collection a migration defines, with the text of its latest definition."""
    blocks: dict[str, str] = {}
    for path in sorted((ROOT / "pocketbase" / "pb_migrations").glob("*.js")):
        for part in path.read_text().split("new Collection(")[1:]:
            named = re.match(r'\s*\{\s*name:\s*"([a-z0-9_]+)"', part)
            if named:
                blocks[named.group(1)] = part  # the latest definition wins
    return blocks


def test_every_contained_collection_names_its_owner_in_its_schema():
    (constants,) = run({"call": "constants"})
    blocks = _collection_blocks()
    assert {"resume_share_links", "ai_providers", "ai_settings"} <= set(blocks)
    for name, spec in constants["owners"].items():
        if name not in blocks:
            assert name in NOT_YET, f"{name} has an OWNERS entry but no migration defines it"
            continue
        assert name not in NOT_YET, f"{name} exists now: confirm its OWNERS entry and drop it from NOT_YET"
        field = spec.get("field") or spec["via"]
        assert re.search(r'name:\s*"' + field + r'",\s*type:\s*"relation"', blocks[name]), (name, field)


# ---- 5 and 6. the reset, the sign-out route, and the sweep -----------------------------------------------

# The reset runs on a table-backed Dao: filters of the forms the hooks
# send, transactions that roll back on a throw and count every row they
# delete, the two cascades the execution store relies on (a job's
# attempts, a command's leases), and the sign-ins an account holds besides
# its password (`auths`). `failOn` makes deletes in one collection throw.
RESET_RUNNER = r"""
const path = require("path");
const [hooksDir] = process.argv.slice(1);
// The step comes on stdin: a big table is over Linux's limit for one
// command-line argument.
const raw = require("fs").readFileSync(0, "utf8");
globalThis.__hooks = hooksDir;
class ApiError extends Error {
  constructor(status, message, data) { super(message); this.status = status; this.data = data; }
}
globalThis.BadRequestError = class extends ApiError { constructor(m, d) { super(400, m, d); } };
globalThis.ForbiddenError = class extends ApiError { constructor(m, d) { super(403, m, d); } };
globalThis.UnauthorizedError = class extends ApiError { constructor(m, d) { super(401, m, d); } };
globalThis.NotFoundError = class extends ApiError {
  constructor(m, d) { super(404, m || "The requested resource wasn't found.", d); }
};
globalThis.ValidationError = class { constructor(code, message) { this.code = code; this.message = message; } };
globalThis.$apis = { requestInfo: (c) => c.info };
const out = { logs: [], errors: [] };
console.log = (line) => { out.logs.push(JSON.parse(line)); };
console.error = (line) => { out.errors.push(JSON.parse(line)); };
const demo = require(path.join(hooksDir, "demo.js"));
const step = JSON.parse(raw);

let tables = JSON.parse(JSON.stringify(step.tables || {}));
let auths = JSON.parse(JSON.stringify(step.auths || []));
const stats = { transactions: 0, perTransaction: [], order: [], saves: 0 };
let current = 0;

function wrap(table, row) {
  return {
    id: row.id,
    tableName: () => table,
    getString: (f) => (row[f] === undefined || row[f] === null ? "" : String(row[f])),
    getInt: (f) => Number(row[f] || 0),
    getBool: (f) => row[f] === true,
    set: (f, v) => { row[f] = v; },
    _row: row,
  };
}
function matches(row, filter, params) {
  return filter.split(" && ").every((term) => {
    let m = term.match(/^(\w+) (=|!=) \{:(\w+)\}$/);
    if (m) return m[2] === "=" ? row[m[1]] === params[m[3]] : row[m[1]] !== params[m[3]];
    m = term.match(/^(\w+) (=|!=) '([^']*)'$/);
    if (m) return m[2] === "=" ? row[m[1]] === m[3] : row[m[1]] !== m[3];
    m = term.match(/^(\w+) = (true|false)$/);
    if (m) return (row[m[1]] === true) === (m[2] === "true");
    throw new Error("unexpected filter " + filter);
  });
}
function sorted(rows, sort) {
  if (!sort) return rows;
  const desc = sort.startsWith("-");
  const field = desc ? sort.slice(1) : sort;
  return rows.slice().sort((a, b) => (a[field] < b[field] ? -1 : a[field] > b[field] ? 1 : 0) * (desc ? -1 : 1));
}
const CASCADES = { execution_jobs: ["execution_attempts", "job"], admission_commands: ["admission_leases", "command"] };
const dao = {
  findRecordsByFilter: (name, filter, sort, limit, offset, params) => {
    const rows = sorted((tables[name] || []).filter((row) => matches(row, filter, params || {})), sort);
    return (limit ? rows.slice(0, limit) : rows).map((row) => wrap(name, row));
  },
  findRecordById: (name, id) => {
    const row = (tables[name] || []).find((r) => r.id === id);
    if (!row) throw new Error("sql: no rows in result set");
    return wrap(name, row);
  },
  findCollectionByNameOrId: (name) => ({ name }),
  deleteRecord: (record) => {
    const table = record.tableName();
    if (step.failOn === table) throw new Error("delete failed");
    tables[table] = (tables[table] || []).filter((r) => r.id !== record.id);
    stats.order.push(table);
    current += 1;
    const cascade = CASCADES[table];
    if (cascade) {
      const kept = (tables[cascade[0]] || []).filter((r) => r[cascade[1]] !== record.id);
      current += (tables[cascade[0]] || []).length - kept.length;
      tables[cascade[0]] = kept;
    }
  },
  saveRecord: (record) => {
    if (step.failOn === "users") throw new Error("save failed");
    stats.saves += 1;
  },
  findAllExternalAuthsByRecord: (record) => auths.filter((a) => a.recordId === record.id).map((a) => ({ id: a.id })),
  deleteExternalAuth: (auth) => {
    if (step.failOn === "external_auths") throw new Error("delete failed");
    auths = auths.filter((a) => a.id !== auth.id);
    current += 1;
  },
  runInTransaction: (fn) => {
    const before = JSON.stringify({ tables, auths });
    stats.transactions += 1;
    current = 0;
    try {
      fn(dao);
    } catch (err) {
      ({ tables, auths } = JSON.parse(before));
      throw err;
    } finally {
      stats.perTransaction.push(current);
    }
  },
};
globalThis.$app = { dao: () => dao };

function outcome(fn) {
  try {
    return fn();
  } catch (err) {
    return { status: err.status, message: err.message };
  }
}
function context() {
  return {
    info: { admin: step.superuser ? { id: "admin" } : null, authRecord: step.auth ? wrap("users", step.auth) : null },
    json: (status, body) => ({ status, body }),
    noContent: (status) => ({ status }),
  };
}

// demo.pb.js's own cron job, as PocketBase runs it: its callback, the
// gate it reads, and the clock.
function cron() {
  let job = null;
  for (const name of ["onAfterBootstrap", "routerUse", "onRecordBeforeAuthWithPasswordRequest",
                      "onRecordBeforeAuthWithOAuth2Request", "onRecordBeforeUpdateRequest",
                      "onRecordBeforeDeleteRequest", "onRecordBeforeRequestEmailChangeRequest",
                      "onRecordBeforeCreateRequest", "onModelBeforeCreate", "onModelBeforeUpdate", "routerAdd"]) {
    globalThis[name] = () => undefined;
  }
  globalThis.cronAdd = (id, schedule, fn) => { if (id === "rounds_demo_reset") job = fn; };
  globalThis.$os = { getenv: (name) => (step.env || {})[name] || "" };
  require(path.join(hooksDir, "demo.pb.js"));
  job();
  return "ran";
}

let result;
if (step.call === "reset") result = demo.resetAccount($app, step.account, step.trigger || "end", step.reason || "");
else if (step.call === "end") result = outcome(() => demo.handleEnd(context(), step.env));
else if (step.call === "sweep") result = demo.sweep($app, step.env, step.now);
else if (step.call === "cron") result = cron();
else throw new Error("unknown call " + step.call);
process.stdout.write(JSON.stringify({ result, tables, auths, stats, logs: out.logs, errors: out.errors }));
"""

DEMO_ID = "demo00000000001"
USER_ID = "user00000000001"
NOW = 1_800_000_000


def stamp(seconds: int) -> str:
    """A PocketBase date, seconds after the epoch."""
    import datetime
    return datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")


def reset_run(step: dict) -> dict:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run([node, "-e", RESET_RUNNER, str(HOOKS)], input=json.dumps(step), capture_output=True,
                         text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


def demo_constants() -> dict:
    (constants,) = run({"call": "constants"})
    return constants


def owned_tables(reset: list[str], *, rows: int = 1, age: int = 0) -> dict:
    """One demo and one standard account, each with `rows` rows in every
    reset collection, the demo's profile drifted from the seeded one."""
    tables: dict = {"users": [dict(OTHER_DEMO, id=DEMO_ID), dict(STANDARD, id=USER_ID, **SEEDED)]}
    n = 0
    for name in reset:
        tables[name] = []
        for owner in (DEMO_ID, USER_ID):
            for _ in range(rows):
                n += 1
                tables[name].append({"id": f"row{n:012d}", "user": owner, "created": stamp(NOW - age),
                                     "updated": stamp(NOW - age)})
    return tables


def counts(tables: dict, owner: str, field: str = "user") -> dict:
    return {name: sum(1 for r in rows if r.get(field) == owner) for name, rows in tables.items() if name != "users"}


def test_the_reset_leaves_no_row_the_demo_account_wrote_and_every_other_accounts_row():
    reset = demo_constants()["reset"]
    out = reset_run({"call": "reset", "account": DEMO_ID, "tables": owned_tables(reset, rows=2)})
    assert all(n == 0 for n in counts(out["tables"], DEMO_ID).values())
    assert counts(out["tables"], USER_ID) == {name: 2 for name in reset}
    assert out["result"]["deleted"] == dict({name: 2 for name in reset}, execution_jobs=0, execution_envelopes=0,
                                            admission_commands=0, external_auths=0)
    # Leaf first: no row of a later collection goes while an earlier one
    # still holds the demo's.
    order = [reset.index(name) for name in out["stats"]["order"]]
    assert order == sorted(order)


def test_the_reset_takes_at_most_a_batch_a_transaction_until_nothing_is_left():
    reset = demo_constants()["reset"]
    tables = owned_tables(reset)
    first = reset[0]
    tables[first] += [{"id": f"big{i:012d}", "user": DEMO_ID, "created": stamp(NOW), "updated": stamp(NOW)}
                      for i in range(1200)]
    out = reset_run({"call": "reset", "account": DEMO_ID, "tables": tables})
    assert max(out["stats"]["perTransaction"]) == 500 and out["stats"]["perTransaction"][:2] == [500, 500]
    assert all(n == 0 for n in counts(out["tables"], DEMO_ID).values())
    assert out["result"]["deleted"][first] == 1201
    order = [reset.index(name) for name in out["stats"]["order"]]
    assert order == sorted(order)


def execution_tables() -> dict:
    """The demo's ended job with its attempt, envelope, command, and lease;
    a job a worker holds; a command no job names; and an hour's counter."""
    tables = owned_tables(demo_constants()["reset"])
    tables.update({
        "execution_jobs": [
            {"id": "job000000000001", "account": DEMO_ID, "command_id": "c1", "state": "completed", "queued_at": 1},
            {"id": "job000000000002", "account": DEMO_ID, "command_id": "c2", "state": "started", "queued_at": 2},
            {"id": "job000000000003", "account": USER_ID, "command_id": "c4", "state": "completed", "queued_at": 3},
        ],
        "execution_attempts": [{"id": "att000000000001", "job": "job000000000001", "account": DEMO_ID},
                               {"id": "att000000000002", "job": "job000000000002", "account": DEMO_ID}],
        "execution_envelopes": [{"id": "env000000000001", "job": "job000000000001", "user": DEMO_ID},
                                {"id": "env000000000003", "job": "job000000000003", "user": USER_ID}],
        "admission_commands": [
            {"id": "cmd000000000001", "account": DEMO_ID, "command_id": "c1", "job": "job000000000001"},
            {"id": "cmd000000000003", "account": DEMO_ID, "command_id": "c3", "job": ""},
        ],
        "admission_leases": [{"id": "lse000000000001", "command": "cmd000000000001", "account": DEMO_ID},
                             {"id": "lse000000000003", "command": "cmd000000000003", "account": DEMO_ID}],
        "admission_counters": [{"id": "ctr000000000001", "account": DEMO_ID, "bucket": "account"}],
    })
    return tables


def test_the_reset_takes_code_run_jobs_no_worker_holds_and_keeps_the_limits():
    out = reset_run({"call": "reset", "account": DEMO_ID, "tables": execution_tables()})
    ids = {name: sorted(r["id"] for r in rows) for name, rows in out["tables"].items()}
    assert ids["execution_jobs"] == ["job000000000002", "job000000000003"]
    assert ids["execution_attempts"] == ["att000000000002"]
    assert ids["execution_envelopes"] == ["env000000000003"]
    # A command no job names, its lease, and the counters hold the limits.
    assert ids["admission_commands"] == ["cmd000000000003"]
    assert ids["admission_leases"] == ["lse000000000003"]
    assert ids["admission_counters"] == ["ctr000000000001"]
    deleted = out["result"]["deleted"]
    assert (deleted["execution_jobs"], deleted["execution_envelopes"], deleted["admission_commands"]) == (1, 1, 1)
    # The started job it couldn't take is counted, never named.
    (line,) = out["logs"]
    assert out["result"]["held_jobs"] == 1 and line["held_jobs"] == 1
    assert "job000000000002" not in json.dumps(line)


def test_the_code_run_stage_holds_to_the_batch_with_everything_a_job_takes_along():
    # 200 ended jobs, each with three attempts, their envelopes, its command,
    # and that command's lease: nine rows a job, cascades included.
    tables = owned_tables([])
    jobs, attempts, envelopes, commands, leases = [], [], [], [], []
    for i in range(200):
        job, command = f"job{i:012d}", f"cmd{i:012d}"
        jobs.append({"id": job, "account": DEMO_ID, "command_id": f"c{i}", "state": "completed", "queued_at": i})
        for n in range(3):
            attempts.append({"id": f"att{i:09d}{n:03d}", "job": job, "account": DEMO_ID})
            envelopes.append({"id": f"env{i:09d}{n:03d}", "job": job, "attempt": f"att{i:09d}{n:03d}", "user": DEMO_ID})
        commands.append({"id": command, "account": DEMO_ID, "command_id": f"c{i}", "job": job})
        leases.append({"id": f"lse{i:012d}", "command": command, "account": DEMO_ID})
    tables.update(execution_jobs=jobs, execution_attempts=attempts, execution_envelopes=envelopes,
                  admission_commands=commands, admission_leases=leases)
    out = reset_run({"call": "reset", "account": DEMO_ID, "tables": tables})
    assert max(out["stats"]["perTransaction"]) <= 500
    for name in ("execution_jobs", "execution_attempts", "execution_envelopes", "admission_commands",
                 "admission_leases"):
        assert out["tables"][name] == [], name
    deleted = out["result"]["deleted"]
    assert (deleted["execution_jobs"], deleted["execution_envelopes"], deleted["admission_commands"]) == (200, 600, 200)


def test_the_reset_leaves_the_demo_account_only_its_password():
    auths = [{"id": "sgn000000000001", "recordId": DEMO_ID}, {"id": "sgn000000000002", "recordId": DEMO_ID},
             {"id": "sgn000000000003", "recordId": USER_ID}]
    out = reset_run({"call": "reset", "account": DEMO_ID, "tables": owned_tables([]), "auths": auths})
    assert out["auths"] == [{"id": "sgn000000000003", "recordId": USER_ID}]
    assert out["result"]["deleted"]["external_auths"] == 2


def test_the_reset_puts_the_seeded_profile_back_and_saves_only_when_a_value_differs():
    drifted = reset_run({"call": "reset", "account": DEMO_ID, "tables": owned_tables([])})
    (demo_row,) = [u for u in drifted["tables"]["users"] if u["id"] == DEMO_ID]
    assert {k: demo_row[k] for k in SEEDED} == SEEDED
    assert drifted["result"]["profile"] == "restored" and drifted["stats"]["saves"] == 1
    tables = owned_tables([])
    tables["users"][0] = dict(SEEDED_DEMO, id=DEMO_ID)
    kept = reset_run({"call": "reset", "account": DEMO_ID, "tables": tables})
    assert kept["result"]["profile"] == "kept" and kept["stats"]["saves"] == 0


def test_the_reset_never_touches_a_standard_account():
    reset = demo_constants()["reset"]
    tables = owned_tables(reset)
    tables["users"][1]["name"] = "Ada"
    out = reset_run({"call": "reset", "account": USER_ID, "tables": tables})
    assert counts(out["tables"], USER_ID) == {name: 1 for name in reset}
    assert out["stats"]["saves"] == 0 and out["stats"]["order"] == []


@pytest.mark.parametrize("fail_on, stage, collection", [
    ("resumes", "rows", "resumes"),
    ("execution_jobs", "execution", None),
    ("external_auths", "external_auths", None),
    ("users", "profile", None),
])
def test_a_stage_that_fails_rolls_its_transaction_back_and_logs_one_error_line_naming_it(fail_on, stage, collection):
    tables = execution_tables()
    auths = [{"id": "sgn000000000001", "recordId": DEMO_ID}]
    out = reset_run({"call": "reset", "account": DEMO_ID, "tables": tables, "auths": auths, "failOn": fail_on,
                     "trigger": "sweep"})
    assert out["result"] is None
    line = {"v": "obs/v1", "event": "demo_reset", "service": "pocketbase", "trigger": "sweep", "stage": stage,
            "code": "failed"}
    if collection:
        line["collection"] = collection
    assert out["errors"] == [line] and out["logs"] == []
    # Everything the failing transaction deleted is back.
    if fail_on in ("resumes", "execution_jobs", "external_auths"):
        assert counts(out["tables"], DEMO_ID)["resume_versions"] == 1
    if fail_on == "users":
        assert all(n == 0 for name, n in counts(out["tables"], DEMO_ID).items() if name in demo_constants()["reset"])


def test_what_earlier_transactions_deleted_stays_deleted_when_a_later_one_fails():
    reset = demo_constants()["reset"]
    tables = owned_tables(reset)
    tables[reset[0]] += [{"id": f"big{i:012d}", "user": DEMO_ID, "created": stamp(NOW), "updated": stamp(NOW)}
                         for i in range(1200)]
    out = reset_run({"call": "reset", "account": DEMO_ID, "tables": tables, "failOn": "campaigns"})
    assert out["result"] is None and out["errors"][0]["collection"] == "campaigns"
    # Two batches committed; the third rolled back.
    assert counts(out["tables"], DEMO_ID)[reset[0]] == 201


def test_each_reset_logs_one_line_with_counts_and_no_id():
    out = reset_run({"call": "reset", "account": DEMO_ID, "tables": owned_tables(demo_constants()["reset"]),
                     "trigger": "sweep", "reason": "quiet"})
    (line,) = out["logs"]
    assert set(line) == {"v", "event", "service", "trigger", "deleted", "held_jobs", "profile", "reason"}
    assert (line["event"], line["trigger"], line["reason"], line["profile"]) == ("demo_reset", "sweep", "quiet",
                                                                                 "restored")
    assert line["held_jobs"] == 0
    assert DEMO_ID not in json.dumps(line) and USER_ID not in json.dumps(line)


def end(env: dict, **step) -> dict:
    return reset_run(dict({"call": "end", "env": env, "account": DEMO_ID,
                           "tables": owned_tables(demo_constants()["reset"])}, **step))


def test_the_sign_out_route_clears_a_demo_callers_account_and_answers_204():
    out = end(ON, auth=dict(OTHER_DEMO, id=DEMO_ID))
    assert out["result"] == {"status": 204}
    assert all(n == 0 for n in counts(out["tables"], DEMO_ID).values())


def test_the_sign_out_route_answers_as_an_unknown_route_with_the_demo_off():
    out = end(OFF, auth=dict(OTHER_DEMO, id=DEMO_ID))
    assert out["result"] == {"status": 404, "message": "The requested resource wasn't found."}
    assert out["stats"]["order"] == []


def test_the_sign_out_route_is_a_demo_callers_alone():
    anonymous = end(ON)
    standard = end(ON, auth=dict(STANDARD, id=USER_ID))
    superuser = end(ON, superuser=True)
    assert anonymous["result"]["status"] == 401
    assert standard["result"] == {"status": 403, "message": demo_constants_text("NOT_DEMO_SESSION")}
    assert superuser["result"]["status"] == 403
    for out in (anonymous, standard, superuser):
        assert out["stats"]["order"] == [] and out["stats"]["saves"] == 0


def test_a_sign_out_whose_reset_failed_answers_503():
    out = end(ON, auth=dict(OTHER_DEMO, id=DEMO_ID), failOn="campaigns")
    assert out["result"] == {"status": 503, "body": {"code": 503, "message": demo_constants_text("RESET_UNAVAILABLE"),
                                                     "data": {}}}


def demo_constants_text(name: str) -> str:
    match = re.search(rf'^const {name} = "([^"]+)";$', (HOOKS / "demo.js").read_text(), re.M)
    assert match, name
    return match.group(1)


def sweep_tables(*, updated: int, created: int) -> dict:
    tables = owned_tables(demo_constants()["reset"][:1])
    for row in tables[demo_constants()["reset"][0]]:
        row.update(updated=stamp(updated), created=stamp(created))
    return tables


def test_the_sweep_resets_a_demo_account_quiet_for_two_hours():
    out = reset_run({"call": "sweep", "env": ON, "now": NOW,
                     "tables": sweep_tables(updated=NOW - 2 * 3600, created=NOW - 3 * 3600)})
    assert out["result"] == {"checked": 1, "reset": 1, "failed": 0}
    assert out["logs"][0]["reason"] == "quiet"


def test_the_sweep_leaves_a_busy_demo_account_until_its_oldest_row_is_a_day_old():
    busy = reset_run({"call": "sweep", "env": ON, "now": NOW,
                      "tables": sweep_tables(updated=NOW - 600, created=NOW - 24 * 3600 + 1)})
    assert busy["result"] == {"checked": 1, "reset": 0, "failed": 0} and busy["logs"] == []
    capped = reset_run({"call": "sweep", "env": ON, "now": NOW,
                        "tables": sweep_tables(updated=NOW - 600, created=NOW - 24 * 3600)})
    assert capped["result"] == {"checked": 1, "reset": 1, "failed": 0}
    assert capped["logs"][0]["reason"] == "cap"


def test_the_sweep_skips_an_empty_demo_account_that_holds_the_seeded_profile():
    seeded = owned_tables([])
    seeded["users"][0] = dict(SEEDED_DEMO, id=DEMO_ID)
    skipped = reset_run({"call": "sweep", "env": ON, "now": NOW, "tables": seeded})
    assert skipped["result"] == {"checked": 1, "reset": 0, "failed": 0} and skipped["stats"]["transactions"] == 0
    drifted = reset_run({"call": "sweep", "env": ON, "now": NOW, "tables": owned_tables([])})
    assert drifted["result"] == {"checked": 1, "reset": 1, "failed": 0}
    assert drifted["logs"][0]["reason"] == "profile"


def held_tables(*, job_state: str = "started", job_created: int, job_updated: int, todo_age: int | None) -> dict:
    """The seeded demo account with one code-run job, and a todo made
    `todo_age` seconds ago unless that's None."""
    tables = owned_tables([])
    tables["users"][0] = dict(SEEDED_DEMO, id=DEMO_ID)
    tables["execution_jobs"] = [{"id": "job000000000009", "account": DEMO_ID, "command_id": "c9", "state": job_state,
                                 "queued_at": 9, "created": stamp(job_created), "updated": stamp(job_updated)}]
    if todo_age is not None:
        tables["todos"] = [{"id": "row000000000001", "user": DEMO_ID, "created": stamp(NOW - todo_age),
                            "updated": stamp(NOW - todo_age)}]
    return tables


def test_a_job_a_worker_may_hold_never_caps_or_resets_the_demo_account_by_itself():
    # A started job a day old beside a todo made a minute ago, and then the
    # job alone: the reset can't take it, so it decides nothing.
    beside = reset_run({"call": "sweep", "env": ON, "now": NOW,
                        "tables": held_tables(job_created=NOW - 25 * 3600, job_updated=NOW - 25 * 3600, todo_age=60)})
    assert beside["result"] == {"checked": 1, "reset": 0, "failed": 0} and beside["logs"] == []
    alone = reset_run({"call": "sweep", "env": ON, "now": NOW,
                       "tables": held_tables(job_created=NOW - 25 * 3600, job_updated=NOW - 25 * 3600, todo_age=None)})
    assert alone["result"] == {"checked": 1, "reset": 0, "failed": 0} and alone["logs"] == []
    assert alone["stats"]["transactions"] == 0


def test_the_cap_still_fires_for_an_old_row_the_reset_can_clear():
    # The same day-old job, ended: now the reset can take it, so it's the
    # oldest row that counts, and the fresh todo goes with it.
    out = reset_run({"call": "sweep", "env": ON, "now": NOW,
                     "tables": held_tables(job_state="completed", job_created=NOW - 24 * 3600, job_updated=NOW - 60,
                                           todo_age=60)})
    assert out["result"] == {"checked": 1, "reset": 1, "failed": 0}
    (line,) = out["logs"]
    assert line["reason"] == "cap" and line["held_jobs"] == 0
    assert (line["deleted"]["execution_jobs"], line["deleted"]["todos"]) == (1, 1)


def test_the_quiet_rule_counts_only_rows_the_reset_can_clear():
    # A todo untouched for two hours beside a started job a worker
    # touched a minute ago: the job doesn't keep the account busy.
    out = reset_run({"call": "sweep", "env": ON, "now": NOW,
                     "tables": held_tables(job_created=NOW - 3 * 3600, job_updated=NOW - 60, todo_age=2 * 3600)})
    assert out["result"] == {"checked": 1, "reset": 1, "failed": 0}
    (line,) = out["logs"]
    assert (line["reason"], line["deleted"]["todos"], line["deleted"]["execution_jobs"]) == ("quiet", 1, 0)
    assert line["held_jobs"] == 1
    assert [job["id"] for job in out["tables"]["execution_jobs"]] == ["job000000000009"]


def test_a_stuck_job_waits_out_the_sweeps_until_it_ends_and_the_next_sweep_clears_it():
    tables = held_tables(job_created=NOW - 25 * 3600, job_updated=NOW - 25 * 3600, todo_age=60)
    # Two sweeps five minutes apart: neither wipes the account.
    for now in (NOW, NOW + 300):
        out = reset_run({"call": "sweep", "env": ON, "now": now, "tables": tables})
        assert out["result"] == {"checked": 1, "reset": 0, "failed": 0} and out["logs"] == []
        tables = out["tables"]
    assert [row["id"] for row in tables["todos"]] == ["row000000000001"]
    # A worker's reap ends the job; the next sweep clears it through the cap.
    tables["execution_jobs"][0].update(state="failed", updated=stamp(NOW + 400))
    out = reset_run({"call": "sweep", "env": ON, "now": NOW + 600, "tables": tables})
    assert out["result"] == {"checked": 1, "reset": 1, "failed": 0}
    (line,) = out["logs"]
    assert (line["reason"], line["deleted"]["execution_jobs"], line["held_jobs"]) == ("cap", 1, 0)
    assert out["tables"]["execution_jobs"] == []


def test_the_sweep_clears_what_an_empty_demo_account_still_holds():
    # Nothing else to clear and the seeded profile, but a sign-in besides
    # its password: it goes at once.
    seeded = owned_tables([])
    seeded["users"][0] = dict(SEEDED_DEMO, id=DEMO_ID)
    auths = [{"id": "sgn000000000001", "recordId": DEMO_ID}, {"id": "sgn000000000002", "recordId": USER_ID}]
    out = reset_run({"call": "sweep", "env": ON, "now": NOW, "tables": seeded, "auths": auths})
    assert out["result"] == {"checked": 1, "reset": 1, "failed": 0}
    (line,) = out["logs"]
    assert (line["reason"], line["deleted"]["external_auths"]) == ("account", 1)
    assert out["auths"] == [{"id": "sgn000000000002", "recordId": USER_ID}]
    # The same on a busy account: it doesn't wait for the cap.
    busy = reset_run({"call": "sweep", "env": ON, "now": NOW, "auths": auths,
                      "tables": held_tables(job_state="completed", job_created=NOW - 60, job_updated=NOW - 60,
                                            todo_age=60)})
    assert busy["logs"][0]["reason"] == "account" and busy["auths"] == [{"id": "sgn000000000002", "recordId": USER_ID}]


def test_the_sweeps_cron_job_runs_the_sweep():
    # demo.pb.js's own callback, as PocketBase runs it on its clock: with the
    # demo on it resets a demo account past the cap; off, it does nothing.
    now = int(time.time())
    tables = sweep_tables(updated=now - 600, created=now - 25 * 3600)
    on = reset_run({"call": "cron", "env": ON, "tables": tables})
    assert [(line["trigger"], line["reason"]) for line in on["logs"]] == [("sweep", "cap")]
    assert counts(on["tables"], DEMO_ID)[demo_constants()["reset"][0]] == 0
    off = reset_run({"call": "cron", "env": OFF, "tables": tables})
    assert off["logs"] == [] and off["stats"]["transactions"] == 0


def test_the_sweep_does_nothing_with_the_demo_off():
    out = reset_run({"call": "sweep", "env": OFF, "now": NOW,
                     "tables": sweep_tables(updated=NOW - 30 * 3600, created=NOW - 30 * 3600)})
    assert out["result"] == {"demo": "disabled"} and out["stats"]["transactions"] == 0


def test_the_sweep_never_resets_a_standard_account():
    tables = sweep_tables(updated=NOW - 30 * 3600, created=NOW - 30 * 3600)
    tables["users"] = [dict(STANDARD, id=USER_ID, name="Ada")]
    out = reset_run({"call": "sweep", "env": ON, "now": NOW, "tables": tables})
    assert out["result"] == {"checked": 0, "reset": 0, "failed": 0} and out["stats"]["order"] == []


# Collections a migration defines that hold no account's rows, and ones a
# later migration drops.
NOT_OWNED = {"system_design_questions", "coding_questions", "behavioral_categories", "behavioral_questions",
             "system_design_guides", "coding_guides", "behavioral_guides", "ai_coding_rounds",
             "take_home_assignments", "definition_migration_journal", "execution_service", "share_resolvers",
             "share_throttle"}
DROPPED = {"anecdotes", "experience_items", "resume_bullets"}
EXECUTION = {"execution_jobs", "execution_attempts", "execution_envelopes"}


def test_every_collection_with_an_account_field_is_reset_refused_or_kept():
    constants = demo_constants()
    classes = {
        "reset": set(constants["reset"]),
        "contained": set(constants["contained"]),
        "not_demo_writable": set(constants["not_demo_writable"]),
        "kept": set(constants["kept"]),
        "execution": EXECUTION,
    }
    named = [name for group in classes.values() for name in group]
    assert len(named) == len(set(named)), "a collection is in two classes"
    manifest = json.loads((ROOT / "docs" / "security" / "account-scope.v1.json").read_text())["collections"]
    owned = set(manifest) - {"users"}
    migrations = sorted((ROOT / "pocketbase" / "pb_migrations").glob("*.js"))
    for path in migrations:
        text = path.read_text()
        for part in text.split("new Collection(")[1:]:
            found = re.match(r'\s*\{\s*name:\s*"([a-z0-9_]+)"', part)
            if found and ("users.id" in part or re.search(r"\baccount(\(\w*\))?,", part)):
                owned.add(found.group(1))
    # The scan finds the account fields no client reads, too.
    assert {"admission_commands", "admission_counters", "admission_leases", "execution_jobs",
            "execution_attempts"} <= owned
    texts = [p.read_text() for p in migrations]
    for name in DROPPED:
        assert any(f'findCollectionByNameOrId("{name}")' in t and "deleteCollection(" in t for t in texts), name
    owned -= DROPPED | NOT_OWNED
    unclassified = owned - set(named) - {"ai_credentials", "ai_provider_models"}
    assert unclassified == set(), f"classify these in demo.js: {sorted(unclassified)}"
    # The reset's own collections are the ones the account writes itself.
    for name in constants["reset"]:
        assert manifest[name]["owner_field"] == "user", name
    assert constants["reset_extra"] == ["execution_jobs", "execution_envelopes", "admission_commands", "external_auths"]


# ---- registration --------------------------------------------------------------------------------------

# Each registration, and the demo.js exports its callback calls: demo.js is
# a stand-in whose every export records its own name, and each callback
# runs once on an empty event.
REGISTRATION = r"""
const path = require("path");
const Module = require("module");
const [hooksDir] = process.argv.slice(1);
globalThis.__hooks = hooksDir;
globalThis.$os = { getenv: () => "" };
globalThis.$app = { dao: () => ({}) };
console.log = () => {};
console.error = () => {};
let called = [];
const target = require.resolve(path.join(hooksDir, "demo.js"));
const standIn = new Module(target);
standIn.filename = target;
standIn.loaded = true;
standIn.exports = new Proxy({}, {
  get: (_, name) => (typeof name === "string" ? () => { called.push(name); } : undefined),
});
require.cache[target] = standIn;
const seen = [];
for (const name of ["onAfterBootstrap", "onRecordBeforeAuthWithPasswordRequest", "onRecordBeforeAuthWithOAuth2Request",
                    "onRecordBeforeUpdateRequest", "onRecordBeforeDeleteRequest", "onRecordBeforeRequestEmailChangeRequest",
                    "onRecordBeforeCreateRequest", "onModelBeforeCreate", "onModelBeforeUpdate"]) {
  globalThis[name] = (fn, ...tags) => seen.push({ name, tags, run: () => fn({}) });
}
globalThis.routerUse = (fn) => seen.push({ name: "routerUse", tags: [], run: () => fn(() => undefined)({}) });
// A route's method and path, a cron job's id and schedule.
globalThis.routerAdd = (method, route, fn) => seen.push({ name: "routerAdd", tags: [method, route], run: () => fn({}) });
globalThis.cronAdd = (id, schedule, fn) => seen.push({ name: "cronAdd", tags: [id, schedule], run: () => fn() });
require(path.join(hooksDir, "demo.pb.js"));
process.stdout.write(JSON.stringify(seen.map((entry) => {
  called = [];
  entry.run();
  return { name: entry.name, tags: entry.tags, calls: called };
})));
"""

CONTAINED = ["resume_share_links", "share_capabilities", "ai_providers", "ai_credentials", "ai_provider_models",
             "ai_settings"]


def test_demo_pb_js_registers_each_hook_on_its_collections_and_calls_its_export():
    node = shutil.which("node")
    assert node
    res = subprocess.run([node, "-e", REGISTRATION, str(HOOKS)], capture_output=True, text=True, timeout=60, check=True)
    assert json.loads(res.stdout) == [
        {"name": "onAfterBootstrap", "tags": [], "calls": ["lockAll", "lockFailed"]},
        {"name": "routerUse", "tags": [], "calls": ["guardSession"]},
        {"name": "onRecordBeforeAuthWithPasswordRequest", "tags": ["users"], "calls": ["guardSignIn"]},
        {"name": "onRecordBeforeAuthWithOAuth2Request", "tags": ["users"], "calls": ["guardPasswordOnly"]},
        {"name": "onRecordBeforeUpdateRequest", "tags": ["users"], "calls": ["guardAccountUpdate"]},
        {"name": "onRecordBeforeDeleteRequest", "tags": ["users"], "calls": ["guardAccountDelete"]},
        {"name": "onRecordBeforeRequestEmailChangeRequest", "tags": ["users"], "calls": ["guardEmailChange"]},
        {"name": "onRecordBeforeCreateRequest", "tags": CONTAINED, "calls": ["guardContainedRequest"]},
        {"name": "onRecordBeforeUpdateRequest", "tags": CONTAINED, "calls": ["guardContainedRequest"]},
        {"name": "onModelBeforeCreate", "tags": CONTAINED, "calls": ["guardContainedModel"]},
        {"name": "onModelBeforeUpdate", "tags": CONTAINED, "calls": ["guardContainedModel"]},
        {"name": "routerAdd", "tags": ["POST", "/api/rounds/demo/sessions/end"], "calls": ["handleEnd"]},
        {"name": "cronAdd", "tags": ["rounds_demo_reset", "*/5 * * * *"], "calls": ["sweepNow"]},
    ]


def test_each_handler_reads_the_demo_gate_itself():
    # PocketBase runs every handler in its own context, so none shares a
    # value read elsewhere (test_hooks.py holds the signup hook to the same).
    source = (HOOKS / "demo.pb.js").read_text()
    assert "function " not in source
    for name in ("ROUNDS_GATE_DEMO", "ROUNDS_ENABLE_DEMO"):
        assert source.count(f'$os.getenv("{name}")') == 6, name
    assert len(re.findall(r"require\(`\$\{__hooks\}/demo\.js`\)", source)) == 13


def test_the_demo_module_is_not_auto_loaded_as_a_hook_file():
    # PocketBase loads only *.pb.js files, so demo.js stays a require target.
    assert (HOOKS / "demo.js").exists() and not (HOOKS / "demo.js").name.endswith(".pb.js")
