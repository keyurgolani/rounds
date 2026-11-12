// A graded result's rubric review on a practice page (ROUNDS-00A-L03 PR 3;
// lib/gradedRows explains the route).
//
// `ask(jobId, files)` asks the review route, and its answer says where the
// review stands: the review, no AI provider set up, files that changed
// since the grade, a review that didn't finish, or one this server can't
// give. A review another request has under way is asked about again after
// the wait the server names, until it ends; a finished review the answer
// doesn't carry is read from the graded row. Asking again never charges
// again: the server charges a review once per result.
//
// The page asks once, when its own grade ends. A graded row it read on its
// own (after a reload) shows `not_requested`, and asks only when the
// person does, since only they know their files are the ones graded.

import { useCallback, useEffect, useRef, useState } from 'react';
import type { ReviewAnswer, RubricReview } from '../lib/gradedRows';
import { mintIdempotencyKey } from '../lib/idempotency';
import { classifyRunnerError } from '../lib/runnerDenial';
import { isRunnerError } from '../lib/runnerFetch';

export type ReviewStatus =
  | 'not_requested'
  | 'reviewing'
  | 'reviewed'
  | 'no_provider'
  | 'files_changed'
  | 'lost'
  | 'not_reviewable'
  | 'limit'
  | 'unavailable';

export interface RubricReviewView {
  /** Null while there's no graded result to review. */
  status: ReviewStatus | null;
  review: RubricReview | null;
  /** For `limit`: when another ask can be admitted. */
  retryAfterSeconds: number | null;
}

export interface RubricReviewApi extends RubricReviewView {
  ask: (jobId: string, files: Record<string, string>) => void;
  /** Asks again with the last ask's job and files; false when nothing
   *  was asked yet. */
  retry: () => boolean;
  /** Shows a review, or a state, without asking. */
  show: (review: RubricReview | null, status?: ReviewStatus | null) => void;
  reset: () => void;
}

export type ReviewRequest = (
  jobId: string,
  files: Record<string, string>,
  idempotencyKey: string,
  signal: AbortSignal,
) => Promise<ReviewAnswer>;

/** The wait before asking about a review under way, when the server
 *  names none. */
export const IN_FLIGHT_WAIT_S = 5;
/** How many times a review under way is asked about. Past its lease the
 *  server answers it as lost, well inside this. */
export const IN_FLIGHT_TRIES = 30;

const NONE: RubricReviewView = { status: null, review: null, retryAfterSeconds: null };

function pause(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(done, ms);
    function done() {
      clearTimeout(timer);
      signal.removeEventListener('abort', done);
      resolve();
    }
    signal.addEventListener('abort', done, { once: true });
  });
}

export function useRubricReview(
  request: ReviewRequest,
  readReview: (jobId: string) => Promise<RubricReview | null>,
): RubricReviewApi {
  const [view, setView] = useState<RubricReviewView>(NONE);
  const requestRef = useRef(request);
  const readRef = useRef(readReview);
  const runRef = useRef<AbortController | null>(null);
  const lastRef = useRef<{ jobId: string; files: Record<string, string> } | null>(null);

  useEffect(() => {
    requestRef.current = request;
    readRef.current = readReview;
  });

  const stop = useCallback(() => {
    runRef.current?.abort();
    runRef.current = null;
  }, []);

  useEffect(() => stop, [stop]);

  const reset = useCallback(() => {
    stop();
    lastRef.current = null;
    setView(NONE);
  }, [stop]);

  const show = useCallback(
    (review: RubricReview | null, status: ReviewStatus | null = null) => {
      stop();
      lastRef.current = null;
      setView({ status: status ?? (review ? 'reviewed' : null), review, retryAfterSeconds: null });
    },
    [stop],
  );

  const ask = useCallback(
    (jobId: string, files: Record<string, string>) => {
      stop();
      lastRef.current = { jobId, files };
      const controller = new AbortController();
      runRef.current = controller;
      const { signal } = controller;
      const settle = (next: RubricReviewView) => {
        if (!signal.aborted) setView(next);
      };
      const state = (status: ReviewStatus, review: RubricReview | null = null): RubricReviewView => ({
        status,
        review,
        retryAfterSeconds: null,
      });
      setView(state('reviewing'));

      const answered = async (answer: ReviewAnswer): Promise<RubricReviewView> => {
        // A finished review wins over anything else the answer says: it's
        // in the graded row whether or not this answer carries it.
        if (answer.rubric_state === 'completed') {
          let review = answer.rubric_review;
          if (review === null) {
            try {
              review = await readRef.current(jobId);
            } catch {
              review = null;
            }
          }
          return review ? state('reviewed', review) : state('unavailable');
        }
        if (answer.rubric_state === 'lost') return state('lost');
        if (answer.unavailable !== null) return state(answer.unavailable);
        return state('unavailable');
      };

      void (async () => {
        for (let tries = 0; tries < IN_FLIGHT_TRIES; tries += 1) {
          let answer: ReviewAnswer;
          try {
            // A fresh key each time: an ask never repeats a command, and
            // the server charges a result's review once whatever the key.
            answer = await requestRef.current(jobId, files, mintIdempotencyKey(), signal);
          } catch (err) {
            if (signal.aborted) return;
            if (isRunnerError(err) && err.code === 'already_in_flight') {
              await pause(Math.max(1, err.retryAfterSeconds ?? IN_FLIGHT_WAIT_S) * 1000, signal);
              if (signal.aborted) return;
              continue;
            }
            const denial = classifyRunnerError(err);
            if (denial?.kind === 'limit') {
              settle({ status: 'limit', review: null, retryAfterSeconds: denial.retryAfterSeconds });
            } else {
              settle(state('unavailable'));
            }
            return;
          }
          if (signal.aborted) return;
          settle(await answered(answer));
          return;
        }
        settle(state('unavailable'));
      })();
    },
    [stop],
  );

  const retry = useCallback(() => {
    const last = lastRef.current;
    if (last === null) return false;
    ask(last.jobId, last.files);
    return true;
  }, [ask]);

  return { ...view, ask, retry, show, reset };
}
