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
  checkThrottle,
  throttle,
  prune,
  usableSecret,
  ensureResolver,
  resolverMayCall,
  pbStore,
  bootstrapResolver,
  syncResolverForLogin,
  guardResolverRequest,
};
