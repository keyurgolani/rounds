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
// A command that enqueued an execution job (ROUNDS-00A-L03 PR 2; the
// `job` link execution.js sets) answers from its job instead of from its
// own state: a duplicate gets the job, never a second charge, and a
// same-key retry of a job lost to infrastructure pays its wall seconds
// and holds a lease but counts no request. Its lease stays after its
// request as the job's charge: jobStarted makes it final when the
// candidate starts, and jobEnded gives the wall seconds back when the job
// ends first. It lives as long as its job, which the execution purge
// removes it with.
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
// at 60 s, and save the attempt, in their request until their jobs take
// over (ROUNDS-00A-L03 PR 3). A job's review is its own operation,
// `review`, which runs nothing and holds its lease for the 60 s call.
const HOLD_S = { grade: 90, take_home_submit: 90, review: 60 };
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
  // ROUNDS-00A-L04: one Legacy Artifact Snapshot, the materializer call
  // bounded at 10 s (legacy_snapshots.js).
  snapshot_create: [10, 10],
  // ROUNDS-00A-L03 PR 3: one rubric review of a grading job's result. It
  // runs no candidate code, so it charges one request and no wall seconds,
  // and execution.js reviewStart admits it once per result.
  review: [0, 0],
};
// Operations only another hook admits, in the transaction that decides
// them, never the admit route: a review is admitted by execution.js
// reviewStart as its result's rubric is marked requested.
const HOOK_ONLY_OPERATIONS = ["review"];
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

// The one place PocketBase decides an account's tier, and so whether it's
// a demo account: admission and every check in demo.js ask it.
// TODO(ROUNDS-00B-L07): stage 2 repoints it at account_system_state, and
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
  if (HOOK_ONLY_OPERATIONS.indexOf(operation) >= 0) return null;
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

// Step 7: whether one more request charging `wall` fits every bucket. A
// job's same-key retry counts no request (`requests` 0), so the request
// limit doesn't gate it; its wall seconds and its lease still count.
function quotaFor(store, account, wall, now, requests) {
  const counts = requests === undefined ? 1 : requests;
  const hour = hourOf(now);
  const over = [];
  bucketsFor(account).forEach((b) => {
    const limit = LIMITS[b.bucket];
    const used = store.counter(b.bucket, b.account, hour) || { requests: 0, wall_seconds: 0 };
    if (limit.requests !== null && counts > 0 && used.requests + counts > limit.requests) {
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

// The execution job store's rules (execution.js), read when a command
// links a job.
function jobRules() {
  return require(`${__hooks}/execution.js`);
}

function jobHasEnded(job) {
  return Object.prototype.hasOwnProperty.call(jobRules().TERMINAL, job.state);
}

// Step 6 for a key the account already used. A command that enqueued a
// job answers from the job: "job" while it waits or runs and once it has
// ended, "retry_job" when a same-key retry would run it again, and
// "retry" when the job is gone. A retry already admitted holds the
// command in flight with a live lease until its enqueue queues the job
// again, so a second retry in that window is "in_flight" and pays
// nothing.
function verdictFor(store, existing, input, now) {
  if (existing.fingerprint !== input.fingerprint || existing.operation !== input.operation) return "mismatch";
  if (existing.job) {
    const job = store.jobOf(existing.job);
    if (job === null) return "retry";
    if (!jobRules().retryable(job)) return "job";
    if (existing.state === "in_flight" && store.liveLeaseForCommand(existing.id, now)) return "in_flight";
    return "retry_job";
  }
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
  const out = { v: VERSION, idempotency: "none", quota: "ok", retry_after: 0, leased: false, result: null, job: null };
  let existing = null;
  if (input.command_id !== null) {
    existing = store.findCommand(account.id, input.command_id);
    // A command that enqueued a job lives as long as the job.
    if (existing !== null && existing.expires_at <= now && !existing.job) {
      store.deleteCommand(existing);
      existing = null;
    }
    out.idempotency = existing === null ? "new" : verdictFor(store, existing, input, now);
  }
  const refused = out.idempotency === "replay" || out.idempotency === "mismatch" || out.idempotency === "in_flight" ||
    out.idempotency === "job";
  // A duplicate of a job runs nothing new, so it's never charged or
  // leased, whatever the mode.
  if (refused && (input.idempotency === "enforce" || out.idempotency === "job")) {
    out.quota = "skipped";
    if (out.idempotency === "replay") out.result = existing.result;
    if (out.idempotency === "in_flight") out.retry_after = inFlightWait(store, existing, now);
    if (out.idempotency === "job") out.job = existing.job;
    return out;
  }
  if (store.findLease(input.lease_hash) !== null) {
    return { invalid: true };
  }

  // A job's same-key retry charges wall seconds and a lease, no request.
  const requests = out.idempotency === "retry_job" ? 0 : 1;
  let counted = true;
  if (input.quota === "off") {
    out.quota = "skipped";
    counted = false;
  } else {
    const verdict = quotaFor(store, account, input.wall_seconds, now, requests);
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
  if (counted) charge(store, bucketsFor(account), hour, requests, input.wall_seconds);
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
  const linked = lease.command ? store.getCommand(lease.command) : null;
  if (linked !== null && linked.job) return finishJobRequest(store, linked);
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

// The end of a request whose command enqueued a job. While the job waits
// or runs, the lease stays as the job's charge. Once the job has ended,
// this request ran nothing new, so its wall seconds come back. The
// store's own rows decide, never what the runner saw: a lost enqueue
// answer neither refunds a job that runs nor keeps a charge for one that
// doesn't.
function finishJobRequest(store, command) {
  const job = store.jobOf(command.job);
  if (job !== null && !jobHasEnded(job)) return { status: 200, body: { v: VERSION, refunded_wall_seconds: 0 } };
  const refund = endJobCharge(store, command, job === null ? "retryable" : commandStateFor(job.outcome_class));
  return { status: 200, body: { v: VERSION, refunded_wall_seconds: refund } };
}

// How a job-backed command ends: failed_infrastructure when its job was
// lost to infrastructure, completed otherwise.
function commandStateFor(outcomeClass) {
  return jobRules().RETRYABLE.indexOf(outcomeClass) >= 0 ? "failed_infrastructure" : "completed";
}

// Gives back the wall seconds of every charge still waiting on the
// command's job, and ends the command in `state`. Answers the seconds.
function endJobCharge(store, command, state) {
  let refund = 0;
  store.leasesForCommand(command.id).forEach((lease) => {
    if (lease.counted && lease.wall_seconds > 0) {
      charge(store, leaseBuckets(lease), lease.hour, 0, -lease.wall_seconds);
      refund += lease.wall_seconds;
    }
    store.deleteLease(lease);
  });
  command.state = state;
  command.result = null;
  command.wall_seconds = Math.max(0, command.wall_seconds - refund);
  store.saveCommand(command);
  return refund;
}

// execution.js's heartbeat, as the job's candidate starts: the charge
// waiting on the job is final, so its lease goes. Nothing for a job its
// command doesn't name.
function jobStarted(store, accountId, commandId, jobId) {
  const command = store.findCommand(accountId, commandId);
  if (command === null || command.job !== jobId) return;
  store.deleteLeasesForCommand(command.id);
}

// execution.js's endJob, as the job ends: a charge still waiting on it
// never reached a started candidate, so its wall seconds come back, and
// the command ends the way the job did.
function jobEnded(store, accountId, commandId, jobId, outcomeClass) {
  const command = store.findCommand(accountId, commandId);
  if (command === null || command.job !== jobId) return 0;
  return endJobCharge(store, command, commandStateFor(outcomeClass));
}

// For a leaf whose own hook finishes its command in the same transaction
// as its write (ROUNDS-00A-L04's legacy snapshots). The account's
// completed command under this key, checked as admit() checks one:
//   { result }          the same operation and request, to replay
//   { mismatch: true }  the key completed another operation or request
//   null                nothing completed under the key, or nothing kept
function completedResult(store, account, commandId, now, operation, fingerprint) {
  if (typeof commandId !== "string" || !COMMAND_ID.test(commandId)) return null;
  const existing = store.findCommand(account.id, commandId);
  if (existing === null || existing.state !== "completed" || existing.expires_at <= now) return null;
  if (existing.operation !== operation || existing.fingerprint !== fingerprint) return { mismatch: true };
  return existing.result === null || existing.result === undefined ? null : { result: existing.result };
}

// Completes the account's in-flight command for `operation` with a result
// to replay, inside the caller's transaction, so the write and the result
// commit together. True when a row was completed. Without a row (the
// runner sent no key, or idempotency is off) nothing is written; the
// runner's own finish later leaves an already completed row as it is.
function completeCommand(store, account, commandId, operation, result) {
  if (typeof commandId !== "string" || !COMMAND_ID.test(commandId)) return false;
  const existing = store.findCommand(account.id, commandId);
  if (existing === null || existing.operation !== operation || existing.state !== "in_flight") return false;
  const kept = storable(result);
  if (kept === null) return false;
  existing.state = "completed";
  existing.result = kept;
  store.saveCommand(existing);
  return true;
}

// For a leaf whose hooks record its command before the work and complete it
// in the same transaction as its write, with no lease: the write's
// transaction is the guard (ROUNDS-00B-L04's share commands). The
// account's command under this key, recorded as in flight when there's none
// or only an expired one:
//   { verdict: "new", command }     recorded now
//   { verdict: "retry", command }   in flight, retryable, or failed; the work runs again
//   { verdict: "replay", result }   completed for the same operation and request
//   { verdict: "mismatch" }         the key belongs to another operation or request
// Any field of the caller's own on the row (command._record) is the caller's
// to set, as execution.js sets `job`.
function beginCommand(store, account, commandId, operation, fingerprint, now) {
  let existing = store.findCommand(account.id, commandId);
  if (existing !== null && existing.expires_at <= now) {
    store.deleteCommand(existing);
    existing = null;
  }
  if (existing === null) {
    const command = store.saveCommand({
      id: "",
      account: account.id,
      command_id: commandId,
      operation,
      fingerprint,
      state: "in_flight",
      wall_seconds: 0,
      result: null,
      expires_at: now + COMMAND_TTL_S,
    });
    return { verdict: "new", command };
  }
  if (existing.operation !== operation || existing.fingerprint !== fingerprint) return { verdict: "mismatch" };
  if (existing.state === "completed") return { verdict: "replay", result: existing.result };
  return { verdict: "retry", command: existing };
}

// Completes a command beginCommand returned, inside the caller's
// transaction, with the result a replay answers. False, and nothing
// written, for a result that can't be kept.
function completeBegunCommand(store, command, result) {
  const kept = storable(result);
  if (kept === null) return false;
  command.state = "completed";
  command.result = kept;
  store.saveCommand(command);
  return true;
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
// counters from before the last 24 hours. Nothing is refunded. A command
// that enqueued a job, and its job's charge, are left to the job.
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
      // The execution job it enqueued (ROUNDS-00A-L03), or "".
      job: record.getString("job"),
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
    leasesForCommand: (commandId) =>
      dao.findRecordsByFilter(LEASES, "command = {:id}", "", 0, 0, { id: commandId }).map(lease),
    // The job a command enqueued, as step 6 and finish read it, or null.
    jobOf: (jobId) => {
      const record = first("execution_jobs", "id = {:id}", { id: jobId });
      if (record === null) return null;
      return {
        id: record.id,
        state: record.getString("state"),
        outcome_class: record.getString("outcome_class"),
        attempts: record.getInt("attempts"),
        attempts_started: record.getInt("attempts_started"),
      };
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
    // A command that enqueued a job ends with the job, never here.
    repairInFlight: (now, limit) => {
      let repaired = 0;
      dao.findRecordsByFilter(COMMANDS, "state = 'in_flight' && job = ''", "", limit, 0).forEach((record) => {
        if (first(LEASES, "command = {:id} && expires_at > {:now}", { id: record.id, now }) !== null) return;
        record.set("state", "failed_infrastructure");
        record.set("result", null);
        dao.saveRecord(record);
        repaired += 1;
      });
      return repaired;
    },
    deleteExpired: (now, oldestHour, limit) => {
      // Leases first: a command outlives every lease it ever had. A
      // command that enqueued a job, and the lease that is its job's
      // charge, stay until the job ends or the execution purge removes
      // them (ROUNDS-00A-L03).
      const expired = arrayOf(new DynamicModel({ id: "" }));
      dao.db()
        .select("l.id")
        .from(LEASES + " l")
        .where($dbx.exp(
          "l.expires_at <= {:now} AND NOT EXISTS (SELECT 1 FROM " + COMMANDS +
            " c WHERE c.id = l.command AND COALESCE(c.job, '') != '')",
          { now },
        ))
        .limit(limit)
        .all(expired);
      expired.forEach((row) => dao.deleteRecord(dao.findRecordById(LEASES, row.id)));
      [
        [COMMANDS, "expires_at <= {:now} && job = ''"],
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
  HOOK_ONLY_OPERATIONS,
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
  jobStarted,
  jobEnded,
  completedResult,
  completeCommand,
  beginCommand,
  completeBegunCommand,
  usage,
  sweep,
  pbStore,
  nowSeconds,
  COMMAND_ID,
  handle,
  sweepNow,
  changedDemoFields,
  guardDemoCreate,
  guardDemoUpdate,
  guardDemoOAuth2,
};
