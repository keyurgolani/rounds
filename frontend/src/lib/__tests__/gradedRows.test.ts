// A grading job's graded row and review call (ROUNDS-00A-L03 PR 3): the
// page reads the row the job's envelope names, as the account, and the
// review route answers where the review stands or the call is refused.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const pbFake = vi.hoisted(() => {
  const calls: Array<{ collection: string; op: string; args: unknown[] }> = [];
  const rows: Record<string, unknown> = {};
  const state = { envelope: null as Record<string, unknown> | null, status: 0 };
  const collection = (name: string) => ({
    async getFirstListItem(...args: unknown[]) {
      calls.push({ collection: name, op: 'getFirstListItem', args });
      if (state.status) throw Object.assign(new Error('x'), { status: state.status });
      if (state.envelope === null) throw Object.assign(new Error('not found'), { status: 404 });
      return state.envelope;
    },
    async getOne(...args: unknown[]) {
      calls.push({ collection: name, op: 'getOne', args });
      if (name === 'execution_envelopes') return state.envelope;
      return rows[args[0] as string];
    },
  });
  return { calls, rows, state, pb: { authStore: { token: 'test-token-placeholder' }, collection } };
});

vi.mock('../pocketbase', () => ({ pb: pbFake.pb }));

import { envelopeJob, isReviewAnswer, readGradedRow, requestReview, rubricState } from '../gradedRows';
import { isRunnerError } from '../runnerFetch';

const JOB = 'jobaaaaaaaaaaa1';
const ROW = 'rowaaaaaaaaaaa1';
const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  pbFake.calls.length = 0;
  pbFake.state.envelope = null;
  pbFake.state.status = 0;
  pbFake.rows[ROW] = { id: ROW, test_results: [], rubric_review: null, envelope: 'envaaaaaaaaaaa1' };
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('readGradedRow', () => {
  it("reads the job's envelope, then the row it names", async () => {
    pbFake.state.envelope = { id: 'envaaaaaaaaaaa1', job: JOB, graded_collection: 'ai_coding_attempts', graded_row: ROW };
    const row = await readGradedRow<{ id: string }>(JOB, 'ai_coding_attempts');
    expect(row?.id).toBe(ROW);
    expect(pbFake.calls[0]).toEqual({
      collection: 'execution_envelopes',
      op: 'getFirstListItem',
      args: [`job="${JOB}" && graded_row!=""`, { sort: '-created' }],
    });
    expect(pbFake.calls[1]).toEqual({ collection: 'ai_coding_attempts', op: 'getOne', args: [ROW] });
  });

  it('is null when the job wrote no row, or wrote it in the other collection', async () => {
    expect(await readGradedRow(JOB, 'ai_coding_attempts')).toBeNull();
    pbFake.state.envelope = { id: 'envaaaaaaaaaaa1', job: JOB, graded_collection: 'take_home_attempts', graded_row: ROW };
    expect(await readGradedRow(JOB, 'ai_coding_attempts')).toBeNull();
    expect(pbFake.calls.some((c) => c.op === 'getOne')).toBe(false);
  });

  it('never puts anything but a record id in the filter', async () => {
    expect(await readGradedRow('x" || user!="', 'ai_coding_attempts')).toBeNull();
    expect(pbFake.calls).toHaveLength(0);
  });

  it('passes on a read that failed for another reason', async () => {
    pbFake.state.status = 500;
    await expect(readGradedRow(JOB, 'ai_coding_attempts')).rejects.toMatchObject({ status: 500 });
  });
});

describe('envelopeJob', () => {
  it("names the envelope's job, and nothing for a row without one", async () => {
    pbFake.state.envelope = { id: 'envaaaaaaaaaaa1', job: JOB };
    expect(await envelopeJob('envaaaaaaaaaaa1')).toBe(JOB);
    expect(await envelopeJob(null)).toBeNull();
    expect(await envelopeJob('')).toBeNull();
  });
});

describe('rubricState', () => {
  it('reads where the review stands, or null before anyone asked', () => {
    expect(rubricState({ rubric: { state: 'requested' } })).toBe('requested');
    expect(rubricState({ rubric: { state: 'completed' } })).toBe('completed');
    expect(rubricState({ rubric: null })).toBeNull();
    expect(rubricState({ rubric: { state: 'graded' } })).toBeNull();
    expect(rubricState(null)).toBeNull();
  });
});

describe('requestReview', () => {
  it('posts the files under its own command id and takes the answer', async () => {
    const reply = { job_id: JOB, rubric_state: 'completed', rubric_review: { items: [], total: 0.5 }, unavailable: null };
    fetchMock.mockResolvedValue(new Response(JSON.stringify(reply), { status: 200 }));
    const out = await requestReview('/api/ai-coding/grade', JOB, { 'a.py': 'x' }, 'key-placeholder');
    expect(out).toEqual(reply);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe(`/api/ai-coding/grade/${JOB}/review`);
    expect(init?.method).toBe('POST');
    expect(JSON.parse(init?.body as string)).toEqual({ files: { 'a.py': 'x' } });
    expect(new Headers(init?.headers).get('Idempotency-Key')).toBe('key-placeholder');
  });

  it("reads an answer in no shape it knows as the server failing", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ job_id: JOB, rubric_state: 'graded' }), { status: 200 }));
    const err = await requestReview('/api/take-home/submit', JOB, {}, 'key-placeholder').catch((e: unknown) => e);
    expect(isRunnerError(err) && err.status).toBe(502);
  });

  it('knows the shapes the route answers', () => {
    expect(isReviewAnswer({ job_id: JOB, rubric_state: null, rubric_review: null, unavailable: 'no_provider' })).toBe(true);
    expect(isReviewAnswer({ job_id: JOB, rubric_state: 'lost', rubric_review: null, unavailable: null })).toBe(true);
    expect(isReviewAnswer({ job_id: JOB, rubric_state: null, rubric_review: null, unavailable: 'other' })).toBe(false);
    expect(isReviewAnswer({ job_id: JOB, rubric_state: null, rubric_review: { items: 'x' }, unavailable: null })).toBe(false);
    expect(isReviewAnswer(null)).toBe(false);
  });
});
