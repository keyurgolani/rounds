// Runs the database benchmark's hook logic (harness/bench/pb_hooks/bench_lib.js)
// on node's SQLite, for pocketbase/tests/test_bench_hooks.py.
//
//   node bench_runner.cjs <repo root>   < {"steps": [...]}
//
// The bench's own migration creates the tables and indexes through a fake
// migrate/Collection/Dao, so the partial unique index and every unique key
// are SQLite's own. Each write step runs in BEGIN/COMMIT, rolled back on a
// refusal or a failpoint, as bench_handlers.js does on PocketBase.
"use strict";

process.removeAllListeners("warning");
const crypto = require("crypto");
const path = require("path");
const fs = require("fs");
const { DatabaseSync } = require("node:sqlite");

const root = process.argv[2];
const lib = require(path.join(root, "harness/bench/pb_hooks/bench_lib.js"));
const db = new DatabaseSync(":memory:");

const sha256 = (text) => crypto.createHash("sha256").update(text).digest("hex");
let clock = 1_800_000_000_000;
let idCounter = 0;

function newId() {
  idCounter += 1;
  return ("r" + idCounter.toString(36)).padEnd(15, "0").slice(0, 15);
}

const SQL_TYPE = { text: "TEXT DEFAULT '' NOT NULL", number: "NUMERIC DEFAULT 0 NOT NULL", bool: "BOOLEAN DEFAULT FALSE NOT NULL", json: "JSON DEFAULT NULL", file: "TEXT DEFAULT '' NOT NULL" };
const columns = {};

function createTable(name, schema, indexes) {
  const cols = ["id TEXT PRIMARY KEY NOT NULL", "created TEXT DEFAULT '' NOT NULL", "updated TEXT DEFAULT '' NOT NULL"];
  columns[name] = {};
  for (const f of schema) {
    cols.push(`${f.name} ${SQL_TYPE[f.type] || "TEXT"}`);
    columns[name][f.name] = f.type;
  }
  db.exec(`CREATE TABLE ${name} (${cols.join(", ")})`);
  for (const sql of indexes || []) db.exec(sql);
}

// The bench migration, run through the smallest fake that can execute it.
global.migrate = (up) => { global.__up = up; };
global.Collection = class { constructor(opts) { Object.assign(this, opts); } };
global.Dao = class {
  saveCollection(c) { createTable(c.name, c.schema, c.indexes); }
  findCollectionByNameOrId() { throw new Error("not in the fake"); }
  deleteCollection() {}
};
require(path.join(root, "harness/bench/pb_migrations/1800000000_bench_fixture.js"));
global.__up(null);

// The legacy pipeline tables the transfer reads (the columns it uses).
createTable("campaigns", [{ name: "user", type: "text" }, { name: "name", type: "text" }, { name: "slug", type: "text" }], []);
createTable("applications", [{ name: "user", type: "text" }, { name: "company", type: "text" }, { name: "role", type: "text" }, { name: "status", type: "text" }], []);
createTable("interview_rounds", [{ name: "user", type: "text" }, { name: "application", type: "text" }, { name: "round_type", type: "text" }], []);
createTable("offers", [{ name: "user", type: "text" }, { name: "application", type: "text" }, { name: "status", type: "text" }], []);
createTable("todos", [{ name: "user", type: "text" }, { name: "campaign", type: "text" }, { name: "body", type: "text" }], []);

const toSqlite = (sql) => sql.replace(/\{:(\w+)\}/g, ":$1");
const bindable = (v) => (v === true ? 1 : v === false ? 0 : v !== null && typeof v === "object" ? JSON.stringify(v) : v);
function bind(params) {
  const out = {};
  for (const [k, v] of Object.entries(params || {})) out[k] = bindable(v);
  return out;
}
function shaped(row, shape) {
  if (!row) return null;
  const out = {};
  for (const [k, blank] of Object.entries(shape)) {
    const v = row[k];
    if (typeof blank === "number") out[k] = v == null ? 0 : Number(v);
    else if (typeof blank === "boolean") out[k] = !!v;
    else out[k] = v == null ? "" : String(v);
  }
  return out;
}

const store = {
  one: (sql, params, shape) => shaped(db.prepare(toSqlite(sql)).get(bind(params)), shape),
  all: (sql, params, shape) => db.prepare(toSqlite(sql)).all(bind(params)).map((r) => shaped(r, shape)),
  exec: (sql, params) => { db.prepare(toSqlite(sql)).run(bind(params)); },
  insert(table, fields) {
    const id = newId();
    const keys = Object.keys(fields);
    db.prepare(`INSERT INTO ${table} (id, created, updated, ${keys.join(", ")}) VALUES (:__id, 'now', 'now', ${keys.map((k) => ":" + k).join(", ")})`)
      .run(Object.assign({ __id: id }, bind(fields)));
    return id;
  },
  update(table, id, fields) {
    const keys = Object.keys(fields);
    if (!keys.length) {
      db.prepare(`UPDATE ${table} SET updated = 'now' WHERE id = :__id`).run({ __id: id });
      return;
    }
    db.prepare(`UPDATE ${table} SET ${keys.map((k) => `${k} = :${k}`).join(", ")}, updated = 'now' WHERE id = :__id`)
      .run(Object.assign({ __id: id }, bind(fields)));
  },
  remove(table, id) { db.prepare(`DELETE FROM ${table} WHERE id = :__id`).run({ __id: id }); },
};

// bench_handlers.inTransaction's contract on SQLite.
function inTransaction(fn) {
  db.exec("BEGIN");
  try {
    const out = fn(store, clock);
    db.exec("COMMIT");
    return { status: out.status || 200, body: out.body || out };
  } catch (err) {
    db.exec("ROLLBACK");
    if (err && err.refusal) return { status: err.status, body: err.body };
    if (err && err.failpoint) return { status: 503, body: { error: "failpoint", failpoint: err.failpoint } };
    if (String(err && err.message).indexOf("UNIQUE constraint failed") >= 0) return { status: 409, body: { error: "invariant_violation" } };
    throw err;
  }
}

const STEPS = {
  tick: (s) => { clock += s.ms; return { now: clock }; },
  raw: (s) => store.all(s.sql, s.params || {}, s.shape),
  rawWrite: (s) => {
    try { store.exec(s.sql, s.params || {}); return { ok: true }; } catch (err) { return { ok: false, error: String(err.message) }; }
  },
  insert: (s) => inTransaction(() => ({ status: 200, body: { id: store.insert(s.table, s.fields) } })),
  command: (s) => inTransaction((st, now) => lib.commandIn(st, { account: s.account, actor: "user:" + s.account, now, sha256, failpoint: s.failpoint }, s.body)),
  background: (s) => inTransaction((st, now) => ({ status: 200, body: { writes: lib.backgroundIn(st, s.kind, s.account, now) } })),
  seed: (s) => inTransaction((st) => ({ status: 200, body: { rows: lib.seedIn(st, s.table, s.columns, s.rows) } })),
  lease: (s) => inTransaction((st, now) => ({ status: 200, body: lib.leaseIn(st, s.holder, s.ttl_ms, now) })),
  read: (s) => ({ status: 200, body: lib.readIn(store, s.limit || 200) }),
  apply: (s) => inTransaction((st, now) => ({ status: 200, body: lib.applyIn(st, s.events, now) })),
  ack: (s) => inTransaction((st, now) => ({ status: 200, body: lib.ackIn(st, s.holder, s.token, s.cursor, now) })),
  projection: (s) => ({ status: 200, body: lib.projectionIn(store, s.account, s.aggregate_id, s.min_position) }),
  transfer: (s) => inTransaction((st, now) => ({ status: 200, body: lib.transferIn(st, { now, sha256 }, s.account, s.after || "", s.limit) })),
  derivedId: (s) => lib.derivedId(sha256, s.time_ms, s.parts),
  checkCommand: (s) => lib.checkCommand(s.body),
};

const input = JSON.parse(fs.readFileSync(0, "utf8"));
const results = [];
for (const step of input.steps) {
  const fn = STEPS[step.op];
  if (!fn) throw new Error("unknown step " + step.op);
  try {
    results.push(fn(step));
  } catch (err) {
    results.push({ thrown: String(err && err.message ? err.message : err) });
  }
}
process.stdout.write(JSON.stringify(results));
