/// <reference path="../pb_data/types.d.ts" />

// The demo account's containment (ROUNDS-00B-L07 stage 1). demo.pb.js
// registers these handlers. PocketBase runs each one in its own context,
// so each requires this file and reads the demo gate itself.
//
// Whether an account is a demo account is #1's tier accessor, tierOf() in
// admission.js, and only that. It reads users.is_demo, which only a
// superuser, a migration, or a server hook can set (admission.pb.js).
//
// With the demo off (ROUNDS_GATE_DEMO, or its alias ROUNDS_ENABLE_DEMO;
// off by default), no demo account signs in or holds a working session. A
// sign-in gets the answer a wrong password gets, any request a demo
// account's token authenticates gets 401, and every start gives each demo
// account a random password and a new token key. On or off, a demo caller
// changes only its profile, and no demo account owns a share link or an AI
// provider, credential, model, or settings row, whether a client or a
// server hook writes it.

// What a demo caller may change on its own users record.
const PROFILE_FIELDS = ["name", "bio", "target", "avatar"];
// What a demo account may not own, and how each row names its account:
// its own field, or the provider it belongs to. share_capabilities (#11)
// and ai_credentials and ai_provider_models (#73) don't exist yet; the
// leaf that adds one confirms its entry (test_demo_hooks.py fails until it
// does), and a collection with no entry is refused outright.
const OWNERS = {
  resume_share_links: { field: "user" },
  share_capabilities: { field: "user" },
  ai_providers: { field: "user" },
  ai_credentials: { via: "provider" },
  ai_provider_models: { via: "provider" },
  ai_settings: { field: "user" },
};
const CONTAINED = Object.keys(OWNERS);
const PASSWORD_CHARS = 48;
const NOT_PERMITTED = "demo_not_permitted";
const NOT_PERMITTED_MESSAGE = "Not available in the demo.";
// PocketBase's own answers to a failed sign-in and to a request without a
// valid token.
const SIGN_IN_FAILED = "Failed to authenticate.";
const NO_SESSION = "The request requires valid record authorization token to be set.";

// ROUNDS_GATE_DEMO wins when set; ROUNDS_ENABLE_DEMO is its alias.
function enabled(env) {
  return require(`${__hooks}/gates.js`).resolve("DEMO", env).value === "enabled";
}

// Stage 2 repoints tierOf() at account_system_state, and every check here
// follows it.
function isDemo(record) {
  return Boolean(record) && require(`${__hooks}/admission.js`).tierOf(record) === "demo";
}

function isSuperuser(httpContext) {
  return Boolean(httpContext && $apis.requestInfo(httpContext).admin);
}

// One log line per denial: what was refused and where, never an id, an
// email, or a value.
function logDenied(code, on, collection) {
  console.log(JSON.stringify({ v: "obs/v1", event: "demo_denied", service: "pocketbase", code, on, collection }));
}

// 403 demo_not_permitted, in PocketBase's error shape.
function notPermitted(on, collection) {
  logDenied(NOT_PERMITTED, on, collection);
  return new ForbiddenError(NOT_PERMITTED_MESSAGE, { demo: new ValidationError(NOT_PERMITTED, NOT_PERMITTED_MESSAGE) });
}

// 1. At every start with the demo off: a random password and a new token
// key for each demo account. A demo account has is_demo set, so the query
// finds every one. Before the first migration there's no users table to
// read (not_ready); the demo account the migrations then create is refused
// at sign-in (2) until the next start gives it a password. Any other
// failure is query_failed, and demo.pb.js logs it, or any failed save, as
// an error; the session check (2) still refuses those accounts.
function lockAll(dao, env) {
  if (enabled(env)) return { demo: "enabled" };
  let accounts;
  try {
    accounts = dao.findRecordsByFilter("users", "is_demo = true");
  } catch (err) {
    return { demo: "disabled", code: /no such table/i.test(String(err)) ? "not_ready" : "query_failed" };
  }
  let locked = 0;
  let failed = 0;
  for (const record of accounts) {
    if (!isDemo(record)) continue;
    try {
      record.setPassword($security.randomString(PASSWORD_CHARS));
      record.refreshTokenKey();
      dao.saveRecord(record);
      locked += 1;
    } catch (_) {
      failed += 1;
    }
  }
  return { demo: "disabled", locked, failed };
}

// Whether the boot lock's result needs an error-level line.
function lockFailed(out) {
  return Boolean(out) && (out.code === "query_failed" || out.failed > 0);
}

// 2. With the demo off, a demo account's sign-in fails as a wrong password
// does, whatever the password.
function guardSignIn(e, env) {
  if (e.record && isDemo(e.record) && !enabled(env)) {
    logDenied("demo_off", "sign_in", "users");
    throw new BadRequestError(SIGN_IN_FAILED);
  }
}

// 2. With the demo off, a demo account holds no working session: any
// request its token authenticates, a token refresh included, gets 401, so
// a token from before stays useless even if the boot lock failed.
function guardSession(c, env) {
  const record = $apis.requestInfo(c).authRecord;
  if (record && isDemo(record) && !enabled(env)) {
    logDenied("demo_off", "session", "users");
    throw new UnauthorizedError(NO_SESSION);
  }
}

// 3. A demo caller changes its own name, bio, target, and avatar, and
// nothing else: not its password, email, username, verification, or demo
// fields. A superuser isn't held to it.
function guardAccountUpdate(e) {
  if (isSuperuser(e.httpContext) || !isDemo(e.record.originalCopy())) return;
  const data = $apis.requestInfo(e.httpContext).data || {};
  const keys = Object.keys(data).concat(Object.keys(e.uploadedFiles || {}));
  if (keys.some((key) => PROFILE_FIELDS.indexOf(key.replace(/[+-]$/, "")) < 0)) throw notPermitted("update", "users");
}

// 3. A demo caller can't delete its account or change its email.
function guardAccountDelete(e) {
  if (!isSuperuser(e.httpContext) && isDemo(e.record)) throw notPermitted("delete", "users");
}

function guardEmailChange(e) {
  if (isDemo(e.record)) throw notPermitted("email_change", "users");
}

function collectionOf(record) {
  try {
    return record.tableName();
  } catch (_) {
    return "";
  }
}

// The account a contained row belongs to, from OWNERS: undefined when the
// collection has no entry, "" when the row names none.
function ownerOf(dao, record) {
  const spec = OWNERS[collectionOf(record)];
  if (!spec) return undefined;
  if (spec.field) return record.getString(spec.field);
  const provider = record.getString(spec.via);
  if (!provider) return "";
  try {
    return dao.findRecordById("ai_providers", provider).getString(OWNERS.ai_providers.field);
  } catch (_) {
    return "";
  }
}

// A row in a collection with no OWNERS entry counts as demo-owned, so a
// missing entry refuses writes rather than letting them through.
function demoOwned(dao, record) {
  if (!record) return false;
  const owner = ownerOf(dao, record);
  if (owner === undefined) return true;
  if (!owner) return false;
  try {
    return isDemo(dao.findRecordById("users", owner));
  } catch (_) {
    return false;
  }
}

// 4. No demo account owns a contained row: a client create or update
// gets 403, a superuser's included, and so does a row it already owns.
function guardContainedRequest(e) {
  const dao = $app.dao();
  if (demoOwned(dao, e.record) || demoOwned(dao, e.record.originalCopy())) {
    throw notPermitted("save", collectionOf(e.record));
  }
}

// 4. The same for every other save through the app's Dao: a server hook or
// a hook route, whichever token the request held. A migration writes with
// its own Dao, which runs no model hooks; its leaf's manifest covers it.
function guardContainedModel(e) {
  if (!demoOwned(e.dao, e.model)) return;
  logDenied(NOT_PERMITTED, "model_save", collectionOf(e.model));
  throw new Error(NOT_PERMITTED);
}

module.exports = {
  PROFILE_FIELDS,
  OWNERS,
  CONTAINED,
  PASSWORD_CHARS,
  NOT_PERMITTED,
  NOT_PERMITTED_MESSAGE,
  SIGN_IN_FAILED,
  NO_SESSION,
  enabled,
  isDemo,
  lockAll,
  lockFailed,
  guardSignIn,
  guardSession,
  guardAccountUpdate,
  guardAccountDelete,
  guardEmailChange,
  ownerOf,
  demoOwned,
  guardContainedRequest,
  guardContainedModel,
};
