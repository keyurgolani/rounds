// A graded result's review on a page (ROUNDS-00A-L03 PR 3): one ask, its
// answer read into a state, a review under way asked about again until it
// ends, a finished one read from the graded row when the answer doesn't
// carry it, and a limit or an outage that offers another ask.

import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';

vi.mock('../../lib/pocketbase', () => ({ pb: { authStore: { token: 'test-token-placeholder' } } }));

import { useRubricReview, type ReviewRequest } from '../useRubricReview';
import type { ReviewAnswer, RubricReview } from '../../lib/gradedRows';
import { RunnerError } from '../../lib/runnerFetch';
import { UUID_V7_PATTERN } from '../../lib/idempotency';

const JOB = 'jobaaaaaaaaaaa1';
const FILES = { 'client.py': 'x = 1\n' };
const REVIEW: RubricReview = { items: [{ id: 'clarity', score: 0.75, evidence: 'Clear.', suggestions: [] }], total: 0.75 };

function answer(extra: Partial<ReviewAnswer>): ReviewAnswer {
  return { job_id: JOB, rubric_state: null, rubric_review: null, unavailable: null, ...extra };
}

function setup(request: ReviewRequest, readReview = vi.fn().mockResolvedValue(REVIEW)) {
  const hook = renderHook(() => useRubricReview(request, readReview));
  return { ...hook, readReview };
}

afterEach(() => {
  vi.useRealTimers();
});

describe('useRubricReview', () => {
  it('asks once with the files, and shows the review the answer carries', async () => {
    const request = vi.fn<ReviewRequest>().mockResolvedValue(answer({ rubric_state: 'completed', rubric_review: REVIEW }));
    const { result, readReview } = setup(request);
    act(() => result.current.ask(JOB, FILES));
    expect(result.current.status).toBe('reviewing');
    await waitFor(() => expect(result.current.status).toBe('reviewed'));
    expect(result.current.review).toEqual(REVIEW);
    expect(request).toHaveBeenCalledTimes(1);
    const [jobId, files, key] = request.mock.calls[0];
    expect([jobId, files]).toEqual([JOB, FILES]);
    expect(key).toMatch(UUID_V7_PATTERN);
    expect(readReview).not.toHaveBeenCalled();
  });

  it('reads a finished review from the graded row when the answer leaves it out', async () => {
    const request = vi.fn<ReviewRequest>().mockResolvedValue(answer({ rubric_state: 'completed' }));
    const { result, readReview } = setup(request);
    act(() => result.current.ask(JOB, FILES));
    await waitFor(() => expect(result.current.status).toBe('reviewed'));
    expect(readReview).toHaveBeenCalledWith(JOB);
    expect(result.current.review).toEqual(REVIEW);
  });

  it('prefers a finished review over a missing provider', async () => {
    const request = vi.fn<ReviewRequest>().mockResolvedValue(answer({ rubric_state: 'completed', unavailable: 'no_provider' }));
    const { result } = setup(request);
    act(() => result.current.ask(JOB, FILES));
    await waitFor(() => expect(result.current.status).toBe('reviewed'));
  });

  it.each([
    [answer({ unavailable: 'no_provider' }), 'no_provider'],
    [answer({ unavailable: 'files_changed' }), 'files_changed'],
    [answer({ unavailable: 'not_reviewable' }), 'not_reviewable'],
    [answer({ rubric_state: 'lost' }), 'lost'],
    [answer({ rubric_state: 'requested' }), 'unavailable'],
  ] as const)('reads %o as %s', async (reply, status) => {
    const { result } = setup(vi.fn<ReviewRequest>().mockResolvedValue(reply));
    act(() => result.current.ask(JOB, FILES));
    await waitFor(() => expect(result.current.status).toBe(status));
    expect(result.current.review).toBeNull();
  });

  it('asks about a review under way again after the wait the server names, until it ends', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const busy = new RunnerError({ message: 'review 409: x', status: 409, code: 'already_in_flight', retryAfterSeconds: 5 });
    const request = vi
      .fn<ReviewRequest>()
      .mockRejectedValueOnce(busy)
      .mockRejectedValueOnce(busy)
      .mockResolvedValueOnce(answer({ rubric_state: 'completed', rubric_review: REVIEW }));
    const { result } = setup(request);
    act(() => result.current.ask(JOB, FILES));
    await waitFor(() => expect(request).toHaveBeenCalledTimes(1));
    expect(result.current.status).toBe('reviewing');
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    await waitFor(() => expect(request).toHaveBeenCalledTimes(2));
    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });
    await waitFor(() => expect(result.current.status).toBe('reviewed'));
    expect(request).toHaveBeenCalledTimes(3);
  });

  it('shows a limit with its wait, and asks again with the same job and files on Try again', async () => {
    const request = vi
      .fn<ReviewRequest>()
      .mockRejectedValueOnce(new RunnerError({ message: 'review 429: x', status: 429, code: 'quota_exceeded', retryAfterSeconds: 90 }))
      .mockResolvedValueOnce(answer({ rubric_state: 'completed', rubric_review: REVIEW }));
    const { result } = setup(request);
    act(() => result.current.ask(JOB, FILES));
    await waitFor(() => expect(result.current.status).toBe('limit'));
    expect(result.current.retryAfterSeconds).toBe(90);
    let asked = false;
    act(() => {
      asked = result.current.retry();
    });
    expect(asked).toBe(true);
    await waitFor(() => expect(result.current.status).toBe('reviewed'));
    expect(request.mock.calls[1].slice(0, 2)).toEqual([JOB, FILES]);
    // Each ask is its own command.
    expect(request.mock.calls[1][2]).not.toBe(request.mock.calls[0][2]);
  });

  it('shows an outage as unavailable', async () => {
    const { result } = setup(
      vi.fn<ReviewRequest>().mockRejectedValue(new RunnerError({ message: 'review 503: x', status: 503, code: 'worker_unavailable' })),
    );
    act(() => result.current.ask(JOB, FILES));
    await waitFor(() => expect(result.current.status).toBe('unavailable'));
  });

  it('has nothing to retry before an ask, or after a state shown without one', () => {
    const { result } = setup(vi.fn<ReviewRequest>());
    expect(result.current.retry()).toBe(false);
    act(() => result.current.show(null, 'not_requested'));
    expect(result.current.status).toBe('not_requested');
    expect(result.current.retry()).toBe(false);
  });

  it('drops an answer that lands after a reset', async () => {
    let reply!: (value: ReviewAnswer) => void;
    const request = vi.fn<ReviewRequest>().mockImplementation(() => new Promise((resolve) => { reply = resolve; }));
    const { result } = setup(request);
    act(() => result.current.ask(JOB, FILES));
    act(() => result.current.reset());
    await act(async () => {
      reply(answer({ rubric_state: 'completed', rubric_review: REVIEW }));
    });
    expect(result.current.status).toBeNull();
    expect(result.current.review).toBeNull();
  });
});
