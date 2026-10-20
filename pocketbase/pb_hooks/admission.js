/// <reference path="../pb_data/types.d.ts" />

// Admission state for admission/v1 (ROUNDS-00A-L01 stage 3): step 6,
// idempotency, and step 7, quotas.
//
// These functions are the only writers of admission_commands,
// admission_counters, and admission_leases
// (docs/security/server-writes.md). admission.pb.js calls them from the
// caller routes under /api/rounds/admission/, which nginx answers with
// 404, and from the sweep; other leaves call them from their own routes
// and hooks. Every call runs in one transaction, and PocketBase runs each
// write transaction on its one write connection, so both runner replicas
// see one count.
//
// Only the runner reaches admit, settle, and finish: each call carries
// the caller's bearer, for the account, and ROUNDS_ADMISSION_SECRET, which
// PocketBase and the runner share and candidate code never sees. The
// runner makes each lease's token and sends only its hash, so it can
// still finish a lease whose admit answer it lost. A lease's window is
// set when it's admitted and a settle can only shorten it, and a lease
// settles its charge once, within what was admitted.
//
// A handler requires this file itself, as with gates.js:
//
//   const admission = require(`${__hooks}/admission.js`);
//
// The decisions take a store, so tests run them on plain objects;
// pbStore() is the store over a PocketBase transaction.

const VERSION = "admission/v1";

// Proposed hourly limits; the owner ratifies them. null means no limit.
// The deployment bucket bounds what new signups can spend.
const LIMITS = {
  account: { requests: 120, wall_seconds: 1800, in_flight: 2 },
  deployment: { requests: 2000, wall_seconds: null, in_flight: 8 },
  demo: { requests: 30, wall_seconds: 300, in_flight: 1 },
};
const HOUR_S = 3600;
const COMMAND_TTL_S = 24 * HOUR_S;
// A lease outlives its admitted wall time by this much, then stops counting.
const LEASE_GRACE_S = 30;
// What a lease holds past its wall time for the work after the run: grade
// and submit ask the provider for a rubric review, which the runner cuts
// at 60 s, and save the attempt.
const HOLD_S = { grade: 90, take_home_submit: 90 };
// The secret only the runner and PocketBase hold, and requestInfo's name
// for the header that carries it (X-Rounds-Admission-Key).
const RUNNER_KEY_ENV = "ROUNDS_ADMISSION_SECRET";
const RUNNER_KEY_HEADER = "x_rounds_admission_key";
const RUNNER_KEY_MIN_CHARS = 32;
// The longest Retry-After for a full in-flight bucket: a lease usually
// ends when its request does, long before it expires.
const IN_FLIGHT_RETRY_S = 10;
// A completed result is kept for replay only up to this many characters
// of JSON; a larger one completes without one.
const RESULT_MAX_CHARS = 256 * 1024;
// Old counters and expired rows go in batches this size.
const SWEEP_BATCH = 500;

// [least, most] wall seconds each operation charges: one request plus the
// longest the execution can run. backend/tests/test_admission_state.py
// keeps these in step with the runner's timeouts. Evaluate and grade are
// admitted on one case or checkpoint, up to their most (32 cases of 10 s,
// 8 checkpoints of 45 s), and settle the exact charge once the runner has
// loaded the definitions.
const OPERATIONS = {
  run: [3, 3],
  evaluate: [0, 32 * 10],
  run_project: [10, 10],
  grade: [0, 8 * 45],
  take_home_run: [60, 60],
  take_home_submit: [120, 120],
  pdf_render: [25, 25],
};
const OUTCOMES = ["completed", "denied", "infrastructure", "error"];
const MODES = ["enforce", "observe"];
// ROUNDS_GATE_ENFORCE_QUOTA: enforce denies, observe runs uncounted past a
// limit, and off counts nothing.
const QUOTA_MODES = ["enforce", "observe", "off"];
const COMMAND_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const FINGERPRINT = /^[0-9a-f]{64}$/;
const LEASE_TOKEN = /^[A-Za-z0-9]{43}$/;
// Fields only a superuser, a migration, or a server hook may set.
const DEMO_FIELDS = ["is_demo", "demo_run_used", "demo_evaluate_used"];

// ---------------------------------------------------------------------------
// Tier
// ---------------------------------------------------------------------------

// TODO(ROUNDS-00B-L07): #177 repoints the tier at account_system_state;
// backend/app/admission.py's tier_of() moves with it.
function tierOf(record) {
  return record && record.getBool("is_demo") === true ? "demo" : "standard";
}

// ---------------------------------------------------------------------------
// Input checks, before any transaction
// ---------------------------------------------------------------------------

function isInt(value) {
  return typeof value === "number" && isFinite(value) && Math.floor(value) === value;
}

function only(data, allowed) {
  if (!data || typeof data !== "object" || Array.isArray(data)) return false;
  return Object.keys(data).every((key) => allowed.indexOf(key) >= 0);
}

function wallIn(operation, wall) {
  const range = OPERATIONS[operation];
  return isInt(wall) && wall >= range[0] && wall <= range[1];
}

// Each returns the checked input, or null when the request is malformed.
function checkAdmit(data) {
  const keys = ["operation", "command_id", "fingerprint", "wall_seconds", "max_wall_seconds", "idempotency", "quota", "lease_hash"];
  if (!only(data, keys)) return null;
  const operation = data.operation;
  if (typeof operation !== "string" || !Object.prototype.hasOwnProperty.call(OPERATIONS, operation)) return null;
  if (!wallIn(operation, data.wall_seconds)) return null;
  const most = data.max_wall_seconds === undefined ? data.wall_seconds : data.max_wall_seconds;
  if (!wallIn(operation, most) || most < data.wall_seconds) return null;
  const commandId = data.command_id === undefined || data.command_id === null ? null : data.command_id;
  if (commandId !== null && (typeof commandId !== "string" || !COMMAND_ID.test(commandId))) return null;
  const fingerprint = data.fingerprint === undefined || data.fingerprint === null ? null : data.fingerprint;
  if ((commandId === null) !== (fingerprint === null)) return null;
  if (fingerprint !== null && (typeof fingerprint !== "string" || !FINGERPRINT.test(fingerprint))) return null;
  const mode = data.idempotency === undefined ? "enforce" : data.idempotency;
  if (MODES.indexOf(mode) < 0) return null;
  const quota = data.quota === undefined ? "enforce" : data.quota;
  if (QUOTA_MODES.indexOf(quota) < 0) return null;
  if (typeof data.lease_hash !== "string" || !FINGERPRINT.test(data.lease_hash)) return null;
  return {
    operation,
    command_id: commandId,
    fingerprint,
    wall_seconds: data.wall_seconds,
    max_wall_seconds: most,
    idempotency: mode,
    quota,
    lease_hash: data.lease_hash,
  };
}

function checkSettle(data) {
  if (!only(data, ["lease", "wall_seconds"])) return null;
  if (typeof data.lease !== "string" || !LEASE_TOKEN.test(data.lease)) return null;
  if (!isInt(data.wall_seconds) || data.wall_seconds < 0) return null;
  return { lease: data.lease, wall_seconds: data.wall_seconds };
}

function checkFinish(data) {
  if (!only(data, ["lease", "outcome", "result"])) return null;
  if (typeof data.lease !== "string" || !LEASE_TOKEN.test(data.lease)) return null;
  if (OUTCOMES.indexOf(data.outcome) < 0) return null;
  const result = data.result === undefined ? null : data.result;
  if (result !== null && data.outcome !== "completed") return null;
  return { lease: data.lease, outcome: data.outcome, result };
}

// ---------------------------------------------------------------------------
// Decisions
// ---------------------------------------------------------------------------

function hourOf(now) {
  return Math.floor(now / HOUR_S);
}

function untilNextHour(now) {
  return (hourOf(now) + 1) * HOUR_S - now;
}

// The buckets a request from `account` counts in, with the lease filter
// for each one's in-flight count.
function bucketsFor(account) {
  const buckets = [
    { bucket: "account", account: account.id, leases: { account: account.id } },
    { bucket: "deployment", account: "", leases: {} },
  ];
  if (account.demo) buckets.push({ bucket: "demo", account: "", leases: { demo: true } });
  return buckets;
}

// Step 7: whether one more request charging `wall` fits every bucket.
function quotaFor(store, account, wall, now) {
  const hour = hourOf(now);
  const over = [];
  bucketsFor(account).forEach((b) => {
    const limit = LIMITS[b.bucket];
    const used = store.counter(b.bucket, b.account, hour) || { requests: 0, wall_seconds: 0 };
    if (limit.requests !== null && used.requests + 1 > limit.requests) {
      over.push({ bucket: b.bucket, retry_after: untilNextHour(now) });
    }
    if (limit.wall_seconds !== null && used.wall_seconds + wall > limit.wall_seconds) {
      over.push({ bucket: b.bucket, retry_after: untilNextHour(now) });
    }
    if (limit.in_flight !== null) {
      const live = store.liveLeases(b.leases, now);
      if (live.count + 1 > limit.in_flight) {
        const wait = live.soonest === null ? 1 : live.soonest - now;
        over.push({ bucket: b.bucket, retry_after: Math.max(1, Math.min(IN_FLIGHT_RETRY_S, wait)) });
      }
    }
  });
  if (over.length === 0) return { quota: "ok", retry_after: 0 };
  const demo = over.some((o) => o.bucket === "demo");
  return {
    quota: demo ? "demo_limit" : "exceeded",
    retry_after: Math.max.apply(null, over.map((o) => o.retry_after)),
  };
}

function charge(store, buckets, hour, requests, wall) {
  buckets.forEach((b) => store.addToCounter(b.bucket, b.account, hour, requests, wall));
}

function leaseBuckets(lease) {
  return bucketsFor({ id: lease.account, demo: lease.demo });
}

// Step 6 for a key the account already used.
function verdictFor(store, existing, input, now) {
  if (existing.fingerprint !== input.fingerprint || existing.operation !== input.operation) return "mismatch";
  if (existing.state === "completed") return "replay";
  if (existing.state === "in_flight" && store.liveLeaseForCommand(existing.id, now)) return "in_flight";
  // Retryable, failed_infrastructure, or in flight with its lease gone.
  return "retry";
}

// How long a duplicate of a running command should wait before trying
// again: until its lease ends, at most IN_FLIGHT_RETRY_S.
function inFlightWait(store, command, now) {
  const until = store.liveLeaseExpiry(command.id, now);
  return until === null ? 1 : Math.max(1, Math.min(IN_FLIGHT_RETRY_S, until - now));
}

// When a lease that may still run `wall` seconds from `now` ends: the
// wall time, what the operation holds after the run, and the grace.
function windowEnd(operation, wall, now) {
  return now + wall + (HOLD_S[operation] || 0) + LEASE_GRACE_S;
}

// Steps 6 and 7 together. Writes the command row, the charge, and the
// lease, or nothing.
//
// Idempotency doesn't depend on the quota mode: whenever a request runs
// with a key it hasn't used, its command row is written. A request that
// idempotency refuses writes no command row, though in observe mode it
// still runs and is leased. Past a limit, enforce writes nothing; observe
// runs the request with a lease that doesn't count and no charge, so the
// hook never counts past a limit. Off counts nothing.
function admit(store, account, input, now) {
  const out = { v: VERSION, idempotency: "none", quota: "ok", retry_after: 0, leased: false, result: null };
  let existing = null;
  if (input.command_id !== null) {
    existing = store.findCommand(account.id, input.command_id);
    if (existing !== null && existing.expires_at <= now) {
      store.deleteCommand(existing);
      existing = null;
    }
    out.idempotency = existing === null ? "new" : verdictFor(store, existing, input, now);
  }
  const refused = out.idempotency === "replay" || out.idempotency === "mismatch" || out.idempotency === "in_flight";
  if (refused && input.idempotency === "enforce") {
    out.quota = "skipped";
    if (out.idempotency === "replay") out.result = existing.result;
    if (out.idempotency === "in_flight") out.retry_after = inFlightWait(store, existing, now);
    return out;
  }
  if (store.findLease(input.lease_hash) !== null) {
    return { invalid: true };
  }

  let counted = true;
  if (input.quota === "off") {
    out.quota = "skipped";
    counted = false;
  } else {
    const verdict = quotaFor(store, account, input.wall_seconds, now);
    out.quota = verdict.quota;
    out.retry_after = verdict.retry_after;
    if (verdict.quota !== "ok") {
      if (input.quota === "enforce") return out;
      counted = false;
    }
  }

  const hour = hourOf(now);
  let command = null;
  if (input.command_id !== null && !refused) {
    command = existing || { id: "", account: account.id, command_id: input.command_id };
    command.operation = input.operation;
    command.fingerprint = input.fingerprint;
    command.state = "in_flight";
    command.wall_seconds = input.wall_seconds;
    command.result = null;
    command.expires_at = now + COMMAND_TTL_S;
    command = store.saveCommand(command);
    // A stale lease of an earlier attempt stops counting now.
    store.deleteLeasesForCommand(command.id);
  }
  if (counted) charge(store, bucketsFor(account), hour, 1, input.wall_seconds);
  store.saveLease({
    id: "",
    account: account.id,
    command: command === null ? "" : command.id,
    operation: input.operation,
    demo: account.demo,
    hour,
    wall_seconds: input.wall_seconds,
    max_wall_seconds: input.max_wall_seconds,
    settled: false,
    counted,
    token_hash: input.lease_hash,
    expires_at: windowEnd(input.operation, input.max_wall_seconds, now),
  });
  out.leased = true;
  return out;
}

function leaseOf(store, account, token) {
  const lease = store.findLease(store.hash(token));
  return lease !== null && lease.account === account.id ? lease : null;
}

// Step 7 again for a settle that raises a lease's charge: whether the
// added wall seconds fit the hour the lease was charged in.
function wallFits(store, lease, extra, now) {
  const over = [];
  leaseBuckets(lease).forEach((b) => {
    const limit = LIMITS[b.bucket];
    const used = store.counter(b.bucket, b.account, lease.hour) || { requests: 0, wall_seconds: 0 };
    if (limit.wall_seconds !== null && used.wall_seconds + extra > limit.wall_seconds) over.push(b.bucket);
  });
  if (over.length === 0) return { quota: "ok", retry_after: 0 };
  return { quota: over.indexOf("demo") >= 0 ? "demo_limit" : "exceeded", retry_after: untilNextHour(now) };
}

// Evaluate and grade: the exact charge, once the definitions are loaded.
// A lease settles once, to at most what it was admitted for, and a raise
// has to fit the hour's limits. Its window ends no later than the settled
// wall time allows from now, and never later than it was admitted for.
function settle(store, account, input, now) {
  const lease = leaseOf(store, account, input.lease);
  if (lease === null || lease.expires_at <= now) return { status: 404, body: { v: VERSION, error: "not_found" } };
  if (lease.settled) return { status: 409, body: { v: VERSION, error: "already_settled" } };
  if (input.wall_seconds > lease.max_wall_seconds) return { status: 400, body: { v: VERSION, error: "invalid_request" } };
  const delta = input.wall_seconds - lease.wall_seconds;
  if (lease.counted && delta > 0) {
    const verdict = wallFits(store, lease, delta, now);
    if (verdict.quota !== "ok") {
      return { status: 429, body: { v: VERSION, quota: verdict.quota, retry_after: verdict.retry_after } };
    }
  }
  if (lease.counted && delta !== 0) charge(store, leaseBuckets(lease), lease.hour, 0, delta);
  lease.wall_seconds = input.wall_seconds;
  lease.settled = true;
  lease.expires_at = Math.min(lease.expires_at, windowEnd(lease.operation, input.wall_seconds, now));
  store.saveLease(lease);
  if (lease.command) {
    const command = store.getCommand(lease.command);
    if (command !== null && command.state === "in_flight") {
      command.wall_seconds = input.wall_seconds;
      store.saveCommand(command);
    }
  }
  return { status: 200, body: { v: VERSION, wall_seconds: input.wall_seconds } };
}

function storable(result) {
  if (!result || typeof result !== "object" || Array.isArray(result)) return null;
  if (!only(result, ["status", "body"]) || !isInt(result.status) || result.status < 200 || result.status > 299) return null;
  if (!Object.prototype.hasOwnProperty.call(result, "body")) return null;
  const text = JSON.stringify(result);
  return typeof text === "string" && text.length <= RESULT_MAX_CHARS ? { status: result.status, body: result.body } : null;
}

// The end of an admitted request. A completed one keeps its result for
// replay. A step 8 or 9 denial ("denied") leaves the command retryable,
// and a typed infrastructure failure ("infrastructure") or any other
// failure ("error") leaves it failed_infrastructure; either way a retry
// with the same key runs admission again. Only "denied" and
// "infrastructure" refund, only wall seconds, and only on a lease that
// counted. The lease goes.
function finish(store, account, input, now) {
  const lease = leaseOf(store, account, input.lease);
  if (lease === null) return { status: 404, body: { v: VERSION, error: "not_found" } };
  const refundable = input.outcome === "denied" || input.outcome === "infrastructure";
  const refund = lease.counted && refundable ? lease.wall_seconds : 0;
  if (refund > 0) charge(store, leaseBuckets(lease), lease.hour, 0, -refund);
  if (lease.command) {
    const command = store.getCommand(lease.command);
    if (command !== null && command.state === "in_flight") {
      if (input.outcome === "completed") {
        command.state = "completed";
        command.result = storable(input.result);
      } else {
        command.state = input.outcome === "denied" ? "retryable" : "failed_infrastructure";
        command.result = null;
      }
      command.wall_seconds = Math.max(0, command.wall_seconds - refund);
      store.saveCommand(command);
    }
  }
  store.deleteLease(lease);
  return { status: 200, body: { v: VERSION, refunded_wall_seconds: refund } };
}

// The account's use this hour, for the dependency check.
function usage(store, account, now) {
  const hour = hourOf(now);
  const used = store.counter("account", account.id, hour) || { requests: 0, wall_seconds: 0 };
  const live = store.liveLeases({ account: account.id }, now);
  return {
    v: VERSION,
    hour,
    tier: account.demo ? "demo" : "standard",
    requests: used.requests,
    wall_seconds: used.wall_seconds,
    in_flight: live.count,
    limits: LIMITS.account,
  };
}

// Forgets commands past their 24 hours, marks in-flight commands whose
// lease is gone failed_infrastructure, and drops expired leases and
// counters from before the last 24 hours. Nothing is refunded.
function sweep(store, now) {
  const repaired = store.repairInFlight(now, SWEEP_BATCH);
  store.deleteExpired(now, hourOf(now) - 24, SWEEP_BATCH);
  return { repaired };
}

// ---------------------------------------------------------------------------
// The PocketBase store
// ---------------------------------------------------------------------------

const COMMANDS = "admission_commands";
const COUNTERS = "admission_counters";
const LEASES = "admission_leases";

function pbStore(dao) {
  const collections = {};
  function collection(name) {
    if (!collections[name]) collections[name] = dao.findCollectionByNameOrId(name);
    return collections[name];
  }
  function first(name, filter, params) {
    const rows = dao.findRecordsByFilter(name, filter, "", 1, 0, params);
    return rows.length > 0 ? rows[0] : null;
  }
  function json(record, field) {
    const raw = record.getString(field);
    return raw ? JSON.parse(raw) : null;
  }
  function command(record) {
    if (record === null) return null;
    return {
      id: record.id,
      account: record.getString("account"),
      command_id: record.getString("command_id"),
      operation: record.getString("operation"),
      fingerprint: record.getString("fingerprint"),
      state: record.getString("state"),
      wall_seconds: record.getInt("wall_seconds"),
      result: json(record, "result"),
      expires_at: record.getInt("expires_at"),
      _record: record,
    };
  }
  function lease(record) {
    if (record === null) return null;
    return {
      id: record.id,
      account: record.getString("account"),
      command: record.getString("command"),
      operation: record.getString("operation"),
      demo: record.getBool("demo"),
      hour: record.getInt("hour"),
      wall_seconds: record.getInt("wall_seconds"),
      max_wall_seconds: record.getInt("max_wall_seconds"),
      settled: record.getBool("settled"),
      counted: record.getBool("counted"),
      token_hash: record.getString("token_hash"),
      expires_at: record.getInt("expires_at"),
      _record: record,
    };
  }
  function save(name, row, fields) {
    const record = row._record || new Record(collection(name));
    fields.forEach((field) => record.set(field, row[field]));
    dao.saveRecord(record);
    row.id = record.id;
    row._record = record;
    return row;
  }
  function liveFilter(leases) {
    const parts = ["expires_at > {:now}", "counted = true"];
    if (leases.account !== undefined) parts.push("account = {:account}");
    if (leases.demo !== undefined) parts.push("demo = true");
    return parts.join(" && ");
  }
  // PocketBase 0.22 binds an empty string parameter as two quote marks,
  // so the shared buckets' empty account is written into the filter.
  function counterRecord(bucket, account, hour) {
    const filter = account === "" ? "bucket = {:bucket} && account = '' && hour = {:hour}" : "bucket = {:bucket} && account = {:account} && hour = {:hour}";
    return first(COUNTERS, filter, { bucket, account, hour });
  }

  return {
    hash: (token) => $security.sha256(token),
    findCommand: (account, commandId) =>
      command(first(COMMANDS, "account = {:account} && command_id = {:id}", { account, id: commandId })),
    getCommand: (id) => command(first(COMMANDS, "id = {:id}", { id })),
    saveCommand: (row) =>
      save(COMMANDS, row, ["account", "command_id", "operation", "fingerprint", "state", "wall_seconds", "result", "expires_at"]),
    deleteCommand: (row) => dao.deleteRecord(row._record),
    findLease: (tokenHash) => lease(first(LEASES, "token_hash = {:hash}", { hash: tokenHash })),
    saveLease: (row) =>
      save(LEASES, row, [
        "account", "command", "operation", "demo", "hour", "wall_seconds", "max_wall_seconds", "settled", "counted",
        "token_hash", "expires_at",
      ]),
    deleteLease: (row) => dao.deleteRecord(row._record),
    deleteLeasesForCommand: (commandId) => {
      dao.findRecordsByFilter(LEASES, "command = {:id}", "", 0, 0, { id: commandId }).forEach((r) => dao.deleteRecord(r));
    },
    liveLeaseForCommand: (commandId, now) =>
      first(LEASES, "command = {:id} && expires_at > {:now}", { id: commandId, now }) !== null,
    liveLeaseExpiry: (commandId, now) => {
      const rows = dao.findRecordsByFilter(LEASES, "command = {:id} && expires_at > {:now}", "-expires_at", 1, 0, { id: commandId, now });
      return rows.length > 0 ? rows[0].getInt("expires_at") : null;
    },
    liveLeases: (leases, now) => {
      const rows = dao.findRecordsByFilter(LEASES, liveFilter(leases), "expires_at", 0, 0, {
        now,
        account: leases.account === undefined ? "" : leases.account,
      });
      return { count: rows.length, soonest: rows.length > 0 ? rows[0].getInt("expires_at") : null };
    },
    counter: (bucket, account, hour) => {
      const record = counterRecord(bucket, account, hour);
      return record === null ? null : { requests: record.getInt("requests"), wall_seconds: record.getInt("wall_seconds") };
    },
    addToCounter: (bucket, account, hour, requests, wall) => {
      let record = counterRecord(bucket, account, hour);
      if (record === null) {
        record = new Record(collection(COUNTERS));
        record.set("bucket", bucket);
        record.set("account", account);
        record.set("hour", hour);
        record.set("requests", 0);
        record.set("wall_seconds", 0);
      }
      record.set("requests", Math.max(0, record.getInt("requests") + requests));
      record.set("wall_seconds", Math.max(0, record.getInt("wall_seconds") + wall));
      dao.saveRecord(record);
    },
    repairInFlight: (now, limit) => {
      let repaired = 0;
      dao.findRecordsByFilter(COMMANDS, "state = 'in_flight'", "", limit, 0).forEach((record) => {
        if (first(LEASES, "command = {:id} && expires_at > {:now}", { id: record.id, now }) !== null) return;
        record.set("state", "failed_infrastructure");
        record.set("result", null);
        dao.saveRecord(record);
        repaired += 1;
      });
      return repaired;
    },
    deleteExpired: (now, oldestHour, limit) => {
      // Leases first: a command outlives every lease it ever had.
      [
        [LEASES, "expires_at <= {:now}"],
        [COMMANDS, "expires_at <= {:now}"],
        [COUNTERS, "hour < {:hour}"],
      ].forEach((entry) => {
        dao.findRecordsByFilter(entry[0], entry[1], "", limit, 0, { now, hour: oldestHour }).forEach((r) => dao.deleteRecord(r));
      });
    },
  };
}

// ---------------------------------------------------------------------------
// Routes and hooks (admission.pb.js)
// ---------------------------------------------------------------------------

function nowSeconds() {
  return Math.floor(Date.now() / 1000);
}

const CHECKS = { admit: checkAdmit, settle: checkSettle, finish: checkFinish };

function sameSecret(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i += 1) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// Why a write route refuses the caller, or null when the runner's key
// came with it: 503 while PocketBase has no key set, 403 for any other
// caller, which is everything candidate code could send.
function runnerKeyError(headers, secret) {
  if (typeof secret !== "string" || secret.length < RUNNER_KEY_MIN_CHARS) {
    return { status: 503, body: { v: VERSION, error: "unconfigured" } };
  }
  const given = headers ? headers[RUNNER_KEY_HEADER] : undefined;
  if (typeof given !== "string" || !sameSecret(given, secret)) {
    return { status: 403, body: { v: VERSION, error: "forbidden" } };
  }
  return null;
}

// One caller route. The account and its tier come from the bearer, never
// from the body, and the writes need the runner's key as well.
function handle(c, action) {
  const info = $apis.requestInfo(c);
  const record = info.authRecord;
  if (!record) throw new UnauthorizedError("Sign in to continue.");
  const account = { id: record.id, demo: tierOf(record) === "demo" };
  const now = nowSeconds();
  if (action === "usage") return c.json(200, usage(pbStore($app.dao()), account, now));
  const refused = runnerKeyError(info.headers, $os.getenv(RUNNER_KEY_ENV));
  if (refused !== null) return c.json(refused.status, refused.body);
  const input = CHECKS[action](info.data);
  if (input === null) return c.json(400, { v: VERSION, error: "invalid_request" });
  let out = null;
  $app.dao().runInTransaction((txDao) => {
    const store = pbStore(txDao);
    if (action === "admit") {
      const body = admit(store, account, input, now);
      out = body.invalid ? { status: 400, body: { v: VERSION, error: "invalid_request" } } : { status: 200, body };
    } else if (action === "settle") out = settle(store, account, input, now);
    else out = finish(store, account, input, now);
  });
  return c.json(out.status, out.body);
}

function sweepNow() {
  let out = null;
  $app.dao().runInTransaction((txDao) => {
    out = sweep(pbStore(txDao), nowSeconds());
  });
  console.log(JSON.stringify({ v: "obs/v1", event: "admission_sweep", service: "pocketbase", repaired: out.repaired }));
}

function isSuperuser(httpContext) {
  return Boolean(httpContext && $apis.requestInfo(httpContext).admin);
}

function changedDemoFields(record, original) {
  return DEMO_FIELDS.filter((name) => record.getBool(name) !== (original ? original.getBool(name) : false));
}

const DEMO_FIELDS_LOCKED = "These account fields can't be changed.";

function guardDemoCreate(e) {
  if (isSuperuser(e.httpContext)) return;
  if (changedDemoFields(e.record, null).length > 0) throw new BadRequestError(DEMO_FIELDS_LOCKED);
}

function guardDemoUpdate(e) {
  if (isSuperuser(e.httpContext)) return;
  if (changedDemoFields(e.record, e.record.originalCopy()).length > 0) throw new BadRequestError(DEMO_FIELDS_LOCKED);
}

// An OAuth2 sign-up's createData skips the create request hook, so its
// keys are checked here.
function guardDemoOAuth2(e) {
  if (!e.isNewRecord) return;
  const data = $apis.requestInfo(e.httpContext).data || {};
  const createData = data.createData;
  if (createData && typeof createData === "object" && DEMO_FIELDS.some((name) => name in createData)) {
    throw new BadRequestError(DEMO_FIELDS_LOCKED);
  }
}

module.exports = {
  VERSION,
  LIMITS,
  HOUR_S,
  COMMAND_TTL_S,
  LEASE_GRACE_S,
  HOLD_S,
  IN_FLIGHT_RETRY_S,
  RESULT_MAX_CHARS,
  OPERATIONS,
  DEMO_FIELDS,
  RUNNER_KEY_ENV,
  RUNNER_KEY_HEADER,
  RUNNER_KEY_MIN_CHARS,
  tierOf,
  runnerKeyError,
  checkAdmit,
  checkSettle,
  checkFinish,
  hourOf,
  quotaFor,
  admit,
  settle,
  finish,
  usage,
  sweep,
  pbStore,
  handle,
  sweepNow,
  changedDemoFields,
  guardDemoCreate,
  guardDemoUpdate,
  guardDemoOAuth2,
};
