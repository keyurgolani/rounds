/// <reference path="../pb_data/types.d.ts" />

// The execution job store (ROUNDS-00A-L03 PR 1): jobs, attempts, leases,
// and result envelopes.
//
// These functions are the only writers of execution_jobs,
// execution_attempts, and execution_envelopes, of the `job` link on
// admission_commands, and, from PR 3, of graded rows in ai_coding_attempts
// and take_home_attempts, which complete writes with their envelope
// (docs/security/server-writes.md). execution.pb.js
// calls them from the routes under /api/rounds/execution/, which nginx
// answers with 404, while ROUNDS_GATE_EXECUTION_STORE is on. Every call
// runs in one transaction, and PocketBase runs each write transaction on
// its one write connection, so two runner replicas never both hold a job.
//
// Two kinds of caller:
//
// - enqueue, cancel, status, review_start, and review_finish act for an
//   account: the caller's bearer names it, and, as with admission's
//   writes, the runner key (ROUNDS_ADMISSION_SECRET) has to come too.
//   enqueue needs the account's in-flight admission command for the same
//   key and fingerprint, and records the job on it. status reads the
//   account's own job (PR 2). The review pair (PR 3) marks a grading
//   result's rubric requested, with its own admission charge, before the
//   runner calls a provider, and then writes the review into the graded
//   row, once per result.
// - claim, heartbeat, complete, and reap are the execution_service
//   record's, which only the runner can log in as (ROUNDS_EXECUTION_SECRET).
//
// A job's admission charge follows the job (PR 2): when its candidate
// starts, the charge is final; when the job ends before that, its wall
// seconds come back (admission.js jobStarted and jobEnded, in the same
// transaction). Scratch jobs purge SCRATCH_RETENTION_S after they end.
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
// A scratch job, its attempts, its envelopes, and its admission command
// go this long after the job ends, or this long after it was last queued
// if it never ended, since the job row holds the candidate's source.
// Each purge takes at most PURGE_BATCH jobs.
// TODO(ROUNDS-14-L01): #72's retention policy sets the number; 7 days
// until then.
const SCRATCH_RETENTION_S = 7 * 24 * 3600;
const PURGE_BATCH = 200;

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

// PR 3: each grading kind's graded row. `content` is the field the runner
// sends with an authoritative result, `item` the collection of the
// practice item's own row, found by the definition's slug, and `link` the
// row's field for it.
const GRADED_FIELDS = {
  grade: { collection: "ai_coding_attempts", content: "test_results", item: "ai_coding_rounds", link: "round" },
  take_home_submit: {
    collection: "take_home_attempts", content: "harness_output", item: "take_home_assignments", link: "assignment",
  },
};
// The classes an authoritative envelope's parts can carry.
const AUTHORITATIVE_CLASSES = ["passed", "candidate-failure", "resource-limit"];
// #2's fd 3 channel, as app/harness_results.py reads it.
const HARNESS_OUTCOMES = ["passed", "failed", "not-run"];
const HARNESS_REASONS = ["ok", "assertion", "exception", "timeout", "no-result", "bad-result"];
// A grade runs at most this many checkpoints (backend/execution/kinds.py).
const MAX_CHECKPOINTS = 8;
const LABEL_MAX_CHARS = 200;
const GRADED_MAX_CHARS = 256 * 1024;
const REVIEW_MAX_CHARS = 256 * 1024;
// The admission operation a review is charged under (admission.js), and
// the prefix of the fingerprint that ties its command to one envelope.
const REVIEW_OPERATION = "review";
const REVIEW_FINGERPRINT_PREFIX = "rounds.execution-review/v1:";

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

// status takes the same one field as cancel.
const checkStatus = checkCancel;

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

// `graded` (PR 3) is what a grading run's graded row holds besides what
// the job already holds: the per-checkpoint or per-criterion results
// complete checks against the envelope (checkGraded). Only an
// authoritative grading result carries it.
function checkComplete(data) {
  if (!only(data, ["attempt_id", "token", "result", "graded"])) return null;
  if (typeof data.attempt_id !== "string" || !RECORD_ID.test(data.attempt_id)) return null;
  if (typeof data.token !== "string" || !TOKEN.test(data.token)) return null;
  const result = checkResult(data.result);
  if (result === null) return null;
  const graded = data.graded === undefined ? null : data.graded;
  if (graded !== null && !(isObject(graded) && jsonWithin(graded, GRADED_MAX_CHARS))) return null;
  return { attempt_id: data.attempt_id, token: data.token, result, graded };
}

// ---------------------------------------------------------------------------
// Graded rows (PR 3)
// ---------------------------------------------------------------------------

// Whether a class is one the candidate's code earned, which alone keeps a
// verdict and a score.
function earned(outcomeClass) {
  return outcomeClass === "passed" || outcomeClass === "candidate-failure";
}

function isUnitScore(value) {
  return typeof value === "number" && isFinite(value) && value >= 0 && value <= 1;
}

function shortText(value, max) {
  return value === null || (typeof value === "string" && value.length <= max);
}

// Each result id's outcome, as #2's fd 3 channel reports it.
function checkOutcomes(list) {
  return Array.isArray(list) && list.length <= MAX_PARTS && list.every((o) =>
    only(o, ["id", "outcome", "reason"]) && typeof o.id === "string" && PART_ID.test(o.id) &&
    HARNESS_OUTCOMES.indexOf(o.outcome) >= 0 && HARNESS_REASONS.indexOf(o.reason) >= 0);
}

// A verdict and a score that agree with a part's class: kept on a class
// the run earned, null on any other.
function verdictFits(outcomeClass, passed, score) {
  if (!earned(outcomeClass)) return passed === null && score === null;
  return passed === (outcomeClass === "passed") && isUnitScore(score);
}

// A graded checkpoint, one per part (`checkpoint-<index>`), in order.
function checkCheckpoint(entry, part, index) {
  const keys = ["index", "label", "outcome_class", "limit", "passed", "score", "executed", "passed_count",
    "failed_count", "outcomes", "error"];
  if (!only(entry, keys) || keys.some((key) => !has(entry, key))) return false;
  if (entry.index !== index || part.id !== "checkpoint-" + index) return false;
  if (entry.outcome_class !== part.outcome_class || entry.limit !== part.limit) return false;
  if (AUTHORITATIVE_CLASSES.indexOf(entry.outcome_class) < 0) return false;
  if (!verdictFits(entry.outcome_class, entry.passed, entry.score)) return false;
  if (!(typeof entry.label === "string" && entry.label.length <= LABEL_MAX_CHARS)) return false;
  if (![entry.executed, entry.passed_count, entry.failed_count].every((n) => isInt(n) && n >= 0 && n <= MAX_PARTS)) {
    return false;
  }
  return checkOutcomes(entry.outcomes) && shortText(entry.error, LABEL_MAX_CHARS);
}

// What a take-home submission's row keeps: the server's score and verdict,
// each criterion's result, and the definition, never what the harness
// printed. Its criteria are the envelope's parts, in order.
function checkHarnessOutput(out, result) {
  const keys = ["outcome_class", "limit", "score", "passed", "criteria", "outcomes", "stdout", "stderr", "error",
    "duration_ms", "truncated", "definition"];
  if (!only(out, keys) || keys.some((key) => !has(out, key))) return false;
  const user = result.user_view;
  if (out.outcome_class !== result.outcome_class || out.limit !== user.limit) return false;
  if (!verdictFits(out.outcome_class, out.passed, out.score)) return false;
  if (out.stdout !== "" || out.stderr !== "" || out.truncated !== false) return false;
  if (!(isInt(out.duration_ms) && out.duration_ms >= 0) || !shortText(out.error, LABEL_MAX_CHARS)) return false;
  if (!checkReceipt(out.definition) || !checkOutcomes(out.outcomes)) return false;
  const parts = user.parts;
  if (!Array.isArray(out.criteria) || out.criteria.length !== parts.length) return false;
  return out.criteria.every((c, i) => {
    if (!only(c, ["id", "passed", "weight", "logs"]) || c.id !== parts[i].id) return false;
    const cls = parts[i].outcome_class;
    const verdict = cls === "passed" ? true : cls === "candidate-failure" ? false : null;
    return c.passed === verdict && typeof c.weight === "number" && isFinite(c.weight) && c.weight >= 0 &&
      HARNESS_REASONS.indexOf(c.logs) >= 0;
  });
}

// Whether `graded` is the graded content for an authoritative result of a
// grading `kind`: grade's checkpoints match its parts one to one, and a
// take-home submission's criteria do. Nothing scores on a limit.
function checkGraded(kind, graded, result) {
  const field = GRADED_FIELDS[kind];
  if (!field || !only(graded, [field.content]) || !has(graded, field.content)) return false;
  if (kind === "grade") {
    const entries = graded.test_results;
    const parts = result.user_view.parts;
    if (!Array.isArray(entries) || entries.length === 0 || entries.length > MAX_CHECKPOINTS) return false;
    if (entries.length !== parts.length) return false;
    return entries.every((entry, i) => checkCheckpoint(entry, parts[i], i));
  }
  return checkHarnessOutput(graded.harness_output, result);
}

// ---------------------------------------------------------------------------
// Rubric reviews (PR 3)
// ---------------------------------------------------------------------------

// review_start: the job, the SHA-256 of the files the caller resent, the
// caller's key for the review's own admission command, and the hash of
// the lease token the runner made for it.
function checkReviewStart(data) {
  if (!only(data, ["job_id", "source_checksum", "command_id", "lease_hash", "quota"])) return null;
  if (typeof data.job_id !== "string" || !RECORD_ID.test(data.job_id)) return null;
  if (typeof data.source_checksum !== "string" || !SHA256_HEX.test(data.source_checksum)) return null;
  if (typeof data.command_id !== "string" || !COMMAND_ID.test(data.command_id)) return null;
  if (typeof data.lease_hash !== "string" || !SHA256_HEX.test(data.lease_hash)) return null;
  const quota = data.quota === undefined ? "enforce" : data.quota;
  if (["enforce", "observe", "off"].indexOf(quota) < 0) return null;
  return { job_id: data.job_id, source_checksum: data.source_checksum, command_id: data.command_id,
    lease_hash: data.lease_hash, quota };
}

// The review the provider gave, as the runner normalized it: its items,
// their scores, evidence, and suggestions, and the total; or a review that
// was skipped, with a fixed reason.
function checkReview(review) {
  if (!isObject(review) || !jsonWithin(review, REVIEW_MAX_CHARS)) return false;
  if (!only(review, ["items", "total", "skipped", "reason"]) || !Array.isArray(review.items)) return false;
  if (!(typeof review.total === "number" && isFinite(review.total))) return false;
  if (has(review, "skipped") && typeof review.skipped !== "boolean") return false;
  if (has(review, "reason") && !(typeof review.reason === "string" && review.reason.length <= LABEL_MAX_CHARS)) {
    return false;
  }
  return review.items.length <= MAX_PARTS && review.items.every(isObject);
}

// review_finish: the job, the lease token review_start was answered for,
// and the review.
function checkReviewFinish(data) {
  if (!only(data, ["job_id", "lease", "review"])) return null;
  if (typeof data.job_id !== "string" || !RECORD_ID.test(data.job_id)) return null;
  if (typeof data.lease !== "string" || !TOKEN.test(data.lease)) return null;
  if (!checkReview(data.review)) return null;
  return { job_id: data.job_id, lease: data.lease, review: data.review };
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

// Every way a job ends goes through here, so its admission charge ends
// with it, in the same transaction (admission.js jobEnded).
function endJob(store, job, state, outcomeClass, cleanup, now) {
  job.state = state;
  job.outcome_class = outcomeClass;
  job.cleanup = cleanup;
  job.finished_at = now;
  job.cancel_requested = false;
  const saved = store.saveJob(job);
  store.jobEnded(saved, outcomeClass);
  return saved;
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

// status: the account's own job, whether a same-key retry would run it
// again, and, once it has ended, the user view of the envelope its last
// attempt ended with. A job can end with no envelope of its own (canceled
// while queued, or out of attempts), and an envelope reap wrote can say
// less than how the job ended, so only an envelope that matches the job's
// terminal state and class is shown. Another account's job is the same
// 404 as an unknown one. It reads and writes nothing else.
function status(store, account, input) {
  const job = store.getJob(input.job_id);
  if (job === null || job.account !== account.id) return { status: 404, body: { v: VERSION, error: "not_found" } };
  let envelope = null;
  if (isTerminal(job.state)) {
    const last = store.currentEnvelope(job);
    if (last !== null && last.state === job.state && last.outcome_class === job.outcome_class) envelope = last.user_view;
  }
  return { status: 200, body: { v: VERSION, job: jobView(job), retryable: retryable(job), envelope } };
}

// The purge: scratch jobs that ended more than SCRATCH_RETENTION_S ago,
// and those that never ended and were last queued that long ago (with
// the store off, nothing claims or reaps a job, so a queue the store left
// would stay), each with its envelopes, its attempts (they cascade from
// the job), and the admission command it was enqueued under (its leases
// cascade). A grading job stays, and so does a job a worker still holds:
// its current attempt's lease is live, so it may be running now. With the
// store off, no lease stays live.
function purge(store, now) {
  const jobs = store.purgeable(now - SCRATCH_RETENTION_S, PURGE_BATCH).filter((job) => !heldByAWorker(store, job, now));
  jobs.forEach((job) => {
    store.deleteEnvelopes(job.id);
    store.deleteCommandOf(job);
    store.deleteJob(job);
  });
  return { purged: jobs.length };
}

// Whether a worker still holds the job: it's leased or started, and its
// current attempt's lease hasn't run out.
function heldByAWorker(store, job, now) {
  if (ACTIVE.indexOf(job.state) < 0) return false;
  const attempt = store.currentAttempt(job);
  return attempt !== null && ACTIVE.indexOf(attempt.state) >= 0 && attempt.lease_expires_at > now;
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
    // The candidate starts now, so the job's admission charge is final.
    store.jobStarted(job);
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
  // A grading run's authoritative result comes with its graded content,
  // and nothing else does (PR 3).
  const grading = has(GRADED_FIELDS, job.kind) && result.authoritative;
  if (grading ? !(input.graded !== null && checkGraded(job.kind, input.graded, result)) : input.graded !== null) {
    return { status: 400, body: { v: VERSION, error: "invalid_request" } };
  }
  // Only a run that started can end with what the candidate did. A run
  // that never got a slot ends timed-out, infrastructure-degraded.
  if (result.authoritative && attempt.state !== "started") {
    return { status: 409, body: { v: VERSION, error: "not_started" } };
  }
  if (grading) return completeGraded(store, job, attempt, input, now);
  const envelope = writeEnvelope(store, job, attempt, result);
  endAttempt(store, attempt, result.state, result.outcome_class, result.cleanup, now, result.operator_view);
  endJob(store, job, result.state, result.outcome_class, result.cleanup, now);
  return { status: 200, body: { v: VERSION, envelope_id: envelope.id, job: jobView(store.getJob(job.id)) } };
}

// An authoritative grading result: its envelope, the graded row it names
// and that names it back, and both ends, all in complete's transaction.
// The row is the account's own: its item is the practice item's row for
// the definition's slug, and its campaign is kept only while that
// campaign is still the account's. When the item's row is gone, no row
// can hold the result, so nothing scores: the job ends failed,
// infrastructure-degraded, with the store's own envelope, and a same-key
// retry runs it again.
function completeGraded(store, job, attempt, input, now) {
  const result = input.result;
  const fields = GRADED_FIELDS[job.kind];
  const item = store.itemRow(fields.item, job.definition.slug);
  if (item === null) {
    const unsaved = serverEnvelope(job, attempt, "failed", "infrastructure-degraded", result.cleanup, now);
    const envelope = writeEnvelope(store, job, attempt, unsaved);
    endAttempt(store, attempt, "failed", "infrastructure-degraded", result.cleanup, now, result.operator_view);
    endJob(store, job, "failed", "infrastructure-degraded", result.cleanup, now);
    return { status: 200, body: { v: VERSION, envelope_id: envelope.id, job: jobView(store.getJob(job.id)) } };
  }
  const envelope = writeEnvelope(store, job, attempt, result);
  const row = store.saveGradedRow(fields.collection, gradedRow(store, job, envelope.id, input.graded, item));
  store.linkGradedRow(envelope, fields.collection, row.id);
  const operatorView = Object.assign({}, result.operator_view, { graded_row: row.id });
  endAttempt(store, attempt, result.state, result.outcome_class, result.cleanup, now, operatorView);
  endJob(store, job, result.state, result.outcome_class, result.cleanup, now);
  return { status: 200, body: { v: VERSION, envelope_id: envelope.id, job: jobView(store.getJob(job.id)) } };
}

function nonNegativeInt(value) {
  return isInt(value) && value >= 0 ? value : 0;
}

// The graded row for a job's authoritative result: the account, the item,
// what the job's input recorded (files, chats, notes, session time, and
// the campaign while it's the account's), and the graded content. Its
// rubric review is empty until the review route fills it.
function gradedRow(store, job, envelopeId, graded, itemId) {
  const input = isObject(job.input) ? job.input : {};
  const campaignId = typeof input.campaign_id === "string" && RECORD_ID.test(input.campaign_id) &&
    store.ownsCampaign(job.account, input.campaign_id) ? input.campaign_id : "";
  const chats = Array.isArray(input.ai_chats) ? input.ai_chats : [];
  const row = {
    user: job.account,
    campaign: campaignId,
    ai_chats: chats,
    rubric_review: null,
    status: "graded",
    duration_ms: nonNegativeInt(input.duration_ms),
    envelope: envelopeId,
  };
  row[GRADED_FIELDS[job.kind].link] = itemId;
  if (job.kind === "grade") {
    row.test_results = graded.test_results;
    row.current_checkpoint = graded.test_results.length - 1;
  } else {
    row.harness_output = graded.harness_output;
    row.files = isObject(input.files) ? input.files : {};
    row.notes = typeof input.notes === "string" ? input.notes : "";
    row.ai_assist_used = chats.length > 0;
  }
  return row;
}

// ---------------------------------------------------------------------------
// Rubric reviews (PR 3)
// ---------------------------------------------------------------------------

// The fingerprint of an envelope's review command: one envelope, one
// review.
function reviewFingerprint(store, envelopeId) {
  return store.hash(REVIEW_FINGERPRINT_PREFIX + envelopeId);
}

// The envelope a review is for: the job's own, the one its last attempt
// ended with, when it's authoritative, matches how the job ended, and
// names a graded row that's still there. Null otherwise.
function reviewable(store, job) {
  if (!isTerminal(job.state)) return null;
  const envelope = store.currentEnvelopeRecord(job);
  if (envelope === null || !envelope.authoritative || envelope.state !== job.state ||
      envelope.outcome_class !== job.outcome_class || !envelope.graded_row) return null;
  const row = store.getGradedRow(envelope.graded_collection, envelope.graded_row);
  if (row === null || row.user !== job.account || row.envelope !== envelope.id) return null;
  return { envelope, row };
}

// What a review's prompt is made of, besides the files the caller resent
// and the rubric the runner reads from the definition: the server's
// results and the chats the graded row holds.
function reviewMaterial(job, row) {
  return {
    kind: job.kind,
    definition: job.definition,
    results: job.kind === "grade" ? row.test_results : row.harness_output,
    ai_chats: Array.isArray(row.ai_chats) ? row.ai_chats : [],
  };
}

function reviewState(envelope) {
  const rubric = envelope.user_view ? envelope.user_view.rubric : null;
  return rubric && typeof rubric.state === "string" ? rubric.state : null;
}

function markRubric(store, envelope, state) {
  envelope.user_view = Object.assign({}, envelope.user_view, { rubric: { state } });
  store.saveEnvelopeView(envelope);
}

// review_start: before the runner calls a provider. For the account's own
// grading job that ended with an authoritative envelope and a graded row,
// and only when the resent files are the ones that ran:
//   - no review yet: its admission command is admitted (one request, no
//     wall seconds, a lease for the call) and the rubric is marked
//     requested, both or neither, and the answer carries what the prompt
//     needs. This is the only way a review is charged, so it's charged
//     once per envelope.
//   - requested, its lease live: in flight, 409.
//   - requested, its lease gone: the call never came back, so it's lost
//     (until #74 stages provider outcomes).
//   - completed or lost: answered as it is.
// Another account's job, an unknown one, and a scratch job are the same
// 404.
function reviewStart(store, account, input, now) {
  const job = store.getJob(input.job_id);
  if (job === null || job.account !== account.id || !has(GRADED_FIELDS, job.kind)) {
    return { status: 404, body: { v: VERSION, error: "not_found" } };
  }
  const found = reviewable(store, job);
  if (found === null) return { status: 409, body: { v: VERSION, error: "not_reviewable" } };
  if (job.source_checksum !== input.source_checksum) return { status: 409, body: { v: VERSION, error: "files_changed" } };
  const envelope = found.envelope;
  const fingerprint = reviewFingerprint(store, envelope.id);
  const state = reviewState(envelope);
  if (state === "requested") {
    const command = store.reviewCommand(account.id, fingerprint);
    if (command !== null && store.liveLeaseForCommand(command.id, now)) {
      return { status: 409, body: { v: VERSION, error: "in_flight", state } };
    }
    markRubric(store, envelope, "lost");
    return { status: 200, body: { v: VERSION, state: "lost" } };
  }
  if (state !== null) return { status: 200, body: { v: VERSION, state } };
  const admission = require(`${__hooks}/admission.js`);
  const admitted = admission.admit(store.admission(), { id: account.id, demo: account.demo === true }, {
    operation: REVIEW_OPERATION,
    command_id: input.command_id,
    fingerprint,
    wall_seconds: 0,
    max_wall_seconds: 0,
    idempotency: "enforce",
    quota: input.quota,
    lease_hash: input.lease_hash,
  }, now);
  if (admitted.invalid) return { status: 400, body: { v: VERSION, error: "invalid_request" } };
  if (admitted.idempotency !== "new" && admitted.idempotency !== "retry") {
    // The key already named another command, or this one is settled.
    return { status: 409, body: { v: VERSION, error: "mismatch" } };
  }
  if (!admitted.leased) {
    return { status: 429, body: { v: VERSION, error: "quota", quota: admitted.quota, retry_after: admitted.retry_after } };
  }
  markRubric(store, envelope, "requested");
  return { status: 200, body: { v: VERSION, state: "requested", material: reviewMaterial(job, found.row) } };
}

// review_finish: the review, into the graded row, while the lease
// review_start was answered for is still live. Then the rubric is
// completed and its command ends, its lease gone. A finish after the
// lease ran out comes too late: the rubric is lost, and nothing is
// written to the row.
function reviewFinish(store, account, input, now) {
  const job = store.getJob(input.job_id);
  if (job === null || job.account !== account.id || !has(GRADED_FIELDS, job.kind)) {
    return { status: 404, body: { v: VERSION, error: "not_found" } };
  }
  const found = reviewable(store, job);
  if (found === null || reviewState(found.envelope) !== "requested") {
    return { status: 409, body: { v: VERSION, error: "superseded" } };
  }
  const envelope = found.envelope;
  const admissionStore = store.admission();
  const lease = admissionStore.findLease(store.hash(input.lease));
  const command = lease !== null && lease.account === account.id ? admissionStore.getCommand(lease.command) : null;
  if (command === null || command.operation !== REVIEW_OPERATION ||
      command.fingerprint !== reviewFingerprint(store, envelope.id)) {
    return { status: 409, body: { v: VERSION, error: "superseded" } };
  }
  if (lease.expires_at <= now) {
    markRubric(store, envelope, "lost");
    return { status: 409, body: { v: VERSION, error: "superseded", state: "lost" } };
  }
  store.saveRubricReview(envelope.graded_collection, found.row, input.review);
  markRubric(store, envelope, "completed");
  const admission = require(`${__hooks}/admission.js`);
  admission.finish(admissionStore, { id: account.id }, { lease: input.lease, outcome: "completed", result: null }, now);
  return { status: 200, body: { v: VERSION, state: "completed" } };
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
    // The job's last attempt, by (job, attempt_number), or null.
    currentAttempt: (job) => attempt(first(ATTEMPTS, "job = {:job} && attempt_number = {:n}", { job: job.id, n: job.attempts })),
    // The envelope the job's last attempt ended with, or null: the
    // attempt by (job, attempt_number), then its one envelope.
    currentEnvelope: (job) => {
      const last = first(ATTEMPTS, "job = {:job} && attempt_number = {:n}", { job: job.id, n: job.attempts });
      if (last === null) return null;
      const record = first(ENVELOPES, "attempt = {:attempt}", { attempt: last.id });
      if (record === null) return null;
      return {
        state: record.getString("state"),
        outcome_class: record.getString("outcome_class"),
        user_view: json(record, "user_view"),
      };
    },
    // The same envelope as a row this transaction may update (PR 3).
    currentEnvelopeRecord: (job) => {
      const last = first(ATTEMPTS, "job = {:job} && attempt_number = {:n}", { job: job.id, n: job.attempts });
      if (last === null) return null;
      const record = first(ENVELOPES, "attempt = {:attempt}", { attempt: last.id });
      if (record === null) return null;
      return {
        id: record.id,
        state: record.getString("state"),
        outcome_class: record.getString("outcome_class"),
        authoritative: record.getBool("authoritative"),
        user_view: json(record, "user_view"),
        graded_collection: record.getString("graded_collection"),
        graded_row: record.getString("graded_row"),
        _record: record,
      };
    },
    saveEnvelopeView: (row) => {
      row._record.set("user_view", row.user_view);
      dao.saveRecord(row._record);
      return row;
    },
    // The graded row a grading job's envelope names, and names it back.
    linkGradedRow: (envelope, collectionName, rowId) => {
      const record = envelope._record || dao.findRecordById(ENVELOPES, envelope.id);
      record.set("graded_collection", collectionName);
      record.set("graded_row", rowId);
      dao.saveRecord(record);
    },
    // The practice item's own row, by its slug, or null.
    itemRow: (collectionName, slug) => {
      const record = first(collectionName, "slug = {:slug}", { slug });
      return record === null ? null : record.id;
    },
    // Whether the campaign is still the account's own.
    ownsCampaign: (account, campaignId) => {
      const record = first("campaigns", "id = {:id}", { id: campaignId });
      return record !== null && record.getString("user") === account;
    },
    saveGradedRow: (collectionName, row) => {
      const record = new Record(collection(collectionName));
      Object.keys(row).forEach((field) => record.set(field, row[field]));
      dao.saveRecord(record);
      return { id: record.id };
    },
    getGradedRow: (collectionName, id) => {
      if (collectionName !== "ai_coding_attempts" && collectionName !== "take_home_attempts") return null;
      const record = first(collectionName, "id = {:id}", { id });
      if (record === null) return null;
      return {
        id: record.id,
        user: record.getString("user"),
        envelope: record.getString("envelope"),
        test_results: json(record, "test_results"),
        harness_output: json(record, "harness_output"),
        ai_chats: json(record, "ai_chats"),
        _record: record,
      };
    },
    saveRubricReview: (_collectionName, row, review) => {
      row._record.set("rubric_review", review);
      dao.saveRecord(row._record);
    },
    // An envelope's review command, by the fingerprint that names the
    // envelope, and whether a lease of it is still live.
    reviewCommand: (account, fingerprint) => {
      const record = first(COMMANDS, "account = {:account} && operation = 'review' && fingerprint = {:fp}",
        { account, fp: fingerprint });
      return record === null ? null : { id: record.id };
    },
    liveLeaseForCommand: (commandId, now) =>
      first("admission_leases", "command = {:id} && expires_at > {:now}", { id: commandId, now }) !== null,
    // admission.js's store over the same transaction.
    admission: () => require(`${__hooks}/admission.js`).pbStore(dao),
    // The job's admission charge (admission.js), in this transaction.
    jobStarted: (row) => {
      const admission = require(`${__hooks}/admission.js`);
      admission.jobStarted(admission.pbStore(dao), row.account, row.command_id, row.id);
    },
    jobEnded: (row, outcomeClass) => {
      const admission = require(`${__hooks}/admission.js`);
      admission.jobEnded(admission.pbStore(dao), row.account, row.command_id, row.id, outcomeClass);
    },
    // Scratch jobs that ended at or before `cutoff`, and those that never
    // ended and were last queued at or before it, at most `limit`.
    purgeable: (cutoff, limit) =>
      dao
        .findRecordsByFilter(
          JOBS,
          "purpose = 'scratch' && ((finished_at > 0 && finished_at <= {:cutoff} && " +
            "(state = 'completed' || state = 'timed-out' || state = 'denied' || state = 'canceled' || state = 'failed')) || " +
            "((state = 'queued' || state = 'leased' || state = 'started') && queued_at <= {:cutoff}))",
          "finished_at,queued_at",
          limit,
          0,
          { cutoff },
        )
        .map(job),
    deleteEnvelopes: (jobId) => {
      dao.findRecordsByFilter(ENVELOPES, "job = {:job}", "", 0, 0, { job: jobId }).forEach((r) => dao.deleteRecord(r));
    },
    // The admission command the job was enqueued under, when it still
    // names this job; its leases go with it.
    deleteCommandOf: (row) => {
      const found = first(COMMANDS, "account = {:account} && command_id = {:id}", { account: row.account, id: row.command_id });
      if (found !== null && found.getString("job") === row.id) dao.deleteRecord(found);
    },
    deleteJob: (row) => dao.deleteRecord(row._record),
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

const CALLER_CHECKS = {
  enqueue: checkEnqueue,
  cancel: checkCancel,
  status: checkStatus,
  review_start: checkReviewStart,
  review_finish: checkReviewFinish,
};
const CALLER_WRITES = {
  enqueue: (store, account, input, now) => enqueue(store, account, input, now),
  cancel: (store, account, input, now) => cancel(store, account, input, now),
  review_start: (store, account, input, now) => reviewStart(store, account, input, now),
  review_finish: (store, account, input, now) => reviewFinish(store, account, input, now),
};
const SERVICE_CHECKS = { claim: checkClaim, heartbeat: checkHeartbeat, complete: checkComplete, reap: checkReap };

function inTransaction(fn) {
  let out = null;
  $app.dao().runInTransaction((txDao) => {
    out = fn(pbStore(txDao));
  });
  return out;
}

// enqueue, cancel, status, and the review's start and finish (PR 3): the
// account and its tier come from the bearer, never the body, and the
// runner key has to come too. status only reads, so it runs outside a
// transaction and never waits on the write connection.
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
  const account = { id: record.id, demo: admission.tierOf(record) === "demo" };
  if (action === "status") {
    const read = status(pbStore($app.dao()), account, input);
    return c.json(read.status, read.body);
  }
  const now = nowSeconds();
  const out = inTransaction((store) => CALLER_WRITES[action](store, account, input, now));
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

// The purge, from the cron in execution.pb.js. It runs whether the store's
// gate is on or off, since it only removes jobs that ended or have waited
// longer than any run lasts, and logs a count, never a row, when it
// removed any.
function purgeNow() {
  const dao = $app.dao();
  try {
    dao.findCollectionByNameOrId(JOBS);
  } catch (_) {
    return { purged: 0 };
  }
  const out = inTransaction((store) => purge(store, nowSeconds()));
  if (out.purged > 0) {
    console.log(JSON.stringify({ v: "obs/v1", event: "execution_purge", service: "pocketbase", purged: out.purged }));
  }
  return out;
}

// Whether a login request named the service collection exactly. A login
// under any other spelling of it, or under its id, gets the 404 an
// unknown collection gets, whatever the proxy in front let through.
function exactServicePath(httpContext) {
  if (!httpContext) return false;
  try {
    return httpContext.pathParam("collection") === SERVICE_COLLECTION;
  } catch (_) {
    return false;
  }
}

// Before PocketBase checks an execution_service login: the worker login
// answers only its exact collection name. Then execution-worker follows
// the secret, and the check uses the record as it is now.
function syncWorkerForLogin(e) {
  if (!exactServicePath(e.httpContext)) throw new NotFoundError();
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
  SCRATCH_RETENTION_S,
  PURGE_BATCH,
  ACTIVE,
  checkEnqueue,
  checkCancel,
  checkStatus,
  checkClaim,
  checkHeartbeat,
  checkComplete,
  checkResult,
  checkReap,
  checkGraded,
  checkReviewStart,
  checkReviewFinish,
  GRADED_FIELDS,
  REVIEW_OPERATION,
  retryable,
  enqueue,
  cancel,
  status,
  claim,
  heartbeat,
  complete,
  reap,
  purge,
  reviewStart,
  reviewFinish,
  ensureWorker,
  usableSecret,
  pbStore,
  handleCaller,
  handleService,
  purgeNow,
  bootstrapWorker,
  syncWorkerForLogin,
  guardEnvelopeCreate,
  guardEnvelopeUpdate,
};
