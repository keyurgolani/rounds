// Runs pb_hooks/share_secrets.js under node for test_share_secrets_hooks.py
// (ROUNDS-00B-L04), on an in-memory throttle store and a fake PocketBase.
//
//   node share_secrets_runner.cjs <hooks dir> < program.json
//
// A program is {"steps": [...], "world": {...}}; each step names a call and
// its arguments, and the output is {"results": [...], "counters": [...],
// "world": {...}}. The world is the share commands' state: admission
// commands by (account, command_id) through admission.js, capabilities by
// id with #11's rotate (share_capabilities.js), and snapshots by id. A
// command transaction runs on a copy and keeps it only when it returns, as
// runInTransaction does.

const fs = require("fs");
const path = require("path");

const [hooksDir] = process.argv.slice(2);
const program = JSON.parse(fs.readFileSync(0, "utf8"));

class BadRequestError extends Error {}
class ForbiddenError extends Error {}
class NotFoundError extends Error {}
class UnauthorizedError extends Error {}
globalThis.BadRequestError = BadRequestError;
globalThis.ForbiddenError = ForbiddenError;
globalThis.NotFoundError = NotFoundError;
globalThis.UnauthorizedError = UnauthorizedError;
globalThis.$apis = { requestInfo: (ctx) => ctx.info };
globalThis.__hooks = hooksDir;

const secrets = require(path.join(hooksDir, "share_secrets.js"));
const admission = require(path.join(hooksDir, "admission.js"));
const capabilities = require(path.join(hooksDir, "share_capabilities.js"));

const clone = (value) => JSON.parse(JSON.stringify(value));

// ---- the share commands' world -------------------------------------------------------

const world = Object.assign({ commands: [], capabilities: {}, snapshots: {}, legacyLinks: {}, failCreate: false },
  program.world || {});
let commandIds = world.commands.length;
let capabilityIds = Object.keys(world.capabilities).length;

// One transaction's view of `state`, as commandTx gives it over a DAO.
function commandTxOver(state, calls) {
  const commands = {
    findCommand: (account, commandId) =>
      clone(state.commands.find((c) => c.account === account && c.command_id === commandId) || null),
    saveCommand: (row) => {
      const saved = clone(row);
      if (!saved.id) {
        commandIds += 1;
        saved.id = "cmd" + String(commandIds).padStart(12, "0");
        state.commands.push(saved);
      } else {
        // A record keeps the fields another caller set on it.
        Object.assign(state.commands.find((c) => c.id === saved.id), saved);
      }
      return clone(saved);
    },
    deleteCommand: (row) => {
      state.commands = state.commands.filter((c) => c.id !== row.id);
    },
  };
  const byId = (id) => (state.capabilities[id] ? Object.assign({ id }, clone(state.capabilities[id])) : null);
  return {
    commands,
    snapshotOf: (command) => (state.commands.find((c) => c.id === command.id) || {})[secrets.SNAPSHOT_FIELD] || "",
    setSnapshot: (command, key) => {
      calls.push("setSnapshot");
      state.commands.find((c) => c.id === command.id)[secrets.SNAPSHOT_FIELD] = key;
    },
    // #11's create_capability, reduced to what these routes depend on: its
    // answers, and a digest unique across capabilities.
    createCapability: (a) => {
      calls.push("createCapability");
      if (world.failCreate) throw new Error("database is locked");
      const snapshot = state.snapshots[a.snapshot_id];
      if (!snapshot || snapshot.user !== a.owner) return { status: "share-unavailable" };
      if (a.password_policy_ref !== "" && a.password_policy_ref.indexOf("pw1$") !== 0) {
        return { status: "invalid", field: "password_policy_ref" };
      }
      if (Object.keys(state.capabilities).some((id) => state.capabilities[id].bearer_digest === a.bearer_digest)) {
        throw new Error("UNIQUE constraint failed: share_capabilities.bearer_digest");
      }
      capabilityIds += 1;
      const id = "capnew" + String(capabilityIds).padStart(9, "0");
      const row = {
        user: a.owner, snapshot: a.snapshot_id, status: "active", expires_at: a.expires_at || "2027-02-09 12:00:00.000Z",
        capability_version: 1, bearer_digest: a.bearer_digest, digest_key_version: a.digest_key_version,
        password_policy_ref: a.password_policy_ref, purpose: a.purpose || "Shared resume", revoked_reason: "",
        revoked_at: "", created: "2026-11-11 12:00:00.000Z",
      };
      state.capabilities[id] = row;
      return { status: "created", capability: capabilities.ownerView(Object.assign({ id }, row)) };
    },
    snapshotSource: (id) => {
      calls.push("snapshotSource");
      const snapshot = state.snapshots[id];
      return snapshot ? { kind: snapshot.source_kind, id: snapshot.source_id } : null;
    },
    // #11's rotate itself, over the same rows.
    rotateBearer: (a) => {
      calls.push("rotateBearer");
      return capabilities.rotate({
        now: Date.parse("2026-11-11T12:00:00Z"),
        store: {
          byId,
          update: (id, fields) => Object.assign(state.capabilities[id], clone(fields)),
        },
      }, a);
    },
    // Older links (ROUNDS-00B-L06), as commandTx reads and marks them.
    legacyLink: (id) => {
      calls.push("legacyLink");
      const link = state.legacyLinks[id];
      if (!link) return null;
      return { id, user: link.user, status: link.legacy_status, replaced_by: link.replaced_by, resume: link.resume,
        variant: link.variant };
    },
    capabilityResult: (id) => {
      calls.push("capabilityResult");
      const capability = state.capabilities[id];
      const snapshot = capability ? state.snapshots[capability.snapshot] : null;
      if (!capability || !snapshot) return null;
      const scope = { target_kind: "legacy_artifact_snapshot" };
      scope[snapshot.source_kind === "resume" ? "resume_id" : "variant_id"] = snapshot.source_id;
      scope.projection_version = 1;
      return {
        user: capability.user,
        result: {
          status: 201,
          body: {
            capability_id: id,
            scope,
            state: capability.status,
            expires_at: capability.expires_at,
            capability_version: capability.capability_version,
          },
        },
      };
    },
    replaceLegacy: (id, capabilityId) => {
      calls.push("replaceLegacy");
      state.legacyLinks[id].replaced_by = capabilityId;
    },
  };
}

function commandDeps(step, calls) {
  return {
    admission,
    now: step.now || 1_800_000_000,
    transaction: (fn) => {
      const copy = clone({ commands: world.commands, capabilities: world.capabilities, snapshots: world.snapshots,
        legacyLinks: world.legacyLinks });
      const out = fn(commandTxOver(copy, calls));
      world.commands = copy.commands;
      world.capabilities = copy.capabilities;
      world.snapshots = copy.snapshots;
      world.legacyLinks = copy.legacyLinks;
      return out;
    },
  };
}

function attempt(fn) {
  try {
    return { value: fn() };
  } catch (err) {
    return { threw: String(err && err.message ? err.message : err) };
  }
}

// A route handler's context: who called, its body and headers, its path
// parameters, and c.json.
function routeContext(step) {
  const who = step.principal || null;
  const authRecord = who === null ? null : {
    id: who.id || "acct00000000001",
    collection: () => ({ name: who.collection }),
    username: () => who.username || "",
  };
  return {
    info: { authRecord, data: step.data, headers: step.headers || {} },
    pathParam: (name) => (step.params || {})[name] || "",
    json: (status, body) => ({ status, body }),
  };
}

function handle(step) {
  globalThis.$os = { getenv: (key) => (key === "ROUNDS_ADMISSION_SECRET" ? step.runnerKey || "" : "") };
  const c = routeContext(step);
  try {
    return { answer: secrets[step.handler](c) };
  } catch (err) {
    return { threw: err.constructor.name, message: err.message };
  }
}

// The throttle store's contract, in memory: one row per key.
function memoryThrottle() {
  const rows = new Map();
  const copy = (row) => ({ key: row.key, scope: row.scope, window_start: row.window_start, count: row.count });
  return {
    counter: (key) => (rows.has(key) ? copy(rows.get(key)) : null),
    save: (row) => rows.set(row.key, copy(row)),
    deleteBefore: (cutoff, limit) => {
      const old = [...rows.values()].filter((r) => r.window_start < cutoff).sort((a, b) => a.window_start - b.window_start);
      old.slice(0, limit).forEach((r) => rows.delete(r.key));
      return Math.min(old.length, limit);
    },
    seed: (row) => rows.set(row.key, copy(row)),
    dump: () => [...rows.values()].map(copy).sort((a, b) => (a.key < b.key ? -1 : 1)),
  };
}

// A DAO over share_throttle with the two filters pbStore uses, so the
// store's glue runs too. A real PocketBase runs it in the harness.
function fakeThrottleDao() {
  const records = [];
  let ids = 0;
  class FakeRecord {
    constructor() {
      this.id = "";
      this.fields = {};
    }
    set(name, value) {
      this.fields[name] = value;
    }
    getString(name) {
      return typeof this.fields[name] === "string" ? this.fields[name] : "";
    }
    getInt(name) {
      return typeof this.fields[name] === "number" ? this.fields[name] : 0;
    }
  }
  globalThis.Record = FakeRecord;
  const dao = {
    calls: [],
    findCollectionByNameOrId: (name) => {
      if (name !== "share_throttle") throw new Error("missing collection " + name);
      return { name };
    },
    findRecordsByFilter: (collection, filter, sort, limit, offset, params) => {
      dao.calls.push({ collection, filter, sort, limit });
      let rows = records.slice();
      if (filter === "key = {:key}") rows = rows.filter((r) => r.fields.key === params.key);
      else if (filter === "window_start < {:cutoff}") rows = rows.filter((r) => r.fields.window_start < params.cutoff);
      else throw new Error("unexpected filter " + filter);
      if (sort === "window_start") rows.sort((a, b) => a.fields.window_start - b.fields.window_start);
      return limit > 0 ? rows.slice(0, limit) : rows;
    },
    saveRecord: (record) => {
      if (!record.id) {
        if (records.some((r) => r.fields.key === record.fields.key)) {
          throw new Error("UNIQUE constraint failed: share_throttle.key");
        }
        record.id = "thr" + String(++ids).padStart(12, "0");
        records.push(record);
      }
    },
    deleteRecord: (record) => {
      const i = records.indexOf(record);
      if (i >= 0) records.splice(i, 1);
    },
    rows: () => records.map((r) => Object.assign({}, r.fields)).sort((a, b) => (a.key < b.key ? -1 : 1)),
  };
  return dao;
}

// The share_resolvers collection as ensureResolver sees it.
function memoryAccounts(initial) {
  const records = initial ? [Object.assign({}, initial)] : [];
  return {
    records,
    find: (username) => records.find((r) => r.username === username) || null,
    create: (username, secret) => records.push({ username, password: secret }),
    validatePassword: (record, secret) => record.password === secret,
    setPassword: (record, secret) => {
      record.password = secret;
    },
  };
}

// $app and $os as bootstrapResolver and syncResolverForLogin use them, over
// one share_resolvers collection that may not exist yet.
function fakeApp(step) {
  const records = step.existing ? [Object.assign({}, step.existing)] : [];
  const logs = [];
  class FakeRecord {
    constructor() {
      this.fields = {};
    }
    set(name, value) {
      this.fields[name] = value;
    }
    setPassword(secret) {
      this.fields.password = secret;
    }
  }
  const view = (r) => (r ? { username: r.username, password: r.password } : null);
  const dao = {
    findCollectionByNameOrId: (name) => {
      if (name !== "share_resolvers" || step.collection === false) throw new Error("missing collection " + name);
      return { name };
    },
    findAuthRecordByUsername: (collection, username) => {
      if (collection !== "share_resolvers" || step.collection === false) throw new Error("missing collection");
      const found = records.find((r) => r.username === username);
      if (!found) throw new Error("sql: no rows in result set");
      return {
        _row: found,
        validatePassword: (secret) => found.password === secret,
        setPassword: (secret) => {
          found.password = secret;
        },
      };
    },
    saveRecord: (record) => {
      if (record instanceof FakeRecord) records.push({ username: record.fields.username, password: record.fields.password });
    },
  };
  globalThis.$app = { dao: () => dao };
  globalThis.$os = { getenv: (key) => (key === "ROUNDS_SHARE_RESOLVER_PASSWORD" ? step.secret : "") };
  globalThis.$security = { randomString: (n) => "r".repeat(n) };
  globalThis.Record = FakeRecord;
  const log = console.log;
  const error = console.error;
  console.log = (...a) => logs.push(a.join(" "));
  console.error = (...a) => logs.push(a.join(" "));
  return {
    records,
    view,
    done: () => {
      console.log = log;
      console.error = error;
      return logs;
    },
  };
}

// guardResolverRequest on a fake request: who made it, its method, and the
// route pattern it matched.
function guard(step) {
  const who = step.principal || null;
  const authRecord = who === null ? null : {
    id: who.id || "res000000000001",
    collection: () => ({ name: who.collection }),
    username: () => who.username || "",
  };
  const c = {
    info: { authRecord, admin: null },
    request: () => ({ method: step.method }),
    path: () => step.path,
  };
  const logs = [];
  const log = console.log;
  console.log = (...a) => logs.push(a.join(" "));
  try {
    secrets.guardResolverRequest(c);
    return { allowed: true, logs };
  } catch (err) {
    return { allowed: false, forbidden: err instanceof ForbiddenError, message: err.message, logs };
  } finally {
    console.log = log;
  }
}

const store = memoryThrottle();
const results = program.steps.map((step) => {
  switch (step.call) {
    case "constants":
      return {
        limits: secrets.LIMITS,
        order: secrets.ORDER,
        routes: secrets.RESOLVER_ROUTES,
        prune: [secrets.PRUNE_LIMIT, secrets.PRUNE_AGE_S],
        secret: [secrets.SECRET_ENV, secrets.SECRET_MIN_CHARS, secrets.SECRET_MAX_CHARS],
        names: [secrets.COLLECTION, secrets.RESOLVER_USERNAME, secrets.THROTTLE],
      };
    case "checkThrottle":
      return secrets.checkThrottle(step.input);
    case "seedCounter":
      store.seed(step.row);
      return null;
    case "throttle":
      return secrets.throttle(store, step.entries, step.now);
    case "prune":
      return secrets.prune(store, step.now);
    case "pbStore": {
      // A run of throttles and a prune through pbStore over a fake DAO.
      const dao = fakeThrottleDao();
      const pb = secrets.pbStore(dao);
      const out = step.runs.map((run) => secrets.throttle(pb, run.entries, run.now));
      const pruned = step.pruneAt === undefined ? null : secrets.prune(pb, step.pruneAt);
      return { out, pruned, rows: dao.rows(), calls: dao.calls };
    }
    case "ensureResolver": {
      const accounts = memoryAccounts(step.existing);
      const did = secrets.ensureResolver(accounts, step.secret, () => "r".repeat(64));
      return { did, records: accounts.records };
    }
    case "resolverMayCall":
      return secrets.resolverMayCall(step.method, step.path);
    case "guardResolverRequest":
      return guard(step);
    case "bootstrapResolver": {
      const app = fakeApp(step);
      const did = secrets.bootstrapResolver();
      const logs = app.done();
      return { did, records: app.records.map(app.view), logs };
    }
    case "syncResolverForLogin": {
      const app = fakeApp(step);
      const segment = step.segment === undefined ? "share_resolvers" : step.segment;
      const httpContext = segment === null ? null : { pathParam: (name) => (name === "collection" ? segment : "") };
      const e = { identity: step.identity, record: null, httpContext };
      try {
        secrets.syncResolverForLogin(e);
      } catch (err) {
        app.done();
        if (!(err instanceof NotFoundError)) throw err;
        return { not_found: true, records: app.records.map(app.view) };
      }
      const lines = app.done().filter((line) => line.startsWith("{")).map((line) => JSON.parse(line));
      let did = null;
      if (step.identity === secrets.RESOLVER_USERNAME) did = lines.length ? lines[0].resolver : "unchanged";
      return { did, record: e.record ? app.view(e.record._row) : null, records: app.records.map(app.view) };
    }
    case "checkLookup":
      return secrets.checkLookup(step.input);
    case "checkBegin":
      return secrets.checkBegin(step.input, admission.COMMAND_ID);
    case "checkCreate":
      return secrets.checkCreate(step.input, admission.COMMAND_ID);
    case "checkRotate":
      return secrets.checkRotate(step.input, admission.COMMAND_ID);
    case "lookup": {
      // The lookup route's decision over the in-memory throttle.
      const asked = [];
      const out = secrets.lookup({
        transaction: (fn) => fn(store),
        now: step.now,
        lookup: (digest) => {
          asked.push(digest);
          return (step.capabilities || {})[digest] || null;
        },
      }, step.input);
      return { out, asked };
    }
    case "begin":
    case "createShare":
    case "rotateShare": {
      const calls = [];
      const deps = commandDeps(step, calls);
      const account = { id: step.account || "acct00000000001" };
      const out = attempt(() => (step.call === "rotateShare"
        ? secrets.rotateShare(deps, account, step.id, step.input)
        : secrets[step.call](deps, account, step.input)));
      return Object.assign({ calls }, out);
    }
    case "handle":
      return handle(step);
    default:
      throw new Error(`unknown call ${step.call}`);
  }
});

process.stdout.write(JSON.stringify({ results, counters: store.dump(), world }));
