// Shared HTTP helper for the FastAPI runner endpoints (/api/ai/*,
// /api/share/*, /api/pdf/*, /api/run, /api/evaluate). Three concerns
// were duplicated across feature folders before this lived here:
//
//   1. Threading the PocketBase auth token through as a Bearer header.
//   2. Parsing FastAPI's `{detail: "..."}` error envelope back into a
//      readable Error message.
//   3. Consuming the SSE shape `data: {delta|done|error}` for the
//      improve / cover-letter streams.
//
// PocketBase SDK calls (collections, records, auth) still go through
// the `pb` client directly — this helper is only for the runner.
//
// Failures throw a `RunnerError` that keeps the old message format
// (`"<prefix> <status>: <detail>"`) and adds the typed parts of the
// runner's error envelope: HTTP status, `code`, `Retry-After`, and the
// correlation id. Unsafe methods carry one `Idempotency-Key` per call,
// and a denial that a moment's wait can clear is retried with that same
// key, so the runner treats the retry as the same command.

import { mintIdempotencyKey } from './idempotency';
import { pb } from './pocketbase';

export type RunnerInit = {
  method?: string;
  /** Auto-serialized via JSON.stringify; pass an already-stringified
   *  body to opt out. */
  body?: unknown;
  headers?: HeadersInit;
  signal?: AbortSignal;
  /** Default `'required'` — throw if no PB token is present.
   *  `'optional'` includes the token when present, omits otherwise.
   *  `'none'` never sends the token (e.g. anonymous /share/by-token). */
  auth?: 'required' | 'optional' | 'none';
  /** Prefix on thrown error messages, e.g. `'AI'` → `"AI 503: …"`. */
  errorPrefix?: string;
  /** One key per user action. POST, PUT, PATCH, and DELETE mint one
   *  when this is omitted; pass a failed action's key to retry it. The
   *  runner keys its command record on it: a completed command's retry
   *  gets the stored result back. */
  idempotencyKey?: string;
  /** How many times a retryable denial is retried with the same key.
   *  Defaults to `RETRY_DELAYS_MS.length` for a call that carries a key;
   *  reads are never retried. */
  retries?: number;
};

export const IDEMPOTENCY_HEADER = 'Idempotency-Key';
export const CORRELATION_HEADER = 'X-Correlation-Id';

/** Denials a short wait can clear: PocketBase, the admission store, or
 *  every worker was briefly unavailable. The runner leaves such a
 *  command retryable, so a same-key retry runs admission again. A retry
 *  that finds its command still running (`already_in_flight`) isn't
 *  retried again; the caller shows it as unavailable, and the next try
 *  sends a new key. */
export const RETRYABLE_CODES: ReadonlySet<string> = new Set([
  'auth_unavailable',
  'quota_unavailable',
  'worker_unavailable',
]);
/** The wait before each retry, unless the response's Retry-After asks
 *  for a wait no longer than `MAX_RETRY_AFTER_S`. */
export const RETRY_DELAYS_MS: readonly number[] = [1000, 3000];
const MAX_RETRY_AFTER_S = 10;

const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
const CODE_PATTERN = /^[a-z][a-z0-9_]{0,63}$/;
const CORRELATION_PATTERN = /^[0-9a-f]{32}$/;

type RunnerErrorInit = {
  message: string;
  /** HTTP status; 0 when no response arrived (no token, network). */
  status: number;
  code?: string | null;
  detail?: string;
  correlationId?: string | null;
  retryAfterSeconds?: number | null;
  idempotencyKey?: string | null;
  cause?: unknown;
};

export class RunnerError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly detail: string;
  readonly correlationId: string | null;
  readonly retryAfterSeconds: number | null;
  readonly idempotencyKey: string | null;

  constructor(init: RunnerErrorInit) {
    super(init.message);
    // `name` stays "Error" so `String(err)` reads as it did before;
    // `isRunnerError` tells the types apart.
    this.status = init.status;
    this.code = init.code ?? null;
    this.detail = init.detail ?? init.message;
    this.correlationId = init.correlationId ?? null;
    this.retryAfterSeconds = init.retryAfterSeconds ?? null;
    this.idempotencyKey = init.idempotencyKey ?? null;
    if (init.cause !== undefined) {
      (this as { cause?: unknown }).cause = init.cause;
    }
  }
}

export function isRunnerError(err: unknown): err is RunnerError {
  return err instanceof RunnerError;
}

// IMF-fixdate, the HTTP date form servers send. `Date.parse` alone would
// read strings like "1.5" as dates.
const HTTP_DATE_PATTERN = /^[A-Z][a-z]{2}, \d{2} [A-Z][a-z]{2} \d{4} \d{2}:\d{2}:\d{2} GMT$/;

/** Seconds to wait from a `Retry-After` value (delta-seconds or an
 *  HTTP date), or null when it's missing or unreadable. */
export function parseRetryAfter(
  value: string | null | undefined,
  now: number = Date.now(),
): number | null {
  const v = value?.trim();
  if (!v) return null;
  if (/^\d+$/.test(v)) return Number(v);
  if (!HTTP_DATE_PATTERN.test(v)) return null;
  const at = Date.parse(v);
  if (Number.isNaN(at)) return null;
  return Math.max(0, Math.ceil((at - now) / 1000));
}

export async function runnerJSON<T>(path: string, init: RunnerInit = {}): Promise<T> {
  const res = await runnerFetch(path, init);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export async function runnerFetch(
  path: string,
  init: RunnerInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);
  if (init.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  const auth = init.auth ?? 'required';
  if (auth !== 'none') {
    const token = pb.authStore.token;
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    } else if (auth === 'required') {
      throw new RunnerError({
        message: 'Not authenticated.',
        status: 0,
        code: 'unauthenticated',
      });
    }
  }
  let idempotencyKey: string | null = null;
  if (UNSAFE_METHODS.has((init.method ?? 'GET').toUpperCase())) {
    idempotencyKey =
      init.idempotencyKey ?? headers.get(IDEMPOTENCY_HEADER) ?? mintIdempotencyKey();
    headers.set(IDEMPOTENCY_HEADER, idempotencyKey);
  }
  const body =
    init.body === undefined
      ? undefined
      : typeof init.body === 'string'
        ? init.body
        : JSON.stringify(init.body);
  const retries =
    idempotencyKey === null ? 0 : Math.max(0, Math.floor(init.retries ?? RETRY_DELAYS_MS.length));
  for (let attempt = 0; ; attempt += 1) {
    let res: Response;
    try {
      res = await fetch(path, {
        method: init.method,
        headers,
        body,
        signal: init.signal,
      });
    } catch (err) {
      // Callers rely on AbortError to tell a cancel from a failure.
      if ((err as Error | undefined)?.name === 'AbortError') throw err;
      const message = (err as Error | undefined)?.message || 'Network request failed.';
      throw new RunnerError({ message, status: 0, idempotencyKey, cause: err });
    }
    if (res.ok) return res;
    const error = await runnerErrorFromResponse(res, init.errorPrefix, idempotencyKey);
    if (attempt >= retries || error.code === null || !RETRYABLE_CODES.has(error.code)) throw error;
    await wait(retryDelayMs(error, attempt), init.signal);
  }
}

function retryDelayMs(error: RunnerError, attempt: number): number {
  const asked = error.retryAfterSeconds;
  if (asked !== null && asked <= MAX_RETRY_AFTER_S) return asked * 1000;
  return RETRY_DELAYS_MS[Math.min(attempt, RETRY_DELAYS_MS.length - 1)] ?? 0;
}

function wait(ms: number, signal: AbortSignal | undefined): Promise<void> {
  return new Promise((resolve, reject) => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    const aborted = () => {
      if (timer !== undefined) clearTimeout(timer);
      reject(new DOMException('The operation was aborted.', 'AbortError'));
    };
    if (signal?.aborted) {
      aborted();
      return;
    }
    timer = setTimeout(() => {
      signal?.removeEventListener('abort', aborted);
      resolve();
    }, ms);
    signal?.addEventListener('abort', aborted, { once: true });
  });
}

async function runnerErrorFromResponse(
  res: Response,
  errorPrefix: string | undefined,
  idempotencyKey: string | null,
): Promise<RunnerError> {
  const parsed = await _extractErrorDetail(res);
  const headerId = res.headers.get(CORRELATION_HEADER);
  const correlationId =
    parsed.correlationId ??
    (headerId && CORRELATION_PATTERN.test(headerId) ? headerId : null);
  return new RunnerError({
    message: `${errorPrefix ?? 'Request'} ${res.status}: ${parsed.detail}`,
    status: res.status,
    code: parsed.code,
    detail: parsed.detail,
    correlationId,
    retryAfterSeconds: parseRetryAfter(res.headers.get('Retry-After')),
    idempotencyKey,
  });
}

async function _extractErrorDetail(
  res: Response,
): Promise<{ detail: string; code: string | null; correlationId: string | null }> {
  const text = await res.text().catch(() => res.statusText);
  if (!text) return { detail: res.statusText, code: null, correlationId: null };
  try {
    const j = JSON.parse(text) as {
      detail?: unknown;
      code?: unknown;
      correlation_id?: unknown;
    } | null;
    if (j && typeof j === 'object') {
      const code = typeof j.code === 'string' && CODE_PATTERN.test(j.code) ? j.code : null;
      const correlationId =
        typeof j.correlation_id === 'string' && CORRELATION_PATTERN.test(j.correlation_id)
          ? j.correlation_id
          : null;
      if (typeof j.detail === 'string' && j.detail) {
        return { detail: j.detail, code, correlationId };
      }
      if (Array.isArray(j.detail)) {
        // FastAPI validation errors: a list of {msg, loc, ...}.
        const msgs = j.detail
          .map((d) => (d && typeof d === 'object' ? (d as { msg?: unknown }).msg : undefined))
          .filter((m): m is string => typeof m === 'string' && m.length > 0);
        if (msgs.length > 0) return { detail: msgs.join('; '), code, correlationId };
      }
      return { detail: text, code, correlationId };
    }
  } catch {
    /* not JSON, return raw */
  }
  return { detail: text, code: null, correlationId: null };
}

// ---- SSE helpers --------------------------------------------------------

export type SSEHandlers = {
  onDelta: (chunk: string) => void;
  onDone?: () => void;
  onError?: (err: Error) => void;
  onEvent?: (event: SSEEvent) => void;
};

export type SSEEvent = {
  delta?: string;
  done?: boolean;
  error?: string;
  /** Set by the backend on error events for support correlation. */
  request_id?: string;
  /** Set by /api/ai-coding/edit on its sidecar patches event.
   *  Shape: PatchProposal[]. Typed as `unknown` here to avoid a
   *  cross-module dependency on AIPatchView; consumers narrow. */
  patches?: unknown;
};

/** Consume a `text/event-stream` response shaped as
 *  `data: {delta|done|error|request_id}\n\n` chunks. Returns when the
 *  stream emits `done`, errors, or the underlying reader closes. */
export async function consumeSSE(
  res: Response,
  handlers: SSEHandlers,
): Promise<void> {
  if (!res.body) {
    handlers.onError?.(new Error('No response body for SSE.'));
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let idx: number;
      while ((idx = buffer.indexOf('\n\n')) >= 0) {
        const event = buffer.slice(0, idx);
        buffer = buffer.slice(idx + 2);
        for (const line of event.split('\n')) {
          if (!line.startsWith('data:')) continue;
          const payload = line.slice(5).trim();
          if (!payload) continue;
          let obj: SSEEvent;
          try {
            obj = JSON.parse(payload) as SSEEvent;
          } catch {
            continue;
          }
          if (obj.error) {
            handlers.onError?.(new Error(obj.error));
            return;
          }
          if (obj.delta) handlers.onDelta(obj.delta);
          // onEvent is for sidecar events (e.g. /edit's `patches` payload)
          // — skip the hot-path delta and the terminal done so handlers
          // don't have to filter every chunk themselves.
          if (!obj.delta && !obj.done) {
            handlers.onEvent?.(obj);
          }
          if (obj.done) {
            handlers.onDone?.();
            return;
          }
        }
      }
    }
    handlers.onDone?.();
  } catch (err) {
    if ((err as Error).name === 'AbortError') return;
    handlers.onError?.(err as Error);
  }
}

/** Open a runner endpoint as SSE and consume it. Errors thrown by the
 *  initial fetch are routed through `onError` (same surface as
 *  per-event errors), which keeps callers from needing two error paths. */
export async function runnerSSE(
  path: string,
  init: RunnerInit & SSEHandlers,
): Promise<void> {
  const { onDelta, onDone, onError, onEvent, ...rest } = init;
  let res: Response;
  try {
    res = await runnerFetch(path, rest);
  } catch (err) {
    onError?.(err as Error);
    return;
  }
  await consumeSSE(res, { onDelta, onDone, onError, onEvent });
}
