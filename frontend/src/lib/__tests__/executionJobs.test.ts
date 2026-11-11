// Scratch jobs (ROUNDS-00A-L03): telling a job from an in-request body,
// one command id per action kept for the tab, Retry keeping that id only
// for the same work, and the job routes' reads.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const authStore = vi.hoisted(() => ({ token: '' }));
vi.mock('../pocketbase', () => ({ pb: { authStore } }));

import {
  ACTION_MAX_AGE_MS,
  beginAction,
  cancelJob,
  clearAction,
  isEnded,
  isJobAnswer,
  loadAction,
  readJob,
  saveAction,
  workHash,
  type JobAnswer,
} from '../executionJobs';
import { UUID_V7_PATTERN } from '../idempotency';
import { isRunnerError } from '../runnerFetch';

const QUEUED: JobAnswer = {
  job_id: 'jobaaaaaaaaaaa1',
  state: 'queued',
  outcome_class: null,
  retryable: false,
  cancel_requested: false,
  envelope: null,
};

const fetchMock = vi.fn<typeof fetch>();

function json(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

beforeEach(() => {
  authStore.token = 'test-token-placeholder';
  window.sessionStorage.clear();
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('isJobAnswer', () => {
  it('takes a job and only a job', () => {
    expect(isJobAnswer(QUEUED)).toBe(true);
    expect(isJobAnswer({ ...QUEUED, state: 'completed', outcome_class: 'passed', envelope: { parts: [] } })).toBe(true);
    for (const other of [
      { stdout: 'ok', stderr: '', return_value: 1, error: null, duration_ms: 1, truncated: false },
      { passed: 1, failed: 0, results: [] },
      { ...QUEUED, job_id: 'JOB-1' },
      { ...QUEUED, state: 'running' },
      { ...QUEUED, outcome_class: 'flaky' },
      { ...QUEUED, retryable: 'yes' },
      { ...QUEUED, envelope: { parts: 'none' } },
      null,
      [QUEUED],
    ]) {
      expect(isJobAnswer(other)).toBe(false);
    }
  });

  it('knows which states have ended', () => {
    expect(['queued', 'leased', 'started'].map((s) => isEnded(s as never))).toEqual([false, false, false]);
    expect(['completed', 'timed-out', 'denied', 'canceled', 'failed'].every((s) => isEnded(s as never))).toBe(true);
  });
});

describe('one command id per action', () => {
  const work = { slug: 'two-sum', code: 'def f(): pass', input: { a: 1 } };

  it('hashes the same work the same in any key order, and an edit differently', () => {
    expect(workHash(work)).toBe(workHash({ input: { a: 1 }, code: 'def f(): pass', slug: 'two-sum' }));
    expect(workHash(work)).not.toBe(workHash({ ...work, code: 'def f(): return 1' }));
    expect(workHash(work)).toMatch(/^[0-9a-f]{16}$/);
  });

  it('mints a new id for each click and keeps it for the tab', () => {
    const first = beginAction('coding:two-sum:python:run', work);
    const second = beginAction('coding:two-sum:python:run', work);
    expect(first.key).toMatch(UUID_V7_PATTERN);
    expect(second.key).not.toBe(first.key);
    expect(loadAction('coding:two-sum:python:run')?.key).toBe(second.key);
  });

  it('keeps the id on a retry of the same work, and not of changed work', () => {
    const scope = 'coding:two-sum:python:run';
    const first = beginAction(scope, work);
    saveAction(scope, { ...first, jobId: 'jobaaaaaaaaaaa1' });
    expect(beginAction(scope, work, true).key).toBe(first.key);
    expect(beginAction(scope, { ...work, code: 'edited' }, true).key).not.toBe(first.key);
  });

  it('forgets an action past its age, a malformed one, and a cleared one', () => {
    const scope = 'take-home:kv-store-py:python:run';
    const kept = beginAction(scope, work, false, 1_000);
    expect(loadAction(scope, 1_000 + ACTION_MAX_AGE_MS)).toEqual(kept);
    expect(loadAction(scope, 1_001 + ACTION_MAX_AGE_MS)).toBeNull();
    window.sessionStorage.setItem(`rounds:job:${scope}`, '{"v":1,"key":"k","hash":"h","jobId":"../x","at":1}');
    expect(loadAction(scope, 1)).toBeNull();
    window.sessionStorage.setItem(`rounds:job:${scope}`, 'not json');
    expect(loadAction(scope)).toBeNull();
    beginAction(scope, work);
    clearAction(scope);
    expect(loadAction(scope)).toBeNull();
  });
});

describe('the job routes', () => {
  it('reads the job with the bearer and a bounded wait', async () => {
    fetchMock.mockImplementation(async () => json(200, QUEUED));
    expect(await readJob('jobaaaaaaaaaaa1', 99)).toEqual(QUEUED);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/execution/jobs/jobaaaaaaaaaaa1?wait=20');
    expect((init!.headers as Headers).get('Authorization')).toBe('Bearer test-token-placeholder');
    await readJob('jobaaaaaaaaaaa1', 0);
    expect(fetchMock.mock.calls[1][0]).toBe('/api/execution/jobs/jobaaaaaaaaaaa1?wait=0');
  });

  it('treats an answer that is no job as the server failing', async () => {
    fetchMock.mockResolvedValue(json(200, { stdout: 'x' }));
    const err = await readJob('jobaaaaaaaaaaa1', 0).catch((e: unknown) => e);
    expect(isRunnerError(err) && err.status).toBe(502);
  });

  it('keeps the uniform not-found a 404', async () => {
    fetchMock.mockResolvedValue(
      json(404, { detail: 'Not found.', code: 'not_found', correlation_id: '0123456789abcdef0123456789abcdef' }),
    );
    const err = await readJob('jobaaaaaaaaaaa1', 0).catch((e: unknown) => e);
    expect(isRunnerError(err) && [err.status, err.code]).toEqual([404, 'not_found']);
  });

  it('cancels with a POST and answers the job', async () => {
    fetchMock.mockResolvedValue(json(200, { ...QUEUED, state: 'canceled', outcome_class: 'canceled' }));
    expect((await cancelJob('jobaaaaaaaaaaa1')).state).toBe('canceled');
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/execution/jobs/jobaaaaaaaaaaa1/cancel');
    expect(init!.method).toBe('POST');
  });
});
