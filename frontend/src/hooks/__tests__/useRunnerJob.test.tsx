// useRunnerJob (ROUNDS-00A-L03): a 202's job followed to its end, a
// reload picking it back up, the waits while the server doesn't answer,
// a job the server no longer has, a refused session, Cancel, and Retry
// keeping the command id only while the job can run again.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';

const authStore = vi.hoisted(() => ({ token: '' }));
vi.mock('../../lib/pocketbase', () => ({ pb: { authStore } }));

import { useRunnerJob } from '../useRunnerJob';
import { beginAction, loadAction, saveAction, type JobAnswer } from '../../lib/executionJobs';

const SCOPE = 'coding:two-sum:python:run';
const WORK = { code: 'def two_sum(nums, target): return [0, 1]', input: { nums: [1, 2], target: 3 } };
const CID = '0123456789abcdef0123456789abcdef';

function job(state: JobAnswer['state'], extra: Partial<JobAnswer> = {}): JobAnswer {
  return { job_id: 'jobaaaaaaaaaaa1', state, outcome_class: null, retryable: false, cancel_requested: false, envelope: null, ...extra };
}

const OUTPUT = { stdout: '', stderr: '', return_value: [0, 1], error: null, duration_ms: 3, truncated: false };
const DONE = job('completed', {
  outcome_class: 'passed',
  envelope: {
    version: 'rounds.execution-envelope/v1', job_id: 'jobaaaaaaaaaaa1', state: 'completed', outcome_class: 'passed',
    authoritative: true, limit: null, parts: [{ id: 'run', outcome_class: 'passed', limit: null }], score: null,
    definition: null, queued_at: 1, started_at: 2, finished_at: 3, cleanup: 'confirmed', rubric: null, output: OUTPUT,
  },
});

const fetchMock = vi.fn<typeof fetch>();

function answer(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
}

function typed(status: number, code: string) {
  return answer(status, { detail: 'A fixed sentence.', code, correlation_id: CID });
}

// Answers each job read in turn; the last one repeats.
function reads(...bodies: Response[]) {
  fetchMock.mockImplementation(async () => (bodies.length > 1 ? bodies.shift()! : bodies[0].clone()));
}

beforeEach(() => {
  authStore.token = 'test-token-placeholder';
  window.sessionStorage.clear();
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('useRunnerJob', () => {
  it('follows a job from its 202 to its end and hands the end over once', async () => {
    reads(answer(200, job('started')), answer(200, DONE));
    const onEnded = vi.fn();
    const { result } = renderHook(() => useRunnerJob(SCOPE, { onEnded }));
    let key = '';
    act(() => {
      key = result.current.begin(WORK);
    });
    act(() => {
      expect(result.current.follow(job('queued'))).toBe(true);
    });
    expect(result.current.active).toBe(true);
    expect(loadAction(SCOPE)).toMatchObject({ key, jobId: 'jobaaaaaaaaaaa1' });
    await waitFor(() => expect(result.current.job?.state).toBe('completed'));
    expect(result.current.active).toBe(false);
    expect(result.current.runningSince).not.toBeNull();
    expect(onEnded).toHaveBeenCalledTimes(1);
    expect(onEnded.mock.calls[0][0].envelope.output).toEqual(OUTPUT);
    expect(fetchMock.mock.calls.map(([url]) => url)).toEqual([
      '/api/execution/jobs/jobaaaaaaaaaaa1?wait=20',
      '/api/execution/jobs/jobaaaaaaaaaaa1?wait=20',
    ]);
    // Ended with no retry left: nothing kept.
    expect(loadAction(SCOPE)).toBeNull();
  });

  it('leaves a body that is no job to the page', () => {
    const { result } = renderHook(() => useRunnerJob(SCOPE));
    act(() => {
      result.current.begin(WORK);
    });
    expect(result.current.follow(OUTPUT)).toBe(false);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('picks a kept job back up after a reload, reading it at once', async () => {
    const kept = beginAction(SCOPE, WORK);
    saveAction(SCOPE, { ...kept, jobId: 'jobaaaaaaaaaaa1' });
    reads(answer(200, DONE));
    const onEnded = vi.fn();
    const { result } = renderHook(() => useRunnerJob(SCOPE, { onEnded }));
    await waitFor(() => expect(result.current.job?.state).toBe('completed'));
    expect(fetchMock.mock.calls[0][0]).toBe('/api/execution/jobs/jobaaaaaaaaaaa1?wait=0');
    expect(onEnded).toHaveBeenCalledTimes(1);
  });

  it('waits and asks again while the server does not answer', async () => {
    vi.useFakeTimers();
    reads(typed(503, 'worker_unavailable'), answer(200, DONE));
    const { result } = renderHook(() => useRunnerJob(SCOPE));
    act(() => {
      result.current.begin(WORK);
      result.current.follow(job('queued'));
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(10);
    });
    expect(result.current.reconnecting).toBe(true);
    expect(result.current.job?.state).toBe('queued');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1000);
    });
    expect(result.current.reconnecting).toBe(false);
    expect(result.current.job?.state).toBe('completed');
  });

  it('says a job the server no longer has is gone, and forgets it', async () => {
    reads(typed(404, 'not_found'));
    const { result } = renderHook(() => useRunnerJob(SCOPE));
    act(() => {
      result.current.begin(WORK);
      result.current.follow(job('queued'));
    });
    await waitFor(() => expect(result.current.gone).toBe(true));
    expect(result.current.job).toBeNull();
    expect(loadAction(SCOPE)).toBeNull();
  });

  it('stops and hands a refused session to the page', async () => {
    reads(typed(401, 'unauthenticated'));
    const onDenied = vi.fn();
    const { result } = renderHook(() => useRunnerJob(SCOPE, { onDenied }));
    act(() => {
      result.current.begin(WORK);
      result.current.follow(job('queued'));
    });
    await waitFor(() => expect(onDenied).toHaveBeenCalledTimes(1));
    expect(onDenied.mock.calls[0][0].code).toBe('unauthenticated');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('cancels the job and shows what the server answered', async () => {
    let release: () => void = () => {};
    fetchMock.mockImplementation(async (url, init) => {
      if (String(url).endsWith('/cancel')) return answer(200, job('started', { cancel_requested: true }));
      // The long-poll waits until the test ends it.
      await new Promise<void>((resolve) => {
        release = resolve;
        init?.signal?.addEventListener('abort', () => resolve());
      });
      return answer(200, job('canceled', { outcome_class: 'canceled' }));
    });
    const { result } = renderHook(() => useRunnerJob(SCOPE));
    act(() => {
      result.current.begin(WORK);
      result.current.follow(job('started'));
    });
    await act(async () => {
      await result.current.cancel();
    });
    expect(result.current.job?.cancel_requested).toBe(true);
    act(() => release());
    await waitFor(() => expect(result.current.job?.state).toBe('canceled'));
  });

  it('keeps the id for Retry while the job can run again', async () => {
    reads(answer(200, job('failed', { outcome_class: 'worker-lost', retryable: true })));
    const { result } = renderHook(() => useRunnerJob(SCOPE));
    let first = '';
    act(() => {
      first = result.current.begin(WORK);
      result.current.follow(job('queued'));
    });
    await waitFor(() => expect(result.current.job?.outcome_class).toBe('worker-lost'));
    let again = '';
    act(() => {
      again = result.current.begin(WORK, true);
    });
    expect(again).toBe(first);
    let edited = '';
    act(() => {
      edited = result.current.begin({ ...WORK, code: 'changed' }, true);
    });
    expect(edited).not.toBe(first);
  });

  it('stops reading when the page goes', async () => {
    let signal: AbortSignal | null | undefined;
    fetchMock.mockImplementation(async (_url, init) => {
      signal = init?.signal;
      return new Promise<Response>(() => {});
    });
    const { result, unmount } = renderHook(() => useRunnerJob(SCOPE));
    act(() => {
      result.current.begin(WORK);
      result.current.follow(job('queued'));
    });
    await waitFor(() => expect(signal).toBeTruthy());
    unmount();
    expect(signal?.aborted).toBe(true);
  });
});
