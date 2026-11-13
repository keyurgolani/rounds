// Runs 1700008800_ai_credentials.js and 1700008820_ai_credentials_move.js
// on node's SQLite, for pocketbase/tests/test_ai_credentials_move.py
// (ROUNDS-14-L02 stage A).
//
//   node ai_credentials_move_runner.cjs <migrations dir> < program.json
//
// The tables the move reads (users, ai_providers, ai_settings, _params)
// have PocketBase's column shapes; 1700008800's own up step creates the two
// new collections, their indexes, and their owner triggers through a fake
// Dao, so every unique key and trigger is SQLite's own. Each migration step
// runs in BEGIN/COMMIT and rolls back on a throw, as PocketBase applies a
// migration. A program is {"env": {...}, "steps": [...]}; the output is
// {"results": [...], "logs": [...], "written": [...]}.
"use strict";

process.removeAllListeners("warning");
const crypto = require("crypto");
const fs = require("fs");
const path = require("path");
const { DatabaseSync } = require("node:sqlite");

const [migrationsDir] = process.argv.slice(2);
const program = JSON.parse(fs.readFileSync(0, "utf8"));
const sqlite = new DatabaseSync(":memory:");
const logs = [];
const written = [];
let idCounter = 0;

const newId = () => {
  idCounter += 1;
  return ("z" + idCounter.toString(36)).padEnd(15, "0");
};

sqlite.exec(`
  CREATE TABLE users (id TEXT PRIMARY KEY NOT NULL, created TEXT DEFAULT '' NOT NULL, updated TEXT DEFAULT '' NOT NULL);
  CREATE TABLE ai_providers (id TEXT PRIMARY KEY NOT NULL, created TEXT DEFAULT '' NOT NULL, updated TEXT DEFAULT '' NOT NULL,
    user TEXT DEFAULT '' NOT NULL, kind TEXT DEFAULT '' NOT NULL, label TEXT DEFAULT '' NOT NULL,
    base_url TEXT DEFAULT '' NOT NULL, encrypted_key TEXT DEFAULT '' NOT NULL, key_iv TEXT DEFAULT '' NOT NULL,
    models_cache JSON DEFAULT NULL, models_cached_at TEXT DEFAULT '' NOT NULL);
  CREATE TABLE ai_settings (id TEXT PRIMARY KEY NOT NULL, created TEXT DEFAULT '' NOT NULL, updated TEXT DEFAULT '' NOT NULL,
    user TEXT DEFAULT '' NOT NULL, text_provider TEXT DEFAULT '' NOT NULL, text_model TEXT DEFAULT '' NOT NULL,
    vision_provider TEXT DEFAULT '' NOT NULL, vision_model TEXT DEFAULT '' NOT NULL);
  CREATE TABLE _params (id TEXT PRIMARY KEY NOT NULL, key TEXT UNIQUE NOT NULL, value JSON DEFAULT NULL,
    created TEXT DEFAULT '' NOT NULL, updated TEXT DEFAULT '' NOT NULL);
`);

const collections = {
  users: { id: "_pb_users_auth_", name: "users" },
  ai_providers: { id: "pbc_ai_providers", name: "ai_providers" },
  ai_settings: { id: "pbc_ai_settings", name: "ai_settings" },
};
const columns = {};

const toSqlite = (sql) => sql.replace(/\{:(\w+)\}/g, ":$1");
const bindable = (v) => (v === true ? 1 : v === false ? 0 : v !== null && typeof v === "object" ? JSON.stringify(v) : v);
function bound(params) {
  const out = {};
  for (const [k, v] of Object.entries(params || {})) out[k] = bindable(v);
  return out;
}
function shaped(row, shape) {
  const out = {};
  for (const [k, blank] of Object.entries(shape)) {
    const v = row[k];
    if (typeof blank === "number") out[k] = v == null ? 0 : Number(v);
    else out[k] = v == null ? "" : String(v);
  }
  return out;
}

global.DynamicModel = class DynamicModel {
  constructor(shape) {
    Object.defineProperty(this, "__shape", { value: Object.assign({}, shape || {}) });
    Object.assign(this, shape || {});
  }
};
global.arrayOf = (model) => {
  const out = [];
  Object.defineProperty(out, "__shape", { value: model.__shape });
  return out;
};
global.Collection = class Collection {
  constructor(opts) {
    Object.assign(this, opts);
    this.id = this.id || "pbc_" + this.name;
  }
};
global.Record = class Record {
  constructor(collection) {
    this._collection = collection.name;
    this.id = "";
    this.data = {};
  }
  set(key, value) {
    if (key === "id") this.id = value;
    else this.data[key] = value;
  }
};

const SQL_TYPE = { text: "TEXT DEFAULT '' NOT NULL", number: "NUMERIC DEFAULT 0 NOT NULL", relation: "TEXT DEFAULT '' NOT NULL", json: "JSON DEFAULT NULL" };

function query(sql) {
  let params = {};
  const q = {
    bind(p) {
      params = Object.assign(params, p || {});
      return q;
    },
    execute() {
      sqlite.prepare(toSqlite(sql)).run(bound(params));
    },
    one(model) {
      const row = sqlite.prepare(toSqlite(sql)).get(bound(params));
      if (!row) throw new Error("sql: no rows in result set");
      Object.assign(model, shaped(row, model.__shape || {}));
    },
    all(rows) {
      for (const row of sqlite.prepare(toSqlite(sql)).all(bound(params))) rows.push(shaped(row, rows.__shape || {}));
    },
  };
  return q;
}
const db = { newQuery: query };

global.Dao = class Dao {
  findCollectionByNameOrId(name) {
    const found = collections[name] || Object.values(collections).find((c) => c.id === name);
    if (!found) throw new Error("sql: no rows in result set");
    return found;
  }
  saveCollection(c) {
    const cols = ["id TEXT PRIMARY KEY NOT NULL", "created TEXT DEFAULT '' NOT NULL", "updated TEXT DEFAULT '' NOT NULL"];
    columns[c.name] = c.schema.map((f) => f.name);
    for (const f of c.schema) cols.push(`"${f.name}" ${SQL_TYPE[f.type] || "TEXT DEFAULT '' NOT NULL"}`);
    sqlite.exec(`CREATE TABLE "${c.name}" (${cols.join(", ")})`);
    for (const index of c.indexes || []) sqlite.exec(index);
    collections[c.name] = c;
  }
  deleteCollection(c) {
    sqlite.exec(`DROP TABLE "${c.name}"`);
    delete collections[c.name];
  }
  saveRecord(r) {
    if (!r.id) r.id = newId();
    const keys = Object.keys(r.data);
    sqlite
      .prepare(`INSERT INTO "${r._collection}" (id, created, updated, ${keys.map((k) => `"${k}"`).join(", ")}) ` +
        `VALUES (:__id, 'now', 'now', ${keys.map((k) => ":" + k).join(", ")})`)
      .run(Object.assign({ __id: r.id }, bound(r.data)));
  }
  saveParam(key, value) {
    sqlite.prepare("INSERT OR REPLACE INTO _params (id, key, value) VALUES (:id, :key, :value)")
      .run({ id: newId(), key, value: JSON.stringify(value) });
  }
};

global.$os = {
  getenv: (name) => (program.env || {})[name] || "",
  writeFile: (file, data, perm) => written.push({ path: file, data: String(data), perm }),
};
global.$security = { sha256: (text) => crypto.createHash("sha256").update(String(text), "utf8").digest("hex") };
global.console = Object.assign(Object.create(console), { log: (line) => logs.push(String(line)) });

const migrations = {};
global.migrate = (up, down) => {
  migrations.__last = { up, down };
};
for (const name of ["1700008800_ai_credentials.js", "1700008820_ai_credentials_move.js"]) {
  require(path.join(migrationsDir, name));
  migrations[name] = migrations.__last;
}

function inTransaction(fn) {
  sqlite.exec("BEGIN");
  try {
    fn();
    sqlite.exec("COMMIT");
    return { ok: true };
  } catch (err) {
    sqlite.exec("ROLLBACK");
    return { ok: false, error: String((err && err.message) || err) };
  }
}

const exists = (name) => Boolean(sqlite.prepare("SELECT 1 AS x FROM sqlite_master WHERE type = 'table' AND name = ?").get(name));
const table = (name) => (exists(name) ? sqlite.prepare(`SELECT * FROM "${name}" ORDER BY id`).all() : null);

const results = [];
for (const step of program.steps) {
  if (step.op === "seed") {
    results.push(inTransaction(() => {
      for (const row of step.rows) {
        const keys = Object.keys(row);
        sqlite.prepare(`INSERT INTO "${step.table}" (${keys.map((k) => `"${k}"`).join(", ")}) VALUES (${keys.map((k) => ":" + k).join(", ")})`)
          .run(bound(row));
      }
    }));
  } else if (step.op === "up" || step.op === "down") {
    results.push(inTransaction(() => migrations[step.file][step.op](db)));
  } else if (step.op === "sql") {
    results.push(inTransaction(() => sqlite.prepare(step.sql).run()));
  } else if (step.op === "dump") {
    const out = {};
    for (const name of ["ai_providers", "ai_settings", "ai_credentials", "ai_provider_models", "_params"]) out[name] = table(name);
    results.push(JSON.parse(JSON.stringify(out)));
  } else {
    throw new Error("unknown step " + step.op);
  }
}
process.stdout.write(JSON.stringify({ results, logs, written }));
