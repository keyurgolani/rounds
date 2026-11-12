/// <reference path="../pb_data/types.d.ts" />

// The database benchmark's hook logic (ROUNDS-02-L01). Bench only:
// pbnative.py copies it beside the repository's hooks in a scratch
// directory; the image never carries it.
//
// It prototypes alternative A of DR-0004: a PocketBase hook route owns one
// transaction per command, and inside it reads the idempotency row, the
// aggregates and their versions, applies the change, and writes the change
// set, audit entries, outbox events, and the idempotency result. The relay
// functions take a fenced lease, read events in relay order, apply them to a
// projection that skips anything it has already seen, and move a cursor.
//
// Every function works on a store, so pocketbase/tests runs the same logic
// on node's SQLite and pbStore() runs it on PocketBase's Dao. The failpoint
// names are the ones #19 to #23 reuse; they exist only in this tree.
// TODO(ROUNDS-34-L01): #170 takes these failpoints over with the harnesses.

const FAILPOINTS = ["before-commit", "after-commit-before-relay", "mid-relay"];
const COMMAND_TYPES = ["update", "create", "compose", "delete_revive"];
const V7 = /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const IDEMPOTENCY_SECONDS = 30 * 24 * 3600;
const RELAY_LEASE = "outbox-relay";
const RELAY_CURSOR = "relay";
const SEED_TABLES = ["bench_records", "bench_change_sets", "bench_audit", "bench_idempotency", "bench_outbox",
  "bench_projection", "bench_blobs", "bench_checkpoints", "campaigns", "applications", "interview_rounds", "offers", "todos"];
const NAME = /^[a-z_]+$/;
const RECORD_ID = /^[a-z0-9]{15}$/;

// Errors carry plain markers, not just a class, because the route reads
// them inside the transaction callback before rolling back.
class Refusal extends Error {
  constructor(status, error, extra) {
    super(error);
    this.refusal = true;
    this.status = status;
    this.body = Object.assign({ error }, extra || {});
  }
}

class Failpoint extends Error {
  constructor(name) {
    super("failpoint " + name);
    this.failpoint = name;
  }
}

function pad(text, width) {
  let out = String(text);
  while (out.length < width) out = "0" + out;
  return out;
}

// A UUIDv7-shaped id for a write no browser command names (DR-0004's
// identifier rules): the source's time in milliseconds, then 74 bits of
// SHA-256 over the parts (actor kind, handler, source id, effect index).
// It passes the same v7 check as a client's command_id, and a retry of the
// same effect gets the same id.
function derivedId(sha256hex, timeMs, parts) {
  const h = sha256hex(parts.join("\u0000"));
  const t = pad(Math.floor(timeMs).toString(16), 12);
  const variant = (8 + (parseInt(h[3], 16) >> 2)).toString(16);
  return t.slice(0, 8) + "-" + t.slice(8, 12) + "-7" + h.slice(0, 3) + "-" + variant + h.slice(4, 7) + "-" + h.slice(7, 19);
}

function canonical(value) {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (value && typeof value === "object") {
    return "{" + Object.keys(value).sort().map((k) => JSON.stringify(k) + ":" + canonical(value[k])).join(",") + "}";
  }
  return JSON.stringify(value === undefined ? null : value);
}

function placeholders(prefix, values, params) {
  return values.map((v, i) => {
    params[prefix + i] = v;
    return "{:" + prefix + i + "}";
  }).join(", ");
}

function checkCommand(body) {
  if (!body || typeof body !== "object") return "invalid_request";
  if (typeof body.command_id !== "string" || !V7.test(body.command_id)) return "invalid_command_id";
  if (COMMAND_TYPES.indexOf(body.type) < 0) return "unknown_command";
  const expected = body.expected || {};
  if (typeof expected !== "object" || Array.isArray(expected)) return "invalid_request";
  for (const id of Object.keys(expected)) {
    if (!RECORD_ID.test(id) || !Number.isInteger(expected[id])) return "invalid_request";
  }
  return null;
}

function loadAggregates(store, account, ids) {
  if (!ids.length) return {};
  const params = {};
  const rows = store.all(
    "SELECT id, account_id, kind, version, status, parent, deleted FROM bench_records WHERE id IN (" + placeholders("i", ids, params) + ")",
    params,
    { id: "", account_id: "", kind: "", version: 0, status: "", parent: "", deleted: false },
  );
  const byId = {};
  rows.forEach((r) => { byId[r.id] = r; });
  for (const id of ids) {
    // Another account's aggregate and a missing one get the same answer.
    if (!byId[id] || byId[id].account_id !== account) throw new Refusal(404, "not_found");
  }
  return byId;
}

function nextNumber(store, sql, params) {
  return store.one(sql, params || {}, { n: 0 }).n;
}

// One command in one transaction. ctx: { account, actor, now (ms), sha256,
// failpoint }. Returns { status, body, writes }.
function commandIn(store, ctx, body) {
  const invalid = checkCommand(body);
  if (invalid) return { status: 400, body: { error: invalid }, writes: 0 };
  const fingerprint = ctx.sha256(canonical({ type: body.type, expected: body.expected || {}, args: body.args || {} }));
  const prior = store.one(
    "SELECT fingerprint, state, result FROM bench_idempotency WHERE account_id = {:a} AND command_id = {:c}",
    { a: ctx.account, c: body.command_id },
    { fingerprint: "", state: "", result: "" },
  );
  if (prior) {
    if (prior.fingerprint !== fingerprint) return { status: 409, body: { error: "fingerprint_conflict" }, writes: 0 };
    return { status: 200, body: Object.assign({ replay: true }, JSON.parse(prior.result || "{}")), writes: 0 };
  }
  const expected = body.expected || {};
  const args = body.args || {};
  const aggs = loadAggregates(store, ctx.account, Object.keys(expected));
  const stale = Object.keys(expected).filter((id) => aggs[id].version !== expected[id]);
  if (stale.length) {
    const current = {};
    stale.forEach((id) => { current[id] = aggs[id].version; });
    return { status: 409, body: { error: "stale_version", current }, writes: 0 };
  }

  // The change, as ordered writes to bench_records.
  const ops = [];
  const bump = (id, fields) => ops.push({ op: "update", id, kind: aggs[id].kind, version: aggs[id].version + 1, fields });
  if (body.type === "update") {
    if (!aggs[args.id]) throw new Refusal(400, "invalid_request");
    bump(args.id, { payload: args.payload || {} });
  } else if (body.type === "create") {
    ops.push({ op: "insert", kind: String(args.kind || "fact"), version: 1,
      fields: { account_id: ctx.account, kind: String(args.kind || "fact"), status: "", parent: "", payload: args.payload || {} } });
  } else if (body.type === "compose") {
    // The offer chain's supersede-and-create plus the opportunity's status,
    // composed in one transaction. The active offer is superseded before
    // the new one is written, so the partial unique index holds throughout.
    const opp = aggs[args.opportunity];
    const offer = aggs[args.offer];
    if (!opp || !offer || offer.kind !== "offer" || offer.parent !== opp.id || offer.status !== "active") throw new Refusal(409, "invariant_violation");
    bump(offer.id, { status: "superseded" });
    ops.push({ op: "insert", kind: "offer", version: 1,
      fields: { account_id: ctx.account, kind: "offer", status: "active", parent: opp.id, payload: args.payload || {} } });
    bump(opp.id, { status: "Offer" });
  } else if (body.type === "delete_revive") {
    // Delete the active offer and revive the one it superseded, together.
    const opp = aggs[args.opportunity];
    const offer = aggs[args.offer];
    const prev = aggs[args.prior];
    if (!opp || !offer || !prev || offer.status !== "active" || prev.status !== "superseded" ||
        offer.parent !== opp.id || prev.parent !== opp.id) throw new Refusal(409, "invariant_violation");
    bump(offer.id, { status: "deleted", deleted: true });
    bump(prev.id, { status: "active" });
    bump(opp.id, {});
  }

  const seq = nextNumber(store, "SELECT COALESCE(MAX(seq), 0) + 1 AS n FROM bench_change_sets");
  const position = nextNumber(store, "SELECT COALESCE(MAX(commit_position), 0) + 1 AS n FROM bench_change_sets WHERE account_id = {:a}", { a: ctx.account });
  let relaySeq = nextNumber(store, "SELECT COALESCE(MAX(relay_seq), 0) + 1 AS n FROM bench_outbox");
  let writes = 0;
  const vector = {};
  ops.forEach((o) => {
    if (o.op === "insert") {
      o.id = store.insert("bench_records", Object.assign({ version: o.version, deleted: false }, o.fields));
    } else {
      store.update("bench_records", o.id, Object.assign({ version: o.version }, o.fields));
    }
    vector[o.id] = o.version;
    writes += 1;
  });
  const changeSet = store.insert("bench_change_sets", {
    account_id: ctx.account, commit_position: position, seq, command_id: body.command_id, actor: ctx.actor,
    vector, ops: ops.map((o) => ({ op: o.op, id: o.id, version: o.version, fields: Object.keys(o.fields) })),
  });
  writes += 1;
  ops.forEach((o, i) => {
    store.insert("bench_audit", { account_id: ctx.account, change_set: changeSet, commit_position: position, actor: ctx.actor,
      action: body.type + "." + o.op, target: o.id, meta: { version: o.version } });
    store.insert("bench_outbox", {
      account_id: ctx.account, commit_position: position, ordinal: i, relay_seq: relaySeq,
      event_id: derivedId(ctx.sha256, ctx.now, ["gateway", body.type, body.command_id, String(i)]),
      aggregate_id: o.id, aggregate_seq: o.version, type: o.kind + "." + o.op, payload: { version: o.version }, occurred_at: ctx.now,
    });
    relaySeq += 1;
    writes += 2;
  });
  const result = { commit_position: position, seq, versions: vector };
  store.insert("bench_idempotency", { account_id: ctx.account, command_id: body.command_id, fingerprint, state: "completed",
    result, expires_at: Math.floor(ctx.now / 1000) + IDEMPOTENCY_SECONDS });
  writes += 1;
  // After every write and before the commit: the transaction rolls back
  // and nothing above persists.
  if (ctx.failpoint === "before-commit") throw new Failpoint("before-commit");
  return { status: 200, body: Object.assign({ writes }, result), writes };
}

// The relay's lease (#22's outbox-relay row): one holder at a time, a new
// fencing token on every takeover.
function leaseIn(store, holder, ttlMs, now) {
  const row = store.one("SELECT id, holder, fencing_token, expires_at FROM bench_leases WHERE name = {:n}", { n: RELAY_LEASE },
    { id: "", holder: "", fencing_token: 0, expires_at: 0 });
  if (!row) {
    store.insert("bench_leases", { name: RELAY_LEASE, holder, fencing_token: 1, expires_at: now + ttlMs });
    return { held: true, token: 1 };
  }
  if (row.holder === holder && row.expires_at > now) {
    store.update("bench_leases", row.id, { expires_at: now + ttlMs });
    return { held: true, token: row.fencing_token };
  }
  if (row.expires_at <= now) {
    store.update("bench_leases", row.id, { holder, fencing_token: row.fencing_token + 1, expires_at: now + ttlMs });
    return { held: true, token: row.fencing_token + 1 };
  }
  return { held: false, holder: row.holder, expires_at: row.expires_at };
}

function cursorOf(store) {
  const row = store.one("SELECT last_seq FROM bench_checkpoints WHERE name = {:n}", { n: RELAY_CURSOR }, { last_seq: 0 });
  return row ? row.last_seq : 0;
}

function readIn(store, limit) {
  const after = cursorOf(store);
  const events = store.all(
    "SELECT relay_seq, event_id, account_id, aggregate_id, aggregate_seq, type, commit_position, occurred_at " +
      "FROM bench_outbox WHERE relay_seq > {:after} ORDER BY relay_seq LIMIT {:limit}",
    { after, limit },
    { relay_seq: 0, event_id: "", account_id: "", aggregate_id: "", aggregate_seq: 0, type: "", commit_position: 0, occurred_at: 0 },
  );
  return { after, events };
}

// The projector: applies each event once. An event at or below what the
// projection already holds for its aggregate is skipped and counted.
function applyIn(store, events, now) {
  let applied = 0;
  let skipped = 0;
  let gaps = 0;
  events.forEach((e) => {
    const row = store.one("SELECT id, aggregate_seq FROM bench_projection WHERE aggregate_id = {:a}", { a: e.aggregate_id },
      { id: "", aggregate_seq: 0 });
    if (row && row.aggregate_seq >= e.aggregate_seq) {
      skipped += 1;
      return;
    }
    if ((row ? row.aggregate_seq : 0) + 1 !== e.aggregate_seq && row) gaps += 1;
    const fields = { account_id: e.account_id, aggregate_id: e.aggregate_id, kind: e.type.split(".")[0], version: e.aggregate_seq,
      aggregate_seq: e.aggregate_seq, position: e.commit_position, applied_at: now, summary: { type: e.type } };
    if (row) store.update("bench_projection", row.id, fields);
    else store.insert("bench_projection", fields);
    applied += 1;
  });
  return { applied, skipped, gaps };
}

// Moves the relay cursor, only for the lease's current holder and token.
function ackIn(store, holder, token, cursor, now) {
  const lease = store.one("SELECT holder, fencing_token, expires_at FROM bench_leases WHERE name = {:n}", { n: RELAY_LEASE },
    { holder: "", fencing_token: 0, expires_at: 0 });
  if (!lease || lease.holder !== holder || lease.fencing_token !== token || lease.expires_at <= now) {
    return { acked: false, reason: "fenced" };
  }
  const row = store.one("SELECT id, last_seq FROM bench_checkpoints WHERE name = {:n}", { n: RELAY_CURSOR }, { id: "", last_seq: 0 });
  if (!row) store.insert("bench_checkpoints", { name: RELAY_CURSOR, last_seq: cursor, updated_at: now });
  else if (cursor > row.last_seq) store.update("bench_checkpoints", row.id, { last_seq: cursor, updated_at: now });
  return { acked: true };
}

// A read-your-writes read: the projection's row for an aggregate, and
// whether it has reached the position the command returned.
function projectionIn(store, account, aggregateId, minPosition) {
  const row = store.one(
    "SELECT account_id, version, position FROM bench_projection WHERE aggregate_id = {:a}",
    { a: aggregateId },
    { account_id: "", version: 0, position: 0 },
  );
  if (!row || row.account_id !== account) return { found: false, reached: false };
  return { found: true, reached: row.position >= minPosition, version: row.version, position: row.position };
}

// One batch of a bounded-context transfer: the account's legacy
// applications after a cursor, with their rounds and offers, written as
// fixture aggregates and change sets. At most `limit` applications, so a
// batch stays inside the writer lock budget.
function transferIn(store, ctx, account, afterId, limit) {
  const apps = store.all(
    "SELECT id, company, role, status FROM applications WHERE user = {:u} AND id > {:after} ORDER BY id LIMIT {:limit}",
    { u: account, after: afterId, limit },
    { id: "", company: "", role: "", status: "" },
  );
  let rows = 0;
  let position = nextNumber(store, "SELECT COALESCE(MAX(commit_position), 0) + 1 AS n FROM bench_change_sets WHERE account_id = {:a}", { a: account });
  let seq = nextNumber(store, "SELECT COALESCE(MAX(seq), 0) + 1 AS n FROM bench_change_sets");
  apps.forEach((app) => {
    const opp = store.insert("bench_records", { account_id: account, kind: "opportunity_t", version: 1, status: app.status, parent: "",
      deleted: false, payload: { company: app.company, role: app.role, legacy: app.id } });
    rows += 1;
    const rounds = store.all("SELECT id, round_type FROM interview_rounds WHERE application = {:a}", { a: app.id }, { id: "", round_type: "" });
    rounds.forEach((r) => {
      store.insert("bench_records", { account_id: account, kind: "activity_t", version: 1, status: "", parent: opp, deleted: false,
        payload: { type: r.round_type, legacy: r.id } });
      rows += 1;
    });
    const offers = store.all("SELECT id FROM offers WHERE application = {:a}", { a: app.id }, { id: "" });
    offers.forEach((o) => {
      store.insert("bench_records", { account_id: account, kind: "offer_t", version: 1, status: "", parent: opp, deleted: false,
        payload: { legacy: o.id } });
      rows += 1;
    });
    store.insert("bench_change_sets", { account_id: account, commit_position: position, seq, command_id: derivedId(ctx.sha256, ctx.now,
      ["migration", "transfer-pipeline", app.id, "0"]), actor: "migration", vector: {}, ops: [{ op: "transfer", id: opp }] });
    position += 1;
    seq += 1;
    rows += 1;
  });
  return { done: apps.length < limit, cursor: apps.length ? apps[apps.length - 1].id : afterId, applications: apps.length, rows };
}

// Modeled background writers, the same size of transaction as the real
// ones: an admission admit (command, counter, and lease), an execution
// heartbeat, and a share-resolve counter with the old-counter cleanup.
function backgroundIn(store, kind, account, now) {
  const upsert = (k, key) => {
    const row = store.one("SELECT id, count FROM bench_bg WHERE kind = {:k} AND key = {:key}", { k, key }, { id: "", count: 0 });
    if (row) store.update("bench_bg", row.id, { count: row.count + 1, at: now });
    else store.insert("bench_bg", { kind: k, key, count: 1, at: now });
  };
  if (kind === "admission") {
    upsert("admission_counter", account + ":" + Math.floor(now / 3600000));
    store.insert("bench_bg", { kind: "admission_command", key: account + ":" + now + ":" + Math.random(), count: 1, at: now });
    store.insert("bench_bg", { kind: "admission_lease", key: account + ":" + now + ":" + Math.random(), count: 1, at: now });
    return 3;
  }
  if (kind === "execution") {
    upsert("execution_job", account + ":job");
    return 1;
  }
  if (kind === "share") {
    upsert("share_throttle", "client:" + Math.floor(Math.random() * 50) + ":" + Math.floor(now / 60000));
    const old = store.all("SELECT id FROM bench_bg WHERE kind = 'share_throttle' AND at < {:cut} LIMIT 100", { cut: now - 86400000 }, { id: "" });
    old.forEach((r) => store.remove("bench_bg", r.id));
    return 1 + old.length;
  }
  throw new Refusal(400, "unknown_background");
}

// A seed batch: one multi-row INSERT into an allowed table.
function seedIn(store, table, columns, rows) {
  if (SEED_TABLES.indexOf(table) < 0) throw new Refusal(400, "table_not_seedable");
  if (!Array.isArray(columns) || !columns.length || columns.some((c) => !NAME.test(c))) throw new Refusal(400, "invalid_columns");
  if (!Array.isArray(rows) || !rows.length || rows.some((r) => !Array.isArray(r) || r.length !== columns.length)) throw new Refusal(400, "invalid_rows");
  const params = {};
  const values = rows.map((r, i) => "(" + r.map((v, j) => {
    params["p" + i + "_" + j] = (v !== null && typeof v === "object") ? JSON.stringify(v) : v;
    return "{:p" + i + "_" + j + "}";
  }).join(", ") + ")").join(", ");
  store.exec("INSERT INTO " + table + " (" + columns.join(", ") + ") VALUES " + values, params);
  return rows.length;
}

// The store on PocketBase's Dao: writes through the record API, as the
// repository's hooks do; reads with dbx queries.
function pbStore(dao) {
  const collections = {};
  const collection = (name) => {
    if (!collections[name]) collections[name] = dao.findCollectionByNameOrId(name);
    return collections[name];
  };
  const asRow = (model, shape) => {
    const out = {};
    Object.keys(shape).forEach((k) => { out[k] = model[k]; });
    return out;
  };
  return {
    one(sql, params, shape) {
      const model = new DynamicModel(shape);
      try {
        dao.db().newQuery(sql).bind(params).one(model);
      } catch (err) {
        if (String(err).indexOf("no rows") >= 0) return null;
        throw err;
      }
      return asRow(model, shape);
    },
    all(sql, params, shape) {
      const models = arrayOf(new DynamicModel(shape));
      dao.db().newQuery(sql).bind(params).all(models);
      return models.map((m) => asRow(m, shape));
    },
    exec(sql, params) {
      dao.db().newQuery(sql).bind(params).execute();
    },
    insert(table, fields) {
      const record = new Record(collection(table));
      Object.keys(fields).forEach((k) => record.set(k, fields[k]));
      dao.saveRecord(record);
      return record.id;
    },
    update(table, id, fields) {
      const record = dao.findRecordById(table, id);
      Object.keys(fields).forEach((k) => record.set(k, fields[k]));
      dao.saveRecord(record);
    },
    remove(table, id) {
      dao.deleteRecord(dao.findRecordById(table, id));
    },
  };
}

module.exports = {
  FAILPOINTS, COMMAND_TYPES, RELAY_LEASE, Refusal, Failpoint, derivedId, canonical, checkCommand,
  commandIn, leaseIn, readIn, applyIn, ackIn, projectionIn, transferIn, backgroundIn, seedIn, pbStore,
};
