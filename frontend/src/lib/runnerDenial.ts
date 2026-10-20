// Maps a runner failure onto the denial states the execution and render
// surfaces show instead of raw errors (ROUNDS-00A-L01).
//
// The typed `code` from the runner's envelope decides first. Older
// servers and proxies answer without a code, so the HTTP status is the
// fallback: 401 sign in, 413 too large, 429 limit, 5xx or no response
// unavailable. Anything else isn't a denial, and callers keep showing
// the error the way they did before.
//
// The idempotency refusals show as unavailable: the action's key was
// refused, already used, or its command is still running, and the next
// try sends a new key.

import { isRunnerError } from './runnerFetch';

export type RunnerDenialKind =
  | 'sign_in'
  | 'limit'
  | 'turned_off'
  | 'unavailable'
  | 'too_large'
  | 'not_permitted';

export interface RunnerDenial {
  kind: RunnerDenialKind;
  status: number;
  code: string | null;
  retryAfterSeconds: number | null;
  correlationId: string | null;
  /** The control that started the action; focus returns to it when
   *  the action dropped focus (a disabled button) and nothing else
   *  took it. */
  trigger?: HTMLElement | null;
}

const LIMIT_CODES = new Set(['quota_exceeded', 'demo_limit_reached']);
const TOO_LARGE_CODES = new Set(['payload_too_large', 'limit_exceeded']);
const UNAVAILABLE_CODES = new Set([
  'auth_unavailable',
  'quota_unavailable',
  'worker_unavailable',
  'idempotency_key_required',
  'already_completed',
  'idempotency_mismatch',
  'already_in_flight',
]);

export function classifyRunnerError(
  err: unknown,
  trigger: HTMLElement | null = null,
): RunnerDenial | null {
  if (!isRunnerError(err)) return null;
  const { status, code } = err;
  let kind: RunnerDenialKind | null = null;
  if (code === 'route_disabled') kind = 'turned_off';
  else if (code === 'unauthenticated' || status === 401) kind = 'sign_in';
  else if ((code !== null && LIMIT_CODES.has(code)) || status === 429) kind = 'limit';
  else if ((code !== null && TOO_LARGE_CODES.has(code)) || status === 413) kind = 'too_large';
  else if (code === 'not_permitted') kind = 'not_permitted';
  else if ((code !== null && UNAVAILABLE_CODES.has(code)) || status === 0 || status >= 500) {
    kind = 'unavailable';
  }
  if (kind === null) return null;
  return {
    kind,
    status,
    code,
    retryAfterSeconds: err.retryAfterSeconds,
    correlationId: err.correlationId,
    trigger,
  };
}

/** The element that has focus now, so a denial can hand it back. */
export function activeTrigger(): HTMLElement | null {
  if (typeof document === 'undefined') return null;
  const el = document.activeElement;
  return el instanceof HTMLElement && el !== document.body ? el : null;
}

/** "in 45 seconds", "in 5 minutes", "in 2 hours", or "later". */
export function formatWait(seconds: number | null): string {
  if (seconds === null || !Number.isFinite(seconds) || seconds < 0) return 'later';
  if (seconds < 60) {
    const s = Math.max(1, Math.ceil(seconds));
    return `in ${s} second${s === 1 ? '' : 's'}`;
  }
  if (seconds < 3600) {
    const m = Math.ceil(seconds / 60);
    return `in ${m} minute${m === 1 ? '' : 's'}`;
  }
  const h = Math.ceil(seconds / 3600);
  return `in ${h} hour${h === 1 ? '' : 's'}`;
}
