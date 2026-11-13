// The live PocketBase schema of a tree, for the privacy field map
// (ROUNDS-14-L01). Each migration's up callback runs, in file order, against
// an empty in-memory database that keeps PocketBase 0.22's collection and
// schema semantics: a found collection is a copy until it's saved, a field
// without an id gets one when it's added, removeField takes an id, and a
// save refuses a duplicated field name. Record and query calls see an empty
// database, except the two schema reads some migrations make (_collections
// and pragma_table_info), which answer from the collections saved so far.
// Seed files read from /pb_seeds/ come from pocketbase/seeds/, as the image
// copies them.
//
// Anything a migration calls that isn't modeled here throws, so a new
// PocketBase API fails the extraction instead of being skipped. The result
// is pinned against real PocketBase in scripts/conformance/test/privacy.test.mjs.

import { createHash } from 'node:crypto';
import vm from 'node:vm';

export const MIGRATIONS_DIR = 'pocketbase/pb_migrations';
export const SEEDS_DIR = 'pocketbase/seeds';
export const BASE_SYSTEM_FIELDS = ['id', 'created', 'updated'];
export const AUTH_SYSTEM_FIELDS = [
  'username', 'email', 'emailVisibility', 'verified', 'tokenKey', 'passwordHash',
  'lastResetSentAt', 'lastVerificationSentAt', 'lastLoginAlertSentAt',
];
// PocketBase 0.22 creates `users` itself, with these two fields.
const BUILTIN = [{
  id: '_pb_users_auth_', name: 'users', type: 'auth', system: false,
  schema: [
    { id: 'users_name', name: 'name', type: 'text', system: false, required: false, presentable: false, unique: false, options: {} },
    { id: 'users_avatar', name: 'avatar', type: 'file', system: false, required: false, presentable: false, unique: false, options: {} },
  ],
  listRule: 'id = @request.auth.id', viewRule: 'id = @request.auth.id', createRule: '', updateRule: 'id = @request.auth.id', deleteRule: 'id = @request.auth.id',
  indexes: [], options: {},
}];
const NO_ROWS = 'sql: no rows in result set';
const TIMEOUT_MS = 10000;

const clone = (v) => (v === undefined ? undefined : JSON.parse(JSON.stringify(v)));

export function migrationFiles(tree) {
  return tree.files().filter((f) => f.startsWith(`${MIGRATIONS_DIR}/`) && f.endsWith('.js') && !f.slice(MIGRATIONS_DIR.length + 1).includes('/')).sort();
}

function makeIds() {
  let n = 0;
  return () => `vm${String(++n).padStart(13, '0')}`;
}

function fieldData(f, nextId) {
  return {
    id: typeof f?.id === 'string' && f.id ? f.id : nextId(),
    name: f?.name,
    type: f?.type,
    system: !!f?.system,
    required: !!f?.required,
    presentable: !!f?.presentable,
    unique: !!f?.unique,
    options: clone(f?.options) || {},
  };
}

// One database: the collections saved so far, and the rows the migrations
// wrote in this run (seed rows included), so a later lookup in the same run
// finds what an earlier step saved.
function createDatabase(tree) {
  const nextId = makeIds();
  const byId = new Map(BUILTIN.map((c) => [c.id, clone(c)]));
  const records = new Map();
  const params = new Map();
  const admins = new Map();

  class SchemaField {
    constructor(data = {}) {
      Object.assign(this, fieldData(data, () => ''));
      if (!data?.id) this.id = '';
    }
  }

  class Schema {
    constructor(fields) {
      this._fields = fields.map((f) => (f instanceof SchemaField ? f : Object.assign(new SchemaField(), fieldData(f, nextId))));
    }
    fields() { return this._fields; }
    addField(field) {
      const f = field instanceof SchemaField ? field : Object.assign(new SchemaField(), fieldData(field, () => ''));
      if (!f.id) f.id = nextId();
      const at = this._fields.findIndex((x) => x.id === f.id);
      if (at === -1) this._fields.push(f);
      else this._fields[at] = f;
    }
    removeField(id) { this._fields = this._fields.filter((f) => f.id !== id); }
    getFieldByName(name) { return this._fields.find((f) => f.name === name) || null; }
    getFieldById(id) { return this._fields.find((f) => f.id === id) || null; }
    fieldNames() { return this._fields.map((f) => f.name); }
    toJSON() { return this._fields.map((f) => fieldData(f, () => f.id)); }
  }

  class Collection {
    constructor(data = {}) {
      this.id = typeof data.id === 'string' ? data.id : '';
      this.name = data.name ?? '';
      this.type = data.type || 'base';
      this.system = !!data.system;
      for (const k of ['listRule', 'viewRule', 'createRule', 'updateRule', 'deleteRule']) this[k] = data[k] === undefined ? null : data[k];
      this.indexes = clone(data.indexes) || [];
      this.options = clone(data.options) || {};
      this.schema = new Schema(Array.isArray(data.schema) ? data.schema : []);
    }
    isAuth() { return this.type === 'auth'; }
    isBase() { return this.type === 'base'; }
    isView() { return this.type === 'view'; }
  }

  const stored = (c) => ({
    id: c.id, name: c.name, type: c.type, system: c.system,
    schema: c.schema.toJSON(),
    listRule: c.listRule, viewRule: c.viewRule, createRule: c.createRule, updateRule: c.updateRule, deleteRule: c.deleteRule,
    indexes: clone(c.indexes), options: clone(c.options),
  });
  const load = (s) => new Collection(clone(s));
  const find = (nameOrId) => {
    const key = String(nameOrId);
    if (byId.has(key)) return byId.get(key);
    for (const c of byId.values()) if (c.name.toLowerCase() === key.toLowerCase()) return c;
    return null;
  };

  class Record {
    constructor(collection, data = {}) {
      if (!(collection instanceof Collection)) throw new Error('new Record needs a collection');
      this._collection = collection.name;
      this._data = { ...clone(data) };
      this.id = typeof data?.id === 'string' && data.id ? data.id : '';
    }
    collection() { return find(this._collection) ? load(find(this._collection)) : null; }
    get(k) { return k === 'id' ? this.id : this._data[k]; }
    set(k, v) { if (k === 'id') this.id = v; else this._data[k] = v; }
    getString(k) { const v = this.get(k); return v === undefined || v === null ? '' : String(v); }
    getInt(k) { return Number.parseInt(this.get(k) ?? 0, 10) || 0; }
    getFloat(k) { return Number(this.get(k) ?? 0) || 0; }
    getBool(k) { return !!this.get(k); }
    getStringSlice(k) { const v = this.get(k); return Array.isArray(v) ? v.map(String) : []; }
    setPassword() {}
    setEmail(v) { this._data.email = v; }
    setUsername(v) { this._data.username = v; }
    setVerified(v) { this._data.verified = v; }
    email() { return this.getString('email'); }
    username() { return this.getString('username'); }
    load(data) { Object.assign(this._data, clone(data)); }
  }

  class Admin {
    constructor() { this.id = ''; this.email = ''; }
    setPassword() {}
  }

  class DynamicModel {
    constructor(shape = {}) { Object.assign(this, clone(shape)); }
  }

  const rowsOf = (name) => {
    const c = find(name);
    if (!c) throw new Error(`no such collection ${name}`);
    if (!records.has(c.name)) records.set(c.name, []);
    return records.get(c.name);
  };

  class Dao {
    constructor() {}
    findCollectionByNameOrId(nameOrId) {
      const c = find(nameOrId);
      if (!c) throw new Error(NO_ROWS);
      return load(c);
    }
    saveCollection(c) {
      if (!(c instanceof Collection)) throw new Error('saveCollection needs a collection');
      if (!c.name) throw new Error('collection name is required');
      if (!c.id) c.id = nextId();
      const clash = find(c.name);
      if (clash && clash.id !== c.id) throw new Error(`collection name ${c.name} is taken`);
      const names = new Set();
      for (const f of c.schema.fields()) {
        if (!f.id) f.id = nextId();
        const lower = String(f.name).toLowerCase();
        if (names.has(lower)) throw new Error(`${c.name}: field ${f.name} is duplicated`);
        names.add(lower);
      }
      byId.set(c.id, stored(c));
    }
    deleteCollection(c) {
      const found = find(c?.id || c?.name || c);
      if (!found) throw new Error(NO_ROWS);
      byId.delete(found.id);
      records.delete(found.name);
    }
    saveRecord(r) {
      if (!(r instanceof Record)) throw new Error('saveRecord needs a record');
      const rows = rowsOf(r._collection);
      if (!r.id) r.id = nextId();
      const at = rows.findIndex((x) => x.id === r.id);
      if (at === -1) rows.push(r);
      else rows[at] = r;
    }
    deleteRecord(r) {
      const rows = rowsOf(r._collection);
      const at = rows.findIndex((x) => x.id === r.id);
      if (at !== -1) rows.splice(at, 1);
    }
    // Filters aren't parsed: a filtered lookup sees an empty table, as on a
    // fresh database. Exact-value lookups read this run's own rows.
    findRecordsByFilter(name) { rowsOf(name); return []; }
    findRecordsByExpr(name) { rowsOf(name); return []; }
    findFirstRecordByFilter(name) { rowsOf(name); throw new Error(NO_ROWS); }
    findFirstRecordByData(name, key, value) {
      const hit = rowsOf(name).find((r) => r.get(key) === value);
      if (!hit) throw new Error(NO_ROWS);
      return hit;
    }
    findRecordById(name, id) {
      const hit = rowsOf(name).find((r) => r.id === id);
      if (!hit) throw new Error(NO_ROWS);
      return hit;
    }
    findAuthRecordByEmail(name, email) { return this.findFirstRecordByData(name, 'email', email); }
    findParamByKey(key) { if (!params.has(key)) throw new Error(NO_ROWS); return params.get(key); }
    saveParam(key, value) { params.set(key, { key, value: clone(value) }); }
    deleteParam(p) { params.delete(p?.key ?? p); }
    findAdminByEmail(email) { if (!admins.has(email)) throw new Error(NO_ROWS); return admins.get(email); }
    saveAdmin(a) { if (!a.id) a.id = nextId(); admins.set(a.email, a); }
    runInTransaction(fn) { fn(this); }
    db() { return database; }
  }

  // Raw SQL sees an empty database, except the two schema reads.
  class Query {
    constructor(sql) { this.sql = String(sql); this.params = {}; }
    bind(params) { Object.assign(this.params, params || {}); return this; }
    execute() { return {}; }
    one() {}
    all(target) {
      if (!Array.isArray(target)) return;
      if (/\bFROM\s+"?_collections"?/i.test(this.sql)) {
        for (const c of byId.values()) target.push(Object.assign(new DynamicModel(), { id: c.id, name: c.name, type: c.type, schema: JSON.stringify(c.schema) }));
        return;
      }
      const pragma = /pragma_table_info\(\{:(\w+)\}\)/i.exec(this.sql);
      if (pragma) {
        const c = find(this.params[pragma[1]]);
        if (!c) return;
        const names = [...BASE_SYSTEM_FIELDS, ...(c.type === 'auth' ? AUTH_SYSTEM_FIELDS : []), ...c.schema.map((f) => f.name)];
        for (const name of names) target.push(Object.assign(new DynamicModel(), { name }));
      }
    }
  }
  const database = { newQuery: (sql) => new Query(sql) };

  const readSeed = (path) => {
    const m = /^\/pb_seeds\/(.+)$/.exec(String(path));
    const text = m ? tree.read(`${SEEDS_DIR}/${m[1]}`) : null;
    if (text === null || text === undefined) throw new Error(`open ${path}: no such file or directory`);
    return text;
  };

  const globals = {
    Dao, Collection, SchemaField, Record, Admin, DynamicModel,
    arrayOf: () => [],
    toString: (v) => (typeof v === 'string' ? v : String(v)),
    $os: {
      getenv: () => '',
      readFile: readSeed,
      writeFile: () => { throw new Error('migrations under extraction write no files'); },
    },
    $security: {
      sha256: (s) => createHash('sha256').update(String(s)).digest('hex'),
    },
    console: { log() {}, warn() {}, error() {}, info() {} },
  };

  const snapshot = () => [...byId.values()].map((c) => clone(c)).sort((a, b) => a.name.localeCompare(b.name));
  return { database, globals, snapshot };
}

// Returns { ok, collections: [{ name, type, fields: [{ name, type }], listRule, viewRule }], errors: [{ path, message }] }.
// `only` limits the run to those migration file names (the pin's set).
export function extractSchema(tree, { only = null } = {}) {
  const db = createDatabase(tree);
  const errors = [];
  const files = migrationFiles(tree).filter((f) => !only || only.includes(f.slice(MIGRATIONS_DIR.length + 1)));
  for (const file of files) {
    let up = null;
    const sandbox = { ...db.globals, migrate: (u) => { up = u; } };
    try {
      vm.runInNewContext(tree.read(file), sandbox, { filename: file, timeout: TIMEOUT_MS });
      if (typeof up !== 'function') throw new Error('no migrate(up, down) call');
      vm.runInNewContext('__up(__db)', { ...sandbox, __up: up, __db: db.database }, { timeout: TIMEOUT_MS });
    } catch (err) {
      errors.push({ path: file, message: String(err?.message || err).split('\n')[0] });
      break;
    }
  }
  const collections = db.snapshot().map((c) => ({
    name: c.name,
    type: c.type,
    // A text field's pattern is what makes it constrained rather than free text.
    fields: c.schema.map((f) => ({ name: f.name, type: f.type, ...(f.options?.pattern ? { pattern: f.options.pattern } : {}) })),
    listRule: c.listRule,
    viewRule: c.viewRule,
  }));
  return { ok: errors.length === 0, collections, errors, files };
}

// Every field id the schema holds: the store itself (`pb:<collection>`, whose
// entry covers id, created, and updated), each auth system field, and each
// field the migrations define.
export function schemaFieldIds(collections) {
  const out = [];
  for (const c of collections) {
    out.push({ id: `pb:${c.name}`, collection: c.name, store: true });
    if (c.type === 'auth') for (const f of AUTH_SYSTEM_FIELDS) out.push({ id: `pb:${c.name}.${f}`, collection: c.name, field: f, system: true });
    for (const f of c.fields) out.push({ id: `pb:${c.name}.${f.name}`, collection: c.name, field: f.name, type: f.type });
  }
  return out;
}
