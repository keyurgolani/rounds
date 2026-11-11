/// <reference path="../pb_data/types.d.ts" />

// Share link secrets (ROUNDS-00B-L04): the share resolver's service login
// and the resolver throttle.
//
// The only writer of share_resolvers and share_throttle
// (docs/security/server-writes.md).
//
//   share-resolver      the one share_resolvers record, which the runner
//                       logs in as to resolve share links for recipients,
//                       who have no account (D16, as execution_service).
//                       Its password follows ROUNDS_SHARE_RESOLVER_PASSWORD
//                       at every start and before every login, and its
//                       login answers only under the collection's exact name.
//                       PocketBase refuses the record on every route but
//                       RESOLVER_ROUTES (guardResolverRequest).
//   throttle, prune     the counters a resolve bumps before any lookup: the
//                       client's resolves a minute, its password tries on one
//                       bearer per 15 minutes, and the bearer's resolves a
//                       day. Keys are hashes only the runner can make, so a
//                       row names neither an address nor a digest.
//   lookup              the one route share-resolver may call: the throttle,
//                       then #11's lookup_capability by the bearer's digest.
//   begin, createShare, CreateShare's and RotateShareBearer's hook routes,
//   rotateShare         which only the runner reaches, with the owner's
//                       bearer and the runner key. A command's row is #1's
//                       admission_commands row (admission.js beginCommand);
//                       each write is one transaction that checks the row,
//                       makes the capability or swaps its digest (#11's
//                       create_capability and rotate_bearer), and keeps the
//                       result a retry replays. No bearer or password reaches
//                       PocketBase, only a digest and a verifier.
//
// A handler requires this file itself, as with admission.js:
//
//   const secrets = require(`${__hooks}/share_secrets.js`);
//
// The decisions take their store as an argument, so tests run them under
// node on plain objects (pocketbase/tests/test_share_secrets_hooks.py);
// pbStore() is the store over a PocketBase DAO.

const VERSION = "share-secrets/v1";

const COLLECTION = "share_resolvers";
const RESOLVER_USERNAME = "share-resolver";
const SECRET_ENV = "ROUNDS_SHARE_RESOLVER_PASSWORD";
// The runner takes the same range (app/share_resolver_client.py); bcrypt
// reads at most 72 bytes.
const SECRET_MIN_CHARS = 32;
const SECRET_MAX_CHARS = 72;
// The routes the share-resolver record may call, by method and route
// pattern. The lookup route lands with the resolver.
const RESOLVER_ROUTES = [{ method: "POST", path: "/api/rounds/share/lookup" }];
const REFUSED = "This isn't available.";

const THROTTLE = "share_throttle";
// The lookup route's answer (backend/app/share_resolver_client.py).
const LOOKUP_VERSION = "share-lookup/v1";
const HEX64 = /^[0-9a-f]{64}$/;
const RECORD_ID = /^[a-z0-9]{15}$/;
// What a share_create row keeps beside #1's fields: its snapshot call's key.
const SNAPSHOT_FIELD = "share_snapshot_command";
const OPERATIONS = ["share_create", "share_rotate"];
const TARGET_KIND = "legacy_artifact_snapshot";
const PROJECTION_VERSION = 1;
// Each scope's limit and window, in the order a resolve counts them. The
// numbers are profile v1; a later revision may change them.
const LIMITS = {
  ip_minute: { limit: 60, window_s: 60 },
  pw_15m: { limit: 10, window_s: 15 * 60 },
  digest_day: { limit: 100, window_s: 24 * 60 * 60 },
};
const ORDER = ["ip_minute", "pw_15m", "digest_day"];
const KEY = /^[0-9a-f]{64}$/;
// Each lookup removes at most this many counters whose window started over
// a day ago.
const PRUNE_LIMIT = 100;
const PRUNE_AGE_S = 24 * 60 * 60;

// ---------------------------------------------------------------------------
// Small checks
// ---------------------------------------------------------------------------

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function only(data, allowed) {
  return isObject(data) && Object.keys(data).every((key) => allowed.indexOf(key) >= 0);
}

// ---------------------------------------------------------------------------
// The throttle
// ---------------------------------------------------------------------------

// The checked entries, or null: ip_minute first, pw_15m only when a password
// came, digest_day last, each a 64-hex key, no key twice.
function checkThrottle(entries) {
  if (!Array.isArray(entries) || entries.length < 2 || entries.length > 3) return null;
  const expected = entries.length === 3 ? ORDER : ["ip_minute", "digest_day"];
  const out = [];
  for (let i = 0; i < entries.length; i += 1) {
    const entry = entries[i];
    if (!only(entry, ["scope", "key"]) || entry.scope !== expected[i]) return null;
    if (typeof entry.key !== "string" || !KEY.test(entry.key)) return null;
    if (out.some((seen) => seen.key === entry.key)) return null;
    out.push({ scope: entry.scope, key: entry.key });
  }
  return out;
}

// Counts one resolve in each counter, in order, and stops at the first one
// past its limit, so a client over its minute adds no other row. A counter
// whose window has ended (or starts after now, if the clock moved back)
// starts again. Answers { throttled, retry_after } in whole seconds. The
// answer depends only on these counters, never on what the bearer is.
//
// store: counter(key) -> { key, scope, window_start, count } or null;
//        save(row)
function throttle(store, entries, now) {
  for (let i = 0; i < entries.length; i += 1) {
    const entry = entries[i];
    const rule = LIMITS[entry.scope];
    let row = store.counter(entry.key);
    if (row === null) row = { key: entry.key, scope: entry.scope, window_start: now, count: 0 };
    if (row.scope !== entry.scope || row.window_start + rule.window_s <= now || row.window_start > now) {
      row.scope = entry.scope;
      row.window_start = now;
      row.count = 0;
    }
    row.count += 1;
    store.save(row);
    if (row.count > rule.limit) {
      return { throttled: true, retry_after: Math.max(1, row.window_start + rule.window_s - now) };
    }
  }
  return { throttled: false, retry_after: 0 };
}

// Removes up to PRUNE_LIMIT counters whose window started over a day ago.
// store: deleteBefore(cutoff, limit) -> how many it removed
function prune(store, now) {
  return store.deleteBefore(now - PRUNE_AGE_S, PRUNE_LIMIT);
}

// ---------------------------------------------------------------------------
// The share-resolver record
// ---------------------------------------------------------------------------

function usableSecret(secret) {
  if (typeof secret !== "string" || secret.length < SECRET_MIN_CHARS || secret.length > SECRET_MAX_CHARS) return false;
  for (let i = 0; i < secret.length; i += 1) {
    const code = secret.charCodeAt(i);
    if (code < 33 || code > 126) return false;
  }
  return true;
}

// share-resolver exists with ROUNDS_SHARE_RESOLVER_PASSWORD as its password.
// A secret that's unset, not SECRET_MIN_CHARS to SECRET_MAX_CHARS long, or
// not printable ASCII without spaces creates nothing, and an existing record
// gets a random password, so no old secret still logs in. `accounts` is the
// small interface over the share_resolvers collection. Returns what it did,
// for the log, never the secret.
function ensureResolver(accounts, secret, randomSecret) {
  const existing = accounts.find(RESOLVER_USERNAME);
  if (!usableSecret(secret)) {
    if (existing !== null) accounts.setPassword(existing, randomSecret());
    return existing === null ? "skipped" : "disabled";
  }
  if (existing === null) {
    accounts.create(RESOLVER_USERNAME, secret);
    return "created";
  }
  if (accounts.validatePassword(existing, secret)) return "unchanged";
  accounts.setPassword(existing, secret);
  return "updated";
}

// Whether the share-resolver record may make this request: only to
// RESOLVER_ROUTES, matched by method and route pattern.
function resolverMayCall(method, routePath) {
  return RESOLVER_ROUTES.some((route) => route.method === method && route.path === routePath);
}

// ---------------------------------------------------------------------------
// The lookup
// ---------------------------------------------------------------------------

// The checked lookup, or null: a digest and the throttle's counters.
function checkLookup(data) {
  if (!only(data, ["digest", "throttle"])) return null;
  if (typeof data.digest !== "string" || !HEX64.test(data.digest)) return null;
  const entries = checkThrottle(data.throttle);
  return entries === null ? null : { digest: data.digest, throttle: entries };
}

// The throttle first, in its own transaction, then the lookup, so a 429
// never depends on whether the bearer is live. Each call also prunes old
// counters.
// deps: transaction(fn(store)), now (seconds), lookup(digest) -> fields or null
function lookup(deps, input) {
  let verdict = null;
  deps.transaction((store) => {
    prune(store, deps.now);
    verdict = throttle(store, input.throttle, deps.now);
  });
  if (verdict.throttled) {
    return { status: 200, body: { v: LOOKUP_VERSION, throttled: true, retry_after: verdict.retry_after } };
  }
  return { status: 200, body: { v: LOOKUP_VERSION, throttled: false, capability: deps.lookup(input.digest) } };
}

// ---------------------------------------------------------------------------
// The commands
// ---------------------------------------------------------------------------

function error(status, code) {
  return { status, body: { v: VERSION, error: code } };
}

function isId(value) {
  return typeof value === "string" && RECORD_ID.test(value);
}

function isWhole(value, least, most) {
  return typeof value === "number" && isFinite(value) && Math.floor(value) === value && value >= least &&
    (most === undefined || value <= most);
}

function textOrNull(value, max) {
  if (value === undefined || value === null) return true;
  return typeof value === "string" && value.length <= max;
}

// The checked begin, or null. A share_create names the key its snapshot
// call runs under; a share_rotate names none.
function checkBegin(data, commandPattern) {
  if (!only(data, ["command_id", "operation", "fingerprint", "snapshot_command_id"])) return null;
  if (typeof data.command_id !== "string" || !commandPattern.test(data.command_id)) return null;
  if (OPERATIONS.indexOf(data.operation) < 0) return null;
  if (typeof data.fingerprint !== "string" || !HEX64.test(data.fingerprint)) return null;
  const snapshot = data.snapshot_command_id === undefined ? null : data.snapshot_command_id;
  if (data.operation === "share_create") {
    if (typeof snapshot !== "string" || !commandPattern.test(snapshot) || snapshot === data.command_id) return null;
  } else if (snapshot !== null) {
    return null;
  }
  return { command_id: data.command_id, operation: data.operation, fingerprint: data.fingerprint, snapshot };
}

// Before any work: the account's command under this key. A completed one
// answers its kept result before anything else happens; any other state
// runs again, with the snapshot key its first attempt stored.
// deps: admission, transaction(fn(tx)) where tx.commands is admission's
//       store, with tx.snapshotOf(command) and tx.setSnapshot(command, key);
//       now (seconds)
function begin(deps, account, input) {
  let out = null;
  deps.transaction((tx) => {
    const begun = deps.admission.beginCommand(tx.commands, account, input.command_id, input.operation,
      input.fingerprint, deps.now);
    if (begun.verdict === "mismatch") {
      out = error(409, "idempotency_mismatch");
      return;
    }
    if (begun.verdict === "replay") {
      out = { status: 200, body: { v: VERSION, verdict: "replay", result: begun.result } };
      return;
    }
    let snapshot = null;
    if (input.operation === "share_create") {
      snapshot = tx.snapshotOf(begun.command);
      if (!snapshot) {
        snapshot = input.snapshot;
        tx.setSnapshot(begun.command, snapshot);
      }
    }
    out = { status: 200, body: { v: VERSION, verdict: begun.verdict, snapshot_command_id: snapshot } };
  });
  return out;
}

// The checked create, or null. #11's create_capability checks each value
// again; this checks only the shape.
function checkCreate(data, commandPattern) {
  const keys = ["command_id", "fingerprint", "snapshot_id", "purpose", "expires_at", "password_policy_ref",
    "bearer_digest", "digest_key_version"];
  if (!only(data, keys)) return null;
  if (typeof data.command_id !== "string" || !commandPattern.test(data.command_id)) return null;
  if (typeof data.fingerprint !== "string" || !HEX64.test(data.fingerprint)) return null;
  if (!isId(data.snapshot_id)) return null;
  if (!textOrNull(data.purpose, 400) || !textOrNull(data.expires_at, 40)) return null;
  if (typeof data.password_policy_ref !== "string" || data.password_policy_ref.length > 512) return null;
  if (typeof data.bearer_digest !== "string" || !HEX64.test(data.bearer_digest)) return null;
  if (!isWhole(data.digest_key_version, 1, 999)) return null;
  return {
    command_id: data.command_id,
    fingerprint: data.fingerprint,
    snapshot_id: data.snapshot_id,
    purpose: data.purpose === undefined ? null : data.purpose,
    expires_at: data.expires_at === undefined ? null : data.expires_at,
    password_policy_ref: data.password_policy_ref,
    bearer_digest: data.bearer_digest,
    digest_key_version: data.digest_key_version,
  };
}

// Thrown inside a write's transaction for an answer that writes nothing, so
// the transaction keeps nothing it began.
function Abort() {}

// The scope a share answers with, from its snapshot: what it is of.
function scopeOf(source) {
  const scope = { target_kind: TARGET_KIND };
  scope[source.kind === "resume" ? "resume_id" : "variant_id"] = source.id;
  scope.projection_version = PROJECTION_VERSION;
  return scope;
}

// CreateShare's write, in one transaction: the command row, the capability,
// and the result a retry with the same key replays. PocketBase never sees
// the bearer, so the kept result can't hold it.
// deps: admission, transaction(fn(tx)): tx.commands, tx.createCapability(args)
//       -> #11's answer, tx.snapshotSource(id) -> { kind, id } or null; now
function createShare(deps, account, input) {
  let out = null;
  try {
    deps.transaction((tx) => {
      const begun = deps.admission.beginCommand(tx.commands, account, input.command_id, "share_create",
        input.fingerprint, deps.now);
      if (begun.verdict === "mismatch") {
        out = error(409, "idempotency_mismatch");
        throw new Abort();
      }
      if (begun.verdict === "replay") {
        out = { status: 200, body: { v: VERSION, delivery: "already_issued", result: begun.result } };
        throw new Abort();
      }
      const made = tx.createCapability({
        owner: account.id,
        snapshot_id: input.snapshot_id,
        purpose: input.purpose,
        expires_at: input.expires_at,
        password_policy_ref: input.password_policy_ref,
        bearer_digest: input.bearer_digest,
        digest_key_version: input.digest_key_version,
      });
      const source = made.status === "created" ? tx.snapshotSource(input.snapshot_id) : null;
      if (made.status !== "created" || source === null) {
        out = made.status === "invalid" ? error(400, "invalid_request") : error(404, "not_found");
        throw new Abort();
      }
      const capability = made.capability;
      const result = {
        status: 201,
        body: {
          capability_id: capability.id,
          scope: scopeOf(source),
          state: capability.status,
          expires_at: capability.expires_at,
          capability_version: capability.capability_version,
        },
      };
      if (!deps.admission.completeBegunCommand(tx.commands, begun.command, result)) throw new Error("result not kept");
      out = { status: 201, body: { v: VERSION, delivery: "issued", result } };
    });
  } catch (err) {
    if (!(err instanceof Abort)) throw err;
  }
  return out;
}

// The checked rotate, or null.
function checkRotate(data, commandPattern) {
  const keys = ["command_id", "fingerprint", "expected_capability_version", "bearer_digest", "digest_key_version"];
  if (!only(data, keys)) return null;
  if (typeof data.command_id !== "string" || !commandPattern.test(data.command_id)) return null;
  if (typeof data.fingerprint !== "string" || !HEX64.test(data.fingerprint)) return null;
  if (!isWhole(data.expected_capability_version, 1)) return null;
  if (typeof data.bearer_digest !== "string" || !HEX64.test(data.bearer_digest)) return null;
  if (!isWhole(data.digest_key_version, 1, 999)) return null;
  return {
    command_id: data.command_id,
    fingerprint: data.fingerprint,
    expected_capability_version: data.expected_capability_version,
    bearer_digest: data.bearer_digest,
    digest_key_version: data.digest_key_version,
  };
}

const ROTATE_REFUSALS = {
  not_found: [404, "not_found"],
  revoked: [409, "capability_revoked"],
  expired: [409, "capability_expired"],
  conflict: [409, "capability_version_conflict"],
  invalid: [400, "invalid_request"],
};

// RotateShareBearer's write, in one transaction: the command row, the digest
// swap with its version raise, and the result a retry replays. Of any number
// of rotations at one version, one swaps; each other one finds the version
// moved on, or its own key's kept result.
// deps: admission, transaction(fn(tx)): tx.commands, tx.rotateBearer(args)
//       -> #11's answer; now
function rotateShare(deps, account, id, input) {
  let out = null;
  try {
    deps.transaction((tx) => {
      const begun = deps.admission.beginCommand(tx.commands, account, input.command_id, "share_rotate",
        input.fingerprint, deps.now);
      if (begun.verdict === "mismatch") {
        out = error(409, "idempotency_mismatch");
        throw new Abort();
      }
      if (begun.verdict === "replay") {
        out = { status: 200, body: { v: VERSION, delivery: "already_issued", result: begun.result } };
        throw new Abort();
      }
      const rotated = tx.rotateBearer({
        owner: account.id,
        id,
        expected_version: input.expected_capability_version,
        bearer_digest: input.bearer_digest,
        digest_key_version: input.digest_key_version,
      });
      if (rotated.status !== "rotated") {
        const refusal = ROTATE_REFUSALS[rotated.status] || [503, "unavailable"];
        out = error(refusal[0], refusal[1]);
        throw new Abort();
      }
      const capability = rotated.capability;
      const result = {
        status: 200,
        body: {
          capability_id: capability.id,
          state: capability.status,
          expires_at: capability.expires_at,
          capability_version: capability.capability_version,
        },
      };
      if (!deps.admission.completeBegunCommand(tx.commands, begun.command, result)) throw new Error("result not kept");
      out = { status: 200, body: { v: VERSION, delivery: "issued", result } };
    });
  } catch (err) {
    if (!(err instanceof Abort)) throw err;
  }
  return out;
}

// ---------------------------------------------------------------------------
// PocketBase
// ---------------------------------------------------------------------------

function emit(fields, error) {
  const line = JSON.stringify(Object.assign({ v: "obs/v1", event: "share_resolver", service: "pocketbase" }, fields));
  if (error) console.error(line);
  else console.log(line);
}

// The throttle's store over `dao`. Rows are saved through the DAO: every
// value is checked above, and a resolve shouldn't pay for a form.
function pbStore(dao) {
  let collection = null;
  function throttleCollection() {
    if (collection === null) collection = dao.findCollectionByNameOrId(THROTTLE);
    return collection;
  }
  return {
    counter: (key) => {
      const rows = dao.findRecordsByFilter(THROTTLE, "key = {:key}", "", 1, 0, { key });
      if (rows.length === 0) return null;
      const record = rows[0];
      return {
        key: record.getString("key"),
        scope: record.getString("scope"),
        window_start: record.getInt("window_start"),
        count: record.getInt("count"),
        _record: record,
      };
    },
    save: (row) => {
      const record = row._record || new Record(throttleCollection());
      record.set("key", row.key);
      record.set("scope", row.scope);
      record.set("window_start", row.window_start);
      record.set("count", row.count);
      dao.saveRecord(record);
      row._record = record;
    },
    deleteBefore: (cutoff, limit) => {
      const rows = dao.findRecordsByFilter(THROTTLE, "window_start < {:cutoff}", "window_start", limit, 0, { cutoff });
      rows.forEach((record) => dao.deleteRecord(record));
      return rows.length;
    },
  };
}

function randomSecret() {
  return $security.randomString(64);
}

// The share_resolvers collection as ensureResolver sees it, over `dao`.
function resolverAccounts(dao) {
  return {
    find: (username) => {
      try {
        return dao.findAuthRecordByUsername(COLLECTION, username);
      } catch (_) {
        return null;
      }
    },
    create: (username, secret) => {
      const record = new Record(dao.findCollectionByNameOrId(COLLECTION));
      record.set("username", username);
      record.set("verified", true);
      record.setPassword(secret);
      dao.saveRecord(record);
    },
    validatePassword: (record, secret) => record.validatePassword(secret),
    setPassword: (record, secret) => {
      record.setPassword(secret);
      dao.saveRecord(record);
    },
  };
}

function logResolver(did) {
  emit({ resolver: did }, did === "skipped" || did === "disabled");
  if (did === "skipped" || did === "disabled") {
    console.error(
      SECRET_ENV + " is unset or not " + SECRET_MIN_CHARS + " to " + SECRET_MAX_CHARS +
        " printable characters; the share resolver can't log in.",
    );
  }
}

function collectionExists(dao) {
  try {
    dao.findCollectionByNameOrId(COLLECTION);
    return true;
  } catch (_) {
    return false;
  }
}

// After bootstrap, on every start: share-resolver follows the secret in the
// environment, so a changed or unset secret takes effect, and every token
// the old one got stops working, before anything logs in. On the first start
// after the migration the collection doesn't exist yet, since PocketBase
// runs migrations after bootstrap; the first login does it then
// (syncResolverForLogin).
function bootstrapResolver() {
  const dao = $app.dao();
  if (!collectionExists(dao)) return "absent";
  const did = ensureResolver(resolverAccounts(dao), $os.getenv(SECRET_ENV), randomSecret);
  logResolver(did);
  return did;
}

// Whether a login request named the collection exactly. A login under any
// other spelling of it, or under its id, gets the 404 an unknown collection
// gets, whatever the proxy in front let through.
function exactResolverPath(httpContext) {
  if (!httpContext) return false;
  try {
    return httpContext.pathParam("collection") === COLLECTION;
  } catch (_) {
    return false;
  }
}

// Before PocketBase checks a share_resolvers login: the login answers only
// its exact collection name. Then share-resolver follows the secret, and the
// check uses the record as it is now.
function syncResolverForLogin(e) {
  if (!exactResolverPath(e.httpContext)) throw new NotFoundError();
  if (e.identity !== RESOLVER_USERNAME) return;
  const accounts = resolverAccounts($app.dao());
  const did = ensureResolver(accounts, $os.getenv(SECRET_ENV), randomSecret);
  if (did !== "unchanged") logResolver(did);
  e.record = accounts.find(RESOLVER_USERNAME);
}

// routerUse, on every request: a share_resolvers record gets 403 everywhere
// but RESOLVER_ROUTES, so it reads and writes nothing else.
function guardResolverRequest(c) {
  const record = $apis.requestInfo(c).authRecord;
  if (!record || record.collection().name !== COLLECTION) return;
  if (resolverMayCall(c.request().method, c.path())) return;
  emit({ outcome: "refused" });
  throw new ForbiddenError(REFUSED);
}

// The owner's command routes take the caller's bearer and the runner key.
// The checked call, or { response } already answered.
function ownerCall(c) {
  const admission = require(`${__hooks}/admission.js`);
  const info = $apis.requestInfo(c);
  const record = info.authRecord;
  if (!record) throw new UnauthorizedError("Sign in to continue.");
  const refused = admission.runnerKeyError(info.headers, $os.getenv(admission.RUNNER_KEY_ENV));
  if (refused !== null) return { response: c.json(refused.status, { v: VERSION, error: refused.body.error }) };
  return { admission, info, account: { id: record.id } };
}

// One command transaction's view, over its DAO.
function commandTx(admission, dao) {
  const capabilities = require(`${__hooks}/share_capabilities.js`);
  return {
    commands: admission.pbStore(dao),
    snapshotOf: (command) => command._record.getString(SNAPSHOT_FIELD),
    setSnapshot: (command, key) => {
      command._record.set(SNAPSHOT_FIELD, key);
      dao.saveRecord(command._record);
    },
    createCapability: (a) => capabilities.create_capability(dao, a.owner, a.snapshot_id, a.purpose, a.expires_at,
      a.password_policy_ref, a.bearer_digest, a.digest_key_version),
    snapshotSource: (snapshotId) => {
      try {
        const snapshot = dao.findRecordById("legacy_artifact_snapshots", snapshotId);
        return { kind: snapshot.getString("source_kind"), id: snapshot.getString("source_id") };
      } catch (_) {
        return null;
      }
    },
    rotateBearer: (a) => capabilities.rotate_bearer(dao, a.owner, a.id, a.expected_version, a.bearer_digest,
      a.digest_key_version),
  };
}

function runCommand(c, check, decide) {
  const call = ownerCall(c);
  if (call.response) return call.response;
  const input = check(call.info.data, call.admission.COMMAND_ID);
  if (input === null) return c.json(400, { v: VERSION, error: "invalid_request" });
  let out = null;
  try {
    out = decide({
      admission: call.admission,
      transaction: (fn) => $app.dao().runInTransaction((txDao) => fn(commandTx(call.admission, txDao))),
      now: call.admission.nowSeconds(),
    }, call.account, input);
  } catch (err) {
    emit({ outcome: "unavailable", route: "command" }, true);
    return c.json(503, { v: VERSION, error: "unavailable" });
  }
  return c.json(out.status, out.body);
}

// POST /api/rounds/share/commands
function handleBegin(c) {
  return runCommand(c, checkBegin, begin);
}

// POST /api/rounds/share/capabilities
function handleCreate(c) {
  return runCommand(c, checkCreate, createShare);
}

// POST /api/rounds/share/capabilities/:id/rotate
function handleRotate(c) {
  const id = c.pathParam("id");
  return runCommand(c, checkRotate, (deps, account, input) => {
    if (!isId(id)) return error(404, "not_found");
    return rotateShare(deps, account, id, input);
  });
}

// POST /api/rounds/share/lookup, as share-resolver only.
function handleLookup(c) {
  const info = $apis.requestInfo(c);
  const record = info.authRecord;
  if (!record || record.collection().name !== COLLECTION || record.username() !== RESOLVER_USERNAME) {
    throw new ForbiddenError(REFUSED);
  }
  const input = checkLookup(info.data);
  if (input === null) return c.json(400, { v: LOOKUP_VERSION, error: "invalid_request" });
  const admission = require(`${__hooks}/admission.js`);
  const capabilities = require(`${__hooks}/share_capabilities.js`);
  try {
    const out = lookup({
      transaction: (fn) => $app.dao().runInTransaction((txDao) => fn(pbStore(txDao))),
      now: admission.nowSeconds(),
      lookup: (digest) => capabilities.lookup_capability(digest),
    }, input);
    if (out.body.throttled) emit({ outcome: "throttled" });
    return c.json(out.status, out.body);
  } catch (err) {
    emit({ outcome: "unavailable", route: "lookup" }, true);
    return c.json(503, { v: LOOKUP_VERSION, error: "unavailable" });
  }
}

module.exports = {
  VERSION,
  COLLECTION,
  RESOLVER_USERNAME,
  SECRET_ENV,
  SECRET_MIN_CHARS,
  SECRET_MAX_CHARS,
  RESOLVER_ROUTES,
  THROTTLE,
  LIMITS,
  ORDER,
  PRUNE_LIMIT,
  PRUNE_AGE_S,
  LOOKUP_VERSION,
  SNAPSHOT_FIELD,
  checkThrottle,
  throttle,
  prune,
  checkLookup,
  lookup,
  checkBegin,
  begin,
  checkCreate,
  createShare,
  checkRotate,
  rotateShare,
  usableSecret,
  ensureResolver,
  resolverMayCall,
  pbStore,
  bootstrapResolver,
  syncResolverForLogin,
  guardResolverRequest,
  handleBegin,
  handleCreate,
  handleRotate,
  handleLookup,
};
