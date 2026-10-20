// runnerFetch (ROUNDS-00A-L01): the bearer, one Idempotency-Key per
// call, and failures mapped to RunnerError with status, code,
// Retry-After, and the correlation id.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const authStore = vi.hoisted(() => ({ token: '' }));
vi.mock('../pocketbase', () => ({ pb: { authStore } }));

import {
  CORRELATION_HEADER,
  IDEMPOTENCY_HEADER,
  RunnerError,
  isRunnerError,
  parseRetryAfter,
  runnerFetch,
  runnerJSON,
  runnerSSE,
} from '../runnerFetch';
import { UUID_V7_PATTERN } from '../idempotency';

const CID = '0123456789abcdef0123456789abcdef';
const OTHER_CID = 'fedcba9876543210fedcba9876543210';

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json', ...headers },
  });
}

function sentHeaders(call = 0): Headers {
  return fetchMock.mock.calls[call][1]!.headers as Headers;
}

async function failure(promise: Promise<unknown>): Promise<RunnerError> {
  try {
    await promise;
  } catch (err) {
    if (isRunnerError(err)) return err;
    throw err;
  }
  throw new Error('expected the call to fail');
}

beforeEach(() => {
  authStore.token = 'test-token-placeholder';
  fetchMock.mockReset();
  fetchMock.mockResolvedValue(jsonResponse(200, { ok: true }));
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('the bearer', () => {
  it('is required by default and nothing is sent without it', async () => {
    authStore.token = '';
    const err = await failure(runnerFetch('/api/run', { method: 'POST', body: {} }));
    expect(err).toBeInstanceOf(RunnerError);
    expect(err.status).toBe(0);
    expect(err.code).toBe('unauthenticated');
    expect(err.message).toBe('Not authenticated.');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('goes on every call that has one', async () => {
    await runnerFetch('/api/run', { method: 'POST', body: {} });
    expect(sentHeaders().get('Authorization')).toBe('Bearer test-token-placeholder');
  });

  it("is left off for 'none' and for 'optional' without a token", async () => {
    await runnerFetch('/api/share/by-token/x', { auth: 'none' });
    expect(sentHeaders(0).has('Authorization')).toBe(false);
    authStore.token = '';
    await runnerFetch('/api/x', { auth: 'optional' });
    expect(sentHeaders(1).has('Authorization')).toBe(false);
  });
});

describe('idempotency keys', () => {
  it.each(['POST', 'PUT', 'PATCH', 'DELETE', 'post'])('mints a UUIDv7 key for %s', async (method) => {
    await runnerFetch('/api/run', { method, body: {} });
    expect(sentHeaders().get(IDEMPOTENCY_HEADER)).toMatch(UUID_V7_PATTERN);
  });

  it('sends none on reads', async () => {
    await runnerFetch('/api/pdf/health');
    await runnerFetch('/api/pdf/health', { method: 'GET' });
    expect(sentHeaders(0).has(IDEMPOTENCY_HEADER)).toBe(false);
    expect(sentHeaders(1).has(IDEMPOTENCY_HEADER)).toBe(false);
  });

  it('mints a new key for each action', async () => {
    await runnerFetch('/api/run', { method: 'POST', body: {} });
    await runnerFetch('/api/run', { method: 'POST', body: {} });
    expect(sentHeaders(0).get(IDEMPOTENCY_HEADER)).not.toBe(sentHeaders(1).get(IDEMPOTENCY_HEADER));
  });

  it('reuses the key a retry passes in, and a header the caller set', async () => {
    const key = '018f3c1e-7d2a-7b3c-8d4e-5f6a7b8c9d0e';
    await runnerFetch('/api/run', { method: 'POST', body: {}, idempotencyKey: key });
    await runnerFetch('/api/run', { method: 'POST', body: {}, headers: { [IDEMPOTENCY_HEADER]: key } });
    expect(sentHeaders(0).get(IDEMPOTENCY_HEADER)).toBe(key);
    expect(sentHeaders(1).get(IDEMPOTENCY_HEADER)).toBe(key);
  });

  it('keeps the key on the error so a retry can send it again', async () => {
    fetchMock.mockResolvedValue(jsonResponse(503, { detail: 'Busy.' }));
    const err = await failure(runnerFetch('/api/run', { method: 'POST', body: {} }));
    expect(err.idempotencyKey).toBe(sentHeaders().get(IDEMPOTENCY_HEADER));
  });
});

describe('error mapping', () => {
  it('reads the typed envelope and Retry-After', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(
        429,
        { detail: "You've reached the limit for now.", code: 'quota_exceeded', correlation_id: CID },
        { 'Retry-After': '30', [CORRELATION_HEADER]: CID },
      ),
    );
    const err = await failure(runnerFetch('/api/run', { method: 'POST', body: {} }));
    expect(err.status).toBe(429);
    expect(err.code).toBe('quota_exceeded');
    expect(err.detail).toBe("You've reached the limit for now.");
    expect(err.correlationId).toBe(CID);
    expect(err.retryAfterSeconds).toBe(30);
    expect(err.message).toBe("Request 429: You've reached the limit for now.");
  });

  it('keeps the old message shape with the caller prefix', async () => {
    fetchMock.mockResolvedValue(jsonResponse(502, { detail: 'Renderer unavailable.' }));
    const err = await failure(runnerFetch('/api/pdf/render', { method: 'POST', body: {}, errorPrefix: 'PDF render failed' }));
    expect(err.message).toBe('PDF render failed 502: Renderer unavailable.');
    expect(err.code).toBeNull();
    expect(String(err)).toBe('Error: PDF render failed 502: Renderer unavailable.');
  });

  it('falls back to the correlation header when the body has none', async () => {
    fetchMock.mockResolvedValue(jsonResponse(500, { detail: 'Internal Server Error' }, { [CORRELATION_HEADER]: OTHER_CID }));
    const err = await failure(runnerFetch('/api/run', { method: 'POST', body: {} }));
    expect(err.correlationId).toBe(OTHER_CID);
  });

  it('ignores a code or correlation id with the wrong shape', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(403, { detail: 'No.', code: 'Not Permitted', correlation_id: 'abc' }, { [CORRELATION_HEADER]: 'not-hex' }),
    );
    const err = await failure(runnerFetch('/api/run', { method: 'POST', body: {} }));
    expect(err.code).toBeNull();
    expect(err.correlationId).toBeNull();
  });

  it('joins FastAPI validation messages', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse(422, { detail: [{ msg: 'Field required', loc: ['body', 'code'] }, { msg: 'Too long' }] }),
    );
    const err = await failure(runnerFetch('/api/run', { method: 'POST', body: {} }));
    expect(err.detail).toBe('Field required; Too long');
  });

  it('uses raw text when the body is not JSON, and the status text when it is empty', async () => {
    fetchMock.mockResolvedValueOnce(new Response('upstream timed out', { status: 504 }));
    fetchMock.mockResolvedValueOnce(new Response('', { status: 503, statusText: 'Service Unavailable' }));
    expect((await failure(runnerFetch('/api/run', { method: 'POST', body: {} }))).detail).toBe('upstream timed out');
    expect((await failure(runnerFetch('/api/run', { method: 'POST', body: {} }))).detail).toBe('Service Unavailable');
  });

  it('turns a failed request into status 0 and keeps its message', async () => {
    const cause = new TypeError('Failed to fetch');
    fetchMock.mockRejectedValue(cause);
    const err = await failure(runnerFetch('/api/run', { method: 'POST', body: {} }));
    expect(err.status).toBe(0);
    expect(err.message).toBe('Failed to fetch');
    expect((err as Error & { cause?: unknown }).cause).toBe(cause);
  });

  it('lets an abort through untouched', async () => {
    const abort = new DOMException('The operation was aborted.', 'AbortError');
    fetchMock.mockRejectedValue(abort);
    await expect(runnerFetch('/api/run', { method: 'POST', body: {} })).rejects.toBe(abort);
  });

  it('routes a refused stream to onError', async () => {
    fetchMock.mockResolvedValue(jsonResponse(401, { detail: 'Not authenticated.', code: 'unauthenticated' }));
    const onError = vi.fn();
    await runnerSSE('/api/ai/improve', { method: 'POST', body: {}, onDelta: vi.fn(), onError });
    const [err] = onError.mock.calls[0];
    expect(isRunnerError(err)).toBe(true);
    expect((err as RunnerError).status).toBe(401);
  });

  it('returns undefined for 204 in runnerJSON', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }));
    await expect(runnerJSON('/api/share/x', { method: 'DELETE' })).resolves.toBeUndefined();
  });
});

describe('parseRetryAfter', () => {
  it('reads delta seconds and HTTP dates', () => {
    const now = Date.parse('2026-10-20T12:00:00Z');
    expect(parseRetryAfter('120', now)).toBe(120);
    expect(parseRetryAfter(' 0 ', now)).toBe(0);
    expect(parseRetryAfter('Tue, 20 Oct 2026 12:01:30 GMT', now)).toBe(90);
    expect(parseRetryAfter('Tue, 20 Oct 2026 11:00:00 GMT', now)).toBe(0);
  });

  it.each([null, undefined, '', 'soon', '-5', '1.5'])('returns null for %s', (value) => {
    expect(parseRetryAfter(value)).toBeNull();
  });
});
