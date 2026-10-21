/// <reference path="../pb_data/types.d.ts" />

// The execution job store (ROUNDS-00A-L03 PR 1): jobs, attempts, leases,
// and result envelopes.
//
// These functions are the only writers of execution_jobs,
// execution_attempts, and execution_envelopes, and of the `job` link on
// admission_commands (docs/security/server-writes.md). execution.pb.js
// calls them from the routes under /api/rounds/execution/, which nginx
// answers with 404, while ROUNDS_GATE_EXECUTION_STORE is on. Every call
// runs in one transaction, and PocketBase runs each write transaction on
// its one write connection, so two runner replicas never both hold a job.
//
// Two kinds of caller:
//
// - enqueue and cancel act for an account: the caller's bearer names it,
//   and, as with admission's writes, the runner key
//   (ROUNDS_ADMISSION_SECRET) has to come too. enqueue needs the account's
//   in-flight admission command for the same key and fingerprint, and
//   records the job on it.
// - claim, heartbeat, complete, and reap are the execution_service
//   record's, which only the runner can log in as (ROUNDS_EXECUTION_SECRET).
//
// A claim makes an attempt with a lease of LEASE_S seconds on
// PocketBase's clock, under the SHA-256 of a fencing token the claiming
// replica made and holds. Every later write for the attempt carries the
// token; one whose attempt was superseded, expired, or ended is counted on
// the attempt as rejected and never applied. reap, which every claim runs
// first, puts a job whose lease ran out before it started back in the
// queue, ends one that had started worker-lost, and ends a started attempt
// BUDGET_GRACE_S past its declared budget infrastructure-degraded, even
// while it heartbeats.
//
// A handler requires this file itself, as with admission.js:
//
//   const execution = require(`${__hooks}/execution.js`);
//
// The decisions take a store, so tests run them on plain objects;
// pbStore() is the store over a PocketBase transaction.

const VERSION = "execution/v1";
const ENVELOPE_VERSION = "rounds.execution-envelope/v1";
const LEASE_S = 30;
const BUDGET_GRACE_S = 30;
// A same-key retry re-queues a job only while fewer attempts have started.
const MAX_STARTED = 3;
// Attempts a job may have in all, started or not.
const MAX_ATTEMPTS = 3;
// claim skips an account with this many jobs leased or started.
const ACCOUNT_ACTIVE_JOBS = 2;
const REAP_BATCH = 100;
// The most accounts one claim considers.
const CLAIM_SCAN = 50;
const INPUT_MAX_CHARS = 8 * 1024 * 1024;
const USER_VIEW_MAX_CHARS = 1024 * 1024;
const OPERATOR_VIEW_MAX_CHARS = 64 * 1024;
const SERVICE_COLLECTION = "execution_service";
const WORKER_USERNAME = "execution-worker";
const SECRET_ENV = "ROUNDS_EXECUTION_SECRET";
// The worker password is bcrypt-hashed, which reads at most 72 bytes.
const SECRET_MIN_CHARS = 32;
const SECRET_MAX_CHARS = 72;

// Each kind, its purpose, and the admission operation it's admitted
// under. backend/execution/kinds.py declares the same six.
const KINDS = {
  run: { purpose: "scratch", operation: "run" },
  evaluate: { purpose: "scratch", operation: "evaluate" },
  run_project: { purpose: "scratch", operation: "run_project" },
  take_home_run: { purpose: "scratch", operation: "take_home_run" },
  grade: { purpose: "grading", operation: "grade" },
  take_home_submit: { purpose: "grading", operation: "take_home_submit" },
};
const ACTIVE = ["leased", "started"];
// Each terminal state, the outcome classes it ends with, and which of
// those make the envelope authoritative.
const TERMINAL = {
  completed: { classes: ["passed", "candidate-failure", "resource-limit"], authoritative: ["passed", "candidate-failure", "resource-limit"] },
  "timed-out": { classes: ["resource-limit", "infrastructure-degraded"], authoritative: ["resource-limit"] },
  denied: { classes: ["definition-invalid", "policy-violation"], authoritative: [] },
  canceled: { classes: ["canceled"], authoritative: [] },
  failed: { classes: ["worker-lost", "infrastructure-degraded"], authoritative: [] },
};
const OUTCOME_CLASSES = [
  "passed", "candidate-failure", "resource-limit", "definition-invalid", "policy-violation", "canceled",
  "worker-lost", "infrastructure-degraded",
];
// An attempt that ended with one of these may be retried with its key.
const RETRYABLE = ["worker-lost", "infrastructure-degraded"];
// Kinds whose runs use hidden material (hidden tests, harness files, a
// rubric). Their envelope carries outcome classes and the server's totals
// only, never output (D9).
const HIDDEN_MATERIAL = ["grade", "take_home_submit"];
const CLEANUP = ["pending", "confirmed", "unconfirmed"];
const LIMITS = ["wall_time", "cpu_time", "memory", "processes", "files", "output"];
const TRACKS = ["coding", "ai-coding", "take-home"];
const COMMAND_ID = /^[0-9a-f]{8}-[0-9a-f]{4}-7[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const SHA256_HEX = /^[0-9a-f]{64}$/;
const RECORD_ID = /^[a-z0-9]{15}$/;
const SLUG = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const VARIANT = /^[a-z]{1,16}$/;
const WORKER_ID = /^[a-z0-9][a-z0-9-]{0,62}$/;
const TOKEN = /^[A-Za-z0-9]{43}$/;
// A case, checkpoint, or criterion id.
const PART_ID = /^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$/;
const MAX_PARTS = 64;
const RUBRIC_STATES = ["requested", "completed", "lost"];
const CHECKSUM = /^sha256:[0-9a-f]{64}$/;
// #2's cap on the visible output a run may show.
const OUTPUT_MAX_CHARS = 256 * 1024;
// The keys a user projection may carry (rounds.execution-envelope/v1).
const USER_VIEW_KEYS = [
  "version", "job_id", "state", "outcome_class", "authoritative", "limit", "parts", "score", "definition",
  "queued_at", "started_at", "finished_at", "cleanup", "rubric", "output",
];
const OPERATOR_VIEW_KEYS = [
  "version", "executor_kind", "worker", "attempt_number", "source_checksum", "input_digest", "output_sha256",
  "output_bytes", "exit_status", "cpu_time_ms", "peak_rss_bytes", "build_revision", "image_digest", "graded_row",
];

// ---------------------------------------------------------------------------
// Input checks, before any transaction
// ---------------------------------------------------------------------------

function isInt(value) {
  return typeof value === "number" && isFinite(value) && Math.floor(value) === value;
}

function isObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function only(data, allowed) {
  return isObject(data) && Object.keys(data).every((key) => allowed.indexOf(key) >= 0);
}

function has(object, key) {
  return Object.prototype.hasOwnProperty.call(object, key);
}

function checkDefinition(ref) {
  if (!only(ref, ["track", "slug", "variant", "version"])) return null;
  if (TRACKS.indexOf(ref.track) < 0) return null;
  if (typeof ref.slug !== "string" || ref.slug.length > 100 || !SLUG.test(ref.slug)) return null;
  if (typeof ref.variant !== "string" || !VARIANT.test(ref.variant)) return null;
  if (!isInt(ref.version) || ref.version < 1 || ref.version > 9999) return null;
  return { track: ref.track, slug: ref.slug, variant: ref.variant, version: ref.version };
}

// Each returns the checked input, or null when the request is malformed.
function checkEnqueue(data) {
  const keys = ["command_id", "kind", "definition", "fingerprint", "source_checksum", "input_digest", "input"];
  if (!only(data, keys) || keys.some((key) => !has(data, key))) return null;
  if (typeof data.command_id !== "string" || !COMMAND_ID.test(data.command_id)) return null;
  if (typeof data.kind !== "string" || !has(KINDS, data.kind)) return null;
  const definition = checkDefinition(data.definition);
  if (definition === null) return null;
  for (const key of ["fingerprint", "source_checksum", "input_digest"]) {
    if (typeof data[key] !== "string" || !SHA256_HEX.test(data[key])) return null;
  }
  if (!isObject(data.input)) return null;
  const text = JSON.stringify(data.input);
  if (typeof text !== "string" || text.length > INPUT_MAX_CHARS) return null;
  return {
    command_id: data.command_id,
    kind: data.kind,
    definition,
    fingerprint: data.fingerprint,
    source_checksum: data.source_checksum,
    input_digest: data.input_digest,
    input: data.input,
  };
}

function checkCancel(data) {
  if (!only(data, ["job_id"]) || typeof data.job_id !== "string" || !RECORD_ID.test(data.job_id)) return null;
  return { job_id: data.job_id };
}

function checkClaim(data) {
  if (!only(data, ["worker", "token_hash"])) return null;
  if (typeof data.worker !== "string" || !WORKER_ID.test(data.worker)) return null;
  if (typeof data.token_hash !== "string" || !SHA256_HEX.test(data.token_hash)) return null;
  return { worker: data.worker, token_hash: data.token_hash };
}

function checkHeartbeat(data) {
  if (!only(data, ["attempt_id", "token", "started", "budget_s"])) return null;
  if (typeof data.attempt_id !== "string" || !RECORD_ID.test(data.attempt_id)) return null;
  if (typeof data.token !== "string" || !TOKEN.test(data.token)) return null;
  const started = data.started === undefined ? false : data.started;
  if (typeof started !== "boolean") return null;
  const budget = data.budget_s === undefined ? null : data.budget_s;
  if (started !== (budget !== null)) return null;
  if (budget !== null && (!isInt(budget) || budget < 1)) return null;
  return { attempt_id: data.attempt_id, token: data.token, started, budget_s: budget };
}

function jsonWithin(value, max) {
  const text = JSON.stringify(value);
  return typeof text === "string" && text.length <= max;
}

function nullableInt(value) {
  return value === null || (isInt(value) && value >= 0);
}

// One part: its id, its outcome class, and the limit a resource-limit
// names. Nothing else, so no part can carry what a test expected or printed.
function checkPart(part) {
  if (!only(part, ["id", "outcome_class", "limit"]) || !has(part, "id") || !has(part, "outcome_class") ||
      !has(part, "limit")) return false;
  if (typeof part.id !== "string" || !PART_ID.test(part.id)) return false;
  if (OUTCOME_CLASSES.indexOf(part.outcome_class) < 0) return false;
  if (part.limit === null) return part.outcome_class !== "resource-limit";
  return part.outcome_class === "resource-limit" && LIMITS.indexOf(part.limit) >= 0;
}

// #2's receipt for what ran: {track, slug, variant, content_version,
// checksum}.
function checkReceipt(ref) {
  if (ref === null) return true;
  const keys = ["track", "slug", "variant", "content_version", "checksum"];
  if (!only(ref, keys) || keys.some((key) => !has(ref, key))) return false;
  if (TRACKS.indexOf(ref.track) < 0) return false;
  if (typeof ref.slug !== "string" || ref.slug.length > 100 || !SLUG.test(ref.slug)) return false;
  if (ref.variant !== null && (typeof ref.variant !== "string" || !VARIANT.test(ref.variant))) return false;
  if (!isInt(ref.content_version) || ref.content_version < 1 || ref.content_version > 9999) return false;
  return typeof ref.checksum === "string" && CHECKSUM.test(ref.checksum);
}

// The user view of rounds.execution-envelope/v1: enums, ids, times, the
// server's score, the receipt, the rubric's state, and the visible output,
// which is null for a run with hidden material (complete checks that).
function checkUserView(user, result) {
  if (!only(user, USER_VIEW_KEYS) || USER_VIEW_KEYS.some((key) => !has(user, key))) return false;
  if (user.version !== ENVELOPE_VERSION) return false;
  if (typeof user.job_id !== "string" || !RECORD_ID.test(user.job_id)) return false;
  if (user.state !== result.state || user.outcome_class !== result.outcome_class) return false;
  if (user.authoritative !== result.authoritative || user.cleanup !== result.cleanup) return false;
  if (user.limit !== null && LIMITS.indexOf(user.limit) < 0) return false;
  // A resource-limit names its limit, and only it does.
  if ((result.outcome_class === "resource-limit") !== (user.limit !== null)) return false;
  if (!Array.isArray(user.parts) || user.parts.length > MAX_PARTS || !user.parts.every(checkPart)) return false;
  if (user.score !== null && !(typeof user.score === "number" && user.score >= 0 && user.score <= 1)) return false;
  if (user.score !== null && result.outcome_class !== "passed" && result.outcome_class !== "candidate-failure") return false;
  if (!checkReceipt(user.definition)) return false;
  if (!(isInt(user.queued_at) && user.queued_at >= 0) || !nullableInt(user.started_at)) return false;
  if (!(isInt(user.finished_at) && user.finished_at >= 0)) return false;
  if (user.rubric !== null && !(only(user.rubric, ["state"]) && RUBRIC_STATES.indexOf(user.rubric.state) >= 0)) return false;
  if (user.output !== null && !(isObject(user.output) && jsonWithin(user.output, OUTPUT_MAX_CHARS))) return false;
  return jsonWithin(user, USER_VIEW_MAX_CHARS);
}

// A runner-built envelope: its terminal state and outcome class agree
// with TERMINAL, authoritative says what TERMINAL says, and each view
// carries the v1 keys only.
function checkResult(result) {
  if (!only(result, ["state", "outcome_class", "authoritative", "cleanup", "user_view", "operator_view"])) return null;
  const terminal = TERMINAL[result.state];
  if (!terminal || terminal.classes.indexOf(result.outcome_class) < 0) return null;
  if (result.authoritative !== (terminal.authoritative.indexOf(result.outcome_class) >= 0)) return null;
  if (CLEANUP.indexOf(result.cleanup) < 0) return null;
  const user = result.user_view;
  if (!checkUserView(user, result)) return null;
  const operator = result.operator_view;
  if (!only(operator, OPERATOR_VIEW_KEYS) || OPERATOR_VIEW_KEYS.some((key) => !has(operator, key))) return null;
  if (operator.version !== ENVELOPE_VERSION) return null;
  if (["legacy-in-process", "isolated-worker"].indexOf(operator.executor_kind) < 0) return null;
  for (const key of ["output_bytes", "exit_status", "cpu_time_ms", "peak_rss_bytes"]) {
    if (key === "exit_status" ? !(operator[key] === null || isInt(operator[key])) : !nullableInt(operator[key])) return null;
  }
  if (!jsonWithin(operator, OPERATOR_VIEW_MAX_CHARS)) return null;
  return {
    state: result.state,
    outcome_class: result.outcome_class,
    authoritative: result.authoritative,
    cleanup: result.cleanup,
    user_view: user,
    operator_view: operator,
  };
}

function checkComplete(data) {
  if (!only(data, ["attempt_id", "token", "result"])) return null;
  if (typeof data.attempt_id !== "string" || !RECORD_ID.test(data.attempt_id)) return null;
  if (typeof data.token !== "string" || !TOKEN.test(data.token)) return null;
  const result = checkResult(data.result);
  if (result === null) return null;
  return { attempt_id: data.attempt_id, token: data.token, result };
}

function checkReap(data) {
  return data === null || data === undefined || only(data, []) ? {} : null;
}

// ---------------------------------------------------------------------------
// Decisions
// ---------------------------------------------------------------------------

function jobView(job) {
  return {
    id: job.id,
    kind: job.kind,
    state: job.state,
    outcome_class: job.outcome_class || null,
    attempts: job.attempts,
    attempts_started: job.attempts_started,
    cancel_requested: job.cancel_requested,
    cleanup: job.cleanup || null,
    queued_at: job.queued_at,
    finished_at: job.finished_at || null,
  };
}

function isTerminal(state) {
  return has(TERMINAL, state);
}

function retryable(job) {
  return (job.state === "failed" || job.state === "timed-out") && RETRYABLE.indexOf(job.outcome_class) >= 0 &&
    job.attempts_started < MAX_STARTED && job.attempts < MAX_ATTEMPTS;
}

// enqueue: the job for an admitted command. The command row must be the
// account's, in flight, for the same operation and fingerprint; the job
// is recorded on it. A key the account already enqueued answers its job
// again, re-queued when its last attempt was lost to infrastructure and a
// retry is left; a different fingerprint is a mismatch.
function enqueue(store, account, input, now) {
  const command = store.findCommand(account.id, input.command_id);
  if (command === null || command.expires_at <= now) {
    return { status: 404, body: { v: VERSION, error: "not_admitted" } };
  }
  if (command.operation !== KINDS[input.kind].operation || command.fingerprint !== input.fingerprint) {
    return { status: 409, body: { v: VERSION, error: "mismatch" } };
  }
  if (command.state !== "in_flight") return { status: 409, body: { v: VERSION, error: "not_admitted" } };
  let job = store.findJob(account.id, input.command_id);
  if (job !== null) {
    if (job.fingerprint !== input.fingerprint || job.kind !== input.kind) {
      return { status: 409, body: { v: VERSION, error: "mismatch" } };
    }
    let requeued = false;
    if (retryable(job)) {
      job.state = "queued";
      job.outcome_class = "";
      job.cleanup = "";
      job.finished_at = 0;
      job.cancel_requested = false;
      job.queued_at = now;
      job = store.saveJob(job);
      requeued = true;
    }
    if (command.job !== job.id) {
      command.job = job.id;
      store.saveCommand(command);
    }
    return { status: 200, body: { v: VERSION, job: jobView(job), duplicate: !requeued, requeued } };
  }
  job = store.saveJob({
    id: "",
    account: account.id,
    command_id: input.command_id,
    kind: input.kind,
    purpose: KINDS[input.kind].purpose,
    definition: input.definition,
    fingerprint: input.fingerprint,
    source_checksum: input.source_checksum,
    input_digest: input.input_digest,
    input: input.input,
    state: "queued",
    outcome_class: "",
    attempts_started: 0,
    attempts: 0,
    cancel_requested: false,
    cleanup: "",
    queued_at: now,
    finished_at: 0,
  });
  command.job = job.id;
  store.saveCommand(command);
  return { status: 200, body: { v: VERSION, job: jobView(job), duplicate: false, requeued: false } };
}

// The envelope an attempt gets when reap ends it and no runner reported
// one. Never authoritative.
function serverEnvelope(job, attempt, state, outcomeClass, cleanup, now) {
  return {
    state,
    outcome_class: outcomeClass,
    authoritative: false,
    cleanup,
    user_view: {
      version: ENVELOPE_VERSION,
      job_id: job.id,
      state,
      outcome_class: outcomeClass,
      authoritative: false,
      limit: null,
      parts: [],
      score: null,
      definition: null,
      queued_at: job.queued_at,
      started_at: attempt && attempt.started_at ? attempt.started_at : null,
      finished_at: now,
      cleanup,
      rubric: null,
      output: null,
    },
    operator_view: {
      version: ENVELOPE_VERSION,
      executor_kind: "legacy-in-process",
      worker: attempt ? attempt.worker : null,
      attempt_number: attempt ? attempt.attempt_number : null,
      source_checksum: job.source_checksum,
      input_digest: job.input_digest,
      output_sha256: null,
      output_bytes: null,
      exit_status: null,
      cpu_time_ms: null,
      peak_rss_bytes: null,
      build_revision: null,
      image_digest: null,
      graded_row: null,
    },
  };
}

// The envelope the account reads, with the user view only. The operator
// view goes on the attempt (endAttempt).
function writeEnvelope(store, job, attempt, result) {
  return store.saveEnvelope({
    id: "",
    user: job.account,
    job: job.id,
    attempt: attempt.id,
    version: ENVELOPE_VERSION,
    state: result.state,
    outcome_class: result.outcome_class,
    authoritative: result.authoritative,
    user_view: result.user_view,
    graded_collection: "",
    graded_row: "",
  });
}

function endAttempt(store, attempt, state, outcomeClass, cleanup, now, operatorView) {
  attempt.state = state;
  attempt.outcome_class = outcomeClass;
  attempt.cleanup = cleanup;
  attempt.finished_at = now;
  attempt.operator_view = operatorView;
  return store.saveAttempt(attempt);
}

function endJob(store, job, state, outcomeClass, cleanup, now) {
  job.state = state;
  job.outcome_class = outcomeClass;
  job.cleanup = cleanup;
  job.finished_at = now;
  job.cancel_requested = false;
  return store.saveJob(job);
}

// cancel: owner-only and idempotent. A queued job ends canceled at once;
// a leased or started one is asked to stop, which its runner honors at
// the next heartbeat; an ended job is left as it is. Another account's
// job is the same 404 as an unknown one.
function cancel(store, account, input, now) {
  const job = store.getJob(input.job_id);
  if (job === null || job.account !== account.id) return { status: 404, body: { v: VERSION, error: "not_found" } };
  if (job.state === "queued") {
    endJob(store, job, "canceled", "canceled", "confirmed", now);
  } else if (ACTIVE.indexOf(job.state) >= 0 && !job.cancel_requested) {
    job.cancel_requested = true;
    store.saveJob(job);
  }
  return { status: 200, body: { v: VERSION, job: jobView(store.getJob(job.id)) } };
}

// reap: the three ways an attempt ends without its runner.
//   1. A lease that ran out before the run started: the attempt is lost
//      and its job goes back in the queue, or ends canceled if a cancel
//      was asked for, or ends failed when it has no attempts left.
//   2. A lease that ran out after it started: the job ends worker-lost.
//   3. A started attempt BUDGET_GRACE_S past its budget, heartbeat or
//      not: the job ends infrastructure-degraded.
function reap(store, now) {
  const out = { requeued: 0, worker_lost: 0, over_budget: 0 };
  store.expiredAttempts(now, REAP_BATCH).forEach((attempt) => {
    const job = store.getJob(attempt.job);
    const current = job !== null && job.attempts === attempt.attempt_number && ACTIVE.indexOf(job.state) >= 0;
    if (job === null) {
      endAttempt(store, attempt, "failed", "worker-lost", "unconfirmed", now, null);
      return;
    }
    const lost = serverEnvelope(job, attempt, "failed", "worker-lost", "unconfirmed", now);
    endAttempt(store, attempt, "failed", "worker-lost", "unconfirmed", now, lost.operator_view);
    writeEnvelope(store, job, attempt, lost);
    if (!current) return;
    if (attempt.started_at) {
      endJob(store, job, "failed", "worker-lost", "unconfirmed", now);
      out.worker_lost += 1;
    } else if (job.cancel_requested) {
      endJob(store, job, "canceled", "canceled", "unconfirmed", now);
    } else if (job.attempts >= MAX_ATTEMPTS) {
      endJob(store, job, "failed", "infrastructure-degraded", "unconfirmed", now);
    } else {
      job.state = "queued";
      job.queued_at = now;
      store.saveJob(job);
      out.requeued += 1;
    }
  });
  store.overBudgetAttempts(now - BUDGET_GRACE_S, REAP_BATCH).forEach((attempt) => {
    const job = store.getJob(attempt.job);
    if (job === null) {
      endAttempt(store, attempt, "failed", "infrastructure-degraded", "unconfirmed", now, null);
      return;
    }
    const degraded = serverEnvelope(job, attempt, "failed", "infrastructure-degraded", "unconfirmed", now);
    endAttempt(store, attempt, "failed", "infrastructure-degraded", "unconfirmed", now, degraded.operator_view);
    writeEnvelope(store, job, attempt, degraded);
    if (job.attempts === attempt.attempt_number && ACTIVE.indexOf(job.state) >= 0) {
      endJob(store, job, "failed", "infrastructure-degraded", "unconfirmed", now);
    }
    out.over_budget += 1;
  });
  return out;
}

// claim: reap first, then lease the next queued job under the caller's
// token hash. Accounts with fewer than ACCOUNT_ACTIVE_JOBS active take
// turns by their oldest queued job, oldest first, so one account's backlog
// never holds another's jobs back. The scan reads ids and attempt counts;
// only the job claimed is read whole.
function claim(store, input, now) {
  const reaped = reap(store, now);
  if (store.findAttemptByToken(input.token_hash) !== null) {
    return { status: 400, body: { v: VERSION, error: "invalid_request" } };
  }
  const heads = store.claimable(ACCOUNT_ACTIVE_JOBS, CLAIM_SCAN);
  for (let i = 0; i < heads.length; i += 1) {
    const job = store.getJob(heads[i].id);
    if (job === null) continue;
    if (job.attempts >= MAX_ATTEMPTS) {
      endJob(store, job, "failed", "infrastructure-degraded", "unconfirmed", now);
      continue;
    }
    const attempt = store.saveAttempt({
      id: "",
      job: job.id,
      account: job.account,
      attempt_number: job.attempts + 1,
      token_hash: input.token_hash,
      worker: input.worker,
      state: "leased",
      outcome_class: "",
      budget_s: 0,
      deadline_at: 0,
      leased_at: now,
      lease_expires_at: now + LEASE_S,
      started_at: 0,
      heartbeat_at: 0,
      finished_at: 0,
      rejected_writes: 0,
      cleanup: "",
      operator_view: null,
    });
    job.state = "leased";
    job.attempts = attempt.attempt_number;
    store.saveJob(job);
    return {
      status: 200,
      body: {
        v: VERSION,
        reaped,
        job: {
          id: job.id,
          account: job.account,
          kind: job.kind,
          purpose: job.purpose,
          definition: job.definition,
          fingerprint: job.fingerprint,
          source_checksum: job.source_checksum,
          input_digest: job.input_digest,
          input: job.input,
          queued_at: job.queued_at,
        },
        attempt: { id: attempt.id, attempt_number: attempt.attempt_number, lease_expires_at: attempt.lease_expires_at },
      },
    };
  }
  return { status: 200, body: { v: VERSION, reaped, job: null, attempt: null } };
}

// The attempt a token holds, if it may still write: the job's current
// attempt, leased or started, with its lease running. A write that fails
// any of that is counted on the attempt and refused.
function fenced(store, attemptId, token, now) {
  const attempt = store.getAttempt(attemptId);
  if (attempt === null || store.hash(token) !== attempt.token_hash) {
    return { refused: { status: 404, body: { v: VERSION, error: "not_found" } } };
  }
  const job = store.getJob(attempt.job);
  const live = job !== null && job.attempts === attempt.attempt_number && ACTIVE.indexOf(job.state) >= 0 &&
    ACTIVE.indexOf(attempt.state) >= 0 && attempt.lease_expires_at > now;
  if (!live) {
    attempt.rejected_writes = (attempt.rejected_writes || 0) + 1;
    store.saveAttempt(attempt);
    return { refused: { status: 409, body: { v: VERSION, error: "superseded" } }, rejected: true };
  }
  return { attempt, job };
}

// heartbeat: keeps the lease, and the first one with `started` marks the
// candidate tree started with its declared budget, which can't be more
// than the kind is admitted for. It answers whether a cancel was asked
// for, which the runner honors.
function heartbeat(store, input, now, maxBudget) {
  const held = fenced(store, input.attempt_id, input.token, now);
  if (held.refused) return held.refused;
  const attempt = held.attempt;
  const job = held.job;
  if (input.started) {
    if (attempt.state !== "leased") return { status: 409, body: { v: VERSION, error: "already_started" } };
    if (input.budget_s > maxBudget(job.kind)) return { status: 400, body: { v: VERSION, error: "invalid_request" } };
    attempt.state = "started";
    attempt.started_at = now;
    attempt.budget_s = input.budget_s;
    attempt.deadline_at = now + input.budget_s;
    job.state = "started";
    job.attempts_started += 1;
    store.saveJob(job);
  }
  attempt.heartbeat_at = now;
  attempt.lease_expires_at = now + LEASE_S;
  store.saveAttempt(attempt);
  return {
    status: 200,
    body: { v: VERSION, lease_expires_at: attempt.lease_expires_at, cancel_requested: job.cancel_requested },
  };
}

// complete: the attempt's envelope, its terminal state, and the job's,
// in one transaction, or nothing. A late or superseded result is counted
// and refused.
function complete(store, input, now) {
  const held = fenced(store, input.attempt_id, input.token, now);
  if (held.refused) return held.refused;
  const attempt = held.attempt;
  const job = held.job;
  const result = input.result;
  if (result.user_view.job_id !== job.id) return { status: 400, body: { v: VERSION, error: "invalid_request" } };
  // A run with hidden material shows the account no output at all.
  if (HIDDEN_MATERIAL.indexOf(job.kind) >= 0 && result.user_view.output !== null) {
    return { status: 400, body: { v: VERSION, error: "invalid_request" } };
  }
  // Only a run that started can end with what the candidate did. A run
  // that never got a slot ends timed-out, infrastructure-degraded.
  if (result.authoritative && attempt.state !== "started") {
    return { status: 409, body: { v: VERSION, error: "not_started" } };
  }
  const envelope = writeEnvelope(store, job, attempt, result);
  endAttempt(store, attempt, result.state, result.outcome_class, result.cleanup, now, result.operator_view);
  endJob(store, job, result.state, result.outcome_class, result.cleanup, now);
  return { status: 200, body: { v: VERSION, envelope_id: envelope.id, job: jobView(store.getJob(job.id)) } };
}

// ---------------------------------------------------------------------------
// The worker record
// ---------------------------------------------------------------------------

function usableSecret(secret) {
  return typeof secret === "string" && secret.length >= SECRET_MIN_CHARS && secret.length <= SECRET_MAX_CHARS &&
    /^[\x21-\x7e]+$/.test(secret);
}

// At start: execution-worker exists with ROUNDS_EXECUTION_SECRET as its
// password. A secret that's unset, not SECRET_MIN_CHARS to
// SECRET_MAX_CHARS long, or not printable ASCII without spaces creates
// nothing, and an existing record gets a random password, so no old
// secret still logs in. `accounts` is the small interface over the
// execution_service collection. Returns what it did, for the log, never
// the secret.
function ensureWorker(accounts, secret, randomSecret) {
  const existing = accounts.find(WORKER_USERNAME);
  if (!usableSecret(secret)) {
    if (existing !== null) accounts.setPassword(existing, randomSecret());
    return existing === null ? "skipped" : "disabled";
  }
  if (existing === null) {
    accounts.create(WORKER_USERNAME, secret);
    return "created";
  }
  if (accounts.validatePassword(existing, secret)) return "unchanged";
  accounts.setPassword(existing, secret);
  return "updated";
}

// ---------------------------------------------------------------------------
// The PocketBase store
// ---------------------------------------------------------------------------

const JOBS = "execution_jobs";
const ATTEMPTS = "execution_attempts";
const ENVELOPES = "execution_envelopes";
const COMMANDS = "admission_commands";
// A queued job a claim may take: its account has fewer than {:cap} jobs
// leased or started, and no queued job before this one.
const CLAIMABLE =
  "j.state = 'queued'" +
  " AND (SELECT COUNT(*) FROM execution_jobs a" +
  " WHERE a.account = j.account AND a.state IN ('leased', 'started')) < {:cap}" +
  " AND NOT EXISTS (SELECT 1 FROM execution_jobs o" +
  " WHERE o.account = j.account AND o.state = 'queued'" +
  " AND (o.queued_at < j.queued_at OR (o.queued_at = j.queued_at" +
  " AND (o.created < j.created OR (o.created = j.created AND o.id < j.id)))))";

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
  function save(name, row, fields) {
    const record = row._record || new Record(collection(name));
    fields.forEach((field) => record.set(field, row[field]));
    dao.saveRecord(record);
    row.id = record.id;
    row._record = record;
    return row;
  }
  function job(record) {
    if (record === null) return null;
    return {
      id: record.id,
      account: record.getString("account"),
      command_id: record.getString("command_id"),
      kind: record.getString("kind"),
      purpose: record.getString("purpose"),
      definition: json(record, "definition"),
      fingerprint: record.getString("fingerprint"),
      source_checksum: record.getString("source_checksum"),
      input_digest: record.getString("input_digest"),
      input: json(record, "input"),
      state: record.getString("state"),
      outcome_class: record.getString("outcome_class"),
      attempts_started: record.getInt("attempts_started"),
      attempts: record.getInt("attempts"),
      cancel_requested: record.getBool("cancel_requested"),
      cleanup: record.getString("cleanup"),
      queued_at: record.getInt("queued_at"),
      finished_at: record.getInt("finished_at"),
      _record: record,
    };
  }
  function attempt(record) {
    if (record === null) return null;
    return {
      id: record.id,
      job: record.getString("job"),
      account: record.getString("account"),
      attempt_number: record.getInt("attempt_number"),
      token_hash: record.getString("token_hash"),
      worker: record.getString("worker"),
      state: record.getString("state"),
      outcome_class: record.getString("outcome_class"),
      budget_s: record.getInt("budget_s"),
      deadline_at: record.getInt("deadline_at"),
      leased_at: record.getInt("leased_at"),
      lease_expires_at: record.getInt("lease_expires_at"),
      started_at: record.getInt("started_at"),
      heartbeat_at: record.getInt("heartbeat_at"),
      finished_at: record.getInt("finished_at"),
      rejected_writes: record.getInt("rejected_writes"),
      cleanup: record.getString("cleanup"),
      operator_view: json(record, "operator_view"),
      _record: record,
    };
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
      expires_at: record.getInt("expires_at"),
      job: record.getString("job"),
      _record: record,
    };
  }
  const JOB_FIELDS = [
    "account", "command_id", "kind", "purpose", "definition", "fingerprint", "source_checksum", "input_digest",
    "input", "state", "outcome_class", "attempts_started", "attempts", "cancel_requested", "cleanup", "queued_at",
    "finished_at",
  ];
  const ATTEMPT_FIELDS = [
    "job", "account", "attempt_number", "token_hash", "worker", "state", "outcome_class", "budget_s", "deadline_at",
    "leased_at", "lease_expires_at", "started_at", "heartbeat_at", "finished_at", "rejected_writes", "cleanup",
    "operator_view",
  ];
  const ENVELOPE_FIELDS = [
    "user", "job", "attempt", "version", "state", "outcome_class", "authoritative", "user_view", "graded_collection",
    "graded_row",
  ];

  return {
    hash: (token) => $security.sha256(token),
    findCommand: (account, commandId) =>
      command(first(COMMANDS, "account = {:account} && command_id = {:id}", { account, id: commandId })),
    saveCommand: (row) => {
      // Only the job link changes here; admission.js owns the rest.
      row._record.set("job", row.job);
      dao.saveRecord(row._record);
      return row;
    },
    findJob: (account, commandId) =>
      job(first(JOBS, "account = {:account} && command_id = {:id}", { account, id: commandId })),
    getJob: (id) => job(first(JOBS, "id = {:id}", { id })),
    saveJob: (row) => save(JOBS, row, JOB_FIELDS),
    // Each account's oldest queued job, for the accounts with fewer than
    // `cap` jobs leased or started, oldest first; jobs queued in the same
    // second, in the order they came. Ids and attempt counts only.
    claimable: (cap, limit) => {
      const heads = arrayOf(new DynamicModel({ id: "", account: "", attempts: 0 }));
      dao.db()
        .select("j.id", "j.account", "j.attempts")
        .from(JOBS + " j")
        .where($dbx.exp(CLAIMABLE, { cap }))
        .orderBy("j.queued_at ASC", "j.created ASC", "j.id ASC")
        .limit(limit)
        .all(heads);
      return heads.map((h) => ({ id: h.id, account: h.account, attempts: h.attempts }));
    },
    getAttempt: (id) => attempt(first(ATTEMPTS, "id = {:id}", { id })),
    findAttemptByToken: (tokenHash) => attempt(first(ATTEMPTS, "token_hash = {:hash}", { hash: tokenHash })),
    saveAttempt: (row) => save(ATTEMPTS, row, ATTEMPT_FIELDS),
    expiredAttempts: (now, limit) =>
      dao.findRecordsByFilter(ATTEMPTS, "(state = 'leased' || state = 'started') && lease_expires_at <= {:now}", "lease_expires_at", limit, 0, { now }).map(attempt),
    overBudgetAttempts: (cutoff, limit) =>
      dao.findRecordsByFilter(ATTEMPTS, "state = 'started' && deadline_at < {:cutoff}", "deadline_at", limit, 0, { cutoff }).map(attempt),
    saveEnvelope: (row) => save(ENVELOPES, row, ENVELOPE_FIELDS),
  };
}

// ---------------------------------------------------------------------------
// Routes and hooks (execution.pb.js)
// ---------------------------------------------------------------------------

function nowSeconds() {
  return Math.floor(Date.now() / 1000);
}

function storeOn() {
  const gates = require(`${__hooks}/gates.js`);
  return gates.resolve("EXECUTION_STORE", { ROUNDS_GATE_EXECUTION_STORE: $os.getenv("ROUNDS_GATE_EXECUTION_STORE") }).value === "on";
}

function maxBudget(kind) {
  const admission = require(`${__hooks}/admission.js`);
  return admission.OPERATIONS[KINDS[kind].operation][1];
}

const CALLER_CHECKS = { enqueue: checkEnqueue, cancel: checkCancel };
const SERVICE_CHECKS = { claim: checkClaim, heartbeat: checkHeartbeat, complete: checkComplete, reap: checkReap };

function inTransaction(fn) {
  let out = null;
  $app.dao().runInTransaction((txDao) => {
    out = fn(pbStore(txDao));
  });
  return out;
}

// enqueue and cancel: the account comes from the bearer, never the body,
// and the runner key has to come too.
function handleCaller(c, action) {
  if (!storeOn()) return c.json(503, { v: VERSION, error: "store_off" });
  const info = $apis.requestInfo(c);
  const record = info.authRecord;
  if (!record) throw new UnauthorizedError("Sign in to continue.");
  const admission = require(`${__hooks}/admission.js`);
  const refused = admission.runnerKeyError(info.headers, $os.getenv(admission.RUNNER_KEY_ENV));
  if (refused !== null) return c.json(refused.status, { v: VERSION, error: refused.body.error });
  const input = CALLER_CHECKS[action](info.data);
  if (input === null) return c.json(400, { v: VERSION, error: "invalid_request" });
  const account = { id: record.id };
  const now = nowSeconds();
  const out = inTransaction((store) => (action === "enqueue" ? enqueue(store, account, input, now) : cancel(store, account, input, now)));
  return c.json(out.status, out.body);
}

// claim, heartbeat, complete, and reap: the execution_service record only.
function handleService(c, action) {
  if (!storeOn()) return c.json(503, { v: VERSION, error: "store_off" });
  const info = $apis.requestInfo(c);
  const record = info.authRecord;
  if (!record || record.collection().name !== SERVICE_COLLECTION || record.username() !== WORKER_USERNAME) {
    throw new ForbiddenError("This is for the execution service.");
  }
  const input = SERVICE_CHECKS[action](info.data);
  if (input === null) return c.json(400, { v: VERSION, error: "invalid_request" });
  const now = nowSeconds();
  const out = inTransaction((store) => {
    if (action === "claim") return claim(store, input, now);
    if (action === "heartbeat") return heartbeat(store, input, now, maxBudget);
    if (action === "complete") return complete(store, input, now);
    return { status: 200, body: Object.assign({ v: VERSION }, reap(store, now)) };
  });
  return c.json(out.status, out.body);
}

function randomSecret() {
  return $security.randomString(64);
}

// The execution_service collection as ensureWorker sees it, over `dao`.
function workerAccounts(dao) {
  return {
    find: (username) => {
      try {
        return dao.findAuthRecordByUsername(SERVICE_COLLECTION, username);
      } catch (_) {
        return null;
      }
    },
    create: (username, secret) => {
      const record = new Record(dao.findCollectionByNameOrId(SERVICE_COLLECTION));
      record.set("username", username);
      record.set("verified", true);
      record.setPassword(secret);
      dao.saveRecord(record);
    },
    validatePassword: (record, secret) => record.validatePassword(secret),
    setPassword: (record, secret) => {
      record.setPassword(secret);
      dao.saveRecord(record);
    },
  };
}

function logWorker(did) {
  console.log(JSON.stringify({ v: "obs/v1", event: "execution_worker", service: "pocketbase", worker: did }));
  if (did === "skipped" || did === "disabled") {
    console.error(
      SECRET_ENV + " is unset or not " + SECRET_MIN_CHARS + " to " + SECRET_MAX_CHARS +
        " printable characters; the execution service can't log in.",
    );
  }
}

function serviceCollectionExists(dao) {
  try {
    dao.findCollectionByNameOrId(SERVICE_COLLECTION);
    return true;
  } catch (_) {
    return false;
  }
}

// After bootstrap, on every start: execution-worker follows the secret in
// the environment, so a changed or unset secret takes effect, and every
// token the old one got stops working, before anything logs in. On the
// first start after the migration the collection doesn't exist yet,
// since PocketBase runs migrations after bootstrap; the first login does
// it then (syncWorkerForLogin).
function bootstrapWorker() {
  const dao = $app.dao();
  if (!serviceCollectionExists(dao)) return "absent";
  const did = ensureWorker(workerAccounts(dao), $os.getenv(SECRET_ENV), randomSecret);
  logWorker(did);
  return did;
}

// Before PocketBase checks an execution_service login: execution-worker
// follows the secret first, and the check uses the record as it is now.
function syncWorkerForLogin(e) {
  if (e.identity !== WORKER_USERNAME) return;
  const dao = $app.dao();
  const accounts = workerAccounts(dao);
  const did = ensureWorker(accounts, $os.getenv(SECRET_ENV), randomSecret);
  if (did !== "unchanged") logWorker(did);
  e.record = accounts.find(WORKER_USERNAME);
}

function isSuperuser(httpContext) {
  return Boolean(httpContext && $apis.requestInfo(httpContext).admin);
}

const ENVELOPE_LOCKED = "This field can't be changed.";

// No client sets or changes an attempt row's `envelope`. Only the server
// sets it, when it writes the graded row (PR 3).
function guardEnvelopeCreate(e) {
  if (isSuperuser(e.httpContext)) return;
  if (e.record.getString("envelope") !== "") throw new BadRequestError(ENVELOPE_LOCKED);
}

function guardEnvelopeUpdate(e) {
  if (isSuperuser(e.httpContext)) return;
  const original = e.record.originalCopy();
  if (e.record.getString("envelope") !== (original ? original.getString("envelope") : "")) {
    throw new BadRequestError(ENVELOPE_LOCKED);
  }
}

module.exports = {
  VERSION,
  ENVELOPE_VERSION,
  LEASE_S,
  BUDGET_GRACE_S,
  MAX_STARTED,
  MAX_ATTEMPTS,
  ACCOUNT_ACTIVE_JOBS,
  KINDS,
  TERMINAL,
  OUTCOME_CLASSES,
  HIDDEN_MATERIAL,
  RETRYABLE,
  CLEANUP,
  LIMITS,
  USER_VIEW_KEYS,
  OPERATOR_VIEW_KEYS,
  SECRET_ENV,
  SECRET_MIN_CHARS,
  SECRET_MAX_CHARS,
  WORKER_USERNAME,
  checkEnqueue,
  checkCancel,
  checkClaim,
  checkHeartbeat,
  checkComplete,
  checkResult,
  checkReap,
  enqueue,
  cancel,
  claim,
  heartbeat,
  complete,
  reap,
  ensureWorker,
  usableSecret,
  pbStore,
  handleCaller,
  handleService,
  bootstrapWorker,
  syncWorkerForLogin,
  guardEnvelopeCreate,
  guardEnvelopeUpdate,
};
