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
// changes nothing on its own users record, signs in with its password
// only, and no demo account owns a share link or an AI provider,
// credential, model, or settings row, whether a client or a server hook
// writes it. With the demo on, a demo session's sign-out clears what the
// demo account holds (5), and a sweep does it when nobody signs out (6).

// The text profile fields. A demo caller's request may name them, but its
// record must save exactly the seeded profile; any other key it sends is
// refused. No client changes a profile file (profile_files.js).
const PROFILE_FIELDS = ["name", "bio", "target"];
// The demo account's profile as 1700000600_demo_user.js seeds it.
const SEEDED_PROFILE = {
  name: "Rounds Demo",
  bio: "Disposable hosted demo account. Changes reset on logout.",
  target: "Explore Rounds",
};
// What a demo account may not own, and how each row names its account:
// its own field, or the provider it belongs to. ai_credentials and
// ai_provider_models (#73) don't exist yet; the leaf that adds one confirms
// its entry (test_demo_hooks.py fails until it does), and a collection with
// no entry is refused outright. #11 stage 2 confirmed share_capabilities.
const OWNERS = {
  resume_share_links: { field: "user" },
  share_capabilities: { field: "user" },
  ai_providers: { field: "user" },
  ai_credentials: { via: "provider" },
  ai_provider_models: { via: "provider" },
  ai_settings: { field: "user" },
};
const CONTAINED = Object.keys(OWNERS);
// The query that finds the candidate demo accounts, which the boot lock
// and the sweep then ask tierOf() about, one by one.
const DEMO_CANDIDATES = "is_demo = true";
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
    accounts = dao.findRecordsByFilter("users", DEMO_CANDIDATES);
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

// 2. The demo account signs in with its password only, whether the demo
// is on or off: any other sign-in to it, or from its session, gets the
// answer a failed sign-in gets, and logs one demo_denied line.
function guardPasswordOnly(e, env) {
  const caller = e.httpContext ? $apis.requestInfo(e.httpContext).authRecord : null;
  if (!(e.record && isDemo(e.record)) && !isDemo(caller)) return;
  logDenied(enabled(env) ? NOT_PERMITTED : "demo_off", "sign_in", "users");
  throw new BadRequestError(SIGN_IN_FAILED);
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

// Whether a record holds exactly the seeded profile.
function seededProfile(record) {
  return PROFILE_FIELDS.every((field) => record.getString(field) === SEEDED_PROFILE[field]);
}

// 3. A demo caller changes nothing on its own users record. A request
// that names a profile field in any form (the field, a + or - modifier,
// or an upload under its name, whatever the value), or whose record would
// save a different one, gets the 400 a locked account field gets, unless
// the record it would save holds exactly the seeded profile. Any other
// key gets 403: its profile file, password, email, username,
// verification, and demo fields. A superuser isn't held to it.
function guardAccountUpdate(e) {
  if (isSuperuser(e.httpContext) || !isDemo(e.record.originalCopy())) return;
  // A change to the demo flags gets admission.js's answer, and one to a
  // profile file profile_files.js's, which is the locked profile's too,
  // whichever users-update hook PocketBase runs first, so it's always the
  // same.
  require(`${__hooks}/admission.js`).guardDemoUpdate(e);
  const files = require(`${__hooks}/profile_files.js`);
  files.guardUpdate(e);
  const data = $apis.requestInfo(e.httpContext).data || {};
  const keys = Object.keys(data).concat(Object.keys(e.uploadedFiles || {}));
  const original = e.record.originalCopy();
  const named = keys.some((key) => PROFILE_FIELDS.indexOf(files.fieldOf(key)) >= 0);
  const changed = PROFILE_FIELDS.some((field) => e.record.getString(field) !== original.getString(field));
  if ((named || changed) && !seededProfile(e.record)) throw new BadRequestError(files.LOCKED);
  if (keys.some((key) => PROFILE_FIELDS.indexOf(files.fieldOf(key)) < 0)) throw notPermitted("update", "users");
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

// 5. The reset. What a demo account writes itself, by its `user` field,
// leaf first, so no delete has to clear a link on a row still to go: the
// experience links, the experience entities, resumes, practice, then the
// pipeline and its campaigns. docs/security/account-scope.v1.json lists
// them; test_demo_hooks.py holds every collection with an account field
// to this list or to one of the others below.
const RESET = [
  "exp_anecdote_bullets", "exp_project_bullets", "exp_project_anecdotes", "exp_job_bullets", "exp_job_anecdotes",
  "exp_job_projects",
  "experience_bullets", "experience_anecdotes", "experience_projects", "experience_jobs",
  "resume_versions", "resume_variants", "resumes",
  "ai_coding_attempts", "take_home_attempts", "ai_coding_drafts", "take_home_drafts", "question_timers",
  "todos", "code_drafts", "offers", "interview_rounds", "user_progress", "user_preferences", "applications",
  "campaigns",
];
// What else the reset removes, by the names its demo_reset line counts:
// the account's code-run jobs no worker holds, with their envelopes and
// the admission commands that name them (execution.js purgeAccount; their
// attempts and the commands' leases cascade). It also leaves the demo
// account no sign-in but its password.
const RESET_EXTRA = ["execution_jobs", "execution_envelopes", "admission_commands", "external_auths"];
// Collections with an account field the reset leaves: OWNERS' rows no
// demo account can own, rows only an owner of those can cause, and the
// admission rows that hold the limits (a command no job names, its
// leases, and the counters), which expire within a day.
const NOT_DEMO_WRITABLE = ["resume_share_views", "legacy_artifact_snapshots"];
const KEPT = ["admission_commands", "admission_counters", "admission_leases"];
// The sweep resets a demo account none of whose rows the reset can clear
// changed in QUIET_S, and one whose oldest such row is CAP_S old, even
// while it's busy.
const QUIET_S = 2 * 3600;
const CAP_S = 24 * 3600;
// A reset stops, and logs a failure, after this many transactions.
const RESET_PASSES = 1000;
const NOT_DEMO_SESSION = "Only a demo session can be ended here.";
const RESET_UNAVAILABLE = "The demo couldn't be cleared just now. Try again.";

function demoAccount(dao, accountId) {
  try {
    const record = dao.findRecordById("users", accountId);
    return isDemo(record) ? record : null;
  } catch (_) {
    return null;
  }
}

// One error-level line for a reset that didn't finish: where it stopped,
// never an id, an error text, or a value.
function logResetFailure(trigger, stage, collection) {
  const line = { v: "obs/v1", event: "demo_reset", service: "pocketbase", trigger, stage, code: "failed" };
  if (collection) line.collection = collection;
  console.error(JSON.stringify(line));
}

// One pass in one transaction: at most a batch of rows, leaf first. The
// code-run jobs, and any sign-in but the password, go only once every
// RESET collection is empty. Returns what it deleted.
function resetPass(tx, accountId, batch, state) {
  const deleted = {};
  const account = demoAccount(tx, accountId);
  if (account === null) return deleted;
  let left = batch;
  for (let i = 0; i < RESET.length && left > 0; i += 1) {
    state.collection = RESET[i];
    const rows = tx.findRecordsByFilter(RESET[i], "user = {:user}", "", left, 0, { user: accountId });
    rows.forEach((row) => tx.deleteRecord(row));
    if (rows.length > 0) deleted[RESET[i]] = rows.length;
    left -= rows.length;
  }
  state.collection = "";
  const execution = require(`${__hooks}/execution.js`);
  // The most rows a job takes with it: itself, its attempts and their
  // envelopes, its command, and the command's leases. A job starts only
  // when that many still fit in the batch; the next pass takes the rest.
  const perJob = 2 * execution.MAX_ATTEMPTS + 4;
  if (left >= perJob) {
    state.stage = "execution";
    const out = execution.purgeAccount(execution.pbStore(tx), accountId, Math.floor(left / perJob));
    if (out.jobs > 0) deleted.execution_jobs = out.jobs;
    if (out.envelopes > 0) deleted.execution_envelopes = out.envelopes;
    if (out.commands > 0) deleted.admission_commands = out.commands;
    left -= out.jobs * perJob;
  }
  if (left > 0) {
    state.stage = "external_auths";
    const auths = tx.findAllExternalAuthsByRecord(account).slice(0, left);
    auths.forEach((auth) => tx.deleteExternalAuth(auth));
    if (auths.length > 0) deleted.external_auths = auths.length;
  }
  state.stage = "rows";
  return deleted;
}

// Clears one demo account: every row it wrote itself and its code-run
// jobs no worker holds with what they left, at most a batch of rows a
// transaction, until a pass finds nothing, and leaves it no sign-in but
// its password; then it puts the seeded profile back, saving only when a
// value differs (a superuser's edit included). A standard account is
// never touched. Its line also counts the jobs a worker may still hold,
// which it left. Returns the counts, or null when a stage failed, which
// it logs at error level by name; what earlier passes deleted stays
// deleted.
function resetAccount(app, accountId, trigger, reason) {
  const batch = require(`${__hooks}/admission.js`).SWEEP_BATCH;
  const deleted = {};
  RESET.concat(RESET_EXTRA).forEach((name) => {
    deleted[name] = 0;
  });
  const state = { stage: "rows", collection: "" };
  let profile = "kept";
  let held = 0;
  try {
    for (let pass = 0; ; pass += 1) {
      if (pass >= RESET_PASSES) {
        logResetFailure(trigger, "rows", "");
        return null;
      }
      let found = {};
      app.dao().runInTransaction((tx) => {
        found = resetPass(tx, accountId, batch, state);
      });
      const names = Object.keys(found);
      names.forEach((name) => {
        deleted[name] += found[name];
      });
      if (names.length === 0) break;
    }
    state.stage = "profile";
    app.dao().runInTransaction((tx) => {
      const account = demoAccount(tx, accountId);
      if (account === null || seededProfile(account)) return;
      PROFILE_FIELDS.forEach((field) => account.set(field, SEEDED_PROFILE[field]));
      tx.saveRecord(account);
      profile = "restored";
    });
    state.stage = "execution";
    held = heldJobs(app.dao(), accountId);
  } catch (_) {
    logResetFailure(trigger, state.stage, state.collection);
    return null;
  }
  const line = { v: "obs/v1", event: "demo_reset", service: "pocketbase", trigger, deleted, held_jobs: held, profile };
  if (reason) line.reason = reason;
  console.log(JSON.stringify(line));
  return { deleted, held_jobs: held, profile };
}

// 5. POST /api/rounds/demo/sessions/end, the demo's sign-out: a demo
// caller's reset, then 204. With the demo off it answers as a route that
// doesn't exist; anyone else gets 401 or 403, and a reset that didn't
// finish 503.
function handleEnd(c, env) {
  if (!enabled(env)) throw new NotFoundError();
  const info = $apis.requestInfo(c);
  if (info.admin) throw new ForbiddenError(NOT_DEMO_SESSION);
  if (!info.authRecord) throw new UnauthorizedError(NO_SESSION);
  if (!isDemo(info.authRecord)) throw new ForbiddenError(NOT_DEMO_SESSION);
  if (resetAccount($app, info.authRecord.id, "end", "") === null) {
    return c.json(503, { code: 503, message: RESET_UNAVAILABLE, data: {} });
  }
  return c.noContent(204);
}

// A PocketBase date, such as "2026-11-12 10:00:00.000Z", in seconds; one
// it can't read counts as long ago.
function secondsOf(text) {
  const ms = Date.parse(String(text || "").replace(" ", "T"));
  return Number.isFinite(ms) ? Math.floor(ms / 1000) : 0;
}

// The jobs a worker may hold, as the reset's count reads them, one state
// each.
const HELD = ["account = {:id} && state = 'leased'", "account = {:id} && state = 'started'"];

// How many of the account's code-run jobs a worker may still hold, so the
// reset left them; each one goes at the first reset after it ends.
function heldJobs(dao, accountId) {
  return HELD.reduce((n, filter) => n + dao.findRecordsByFilter("execution_jobs", filter, "", 0, 0, { id: accountId })
    .length, 0);
}

// Why the sweep resets this demo account now, or "" to leave it. Only
// rows the reset can delete decide, so each of them goes within a day: the
// oldest is past the cap, or none changed in the quiet window. A job a
// worker may hold decides nothing until it ends. An account with no such
// row is reset when its profile isn't the seeded one. One that still has
// a sign-in other than its password is reset at once.
function sweepReason(dao, account, now) {
  if (dao.findAllExternalAuthsByRecord(account).length > 0) return "account";
  let newest = null;
  let oldest = null;
  const params = { id: account.id };
  const scan = (name, filter) => {
    dao.findRecordsByFilter(name, filter, "-updated", 1, 0, params).forEach((record) => {
      const updated = secondsOf(record.getString("updated"));
      if (newest === null || updated > newest) newest = updated;
    });
    dao.findRecordsByFilter(name, filter, "created", 1, 0, params).forEach((record) => {
      const created = secondsOf(record.getString("created"));
      if (oldest === null || created < oldest) oldest = created;
    });
  };
  RESET.forEach((name) => scan(name, "user = {:id}"));
  // A job's attempts, envelopes, command, and leases go with it, none
  // made more than moments before it, so its age stands for theirs.
  scan("execution_jobs", "account = {:id} && state != 'leased' && state != 'started'");
  if (oldest === null) return seededProfile(account) ? "" : "profile";
  if (oldest <= now - CAP_S) return "cap";
  if (newest <= now - QUIET_S) return "quiet";
  return "";
}

// 6. Every 5 minutes with the demo on: each demo account the sweep has a
// reason for is reset. Off, it does nothing.
function sweep(app, env, now) {
  if (!enabled(env)) return { demo: "disabled" };
  const out = { checked: 0, reset: 0, failed: 0 };
  let accounts;
  try {
    accounts = app.dao().findRecordsByFilter("users", DEMO_CANDIDATES);
  } catch (_) {
    logResetFailure("sweep", "accounts", "");
    out.failed += 1;
    return out;
  }
  accounts.forEach((account) => {
    if (!isDemo(account)) return;
    out.checked += 1;
    let reason;
    try {
      reason = sweepReason(app.dao(), account, now);
    } catch (_) {
      logResetFailure("sweep", "extent", "");
      out.failed += 1;
      return;
    }
    if (!reason) return;
    if (resetAccount(app, account.id, "sweep", reason) === null) out.failed += 1;
    else out.reset += 1;
  });
  return out;
}

function sweepNow(env) {
  return sweep($app, env, require(`${__hooks}/admission.js`).nowSeconds());
}

module.exports = {
  PROFILE_FIELDS,
  SEEDED_PROFILE,
  RESET,
  RESET_EXTRA,
  NOT_DEMO_WRITABLE,
  KEPT,
  QUIET_S,
  CAP_S,
  RESET_PASSES,
  NOT_DEMO_SESSION,
  RESET_UNAVAILABLE,
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
  guardPasswordOnly,
  guardSession,
  guardAccountUpdate,
  guardAccountDelete,
  guardEmailChange,
  ownerOf,
  demoOwned,
  guardContainedRequest,
  guardContainedModel,
  resetPass,
  resetAccount,
  handleEnd,
  sweepReason,
  sweep,
  sweepNow,
};
