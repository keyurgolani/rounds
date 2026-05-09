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
};

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
      throw new Error('Not authenticated.');
    }
  }
  const body =
    init.body === undefined
      ? undefined
      : typeof init.body === 'string'
        ? init.body
        : JSON.stringify(init.body);
  const res = await fetch(path, {
    method: init.method,
    headers,
    body,
    signal: init.signal,
  });
  if (!res.ok) {
    const detail = await _extractErrorDetail(res);
    throw new Error(`${init.errorPrefix ?? 'Request'} ${res.status}: ${detail}`);
  }
  return res;
}

async function _extractErrorDetail(res: Response): Promise<string> {
  const text = await res.text().catch(() => res.statusText);
  if (!text) return res.statusText;
  try {
    const j = JSON.parse(text) as { detail?: string };
    if (j.detail) return j.detail;
  } catch {
    /* not JSON, return raw */
  }
  return text;
}

// ---- SSE helpers --------------------------------------------------------

export type SSEHandlers = {
  onDelta: (chunk: string) => void;
  onDone?: () => void;
  onError?: (err: Error) => void;
};

export type SSEEvent = {
  delta?: string;
  done?: boolean;
  error?: string;
  /** Set by the backend on error events for support correlation. */
  request_id?: string;
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
  const { onDelta, onDone, onError, ...rest } = init;
  let res: Response;
  try {
    res = await runnerFetch(path, rest);
  } catch (err) {
    onError?.(err as Error);
    return;
  }
  await consumeSSE(res, { onDelta, onDone, onError });
}
