// Runs pb_hooks/share_secrets.js under node for test_share_secrets_hooks.py
// (ROUNDS-00B-L04), on an in-memory throttle store and a fake PocketBase.
//
//   node share_secrets_runner.cjs <hooks dir> < program.json
//
// A program is {"steps": [...]}; each step names a call and its
// arguments, and the output is {"results": [...], "counters": [...]}.

const fs = require("fs");
const path = require("path");

const [hooksDir] = process.argv.slice(2);
const program = JSON.parse(fs.readFileSync(0, "utf8"));

class BadRequestError extends Error {}
class ForbiddenError extends Error {}
class NotFoundError extends Error {}
globalThis.BadRequestError = BadRequestError;
globalThis.ForbiddenError = ForbiddenError;
globalThis.NotFoundError = NotFoundError;
globalThis.$apis = { requestInfo: (ctx) => ctx.info };
globalThis.__hooks = hooksDir;

const secrets = require(path.join(hooksDir, "share_secrets.js"));

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
    default:
      throw new Error(`unknown call ${step.call}`);
  }
});

process.stdout.write(JSON.stringify({ results, counters: store.dump() }));
