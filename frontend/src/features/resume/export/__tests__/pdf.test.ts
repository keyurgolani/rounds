// Server PDF export goes through runnerFetch (ROUNDS-00A-L01), so it
// carries the caller's bearer and one Idempotency-Key, and failures are
// typed.

import { beforeEach, describe, expect, it, vi } from 'vitest';

const authStore = vi.hoisted(() => ({ token: 'test-token-placeholder' }));
vi.mock('../../../../lib/pocketbase', () => ({ pb: { authStore } }));
vi.mock('../html', () => ({ buildStandaloneHtml: vi.fn(() => '<html><body>Jane</body></html>') }));
vi.mock('../index', () => ({ downloadBlob: vi.fn() }));

import { exportPdfServer } from '../pdf';
import { downloadBlob } from '../index';
import { buildStandaloneHtml } from '../html';
import { isRunnerError } from '../../../../lib/runnerFetch';
import { UUID_V7_PATTERN } from '../../../../lib/idempotency';

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  authStore.token = 'test-token-placeholder';
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  vi.mocked(downloadBlob).mockReset();
});

describe('exportPdfServer', () => {
  it('posts the preview with the bearer and an idempotency key', async () => {
    fetchMock.mockResolvedValue(new Response('%PDF-1.7', { status: 200 }));
    await exportPdfServer('jane-doe', 4);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/pdf/render');
    expect(init!.method).toBe('POST');
    expect(JSON.parse(init!.body as string)).toEqual({ html: '<html><body>Jane</body></html>', margin_mm: 4 });
    const headers = init!.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer test-token-placeholder');
    expect(headers.get('Idempotency-Key')).toMatch(UUID_V7_PATTERN);
    expect(downloadBlob).toHaveBeenCalledWith(expect.anything(), 'jane-doe.pdf');
  });

  it('needs a signed-in caller and sends nothing without one', async () => {
    authStore.token = '';
    const err = await exportPdfServer('jane-doe').catch((e: unknown) => e);
    expect(isRunnerError(err)).toBe(true);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('throws a typed error that keeps the status, code, and wait', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Try later.', code: 'quota_exceeded', correlation_id: '0'.repeat(32) }), {
        status: 429,
        headers: { 'Retry-After': '60' },
      }),
    );
    const err = await exportPdfServer('jane-doe').catch((e: unknown) => e);
    expect(isRunnerError(err)).toBe(true);
    expect(err).toMatchObject({ status: 429, code: 'quota_exceeded', retryAfterSeconds: 60 });
    expect((err as Error).message).toBe('PDF render failed 429: Try later.');
    expect(downloadBlob).not.toHaveBeenCalled();
  });

  it('refuses before any request when no preview is rendered', async () => {
    vi.mocked(buildStandaloneHtml).mockReturnValueOnce('');
    await expect(exportPdfServer('jane-doe')).rejects.toThrow('No resume preview is currently rendered.');
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
