// Server PDF export (ROUNDS-00A-L01, ROUNDS-00A-L04): the browser sends
// ids, never markup. It asks for a snapshot of the saved resume, renders
// that snapshot by id and checksum under render-request/v1, and each call
// carries the caller's bearer and its own Idempotency-Key; failures are
// typed.

import { beforeEach, describe, expect, it, vi } from 'vitest';

const authStore = vi.hoisted(() => ({ token: 'test-token-placeholder' }));
vi.mock('../../../../lib/pocketbase', () => ({ pb: { authStore } }));
vi.mock('../index', () => ({ downloadBlob: vi.fn() }));

import { exportPdfServer, SnapshotAnswerInvalid, SnapshotIneligible } from '../pdf';
import { downloadBlob } from '../index';
import { isRunnerError } from '../../../../lib/runnerFetch';
import { UUID_V7_PATTERN } from '../../../../lib/idempotency';

const fetchMock = vi.fn<typeof fetch>();
const CHECKSUM = 'sha256:' + 'c'.repeat(64);
const REQUEST = {
  sourceId: 'resumeaaaaaaaa1',
  expectedUpdated: '2026-11-11 08:00:00.000Z',
  filenameBase: 'jane-doe',
};

function json(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });
}

const created = (status = 'created') =>
  json(status === 'created' ? 201 : 200, { status, snapshot_id: 'snapaaaaaaaaaa1', content_checksum: CHECKSUM });

function sent(call: number): { url: string; body: Record<string, unknown>; headers: Headers } {
  const [url, init] = fetchMock.mock.calls[call];
  return { url: url as string, body: JSON.parse(init!.body as string), headers: init!.headers as Headers };
}

beforeEach(() => {
  authStore.token = 'test-token-placeholder';
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
  vi.mocked(downloadBlob).mockReset();
});

describe('exportPdfServer', () => {
  it('asks for a snapshot of the saved resume, then renders it by id and checksum', async () => {
    fetchMock.mockResolvedValueOnce(created()).mockResolvedValueOnce(new Response('%PDF-1.7', { status: 200 }));
    await exportPdfServer(REQUEST);

    const snapshot = sent(0);
    expect(snapshot.url).toBe('/api/pdf/snapshots');
    expect(snapshot.body).toEqual({
      source_kind: 'resume',
      source_id: 'resumeaaaaaaaa1',
      expected_updated: '2026-11-11 08:00:00.000Z',
    });
    expect(snapshot.headers.get('Authorization')).toBe('Bearer test-token-placeholder');
    expect(snapshot.headers.get('Idempotency-Key')).toMatch(UUID_V7_PATTERN);

    const render = sent(1);
    expect(render.url).toBe('/api/pdf/render');
    expect(render.body).toEqual({
      snapshot_id: 'snapaaaaaaaaaa1',
      expected_checksum: CHECKSUM,
      idempotency_id: render.headers.get('Idempotency-Key'),
      format: 'pdf',
      locale: 'en',
      page_size: 'A4',
      margin_mm: 0,
    });
    expect(render.headers.get('Idempotency-Key')).toMatch(UUID_V7_PATTERN);
    // Each call is its own command.
    expect(render.headers.get('Idempotency-Key')).not.toBe(snapshot.headers.get('Idempotency-Key'));
    expect(downloadBlob).toHaveBeenCalledWith(expect.anything(), 'jane-doe.pdf');
  });

  it('renders a reused snapshot the same way and says when each step starts', async () => {
    fetchMock.mockResolvedValueOnce(created('reused')).mockResolvedValueOnce(new Response('%PDF-1.7'));
    const phases: string[] = [];
    await exportPdfServer({ ...REQUEST, onPhase: (p) => phases.push(p) });
    expect(phases).toEqual(['preparing', 'rendering']);
    expect(sent(1).body.snapshot_id).toBe('snapaaaaaaaaaa1');
  });

  it('never sends markup, a template, or a design', async () => {
    fetchMock.mockResolvedValueOnce(created()).mockResolvedValueOnce(new Response('%PDF-1.7'));
    await exportPdfServer(REQUEST);
    for (const call of [0, 1]) {
      const { body } = sent(call);
      for (const field of ['html', 'markup', 'template_id', 'design', 'data']) expect(body).not.toHaveProperty(field);
    }
  });

  it('stops with the reason when the server will not snapshot this resume', async () => {
    fetchMock.mockResolvedValueOnce(
      json(200, { status: 'ineligible', snapshot_id: null, content_checksum: null, reason: 'design_out_of_domain' }),
    );
    const err = await exportPdfServer(REQUEST).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(SnapshotIneligible);
    expect((err as SnapshotIneligible).reason).toBe('design_out_of_domain');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(downloadBlob).not.toHaveBeenCalled();
  });

  it('keeps no reason it does not know', async () => {
    fetchMock.mockResolvedValueOnce(json(200, { status: 'ineligible', reason: '<b>bold</b>' }));
    const err = await exportPdfServer(REQUEST).catch((e: unknown) => e);
    expect((err as SnapshotIneligible).reason).toBeNull();
  });

  it.each([
    { status: 'created', snapshot_id: 'SNAP', content_checksum: CHECKSUM },
    { status: 'created', snapshot_id: 'snapaaaaaaaaaa1', content_checksum: 'md5:x' },
    { status: 'conflict' },
    {},
  ])('renders nothing for an answer off its contract: %o', async (answer) => {
    fetchMock.mockResolvedValueOnce(json(201, answer));
    await expect(exportPdfServer(REQUEST)).rejects.toBeInstanceOf(SnapshotAnswerInvalid);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('needs a signed-in caller and sends nothing without one', async () => {
    authStore.token = '';
    const err = await exportPdfServer(REQUEST).catch((e: unknown) => e);
    expect(isRunnerError(err)).toBe(true);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('passes the snapshot step’s typed refusal on and renders nothing', async () => {
    fetchMock.mockResolvedValueOnce(
      json(409, { detail: 'Changed.', code: 'snapshot_conflict', correlation_id: '0'.repeat(32) }),
    );
    const err = await exportPdfServer(REQUEST).catch((e: unknown) => e);
    expect(err).toMatchObject({ status: 409, code: 'snapshot_conflict' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('throws a typed render error that keeps the status, code, and wait', async () => {
    fetchMock
      .mockResolvedValueOnce(created())
      .mockResolvedValueOnce(
        json(429, { detail: 'Try later.', code: 'quota_exceeded', correlation_id: '0'.repeat(32) }, { 'Retry-After': '60' }),
      );
    const err = await exportPdfServer(REQUEST).catch((e: unknown) => e);
    expect(isRunnerError(err)).toBe(true);
    expect(err).toMatchObject({ status: 429, code: 'quota_exceeded', retryAfterSeconds: 60 });
    expect((err as Error).message).toBe('PDF render failed 429: Try later.');
    expect(downloadBlob).not.toHaveBeenCalled();
  });

  it('retries a moment’s unavailability with the same render key and body', async () => {
    vi.useFakeTimers();
    try {
      fetchMock
        .mockResolvedValueOnce(created())
        .mockResolvedValueOnce(json(503, { detail: 'Busy.', code: 'worker_unavailable', correlation_id: '0'.repeat(32) }))
        .mockResolvedValueOnce(new Response('%PDF-1.7'));
      const done = exportPdfServer(REQUEST);
      await vi.runAllTimersAsync();
      await done;
      const [first, again] = [sent(1), sent(2)];
      expect(again.headers.get('Idempotency-Key')).toBe(first.headers.get('Idempotency-Key'));
      expect(again.body).toEqual(first.body);
    } finally {
      vi.useRealTimers();
    }
  });
});
