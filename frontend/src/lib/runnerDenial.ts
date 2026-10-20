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
//
// The definition refusals (ROUNDS-00A-L02) say what the page should do:
// an out-of-date page reloads (an older request shape, a case or
// version the server replaced), a retired or missing practice item runs
// nothing, and an unsupported language or a file the grader won't take
// shows the server's fixed sentence, which never repeats the request.

import { isRunnerError } from './runnerFetch';

export type RunnerDenialKind =
  | 'sign_in'
  | 'limit'
  | 'turned_off'
  | 'unavailable'
  | 'too_large'
  | 'not_permitted'
  | 'reload'
  | 'retired'
  | 'not_found'
  | 'unsupported'
  | 'path_not_allowed';

export interface RunnerDenial {
  kind: RunnerDenialKind;
  status: number;
  code: string | null;
  retryAfterSeconds: number | null;
  correlationId: string | null;
  /** The server's fixed sentence, for the kinds that show it. */
  detail?: string | null;
  /** The control that started the action; focus returns to it when
   *  the action dropped focus (a disabled button) and nothing else
   *  took it. */
  trigger?: HTMLElement | null;
}

const LIMIT_CODES = new Set(['quota_exceeded', 'demo_limit_reached']);
const RELOAD_CODES = new Set(['legacy_request_rejected', 'case_unknown', 'definition_superseded']);
const DEFINITION_KINDS: Record<string, RunnerDenialKind> = {
  definition_retired: 'retired',
  definition_not_found: 'not_found',
  runtime_unsupported: 'unsupported',
  path_not_allowed: 'path_not_allowed',
};
const SHOWS_DETAIL = new Set<RunnerDenialKind>(['unsupported', 'path_not_allowed']);
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
  // definitions_disabled is ROUNDS_GATE_EXECUTION_DEFINITIONS turned off.
  if (code === 'route_disabled' || code === 'definitions_disabled') kind = 'turned_off';
  else if (code !== null && RELOAD_CODES.has(code)) kind = 'reload';
  else if (code !== null && code in DEFINITION_KINDS) kind = DEFINITION_KINDS[code];
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
    detail: SHOWS_DETAIL.has(kind) && err.detail ? err.detail : null,
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
