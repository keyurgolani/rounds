// Durable execution jobs on the runner's scratch routes (ROUNDS-00A-L03).
//
// While ROUNDS_GATE_EXECUTION_SCRATCH is on, the four scratch routes (a
// coding run and test run, a project run, and a take-home run) don't run
// in their request. They answer 202 with a job:
//
//   { job_id, state, outcome_class, retryable, cancel_requested, envelope }
//
// and the page follows it with GET /api/execution/jobs/{job_id}?wait=20,
// which answers the same shape once the job changed or ended. The
// envelope is the user view of rounds.execution-envelope/v1, and its
// `output` is the body the route answers in its request, shown only on
// an end the run earned (`earnedOutput`). Until PR 4 a route may answer
// either way, so a caller takes both: `isJobAnswer` tells them apart.
// TODO(ROUNDS-00A-L03): PR 4 retires the in-request answer, and with it
// the pages' handling of a 200.
//
// One command id per user action lives in sessionStorage, with the job
// id once the 202 arrives and a hash of the work it sent. A reload picks
// the job back up, and Retry sends the same work under the same id, so
// the runner runs that job again instead of starting a new one; work
// that changed since gets a new id.

import { mintIdempotencyKey } from './idempotency';
import { RunnerError, runnerJSON } from './runnerFetch';

export const JOB_STATES = [
  'queued',
  'leased',
  'started',
  'completed',
  'timed-out',
  'denied',
  'canceled',
  'failed',
] as const;
export type JobState = (typeof JOB_STATES)[number];

export const OUTCOME_CLASSES = [
  'passed',
  'candidate-failure',
  'resource-limit',
  'definition-invalid',
  'policy-violation',
  'canceled',
  'worker-lost',
  'infrastructure-degraded',
] as const;
export type OutcomeClass = (typeof OUTCOME_CLASSES)[number];

export const JOB_LIMITS = ['wall_time', 'cpu_time', 'memory', 'processes', 'files', 'output'] as const;
export type JobLimit = (typeof JOB_LIMITS)[number];

export interface JobPart {
  id: string;
  outcome_class: OutcomeClass;
  limit: JobLimit | null;
}

/** The envelope's user view: no hidden material, and `output` is the
 *  visible answer a scratch run shows, at most 256 KiB. */
export interface JobEnvelope {
  version: string;
  job_id: string;
  state: JobState;
  outcome_class: OutcomeClass;
  authoritative: boolean;
  limit: JobLimit | null;
  parts: JobPart[];
  score: number | null;
  definition: Record<string, unknown> | null;
  queued_at: number;
  started_at: number | null;
  finished_at: number;
  cleanup: string;
  rubric: unknown;
  output: Record<string, unknown> | null;
}

export interface JobAnswer {
  job_id: string;
  state: JobState;
  outcome_class: OutcomeClass | null;
  /** Whether a same-key retry would run the job again. */
  retryable: boolean;
  cancel_requested: boolean;
  /** Set once the job ended with an envelope. */
  envelope: JobEnvelope | null;
}

/** What a call to a scratch route sends besides its body: the action's
 *  command id, so a retry or a reload stays the same command. */
export interface RunnerCallInit {
  idempotencyKey?: string;
}

const JOB_ID = /^[a-z0-9]{15}$/;
const ENDED: ReadonlySet<JobState> = new Set(['completed', 'timed-out', 'denied', 'canceled', 'failed']);

export function isEnded(state: JobState): boolean {
  return ENDED.has(state);
}

// The ends the candidate's code earned. Every other end (a limit, a
// cancel, an end the definition or the infrastructure caused) shows its
// own notice and no output, since a body from such an end holds a score
// or a failure nothing earned.
const EARNED: ReadonlySet<OutcomeClass> = new Set(['passed', 'candidate-failure']);

/** The output an ended job shows: the envelope's, only when the run
 *  earned its end; null on every other end. */
export function earnedOutput(job: JobAnswer): Record<string, unknown> | null {
  const envelope = job.envelope;
  if (envelope === null || envelope.output === null || typeof envelope.output !== 'object') return null;
  if (!EARNED.has(envelope.outcome_class) || job.outcome_class !== envelope.outcome_class) return null;
  return envelope.output;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** Whether a route's answer is a job rather than the body it answers in
 *  its request. */
export function isJobAnswer(value: unknown): value is JobAnswer {
  if (!isObject(value)) return false;
  const { job_id, state, outcome_class, retryable, cancel_requested, envelope } = value;
  return (
    typeof job_id === 'string' &&
    JOB_ID.test(job_id) &&
    (JOB_STATES as readonly unknown[]).includes(state) &&
    (outcome_class === null || (OUTCOME_CLASSES as readonly unknown[]).includes(outcome_class)) &&
    typeof retryable === 'boolean' &&
    typeof cancel_requested === 'boolean' &&
    (envelope === null || (isObject(envelope) && Array.isArray(envelope.parts)))
  );
}

/** The longest a job read waits for its job to change. */
export const WAIT_S = 20;
/** The waits between job reads that failed, up to the last. */
export const BACKOFF_MS: readonly number[] = [1000, 2000, 5000, 10000, 15000];

// An answer in no shape this page knows reads as the server failing, so
// the poll backs off and asks again.
function malformed(): RunnerError {
  return new RunnerError({ message: "job 502: The server's answer wasn't a job.", status: 502 });
}

/** The account's job as it is, or once it changed or ended within
 *  `waitS` seconds. Another account's job and an unknown one are the
 *  same 404. */
export async function readJob(jobId: string, waitS: number, signal?: AbortSignal): Promise<JobAnswer> {
  const wait = Math.max(0, Math.min(WAIT_S, Math.floor(waitS)));
  const answer = await runnerJSON<unknown>(`/api/execution/jobs/${encodeURIComponent(jobId)}?wait=${wait}`, {
    signal,
    errorPrefix: 'job',
  });
  if (!isJobAnswer(answer)) throw malformed();
  return answer;
}

/** Asks the account's job to stop: a queued one ends at once, a running
 *  one within a few seconds. Asking again changes nothing. */
export async function cancelJob(jobId: string): Promise<JobAnswer> {
  const answer = await runnerJSON<unknown>(`/api/execution/jobs/${encodeURIComponent(jobId)}/cancel`, {
    method: 'POST',
    errorPrefix: 'job',
  });
  if (!isJobAnswer(answer)) throw malformed();
  return answer;
}

// ---- one action's id, kept for the tab --------------------------------

const STORAGE_PREFIX = 'rounds:job:';
/** How long a kept action stays resumable. Ended scratch jobs are kept
 *  for 7 days; a tab rarely lives a day. */
export const ACTION_MAX_AGE_MS = 24 * 60 * 60 * 1000;

export interface StoredAction {
  v: 1;
  /** The Idempotency-Key the action sent: the runner's command id. */
  key: string;
  /** `workHash` of what it sent. */
  hash: string;
  /** Its job, once the route answered 202. */
  jobId: string | null;
  at: number;
}

function storage(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

export function loadAction(scope: string, now: number = Date.now()): StoredAction | null {
  try {
    const raw = storage()?.getItem(STORAGE_PREFIX + scope);
    if (!raw) return null;
    const value = JSON.parse(raw) as Partial<StoredAction> | null;
    if (
      !value ||
      value.v !== 1 ||
      typeof value.key !== 'string' ||
      typeof value.hash !== 'string' ||
      !(value.jobId === null || (typeof value.jobId === 'string' && JOB_ID.test(value.jobId))) ||
      typeof value.at !== 'number' ||
      now - value.at > ACTION_MAX_AGE_MS
    ) {
      return null;
    }
    return value as StoredAction;
  } catch {
    return null;
  }
}

export function saveAction(scope: string, action: StoredAction): void {
  try {
    storage()?.setItem(STORAGE_PREFIX + scope, JSON.stringify(action));
  } catch {
    // A full or blocked storage only costs resuming after a reload.
  }
}

export function clearAction(scope: string): void {
  try {
    storage()?.removeItem(STORAGE_PREFIX + scope);
  } catch {
    /* nothing kept */
  }
}

function stable(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(stable);
  if (isObject(value)) {
    const out: Record<string, unknown> = {};
    for (const key of Object.keys(value).sort()) out[key] = stable(value[key]);
    return out;
  }
  return value;
}

/** A short hash of `work`'s JSON with its keys sorted: whether a retry
 *  sends the same work, never a secret. */
export function workHash(work: unknown): string {
  const text = JSON.stringify(stable(work)) ?? '';
  // cyrb53: two 32-bit lanes, enough to tell edits apart.
  let h1 = 0xdeadbeef;
  let h2 = 0x41c6ce57;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text.charCodeAt(i);
    h1 = Math.imul(h1 ^ ch, 2654435761);
    h2 = Math.imul(h2 ^ ch, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (h2 >>> 0).toString(16).padStart(8, '0') + (h1 >>> 0).toString(16).padStart(8, '0');
}

/** The command id an action on `work` sends. A retry of the kept
 *  action's same work keeps its id, so the runner runs that job again;
 *  anything else is a new action with a new id, kept for the tab. */
export function beginAction(scope: string, work: unknown, retry = false, now: number = Date.now()): StoredAction {
  const hash = workHash(work);
  const kept = loadAction(scope, now);
  if (retry && kept !== null && kept.hash === hash) {
    const again = { ...kept, at: now };
    saveAction(scope, again);
    return again;
  }
  const action: StoredAction = { v: 1, key: mintIdempotencyKey(now), hash, jobId: null, at: now };
  saveAction(scope, action);
  return action;
}
