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
// off by default), no demo account signs in. A sign-in gets the answer a
// wrong password gets, and every start gives each demo account a random
// password and a new token key, so a token from before stops working. On
// or off, a demo caller changes only its profile, and no demo account owns
// a share link or an AI provider, credential, model, or settings row,
// whoever writes it.

// What a demo caller may change on its own users record.
const PROFILE_FIELDS = ["name", "bio", "target", "avatar"];
// What a demo account may not own. share_capabilities (#11) and
// ai_credentials and ai_provider_models (#73) don't exist yet; their rows
// are covered once they do.
const CONTAINED = [
  "resume_share_links", "share_capabilities", "ai_providers", "ai_credentials", "ai_provider_models", "ai_settings",
];
const PASSWORD_CHARS = 48;
const NOT_PERMITTED = "demo_not_permitted";
const NOT_PERMITTED_MESSAGE = "Not available in the demo.";
// PocketBase's own answer to a failed sign-in.
const SIGN_IN_FAILED = "Failed to authenticate.";

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

// 403 demo_not_permitted, in PocketBase's error shape.
function notPermitted() {
  return new ForbiddenError(NOT_PERMITTED_MESSAGE, { demo: new ValidationError(NOT_PERMITTED, NOT_PERMITTED_MESSAGE) });
}

// 1. At every start with the demo off: a random password and a new token
// key for each demo account. A demo account has is_demo set, so the query
// finds every one. Before the first migration there's no users collection
// to read; the demo account the migrations then create is refused at
// sign-in (2) until the next start gives it a password.
function lockAll(dao, env) {
  if (enabled(env)) return { demo: "enabled" };
  let accounts;
  try {
    accounts = dao.findRecordsByFilter("users", "is_demo = true");
  } catch (_) {
    return { demo: "disabled", code: "not_ready" };
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

// 2. With the demo off, a demo account's sign-in fails as a wrong password
// does, whatever the password.
function guardSignIn(e, env) {
  if (e.record && isDemo(e.record) && !enabled(env)) throw new BadRequestError(SIGN_IN_FAILED);
}

// 3. A demo caller changes its own name, bio, target, and avatar, and
// nothing else: not its password, email, username, verification, or demo
// fields. A superuser isn't held to it.
function guardAccountUpdate(e) {
  if (isSuperuser(e.httpContext) || !isDemo(e.record.originalCopy())) return;
  const data = $apis.requestInfo(e.httpContext).data || {};
  const keys = Object.keys(data).concat(Object.keys(e.uploadedFiles || {}));
  if (keys.some((key) => PROFILE_FIELDS.indexOf(key.replace(/[+-]$/, "")) < 0)) throw notPermitted();
}

// 3. A demo caller can't delete its account or change its email.
function guardAccountDelete(e) {
  if (!isSuperuser(e.httpContext) && isDemo(e.record)) throw notPermitted();
}

function guardEmailChange(e) {
  if (isDemo(e.record)) throw notPermitted();
}

// The account a contained row belongs to: its user, or its provider's.
function ownerOf(dao, record) {
  const user = record.getString("user");
  if (user) return user;
  const provider = record.getString("provider");
  if (!provider) return "";
  try {
    return dao.findRecordById("ai_providers", provider).getString("user");
  } catch (_) {
    return "";
  }
}

function demoOwned(dao, record) {
  const owner = record ? ownerOf(dao, record) : "";
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
  if (demoOwned(dao, e.record) || demoOwned(dao, e.record.originalCopy())) throw notPermitted();
}

// 4. The same for every other writer: a server hook, a migration, or the
// runner, whichever token it holds.
function guardContainedModel(e) {
  if (demoOwned(e.dao, e.model)) throw new Error(NOT_PERMITTED);
}

module.exports = {
  PROFILE_FIELDS,
  CONTAINED,
  PASSWORD_CHARS,
  NOT_PERMITTED,
  NOT_PERMITTED_MESSAGE,
  SIGN_IN_FAILED,
  enabled,
  isDemo,
  lockAll,
  guardSignIn,
  guardAccountUpdate,
  guardAccountDelete,
  guardEmailChange,
  ownerOf,
  demoOwned,
  guardContainedRequest,
  guardContainedModel,
};
