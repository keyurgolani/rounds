// Runs pb_hooks/share_capabilities.js under node for
// test_share_capability_hooks.py (ROUNDS-00B-L03 stage 2).
//
// The decisions run on an in-memory store with the PocketBase store's
// contract (pbStore in share_capabilities.js): users, resumes, variants,
// snapshots with their markup text, and capabilities unique by
// bearer_digest. A transaction runs on a copy and keeps it only when it
// returns, so a throw leaves the store as it was. The PocketBase store
// itself runs natively and in the harness.
//
//   node share_capabilities_runner.cjs <hooks dir> < program.json
//
// A program is {"state": {...}, "now": <ms>, "steps": [...]}. Each step is
// one call with its arguments; the output is {"results": [...], "state":
// {...}, "logs": [...]}, and each result carries the store calls it made.

const crypto = require("crypto");
const fs = require("fs");
const path = require("path");

const [hooksDir] = process.argv.slice(2);
const program = JSON.parse(fs.readFileSync(0, "utf8"));

globalThis.__hooks = hooksDir;
globalThis.UnauthorizedError = class UnauthorizedError extends Error {};
const logs = [];
console.log = (line) => logs.push({ level: "info", line: JSON.parse(line) });
console.error = (line) => logs.push({ level: "error", line: JSON.parse(line) });

const caps = require(path.join(hooksDir, "share_capabilities.js"));

const sha256 = (text) => crypto.createHash("sha256").update(text, "utf8").digest("hex");
const clone = (value) => JSON.parse(JSON.stringify(value));
const now = program.now;

function emptyState() {
  return { users: {}, resumes: {}, variants: {}, snapshots: {}, capabilities: {} };
}

let ids = 0;

function storeOver(state, calls, options) {
  const opts = options || {};
  const call = (name) => calls.push(name);
  const view = (id) => {
    const s = state.snapshots[id];
    return s
      ? { id, user: s.user, source_kind: s.source_kind, source_id: s.source_id, content_checksum: s.content_checksum,
          markup: typeof s.markup === "string" ? s.markup : "snapshot_x.html", key: "snapshots/" + id }
      : null;
  };
  const rows = () => Object.keys(state.capabilities).map((id) => clone(state.capabilities[id]));
  return {
    snapshot: (id) => {
      call("snapshot");
      return view(id);
    },
    source: (kind, id) => {
      call("source");
      const row = (kind === "resume" ? state.resumes : state.variants)[id];
      return row ? { id, user: row.user, name: row.name } : null;
    },
    isDemo: (user) => {
      call("isDemo");
      return Boolean(state.users[user] && state.users[user].is_demo);
    },
    hasMarkup: (snapshot) => {
      call("hasMarkup");
      return typeof state.snapshots[snapshot.id].markup_text === "string";
    },
    markup: (snapshot) => {
      call("markup");
      if (opts.failMarkup) throw new Error("storage unavailable");
      const text = state.snapshots[snapshot.id].markup_text;
      return typeof text === "string" ? text : null;
    },
    byDigest: (digest) => {
      call("byDigest");
      if (opts.failStore) throw new Error("database unavailable");
      return rows().find((row) => row.bearer_digest === digest) || null;
    },
    byId: (id) => {
      call("byId");
      return state.capabilities[id] ? clone(state.capabilities[id]) : null;
    },
    ownRows: (user, limit) => {
      call("ownRows");
      return rows()
        .filter((row) => row.user === user)
        .sort((a, b) => (a.created < b.created ? 1 : a.created > b.created ? -1 : a.id < b.id ? 1 : -1))
        .slice(0, limit);
    },
    ofAccount: (user, limit) => {
      call("ofAccount");
      if (opts.failStore) throw new Error("database unavailable");
      return rows().filter((row) => row.user === user).slice(0, limit);
    },
    snapshotsOf: (user, kind, id) => {
      call("snapshotsOf");
      return Object.keys(state.snapshots).filter(
        (sid) => state.snapshots[sid].user === user && state.snapshots[sid].source_kind === kind &&
          state.snapshots[sid].source_id === id,
      );
    },
    activeOn: (snapshotId) => {
      call("activeOn");
      return rows().filter((row) => row.snapshot === snapshotId && row.status === "active");
    },
    insert: (fields) => {
      call("insert");
      if (rows().some((row) => row.bearer_digest === fields.bearer_digest)) {
        throw new Error("UNIQUE constraint failed: share_capabilities.bearer_digest");
      }
      ids += 1;
      const id = "capnew" + String(ids).padStart(9, "0");
      const created = caps.formatDate(now);
      state.capabilities[id] = Object.assign({ id, created }, clone(fields));
      return { id, created };
    },
    update: (id, fields) => {
      call("update");
      if (opts.failUpdate) throw new Error("database busy");
      Object.assign(state.capabilities[id], clone(fields));
    },
    remove: (id) => {
      call("remove");
      delete state.capabilities[id];
    },
  };
}

// fn(txStore) runs on a copy that's kept only when fn returns.
function transactionOver(holder, calls, options) {
  return (fn) => {
    const copy = clone(holder.state);
    const out = fn(storeOver(copy, calls, options));
    holder.state = copy;
    return out;
  };
}

// A PocketBase record as the model hooks read it.
function record(fields, original) {
  const data = Object.assign({}, fields || {});
  return {
    id: data.id || "",
    getString: (name) => (typeof data[name] === "string" ? data[name] : ""),
    getInt: (name) => (typeof data[name] === "number" ? Math.trunc(data[name]) : 0),
    baseFilesPath: () => "snapshots/" + (data.id || ""),
    originalCopy: () => record(original || {}),
  };
}

function attempt(fn) {
  try {
    return { value: fn() };
  } catch (err) {
    return { threw: String(err && err.message ? err.message : err) };
  }
}

const holder = { state: Object.assign(emptyState(), clone(program.state || {})) };
const results = [];

for (const step of program.steps) {
  const calls = [];
  const options = step.options || {};
  const read = () => storeOver(holder.state, calls, options);
  const transaction = transactionOver(holder, calls, options);
  let out;
  switch (step.call) {
    case "constants":
      out = { value: {
        VERSION: caps.VERSION, KIND: caps.KIND, PROJECTION_VERSION: caps.PROJECTION_VERSION,
        VIEW_POLICY: caps.VIEW_POLICY, DEFAULT_DAYS: caps.DEFAULT_DAYS, MAX_DAYS: caps.MAX_DAYS,
        MIN_LIFETIME_MS: caps.MIN_LIFETIME_MS, PURPOSE_MAX: caps.PURPOSE_MAX, PURPOSE_FALLBACK: caps.PURPOSE_FALLBACK,
        LIST_LIMIT: caps.LIST_LIMIT, OWNER_FIELDS: caps.OWNER_FIELDS, LOOKUP_FIELDS: caps.LOOKUP_FIELDS,
        FIXED: caps.FIXED, MUTABLE: caps.MUTABLE,
      } };
      break;
    case "parseDate":
      out = { value: caps.parseDate(step.value) };
      break;
    case "formatDate":
      out = { value: caps.formatDate(step.ms) };
      break;
    case "defaultPurpose":
      out = { value: caps.defaultPurpose(step.name) };
      break;
    case "create":
      // As #12's create and #14's re-issue call it: inside their transaction.
      out = attempt(() => transaction((tx) => caps.create({ store: tx, now: step.now || now, log: (f) => logs.push({ level: "info", line: f }) }, step.input)));
      break;
    case "lookup":
      out = attempt(() => caps.lookup({ store: read(), now: step.now || now, sha256 }, step.digest));
      break;
    case "screenCreate":
      out = { value: caps.screenCreate(step.row, step.snapshot === undefined ? null : step.snapshot, step.now || now) };
      break;
    case "screenUpdate":
      out = { value: caps.screenUpdate(step.before, step.after) };
      break;
    case "list":
      out = { value: caps.listOwn({ store: read() }, step.caller) };
      break;
    case "revoke":
      out = attempt(() => caps.revoke({ transaction, now: step.now || now }, step.caller, step.id));
      break;
    case "revokeForSource":
      out = attempt(() => caps.revokeForSource({ transaction, now: step.now || now }, step.kind, step.id, step.owner));
      break;
    case "deleteForAccount":
      out = attempt(() => transaction((tx) => caps.deleteForAccount({ store: tx }, step.user)));
      break;
    case "guardCreate": {
      const snapshot = step.snapshot ? record(step.snapshot) : null;
      const dao = {
        findRecordById: (name, id) => {
          if (name !== "legacy_artifact_snapshots" || !snapshot || snapshot.id !== id) throw new Error("sql: no rows in result set");
          return snapshot;
        },
      };
      out = attempt(() => caps.guardCreate({ model: record(step.row), dao }));
      break;
    }
    case "guardUpdate":
      out = attempt(() => caps.guardUpdate({ model: record(step.row, step.original), dao: {} }));
      break;
    case "onSourceDeleted": {
      // A Dao whose transaction fails, as a busy database would.
      const dao = { runInTransaction: () => { throw new Error("database is locked"); } };
      out = attempt(() => caps.onSourceDeleted({ model: record({ id: step.id, user: step.owner }), dao }, step.kind));
      break;
    }
    case "onAccountDelete": {
      const dao = { findRecordsByFilter: () => { throw new Error("database is locked"); } };
      out = attempt(() => caps.onAccountDelete({ model: record({ id: step.id }), dao }));
      break;
    }
    default:
      throw new Error("unknown step " + step.call);
  }
  results.push(Object.assign({ calls }, out));
}

process.stdout.write(JSON.stringify({ results, state: holder.state, logs }));
