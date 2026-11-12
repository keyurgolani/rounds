/// <reference path="../pb_data/types.d.ts" />

// Route handlers for the database benchmark (ROUNDS-02-L01). Bench only.
// The logic is in bench_lib.js; this file is the PocketBase side: auth,
// the per-run bench key, one transaction per write, and the timestamps the
// lock measures come from (route entry, transaction start, commit).
//
// Commands and background writes run as the signed-in account. Seeding, the
// relay, the freeze, the transfer, and the storage probes need the per-run
// BENCH_KEY, which only bench.py holds; without it they answer 503.

const lib = require(`${__hooks}/bench_lib.js`);

const KEY_HEADER = "x_bench_key";
const MIN_KEY = 32;

function same(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function keyRefusal(info) {
  const secret = $os.getenv("BENCH_KEY");
  if (typeof secret !== "string" || secret.length < MIN_KEY) return { status: 503, body: { error: "unconfigured" } };
  const given = info.headers ? info.headers[KEY_HEADER] : undefined;
  if (typeof given !== "string" || !same(given, secret)) return { status: 403, body: { error: "forbidden" } };
  return null;
}

function sha256(text) {
  return $security.sha256(text);
}

// Runs fn(store) in one transaction. A Refusal or a failpoint is recorded
// inside the callback and then rolls the transaction back.
function inTransaction(fn) {
  const t = { enter: Date.now(), start: 0, end: 0, commit: 0 };
  let out = null;
  let refusal = null;
  let failpoint = null;
  try {
    $app.dao().runInTransaction((tx) => {
      t.start = Date.now();
      try {
        out = fn(lib.pbStore(tx), t.start);
      } catch (err) {
        if (err && err.refusal) refusal = { status: err.status, body: err.body };
        else if (err && err.failpoint) failpoint = err.failpoint;
        else if (String(err).indexOf("UNIQUE constraint failed") >= 0) refusal = { status: 409, body: { error: "invariant_violation" } };
        else throw err;
        throw new Error("bench rollback");
      }
      t.end = Date.now();
    });
    t.commit = Date.now();
  } catch (err) {
    t.commit = Date.now();
    if (!refusal && !failpoint) throw err;
  }
  const timing = { queue_ms: (t.start || t.commit) - t.enter, hold_ms: t.start ? t.commit - t.start : 0, work_ms: t.end ? t.end - t.start : 0 };
  if (refusal) return { status: refusal.status, body: Object.assign({}, refusal.body, { timing }) };
  if (failpoint) return { status: 503, body: { error: "failpoint", failpoint, timing } };
  return { status: out.status || 200, body: Object.assign({}, out.body || out, { timing }) };
}

function signedIn(c) {
  const info = $apis.requestInfo(c);
  return { info, record: info.authRecord };
}

function command(c) {
  const { info, record } = signedIn(c);
  if (!record) return c.json(401, { error: "unauthorized" });
  if ($app.cache().get("bench_freeze") === true) return c.json(503, { error: "frozen" });
  const body = info.data || {};
  const failpoint = $os.getenv("BENCH_FAILPOINTS") === "1" ? body.failpoint : undefined;
  const out = inTransaction((store, now) =>
    lib.commandIn(store, { account: record.id, actor: "user:" + record.id, now, sha256, failpoint }, body));
  return c.json(out.status, out.body);
}

function background(c) {
  const { info, record } = signedIn(c);
  if (!record) return c.json(401, { error: "unauthorized" });
  const kind = (info.data || {}).kind;
  const out = inTransaction((store, now) => ({ status: 200, body: { writes: lib.backgroundIn(store, kind, record.id, now) } }));
  return c.json(out.status, out.body);
}

function projection(c) {
  const { info, record } = signedIn(c);
  if (!record) return c.json(401, { error: "unauthorized" });
  const data = info.data || {};
  return c.json(200, lib.projectionIn(lib.pbStore($app.dao()), record.id, String(data.aggregate_id || ""), Number(data.min_position || 0)));
}

function keyed(c, fn) {
  const info = $apis.requestInfo(c);
  const refused = keyRefusal(info);
  if (refused) return c.json(refused.status, refused.body);
  const out = fn(info.data || {});
  return c.json(out.status || 200, out.body || out);
}

function seed(c) {
  return keyed(c, (d) => inTransaction((store) => ({ status: 200, body: { rows: lib.seedIn(store, d.table, d.columns, d.rows) } })));
}

function lease(c) {
  return keyed(c, (d) => inTransaction((store, now) => ({ status: 200, body: lib.leaseIn(store, String(d.holder || ""), Number(d.ttl_ms || 0), now) })));
}

function read(c) {
  return keyed(c, (d) => ({ status: 200, body: lib.readIn(lib.pbStore($app.dao()), Math.min(Number(d.limit || 200), 1000)) }));
}

function apply(c) {
  return keyed(c, (d) => inTransaction((store, now) => ({ status: 200, body: lib.applyIn(store, d.events || [], now) })));
}

function ack(c) {
  return keyed(c, (d) => inTransaction((store, now) => ({ status: 200,
    body: lib.ackIn(store, String(d.holder || ""), Number(d.token || 0), Number(d.cursor || 0), now) })));
}

function freeze(c) {
  return keyed(c, (d) => {
    $app.cache().set("bench_freeze", d.on === true);
    return { status: 200, body: { frozen: d.on === true } };
  });
}

function transfer(c) {
  return keyed(c, (d) => inTransaction((store, now) => ({ status: 200,
    body: lib.transferIn(store, { now, sha256 }, String(d.account || ""), String(d.after || ""), Math.min(Number(d.limit || 30), 200)) })));
}

function pragmas(c) {
  return keyed(c, () => {
    const read = (db, sql, key, blank) => {
      const shape = {};
      shape[key] = blank;
      const m = new DynamicModel(shape);
      db.newQuery(sql).one(m);
      return m[key];
    };
    const out = {};
    [["read", $app.dao().db()], ["write", $app.dao().nonconcurrentDB()]].forEach((pair) => {
      const name = pair[0];
      const db = pair[1];
      out[name] = {
        journal_mode: read(db, "PRAGMA journal_mode", "journal_mode", ""),
        synchronous: read(db, "PRAGMA synchronous", "synchronous", 0),
        busy_timeout: read(db, "PRAGMA busy_timeout", "timeout", 0),
        journal_size_limit: read(db, "PRAGMA journal_size_limit", "journal_size_limit", 0),
        cache_size: read(db, "PRAGMA cache_size", "cache_size", 0),
        foreign_keys: read(db, "PRAGMA foreign_keys", "foreign_keys", 0),
        temp_store: read(db, "PRAGMA temp_store", "temp_store", 0),
        wal_autocheckpoint: read(db, "PRAGMA wal_autocheckpoint", "wal_autocheckpoint", 0),
        page_size: read(db, "PRAGMA page_size", "page_size", 0),
      };
    });
    out.sqlite_version = read($app.dao().db(), "SELECT sqlite_version() AS v", "v", "");
    return { status: 200, body: out };
  });
}

function checkpoint(c) {
  return keyed(c, () => {
    const t0 = Date.now();
    const m = new DynamicModel({ busy: 0, log: 0, checkpointed: 0 });
    $app.dao().db().newQuery("PRAGMA wal_checkpoint(TRUNCATE)").one(m);
    return { status: 200, body: { busy: m.busy, log: m.log, checkpointed: m.checkpointed, ms: Date.now() - t0 } };
  });
}

function vacuumInto(c) {
  return keyed(c, (d) => {
    const root = $os.getenv("BENCH_SCRATCH");
    const target = String(d.path || "");
    if (!root || target.indexOf(root + "/") !== 0 || target.indexOf("..") >= 0) return { status: 400, body: { error: "path" } };
    const t0 = Date.now();
    $app.dao().db().newQuery("VACUUM INTO {:p}").bind({ p: target }).execute();
    return { status: 200, body: { ms: Date.now() - t0 } };
  });
}

module.exports = { command, background, projection, seed, lease, read, apply, ack, freeze, transfer, pragmas, checkpoint, vacuumInto };
