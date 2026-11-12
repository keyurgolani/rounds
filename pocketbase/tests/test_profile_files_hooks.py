"""No client creates or changes a profile file (ROUNDS-00B-L07).

pocketbase/pb_hooks/profile_files.js runs under node with PocketBase's
globals faked. A client's users create or update, or an OAuth2 sign-up,
that names a profile file in any form is refused, and so is one whose
record would save a different file there. Other fields still save, a
file already stored stays, and a superuser isn't held to it.
profile_files.pb.js's registrations are checked too.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOKS = ROOT / "pocketbase" / "pb_hooks"

FAKES = r"""
const path = require("path");
class ApiError extends Error {
  constructor(status, message, data) { super(message); this.status = status; this.data = data; }
}
globalThis.BadRequestError = class BadRequestError extends ApiError { constructor(m, d) { super(400, m, d); } };
globalThis.$apis = { requestInfo: (ctx) => ctx.info };

// A users record. A file field holds its names as PocketBase reads them:
// getStringSlice gives a string as one name and "" as none.
function record(fields) {
  const data = fields || {};
  return {
    getBool: (name) => data[name] === true,
    getString: (name) => (typeof data[name] === "string" ? data[name] : ""),
    getStringSlice: (name) => {
      const value = data[name];
      if (Array.isArray(value)) return value.filter((v) => v !== "");
      return typeof value === "string" && value !== "" ? [value] : [];
    },
  };
}

// The event a users request hook gets: the record as PocketBase would save
// it, its stored copy, the request's data, and its uploads.
function event(step) {
  const original = step.original === undefined ? null : record(step.original);
  return {
    httpContext: { info: { admin: step.superuser ? { id: "admin" } : null, data: step.data || {} } },
    record: Object.assign(record(step.fields), { originalCopy: () => original }),
    uploadedFiles: step.uploaded || {},
    isNewRecord: step.isNewRecord !== false,
  };
}

function outcome(fn) {
  try {
    fn();
    return { allowed: true };
  } catch (err) {
    if (err.status) return { status: err.status, message: err.message };
    return { error: String(err && err.message) };
  }
}
"""

RUNNER = FAKES + r"""
const [hooksDir, raw] = process.argv.slice(1);
globalThis.__hooks = hooksDir;
const files = require(path.join(hooksDir, "profile_files.js"));
const admission = require(path.join(hooksDir, "admission.js"));

function exec(step) {
  switch (step.call) {
    case "guardCreate":
    case "guardUpdate":
    case "guardOAuth2":
      return outcome(() => files[step.call](event(step)));
    case "guardDemoUpdate":
      return outcome(() => admission.guardDemoUpdate(event(step)));
    case "constants":
      return { fields: files.FILE_FIELDS };
    default:
      throw new Error("unknown call " + step.call);
  }
}
process.stdout.write(JSON.stringify(JSON.parse(raw).map(exec)));
"""

LOCKED = {"status": 400, "message": "These account fields can't be changed."}
ALLOWED = {"allowed": True}
STORED = {"avatar": "face.png"}

# Each form a request can name the profile file in, whatever the value.
FORMS = [
    {"data": {"avatar": "face.png"}},
    {"data": {"avatar+": "face.png"}},
    {"data": {"avatar-": "face.png"}},
    {"data": {"+avatar": "face.png"}},
    {"data": {"avatar": ["face.png"]}},
    {"data": {"avatar": ""}},
    {"data": {"avatar": None}},
    {"data": {"avatar": []}},
    {"uploaded": {"avatar": [{}]}},
]


def run(*steps: dict) -> list:
    node = shutil.which("node")
    assert node, "node is required for the PocketBase hook checks; CI installs it"
    res = subprocess.run([node, "-e", RUNNER, str(HOOKS), json.dumps(list(steps))], capture_output=True, text=True,
                         timeout=60)
    assert res.returncode == 0, res.stderr
    return json.loads(res.stdout)


# ---- create and update ---------------------------------------------------------------------------


def test_no_client_creates_an_account_with_a_profile_file():
    steps = [dict(form, call="guardCreate") for form in FORMS]
    steps.append({"call": "guardCreate", "data": {"email": "someone@example.test", "name": "Someone", "avatar": ""}})
    assert run(*steps) == [LOCKED] * len(steps)


def test_no_client_changes_its_profile_file():
    # The request names it, whether or not the record would save it
    # differently, and whether or not one is stored.
    steps = []
    for stored in ({}, STORED):
        steps += [dict(form, call="guardUpdate", fields=stored, original=stored) for form in FORMS]
    steps.append({"call": "guardUpdate", "fields": STORED, "original": STORED,
                  "data": {"name": "Someone", "avatar-": "face.png"}})
    assert run(*steps) == [LOCKED] * len(steps)


def test_a_client_cant_change_its_profile_file_whatever_form_the_request_takes():
    # The record as PocketBase would save it, with no request key that names
    # the file: a new file, another one, or none where one was.
    assert run(
        {"call": "guardCreate", "fields": STORED},
        {"call": "guardUpdate", "fields": STORED, "original": {}},
        {"call": "guardUpdate", "fields": {"avatar": "other.png"}, "original": STORED},
        {"call": "guardUpdate", "fields": {}, "original": STORED, "data": {"name": "Someone"}},
    ) == [LOCKED] * 4


def test_a_client_still_saves_its_other_fields():
    assert run(
        {"call": "guardCreate", "fields": {"name": "Someone"},
         "data": {"email": "someone@example.test", "password": "a-test-password-1",
                  "passwordConfirm": "a-test-password-1", "name": "Someone"}},
        {"call": "guardUpdate", "fields": {"name": "Someone"}, "original": {},
         "data": {"name": "Someone", "bio": "Trying it out", "target": "Staff engineer"}},
        # A file already stored stays as it is.
        {"call": "guardUpdate", "fields": dict(STORED, name="Someone"), "original": STORED, "data": {"name": "Someone"}},
        {"call": "guardUpdate", "fields": STORED, "original": STORED},
    ) == [ALLOWED] * 4


def test_a_superuser_still_sets_or_clears_a_profile_file():
    assert run(
        {"call": "guardCreate", "fields": STORED, "uploaded": {"avatar": [{}]}, "superuser": True},
        {"call": "guardUpdate", "fields": {"avatar": "other.png"}, "original": STORED, "uploaded": {"avatar": [{}]},
         "superuser": True},
        {"call": "guardUpdate", "fields": {}, "original": STORED, "data": {"avatar": ""}, "superuser": True},
        {"call": "guardUpdate", "fields": {}, "original": STORED, "data": {"avatar-": "face.png"}, "superuser": True},
        {"call": "guardOAuth2", "data": {"createData": {"avatar": ""}}, "superuser": True},
    ) == [ALLOWED] * 5


# ---- OAuth2 sign-up ------------------------------------------------------------------------------


def test_an_oauth2_sign_up_names_no_profile_file():
    # Its createData skips the create request hook, so its keys are checked.
    steps = [{"call": "guardOAuth2", "data": {"provider": "github", "createData": form["data"]}}
             for form in FORMS if "data" in form]
    assert run(*steps) == [LOCKED] * len(steps)


def test_other_oauth2_sign_ins_pass():
    assert run(
        {"call": "guardOAuth2", "data": {"provider": "github"}},
        {"call": "guardOAuth2", "data": {"provider": "github", "createData": {"name": "Someone"}}},
        # An existing account's sign-in creates nothing from createData.
        {"call": "guardOAuth2", "data": {"provider": "github", "createData": {"avatar": ""}}, "isNewRecord": False},
    ) == [ALLOWED] * 3


# ---- the answer ----------------------------------------------------------------------------------


def test_the_answer_is_the_one_a_locked_account_field_gets():
    # So a request that also changes a demo flag gets one answer whichever
    # users hook PocketBase runs first.
    flag, file = run(
        {"call": "guardDemoUpdate", "fields": {"is_demo": True}, "original": {"is_demo": False}},
        {"call": "guardUpdate", "fields": {"is_demo": True}, "original": {"is_demo": False},
         "data": {"is_demo": True, "avatar": ""}},
    )
    assert flag == file == LOCKED


def test_the_profile_file_fields_are_the_users_avatar():
    assert run({"call": "constants"}) == [{"fields": ["avatar"]}]


# ---- registration --------------------------------------------------------------------------------

REGISTRATION = FAKES + r"""
const [hooksDir] = process.argv.slice(1);
globalThis.__hooks = hooksDir;
const handlers = [];
for (const name of ["onRecordBeforeCreateRequest", "onRecordBeforeUpdateRequest", "onRecordBeforeAuthWithOAuth2Request"]) {
  globalThis[name] = (fn, ...tags) => handlers.push({ name, tags, fn });
}
require(path.join(hooksDir, "profile_files.pb.js"));
// Each handler, given a request that names the profile file.
const step = { fields: {}, original: {}, data: { avatar: "", createData: { avatar: "" } } };
process.stdout.write(JSON.stringify(handlers.map((h) => ({ name: h.name, tags: h.tags, ...outcome(() => h.fn(event(step))) }))));
"""


def test_profile_files_pb_js_guards_every_users_create_update_and_oauth2_sign_up():
    node = shutil.which("node")
    assert node
    res = subprocess.run([node, "-e", REGISTRATION, str(HOOKS)], capture_output=True, text=True, timeout=60)
    assert res.returncode == 0, res.stderr
    assert json.loads(res.stdout) == [
        dict(LOCKED, name="onRecordBeforeCreateRequest", tags=["users"]),
        dict(LOCKED, name="onRecordBeforeUpdateRequest", tags=["users"]),
        dict(LOCKED, name="onRecordBeforeAuthWithOAuth2Request", tags=["users"]),
    ]


def test_each_handler_requires_the_module_itself():
    # PocketBase runs every handler in its own context, so none shares a
    # value or a function from the file around it.
    source = (HOOKS / "profile_files.pb.js").read_text()
    assert "function " not in source
    assert len(re.findall(r"require\(`\$\{__hooks\}/profile_files\.js`\)", source)) == 3


def test_the_profile_files_module_is_not_auto_loaded_as_a_hook_file():
    # PocketBase loads only *.pb.js files, so profile_files.js stays a require target.
    assert (HOOKS / "profile_files.js").exists() and not (HOOKS / "profile_files.js").name.endswith(".pb.js")
