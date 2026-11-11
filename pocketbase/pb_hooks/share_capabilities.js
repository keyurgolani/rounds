/// <reference path="../pb_data/types.d.ts" />

// Share capabilities (ROUNDS-00B-L03 stage 2), and the only writer of
// share_capabilities (docs/security/server-writes.md):
//
//   create_capability   a library that #12's create and #14's re-issue call
//                       inside their own transaction
//   lookup_capability   the read #12's lookup route makes; nothing calls it
//                       until then
//   listOwn, revoke     the owner's two hook routes (share_capabilities.pb.js),
//                       which only the runner reaches, with the owner's
//                       bearer; nginx and the Vite proxy answer
//                       /api/rounds/share with 404
//   guardCreate,        model hooks: what any writer, a superuser included,
//   guardUpdate         may store, and the only changes it may make
//   onSourceDeleted     revokes the capabilities over a deleted resume's or
//                       variant's snapshots and keeps the snapshots
//   onAccountDelete     deletes an account's capabilities in the account
//                       delete's transaction, before its snapshots go
//
// A capability resolves only while it's active and unexpired, its snapshot
// is in its own account and still holds the content it was made over, and
// that snapshot's source still exists in the same account. lookup checks
// every one of those on every call, whatever a hook did or didn't do.
//
// A handler requires this file itself, as with admission.js:
//
//   const capabilities = require(`${__hooks}/share_capabilities.js`);
//
// The decisions take their store as an argument, so tests run them under
// node on plain objects (pocketbase/tests/test_share_capability_hooks.py);
// pbStore() is the store over a PocketBase DAO.

const VERSION = "share-capability/v1";
const COLLECTION = "share_capabilities";
const SNAPSHOTS = "legacy_artifact_snapshots";
const KIND = "legacy_artifact_snapshot";
const PROJECTION_VERSION = 1;
const VIEW_POLICY = "disabled";
const SOURCE_KINDS = ["resume", "variant"];
const REASONS = ["owner", "source_deleted"];

const DAY_MS = 24 * 60 * 60 * 1000;
const DEFAULT_DAYS = 90;
const MAX_DAYS = 365;
// A new capability lives at least this long, so it's still unexpired when
// the model hook checks it a moment later.
const MIN_LIFETIME_MS = 60 * 1000;
const PURPOSE_MAX = 80;
const PURPOSE_FALLBACK = "Shared resume";
const LIST_LIMIT = 200;
const BATCH = 500;
// #4's cap on a snapshot's markup.
const MAX_MARKUP_BYTES = 2 * 1024 * 1024;

const RECORD_ID = /^[a-z0-9]{15}$/;
const DIGEST = /^[0-9a-f]{64}$/;
const CHECKSUM = /^sha256:[0-9a-f]{64}$/;
// TODO(ROUNDS-00B-L04): #12 pins its verifier's format. Until then, any
// printable value up to 512 characters, or none.
const VERIFIER = /^[!-~]{1,512}$/;
const CONTROL = /[\u0000-\u001f\u007f]/;
const CONTROLS = /[\u0000-\u001f\u007f]/g;
// PocketBase 0.22's datetime text, "2006-01-02 15:04:05.000Z", or the same
// with a T.
const DATETIME = /^([0-9]{4})-([0-9]{2})-([0-9]{2})[ T]([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,9}))?Z$/;

// What the owner sees, and all the owner's routes answer with.
const OWNER_FIELDS = ["id", "status", "revoked_reason", "purpose", "expires_at", "created", "revoked_at"];
// What lookup_capability answers with, for #12's route: #12's fields plus
// the markup, which is projection v1.
const LOOKUP_FIELDS = ["id", "status", "expires_at", "capability_version", "snapshot", "password_policy_ref", "markup"];
// What no update may change.
const FIXED = [
  "user", "target_kind", "snapshot", "target_checksum", "purpose", "password_policy_ref", "view_policy",
  "projection_version", "digest_key_version",
];
// What an update of an active capability may change, within the rules.
const MUTABLE = ["capability_version", "bearer_digest", "expires_at", "status", "revoked_at", "revoked_reason"];
const CREATE_KEYS = [
  "owner", "snapshot_id", "purpose", "expires_at", "password_policy_ref", "bearer_digest", "digest_key_version",
];

const NOT_FOUND = { status: 404, body: { v: VERSION, error: "not_found" } };

// ---------------------------------------------------------------------------
// Small checks
// ---------------------------------------------------------------------------

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function only(data, allowed) {
  return isObject(data) && Object.keys(data).every((key) => allowed.indexOf(key) >= 0);
}

function isId(value) {
  return typeof value === "string" && RECORD_ID.test(value);
}

function isInt(value) {
  return typeof value === "number" && isFinite(value) && Math.floor(value) === value;
}

function absent(value) {
  return value === null || value === undefined || value === "";
}

// Characters as PocketBase counts them: a surrogate pair is one.
function charCount(text) {
  return text.replace(/[\uD800-\uDBFF][\uDC00-\uDFFF]/g, "_").length;
}

function cutChars(text, max) {
  let out = "";
  let count = 0;
  for (let i = 0; i < text.length && count < max; i += 1) {
    const code = text.charCodeAt(i);
    if (code >= 0xd800 && code <= 0xdbff && i + 1 < text.length) {
      out += text.slice(i, i + 2);
      i += 1;
    } else {
      out += text[i];
    }
    count += 1;
  }
  return out;
}

function pad(value, width) {
  let text = String(value);
  while (text.length < width) text = "0" + text;
  return text;
}

// Milliseconds since the epoch for PocketBase's datetime text, or null for
// anything else, a day that doesn't exist included.
function parseDate(value) {
  if (typeof value !== "string") return null;
  const m = DATETIME.exec(value);
  if (m === null) return null;
  const year = Number(m[1]);
  const month = Number(m[2]);
  const day = Number(m[3]);
  const hour = Number(m[4]);
  const minute = Number(m[5]);
  const second = Number(m[6]);
  const ms = Number(((m[7] || "") + "000").slice(0, 3));
  const at = Date.UTC(year, month - 1, day, hour, minute, second, ms);
  const back = new Date(at);
  if (back.getUTCFullYear() !== year || back.getUTCMonth() !== month - 1 || back.getUTCDate() !== day ||
      back.getUTCHours() !== hour || back.getUTCMinutes() !== minute || back.getUTCSeconds() !== second) {
    return null;
  }
  return at;
}

// PocketBase's datetime text for milliseconds since the epoch.
function formatDate(ms) {
  const d = new Date(ms);
  return d.getUTCFullYear() + "-" + pad(d.getUTCMonth() + 1, 2) + "-" + pad(d.getUTCDate(), 2) + " " +
    pad(d.getUTCHours(), 2) + ":" + pad(d.getUTCMinutes(), 2) + ":" + pad(d.getUTCSeconds(), 2) + "." +
    pad(d.getUTCMilliseconds(), 3) + "Z";
}

function purposeOk(value) {
  return typeof value === "string" && value === value.trim() && value !== "" &&
    charCount(value) <= PURPOSE_MAX && !CONTROL.test(value);
}

// The default purpose: the source's name, without control characters,
// trimmed and cut to 80 characters.
function defaultPurpose(name) {
  const clean = typeof name === "string" ? cutChars(name.replace(CONTROLS, " ").trim(), PURPOSE_MAX).trim() : "";
  return clean === "" ? PURPOSE_FALLBACK : clean;
}

function ownerView(row) {
  const out = {};
  OWNER_FIELDS.forEach((key) => {
    out[key] = typeof row[key] === "string" ? row[key] : "";
  });
  return out;
}

// The fields a revoke sets on an active row.
function revokedFields(row, reason, now) {
  return {
    status: "revoked",
    revoked_at: formatDate(now),
    revoked_reason: reason,
    capability_version: row.capability_version + 1,
  };
}

// ---------------------------------------------------------------------------
// create_capability
// ---------------------------------------------------------------------------

// The checked arguments, or { error: <argument> } for the first bad one.
// Nothing here reads the store.
function checkCreate(input, now) {
  if (!only(input, CREATE_KEYS)) return { error: "arguments" };
  if (!isId(input.owner)) return { error: "owner" };
  if (!isId(input.snapshot_id)) return { error: "snapshot_id" };
  let purpose = null;
  if (!absent(input.purpose)) {
    if (typeof input.purpose !== "string") return { error: "purpose" };
    const trimmed = input.purpose.trim();
    if (!purposeOk(trimmed)) return { error: "purpose" };
    purpose = trimmed;
  }
  let expires = now + DEFAULT_DAYS * DAY_MS;
  if (!absent(input.expires_at)) {
    const at = parseDate(input.expires_at);
    if (at === null || at < now + MIN_LIFETIME_MS || at > now + MAX_DAYS * DAY_MS) return { error: "expires_at" };
    expires = at;
  }
  let verifier = "";
  if (!absent(input.password_policy_ref)) {
    if (typeof input.password_policy_ref !== "string" || !VERIFIER.test(input.password_policy_ref)) {
      return { error: "password_policy_ref" };
    }
    verifier = input.password_policy_ref;
  }
  if (typeof input.bearer_digest !== "string" || !DIGEST.test(input.bearer_digest)) return { error: "bearer_digest" };
  if (!isInt(input.digest_key_version) || input.digest_key_version < 1 || input.digest_key_version > 999) {
    return { error: "digest_key_version" };
  }
  return {
    owner: input.owner,
    snapshot_id: input.snapshot_id,
    purpose,
    expires,
    verifier,
    digest: input.bearer_digest,
    key_version: input.digest_key_version,
  };
}

// deps:
//   store   reads and the insert, inside the caller's transaction:
//           snapshot(id), source(kind, id), isDemo(user), hasMarkup(snapshot),
//           insert(fields) -> { id, created }
//   now     milliseconds since the epoch
//   log     (fields) => one line with no id, owner, or value
//
// Answers { status: "created", capability } with the owner's fields,
// { status: "invalid", field } for a bad argument (nothing read), or
// { status: "share-unavailable" } for a missing, another account's, or
// ineligible snapshot, one answer for all three, with nothing written.
function create(deps, input) {
  const log = deps.log || (() => {});
  const args = checkCreate(input, deps.now);
  if (args.error) {
    log({ outcome: "invalid", field: args.error });
    return { status: "invalid", field: args.error };
  }
  const unavailable = (why) => {
    log({ outcome: "share_unavailable", why });
    return { status: "share-unavailable" };
  };
  const store = deps.store;
  const snapshot = store.snapshot(args.snapshot_id);
  if (snapshot === null || snapshot.user !== args.owner) return unavailable("snapshot");
  if (!CHECKSUM.test(snapshot.content_checksum || "") || SOURCE_KINDS.indexOf(snapshot.source_kind) < 0 ||
      !isId(snapshot.source_id)) {
    return unavailable("snapshot");
  }
  if (store.isDemo(args.owner)) return unavailable("demo_account");
  const source = store.source(snapshot.source_kind, snapshot.source_id);
  if (source === null || source.user !== args.owner) return unavailable("source");
  if (!store.hasMarkup(snapshot)) return unavailable("markup");

  const fields = {
    user: args.owner,
    target_kind: KIND,
    snapshot: snapshot.id,
    target_checksum: snapshot.content_checksum,
    purpose: args.purpose !== null ? args.purpose : defaultPurpose(source.name),
    expires_at: formatDate(args.expires),
    password_policy_ref: args.verifier,
    view_policy: VIEW_POLICY,
    capability_version: 1,
    status: "active",
    revoked_at: "",
    revoked_reason: "",
    projection_version: PROJECTION_VERSION,
    bearer_digest: args.digest,
    digest_key_version: args.key_version,
  };
  const saved = store.insert(fields);
  log({ outcome: "created" });
  return { status: "created", capability: ownerView(Object.assign({}, fields, saved)) };
}

// ---------------------------------------------------------------------------
// lookup_capability
// ---------------------------------------------------------------------------

// deps:
//   store    byDigest(digest), snapshot(id), source(kind, id), and
//            markup(snapshot) -> the markup text, or null
//   now      milliseconds since the epoch
//   sha256   (text) => hex over the text's UTF-8 bytes
//
// Answers { capability, reason }: capability is LOOKUP_FIELDS, or null for
// every state that doesn't resolve; reason says which, for tests and logs
// only. A store error is thrown, for the caller to answer as degraded.
function lookup(deps, digest) {
  const miss = (reason) => ({ capability: null, reason });
  if (typeof digest !== "string" || !DIGEST.test(digest)) return miss("malformed");
  const store = deps.store;
  const cap = store.byDigest(digest);
  if (cap === null) return miss("unknown");
  if (cap.status !== "active") return miss("revoked");
  const expires = parseDate(cap.expires_at);
  if (expires === null || expires <= deps.now) return miss("expired");
  if (cap.target_kind !== KIND || cap.projection_version !== PROJECTION_VERSION || cap.view_policy !== VIEW_POLICY) {
    return miss("unsupported");
  }
  const snapshot = isId(cap.snapshot) ? store.snapshot(cap.snapshot) : null;
  if (snapshot === null || snapshot.user !== cap.user) return miss("snapshot");
  if (snapshot.content_checksum !== cap.target_checksum) return miss("checksum");
  const source = SOURCE_KINDS.indexOf(snapshot.source_kind) >= 0 && isId(snapshot.source_id)
    ? store.source(snapshot.source_kind, snapshot.source_id)
    : null;
  if (source === null || source.user !== cap.user) return miss("source");
  const markup = store.markup(snapshot);
  if (typeof markup !== "string" || markup === "" || "sha256:" + deps.sha256(markup) !== cap.target_checksum) {
    return miss("markup");
  }
  return {
    capability: {
      id: cap.id,
      status: cap.status,
      expires_at: cap.expires_at,
      capability_version: cap.capability_version,
      snapshot: cap.snapshot,
      password_policy_ref: cap.password_policy_ref,
      markup,
    },
    reason: "available",
  };
}

// ---------------------------------------------------------------------------
// Model hooks: what a row may hold, and how it may change
// ---------------------------------------------------------------------------

// The first reason a new row may not be stored, or null. snapshot is the
// row's snapshot as the store reads it, or null.
function screenCreate(row, snapshot, now) {
  if (!isId(row.user)) return "user";
  if (row.target_kind !== KIND) return "target_kind";
  if (!isId(row.snapshot) || snapshot === null || snapshot.id !== row.snapshot || snapshot.user !== row.user) {
    return "snapshot";
  }
  if (!CHECKSUM.test(row.target_checksum || "") || row.target_checksum !== snapshot.content_checksum) {
    return "target_checksum";
  }
  if (!purposeOk(row.purpose)) return "purpose";
  const expires = parseDate(row.expires_at);
  if (expires === null || expires <= now || expires > now + MAX_DAYS * DAY_MS) return "expires_at";
  if (row.password_policy_ref !== "" && !VERIFIER.test(row.password_policy_ref || "")) return "password_policy_ref";
  if (row.view_policy !== VIEW_POLICY) return "view_policy";
  if (row.capability_version !== 1) return "capability_version";
  if (row.status !== "active") return "status";
  if (row.revoked_at !== "" || row.revoked_reason !== "") return "revoked";
  if (row.projection_version !== PROJECTION_VERSION) return "projection_version";
  if (!DIGEST.test(row.bearer_digest || "")) return "bearer_digest";
  if (!isInt(row.digest_key_version) || row.digest_key_version < 1 || row.digest_key_version > 999) {
    return "digest_key_version";
  }
  return null;
}

// The first reason an update may not be stored, or null. A revoked row
// never changes again. Otherwise only these move: the version up; the
// digest, only with a version raise (#12's rotate); the expiry earlier; and
// active to revoked, with a version raise, a reason, and a time.
// TODO(ROUNDS-15-L04): #80's retarget to an Artifact Revision is the one
// other change.
function screenUpdate(before, after) {
  for (let i = 0; i < FIXED.length; i += 1) {
    if (before[FIXED[i]] !== after[FIXED[i]]) return FIXED[i];
  }
  if (before.status === "revoked") {
    for (let i = 0; i < MUTABLE.length; i += 1) {
      if (before[MUTABLE[i]] !== after[MUTABLE[i]]) return "revoked";
    }
    return null;
  }
  if (!isInt(after.capability_version) || after.capability_version < before.capability_version) {
    return "capability_version";
  }
  const raised = after.capability_version > before.capability_version;
  if (after.bearer_digest !== before.bearer_digest && (!raised || !DIGEST.test(after.bearer_digest || ""))) {
    return "bearer_digest";
  }
  const was = parseDate(before.expires_at);
  const is = parseDate(after.expires_at);
  if (is === null || was === null || is > was) return "expires_at";
  if (after.status === "active") {
    if (after.revoked_at !== "" || after.revoked_reason !== "") return "revoked";
    return null;
  }
  if (after.status !== "revoked") return "status";
  if (!raised) return "capability_version";
  if (REASONS.indexOf(after.revoked_reason) < 0 || parseDate(after.revoked_at) === null) return "revoked";
  return null;
}

// ---------------------------------------------------------------------------
// The owner's routes
// ---------------------------------------------------------------------------

// deps.store.ownRows(user, limit): the account's rows, newest first.
function listOwn(deps, caller) {
  if (!isId(caller)) return { status: 200, body: { v: VERSION, items: [] } };
  return { status: 200, body: { v: VERSION, items: deps.store.ownRows(caller, LIST_LIMIT).map(ownerView) } };
}

// deps:
//   transaction   (fn) => runs fn(txStore) in one transaction
//   now           milliseconds since the epoch
// txStore: byId(id), update(id, fields)
//
// Another account's id, a missing one, and a malformed one get the same
// 404. Revoking a revoked capability answers as the first revoke did and
// writes nothing.
function revoke(deps, caller, id) {
  if (!isId(caller) || !isId(id)) return NOT_FOUND;
  let out = NOT_FOUND;
  deps.transaction((tx) => {
    const row = tx.byId(id);
    if (row === null || row.user !== caller) return;
    if (row.status === "revoked") {
      out = { status: 200, body: { v: VERSION, capability: ownerView(row), changed: false } };
      return;
    }
    const fields = revokedFields(row, "owner", deps.now);
    tx.update(row.id, fields);
    out = { status: 200, body: { v: VERSION, capability: ownerView(Object.assign({}, row, fields)), changed: true } };
  });
  return out;
}

// ---------------------------------------------------------------------------
// Deletes
// ---------------------------------------------------------------------------

// A resume or variant was deleted: revoke the active capabilities over its
// owner's snapshots of it (source_deleted). Only the owner's snapshots are
// read, through the store's index that starts with the account. The
// snapshots stay, so a revoked capability keeps pointing at what it granted
// until the account goes (#76 purges later). The snapshots name their
// source as plain text, so the delete itself never reaches them.
// txStore: snapshotsOf(user, kind, id) -> snapshot ids, activeOn(snapshotId) -> rows, update(id, fields)
function revokeForSource(deps, kind, id, owner) {
  if (SOURCE_KINDS.indexOf(kind) < 0 || !isId(id) || !isId(owner)) return { revoked: 0 };
  let revoked = 0;
  deps.transaction((tx) => {
    tx.snapshotsOf(owner, kind, id).forEach((snapshotId) => {
      tx.activeOn(snapshotId).forEach((row) => {
        tx.update(row.id, revokedFields(row, "source_deleted", deps.now));
        revoked += 1;
      });
    });
  });
  return { revoked };
}

// An account is being deleted: delete its capabilities first, in the same
// transaction, so the account's cascade into its snapshots never meets a
// capability that still names one. It's the only runtime code that
// hard-deletes a capability; an admin UI delete is an operator action.
// store: ofAccount(user, limit) -> rows, remove(id)
function deleteForAccount(deps, user) {
  if (!isId(user)) return { deleted: 0 };
  let deleted = 0;
  for (;;) {
    const rows = deps.store.ofAccount(user, BATCH);
    rows.forEach((row) => deps.store.remove(row.id));
    deleted += rows.length;
    if (rows.length < BATCH) break;
  }
  return { deleted };
}

// ---------------------------------------------------------------------------
// PocketBase
// ---------------------------------------------------------------------------

function rowOf(record) {
  return {
    id: record.id,
    user: record.getString("user"),
    target_kind: record.getString("target_kind"),
    snapshot: record.getString("snapshot"),
    target_checksum: record.getString("target_checksum"),
    purpose: record.getString("purpose"),
    expires_at: record.getString("expires_at"),
    password_policy_ref: record.getString("password_policy_ref"),
    view_policy: record.getString("view_policy"),
    capability_version: record.getInt("capability_version"),
    status: record.getString("status"),
    revoked_at: record.getString("revoked_at"),
    revoked_reason: record.getString("revoked_reason"),
    projection_version: record.getInt("projection_version"),
    bearer_digest: record.getString("bearer_digest"),
    digest_key_version: record.getInt("digest_key_version"),
    created: record.getString("created"),
  };
}

function snapshotOf(record) {
  return {
    id: record.id,
    user: record.getString("user"),
    source_kind: record.getString("source_kind"),
    source_id: record.getString("source_id"),
    content_checksum: record.getString("content_checksum"),
    markup: record.getString("markup"),
    // The markup file's key in PocketBase's file storage.
    key: record.baseFilesPath() + "/" + record.getString("markup"),
  };
}

function pbStore(dao) {
  function byId(collection, id) {
    try {
      return dao.findRecordById(collection, id);
    } catch (err) {
      return null;
    }
  }
  function rows(collection, filter, sort, limit, params) {
    return dao.findRecordsByFilter(collection, filter, sort, limit, 0, params);
  }
  function withFiles(fn) {
    const fs = $app.newFilesystem();
    try {
      return fn(fs);
    } finally {
      fs.close();
    }
  }
  // Writes go through PocketBase's own form, so its schema rules hold as
  // well as the model hooks.
  function save(record, data) {
    const form = new RecordUpsertForm($app, record);
    form.setDao(dao);
    form.loadData(data);
    form.submit();
    return record;
  }
  return {
    snapshot: (id) => {
      const record = byId(SNAPSHOTS, id);
      return record === null ? null : snapshotOf(record);
    },
    source: (kind, id) => {
      const record = byId(kind === "resume" ? "resumes" : "resume_variants", id);
      return record === null ? null : { id: record.id, user: record.getString("user"), name: record.getString("name") };
    },
    isDemo: (user) => {
      const record = byId("users", user);
      return record !== null && require(`${__hooks}/admission.js`).tierOf(record) === "demo";
    },
    hasMarkup: (snapshot) => snapshot.markup !== "" && withFiles((fs) => fs.exists(snapshot.key)),
    markup: (snapshot) => {
      if (snapshot.markup === "") return null;
      return withFiles((fs) => {
        const reader = fs.getFile(snapshot.key);
        try {
          return readerToString(reader, MAX_MARKUP_BYTES + 1);
        } finally {
          reader.close();
        }
      });
    },
    byDigest: (digest) => {
      const found = rows(COLLECTION, "bearer_digest = {:digest}", "", 1, { digest });
      return found.length > 0 ? rowOf(found[0]) : null;
    },
    byId: (id) => {
      const record = byId(COLLECTION, id);
      return record === null ? null : rowOf(record);
    },
    ownRows: (user, limit) => rows(COLLECTION, "user = {:user}", "-created,-id", limit, { user }).map(rowOf),
    ofAccount: (user, limit) => rows(COLLECTION, "user = {:user}", "", limit, { user }).map(rowOf),
    snapshotsOf: (user, kind, id) =>
      rows(SNAPSHOTS, "user = {:user} && source_kind = {:kind} && source_id = {:id}", "", 0, { user, kind, id })
        .map((r) => r.id),
    activeOn: (snapshotId) =>
      rows(COLLECTION, "snapshot = {:snapshot} && status = 'active'", "", 0, { snapshot: snapshotId }).map(rowOf),
    insert: (fields) => {
      const record = save(new Record(dao.findCollectionByNameOrId(COLLECTION)), fields);
      return { id: record.id, created: record.getString("created") };
    },
    update: (id, fields) => {
      save(dao.findRecordById(COLLECTION, id), fields);
    },
    remove: (id) => {
      dao.deleteRecord(dao.findRecordById(COLLECTION, id));
    },
  };
}

function emit(fields, error) {
  const line = JSON.stringify(Object.assign({ v: "obs/v1", event: "share_capability", service: "pocketbase" }, fields));
  if (error) console.error(line);
  else console.log(line);
}

// create_capability(txDao, owner, snapshot_id, purpose, expires_at,
// password_policy_ref, bearer_digest, digest_key_version), for #12's create
// and #14's re-issue, inside their transaction. Pass "" or null for the
// purpose, expiry, and verifier to take the defaults.
function create_capability(txDao, owner, snapshot_id, purpose, expires_at, password_policy_ref, bearer_digest,
  digest_key_version) {
  return create(
    { store: pbStore(txDao), now: Date.now(), log: emit },
    { owner, snapshot_id, purpose, expires_at, password_policy_ref, bearer_digest, digest_key_version },
  );
}

// lookup_capability(digest), for #12's lookup route: LOOKUP_FIELDS, or null.
function lookup_capability(digest) {
  return lookup(
    { store: pbStore($app.dao()), now: Date.now(), sha256: (text) => $security.sha256(text) },
    digest,
  ).capability;
}

function handleList(c) {
  const record = $apis.requestInfo(c).authRecord;
  if (!record) throw new UnauthorizedError("Sign in to continue.");
  const out = listOwn({ store: pbStore($app.dao()) }, record.id);
  return c.json(out.status, out.body);
}

function handleRevoke(c) {
  const info = $apis.requestInfo(c);
  const record = info.authRecord;
  if (!record) throw new UnauthorizedError("Sign in to continue.");
  // Revoke takes no body; anything in one is refused before any lookup.
  if (isObject(info.data) && Object.keys(info.data).length > 0) {
    return c.json(400, { v: VERSION, error: "invalid_request" });
  }
  const out = revoke(
    { transaction: (fn) => $app.dao().runInTransaction((txDao) => fn(pbStore(txDao))), now: Date.now() },
    record.id,
    c.pathParam("id"),
  );
  if (out.status === 200) emit({ outcome: out.body.changed ? "revoked" : "unchanged", reason: "owner" });
  return c.json(out.status, out.body);
}

function refuse(on, field) {
  emit({ outcome: "refused", on, field });
  throw new Error("share capability refused: " + field);
}

// onModelBeforeCreate on share_capabilities.
function guardCreate(e) {
  const row = rowOf(e.model);
  let snapshot = null;
  if (isId(row.snapshot)) {
    try {
      snapshot = snapshotOf(e.dao.findRecordById(SNAPSHOTS, row.snapshot));
    } catch (err) {
      snapshot = null;
    }
  }
  const reason = screenCreate(row, snapshot, Date.now());
  if (reason !== null) refuse("create", reason);
}

// onModelBeforeUpdate on share_capabilities.
function guardUpdate(e) {
  const reason = screenUpdate(rowOf(e.model.originalCopy()), rowOf(e.model));
  if (reason !== null) refuse("update", reason);
}

// onModelAfterDelete on resumes and resume_variants. PocketBase 0.22 runs it
// after the delete commits, so a failure here can't undo the delete, and is
// caught, never thrown, so it can't turn a finished delete into an error
// either. lookup refuses a capability whose source is gone in any case.
function onSourceDeleted(e, kind) {
  try {
    const dao = e.dao || $app.dao();
    const out = revokeForSource(
      { transaction: (fn) => dao.runInTransaction((txDao) => fn(pbStore(txDao))), now: Date.now() },
      kind,
      e.model.id,
      e.model.getString("user"),
    );
    if (out.revoked > 0) emit({ outcome: "revoked", reason: "source_deleted", count: out.revoked });
  } catch (err) {
    emit({ outcome: "revoke_failed", reason: "source_deleted" }, true);
  }
}

// onModelBeforeDelete on users: inside the delete's transaction (e.dao), so
// a failure here fails the account delete and nothing is half done.
function onAccountDelete(e) {
  const out = deleteForAccount({ store: pbStore(e.dao) }, e.model.id);
  if (out.deleted > 0) emit({ outcome: "deleted", reason: "account_deleted", count: out.deleted });
}

module.exports = {
  VERSION,
  KIND,
  PROJECTION_VERSION,
  VIEW_POLICY,
  DEFAULT_DAYS,
  MAX_DAYS,
  MIN_LIFETIME_MS,
  PURPOSE_MAX,
  PURPOSE_FALLBACK,
  LIST_LIMIT,
  OWNER_FIELDS,
  LOOKUP_FIELDS,
  FIXED,
  MUTABLE,
  parseDate,
  formatDate,
  defaultPurpose,
  checkCreate,
  create,
  lookup,
  screenCreate,
  screenUpdate,
  listOwn,
  revoke,
  revokeForSource,
  deleteForAccount,
  ownerView,
  rowOf,
  pbStore,
  create_capability,
  lookup_capability,
  handleList,
  handleRevoke,
  guardCreate,
  guardUpdate,
  onSourceDeleted,
  onAccountDelete,
};
