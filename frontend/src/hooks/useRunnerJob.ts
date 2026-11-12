// One runner action's durable job, from its 202 to its end
// (ROUNDS-00A-L03; lib/executionJobs explains the protocol).
//
// A page asks `begin(work)` for the command id an action sends, then
// hands the route's answer to `follow`. A job is followed here: one
// long-poll at a time, backing off while the server doesn't answer, and
// stopped when the page leaves. The page hears of the end through
// `onEnded`, with the envelope's output for its result views. Since PR 4
// every code run is a job, so a page reports any other answer as a
// failure (`notAJobAnswer`).
//
// The action is kept for the tab under `scope` (page, item, action): a
// reload picks its job back up, and `begin(work, true)` after an end the
// server caused sends the same id while the work is unchanged, so the
// runner runs that job again.

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  BACKOFF_MS,
  WAIT_S,
  beginAction,
  cancelJob,
  clearAction,
  isEnded,
  isJobAnswer,
  loadAction,
  readJob,
  saveAction,
  type JobAnswer,
  type StoredAction,
} from '../lib/executionJobs';
import { mintIdempotencyKey } from '../lib/idempotency';
import { isRunnerError, type RunnerError } from '../lib/runnerFetch';

export interface RunnerJobOptions {
  /** The job ended. Its envelope's `output`, when there is one, is the
   *  body the route answers in its request. */
  onEnded?: (job: JobAnswer) => void;
  /** A job read the server refused for the session: sign in again. */
  onDenied?: (err: RunnerError) => void;
}

export interface RunnerJob {
  /** The job as last read; null before one and after a new action. */
  job: JobAnswer | null;
  /** Queued or running. */
  active: boolean;
  /** The last read failed, and the next one is on its way. */
  reconnecting: boolean;
  /** The server no longer has the job. */
  gone: boolean;
  /** When this page first saw the job running (Date.now()). */
  runningSince: number | null;
  /** The command id an action on `work` sends. */
  begin: (work: unknown, retry?: boolean) => string;
  /** True when `answer` is a job, which is followed from here on. */
  follow: (answer: unknown) => boolean;
  cancel: () => Promise<void>;
}

function isAbort(err: unknown): boolean {
  return (err as { name?: string } | null)?.name === 'AbortError';
}

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

export function useRunnerJob(scope: string | null, options: RunnerJobOptions = {}): RunnerJob {
  const [job, setJob] = useState<JobAnswer | null>(null);
  const [reconnecting, setReconnecting] = useState(false);
  const [gone, setGone] = useState(false);
  const [runningSince, setRunningSince] = useState<number | null>(null);
  const optionsRef = useRef(options);
  const scopeRef = useRef(scope);
  const jobRef = useRef<JobAnswer | null>(null);
  const loopRef = useRef<AbortController | null>(null);
  const pendingRef = useRef<StoredAction | null>(null);

  useEffect(() => {
    optionsRef.current = options;
  });

  const stop = useCallback(() => {
    loopRef.current?.abort();
    loopRef.current = null;
  }, []);

  const forget = useCallback(() => {
    jobRef.current = null;
    setJob(null);
    setGone(false);
    setReconnecting(false);
    setRunningSince(null);
  }, []);

  const apply = useCallback((next: JobAnswer, forScope: string) => {
    if (scopeRef.current !== forScope) return;
    const before = jobRef.current;
    jobRef.current = next;
    setJob(next);
    if (next.state === 'leased' || next.state === 'started') {
      setRunningSince((since) => since ?? Date.now());
    }
    const endedNow = isEnded(next.state) && !(before?.job_id === next.job_id && isEnded(before.state));
    if (endedNow) {
      // Kept only while a same-key retry would run it again.
      if (!next.retryable) clearAction(forScope);
      optionsRef.current.onEnded?.(next);
    }
  }, []);

  const lost = useCallback((forScope: string) => {
    if (scopeRef.current !== forScope) return;
    clearAction(forScope);
    jobRef.current = null;
    setJob(null);
    setReconnecting(false);
    setGone(true);
  }, []);

  const refused = useCallback((err: unknown, forScope: string): boolean => {
    if (!isRunnerError(err)) return false;
    if (err.status === 404) {
      lost(forScope);
      return true;
    }
    if (err.status === 401 || err.code === 'unauthenticated') {
      setReconnecting(false);
      optionsRef.current.onDenied?.(err);
      return true;
    }
    return false;
  }, [lost]);

  const watch = useCallback(
    (jobId: string, forScope: string, firstWait: number) => {
      stop();
      const controller = new AbortController();
      loopRef.current = controller;
      void (async () => {
        let wait = firstWait;
        let failures = 0;
        while (!controller.signal.aborted) {
          try {
            const next = await readJob(jobId, wait, controller.signal);
            if (controller.signal.aborted) return;
            failures = 0;
            setReconnecting(false);
            apply(next, forScope);
            if (isEnded(next.state)) return;
            wait = WAIT_S;
          } catch (err) {
            if (controller.signal.aborted || isAbort(err)) return;
            if (refused(err, forScope)) return;
            setReconnecting(true);
            await pause(BACKOFF_MS[Math.min(failures, BACKOFF_MS.length - 1)], controller.signal);
            failures += 1;
          }
        }
      })();
    },
    [apply, refused, stop],
  );

  // A new scope starts clean, and picks up a job the tab kept for it.
  useEffect(() => {
    scopeRef.current = scope;
    pendingRef.current = null;
    forget();
    if (scope !== null) {
      const kept = loadAction(scope);
      if (kept?.jobId) watch(kept.jobId, scope, 0);
    }
    return stop;
  }, [scope, forget, stop, watch]);

  const begin = useCallback(
    (work: unknown, retry = false) => {
      stop();
      forget();
      if (scope === null) {
        pendingRef.current = null;
        return mintIdempotencyKey();
      }
      const action = beginAction(scope, work, retry);
      pendingRef.current = action;
      return action.key;
    },
    [scope, forget, stop],
  );

  const follow = useCallback(
    (answer: unknown) => {
      if (scope === null || !isJobAnswer(answer)) return false;
      const action = pendingRef.current;
      if (action !== null) saveAction(scope, { ...action, jobId: answer.job_id, at: Date.now() });
      apply(answer, scope);
      if (!isEnded(answer.state)) watch(answer.job_id, scope, WAIT_S);
      return true;
    },
    [scope, apply, watch],
  );

  const cancel = useCallback(async () => {
    const current = jobRef.current;
    if (scope === null || current === null || isEnded(current.state)) return;
    try {
      apply(await cancelJob(current.job_id), scope);
    } catch (err) {
      // Any other failure leaves it to the poll, which shows where the
      // job stands once the server answers.
      refused(err, scope);
    }
  }, [scope, apply, refused]);

  return {
    job,
    active: job !== null && !isEnded(job.state),
    reconnecting,
    gone,
    runningSince,
    begin,
    follow,
    cancel,
  };
}
