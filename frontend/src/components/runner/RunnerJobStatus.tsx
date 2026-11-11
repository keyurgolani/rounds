// A runner action's durable job (ROUNDS-00A-L03), shown in the runner
// notice's live region (RunnerDenialNotice) so a page has one polite
// region for every runner state.
//
// - Queued and running offer Cancel; running shows how long it has run
//   and a thin progress line; a cancel asked for shows Stopping.
// - A run that finished with a result says so to screen readers only:
//   the result shows in the page's own result views.
// - A limit names itself. An end the server caused (the runner was lost,
//   or the server couldn't finish) offers Retry while the job has a retry
//   left. A definition the server can't run, a run it stopped, and a job
//   it no longer has each say what happened.
//
// None of them shows a score or a verdict. Every state has an icon and a
// written title, so color is never the only signal. When an action ends
// and focus was left on nothing, it goes back to the control that started
// the action; while a Cancel or Retry is under way it rests on the notice.

import { useEffect, useRef, useState, type CSSProperties } from 'react';
import {
  Ban,
  CircleStop,
  FileX,
  Hourglass,
  RotateCcw,
  SearchX,
  ServerCrash,
  ShieldAlert,
  Timer,
  Unplug,
  type LucideIcon,
} from 'lucide-react';
import { isEnded, type JobAnswer, type JobLimit } from '../../lib/executionJobs';

export type RunnerJobAction = 'run' | 'tests';

export interface RunnerJobView {
  job: JobAnswer | null;
  gone: boolean;
  reconnecting: boolean;
  runningSince: number | null;
  action: RunnerJobAction;
  onCancel: () => void;
  /** Offered after an end the server caused, while the job is retryable. */
  onRetry?: () => void;
  /** The control that started the action. */
  trigger?: HTMLElement | null;
}

type Tone = 'progress' | 'attention' | 'quiet';

interface JobCopy {
  tone: Tone;
  icon: LucideIcon | null;
  title: string;
  body: string;
  /** Read out but not shown: the page's result views show the rest. */
  hidden?: boolean;
  cancel?: boolean;
  retry?: boolean;
  running?: boolean;
  /** Shows the job's reference, for an end worth reporting. */
  reference?: boolean;
}

const WHO: Record<RunnerJobAction, { run: string; runs: string; kept: string }> = {
  run: { run: 'run', runs: 'Your code is running', kept: 'Your code is still here.' },
  tests: { run: 'test run', runs: 'Your tests are running', kept: 'Your code is still here.' },
};

const LIMITS: Record<JobLimit, { title: string; body: string }> = {
  wall_time: { title: 'Time limit reached', body: 'It stopped when it reached its time limit.' },
  cpu_time: { title: 'CPU limit reached', body: 'It stopped when it used all the CPU time it may.' },
  memory: { title: 'Memory limit reached', body: 'It stopped when it used all the memory it may.' },
  processes: { title: 'Process limit reached', body: 'It stopped when it started more processes than it may.' },
  files: { title: 'File limit reached', body: 'It stopped when it wrote more than it may.' },
  output: { title: 'Output limit reached', body: 'It stopped when its output reached the limit.' },
};

/** What a job view shows, or null when there's nothing to show. */
export function jobCopy(view: RunnerJobView): JobCopy | null {
  const who = WHO[view.action];
  if (view.gone) {
    return {
      tone: 'quiet',
      icon: SearchX,
      title: 'Run not found',
      body: `This ${who.run} is no longer on the server. ${who.kept}`,
    };
  }
  const job = view.job;
  if (job === null) return null;
  const waiting = view.reconnecting ? " Can't reach the server right now, so this page is checking again." : '';
  if (!isEnded(job.state)) {
    if (job.cancel_requested) {
      return { tone: 'progress', icon: CircleStop, title: 'Stopping', body: `The ${who.run} stops in a few seconds.${waiting}` };
    }
    if (job.state === 'queued') {
      return {
        tone: 'progress',
        icon: Hourglass,
        title: 'Queued',
        body: `Your ${who.run} starts when a runner is free.${waiting}`,
        cancel: true,
      };
    }
    return {
      tone: 'progress',
      icon: Timer,
      title: 'Running',
      body: `${who.runs} on the server.${waiting}`,
      cancel: true,
      running: true,
    };
  }
  const limit = job.envelope?.limit ?? null;
  switch (job.outcome_class) {
    case 'passed':
    case 'candidate-failure':
      return { tone: 'quiet', icon: null, title: 'Finished', body: 'The results are ready.', hidden: true };
    case 'resource-limit': {
      const named = limit ? LIMITS[limit] : LIMITS.wall_time;
      return { tone: 'attention', icon: Timer, title: named.title, body: `${named.body} ${who.kept}` };
    }
    case 'canceled':
      return { tone: 'quiet', icon: Ban, title: 'Canceled', body: `The ${who.run} was stopped. ${who.kept}` };
    case 'worker-lost':
      return {
        tone: 'attention',
        icon: Unplug,
        title: 'Interrupted',
        body: `The server running this stopped before it finished, so nothing was scored. ${
          job.retryable ? 'Retry runs it again.' : 'Try again later.'
        }`,
        retry: job.retryable,
        reference: true,
      };
    case 'infrastructure-degraded':
      return {
        tone: 'attention',
        icon: ServerCrash,
        title: "Couldn't finish",
        body: `The server couldn't finish this ${who.run}, so nothing was scored. ${
          job.retryable ? 'Retry runs it again.' : 'Try again later.'
        }`,
        retry: job.retryable,
        reference: true,
      };
    case 'definition-invalid':
      return {
        tone: 'quiet',
        icon: FileX,
        title: "Can't run here",
        body: `This practice item can't run on this server right now, so nothing ran. ${who.kept}`,
        reference: true,
      };
    case 'policy-violation':
      return {
        tone: 'attention',
        icon: ShieldAlert,
        title: 'Stopped',
        body: `The ${who.run} did something this server doesn't allow, so it was stopped. ${who.kept}`,
        reference: true,
      };
    default:
      return { tone: 'quiet', icon: null, title: 'Finished', body: 'The results are ready.', hidden: true };
  }
}

/** "8 s", "1 min 5 s". */
export function formatElapsed(ms: number): string {
  const total = Math.max(0, Math.floor(ms / 1000));
  if (total < 60) return `${total} s`;
  const minutes = Math.floor(total / 60);
  const seconds = total % 60;
  return seconds === 0 ? `${minutes} min` : `${minutes} min ${seconds} s`;
}

const TONE_COLOR: Record<Tone, string> = {
  progress: 'var(--ochre)',
  attention: 'var(--status-warn)',
  quiet: 'var(--text-3)',
};

function useNow(enabled: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!enabled) return;
    setNow(Date.now());
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [enabled]);
  return now;
}

interface RunnerJobStatusProps {
  view: RunnerJobView;
  /** Extra style for the notice, as RunnerDenialNotice's contentStyle. */
  contentStyle?: CSSProperties;
  actionStyle: CSSProperties;
}

export function RunnerJobStatus({ view, contentStyle, actionStyle }: RunnerJobStatusProps) {
  const copy = jobCopy(view);
  const rootRef = useRef<HTMLDivElement | null>(null);
  // A Cancel or Retry was pressed: its button goes, so focus rests here.
  const pressed = useRef(false);
  const now = useNow(Boolean(copy?.running) && view.runningSince !== null);
  const job = view.job;
  const ended = view.gone || (job !== null && isEnded(job.state));
  const stage = view.gone ? 'gone' : job ? `${job.job_id}:${job.state}:${job.cancel_requested}` : 'none';

  useEffect(() => {
    const active = document.activeElement;
    if (active && active !== document.body) return;
    const trigger = view.trigger;
    if (ended && trigger && trigger.isConnected && !(trigger as HTMLButtonElement).disabled) {
      pressed.current = false;
      trigger.focus({ preventScroll: true });
      return;
    }
    if (pressed.current && rootRef.current) rootRef.current.focus({ preventScroll: true });
    // The stage is what changes the buttons.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage]);

  if (copy === null) return null;
  if (copy.hidden) {
    return (
      <span className="sr-only">
        {copy.title}. {copy.body}
      </span>
    );
  }
  const Icon = copy.icon;
  const press = (fn: (() => void) | undefined) => () => {
    pressed.current = true;
    rootRef.current?.focus({ preventScroll: true });
    fn?.();
  };

  return (
    <div
      ref={rootRef}
      tabIndex={-1}
      data-job-state={job?.state ?? 'gone'}
      data-job-outcome={job?.outcome_class ?? ''}
      style={{
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        gap: 10,
        alignItems: 'flex-start',
        padding: '10px 12px',
        borderRadius: 'var(--radius)',
        background: 'var(--bg-elev)',
        boxShadow: 'inset 0 0 0 1px var(--border-strong)',
        fontSize: 12.5,
        lineHeight: 1.45,
        color: 'var(--text-2)',
        outline: 'none',
        ...contentStyle,
      }}
    >
      {Icon && (
        <Icon
          aria-hidden="true"
          size={16}
          strokeWidth={1.8}
          style={{ flexShrink: 0, marginTop: 1, color: TONE_COLOR[copy.tone] }}
        />
      )}
      <div style={{ minWidth: 0, flex: 1 }}>
        <strong style={{ display: 'block', color: 'var(--text)', fontWeight: 600 }}>
          {copy.title}
          <span className="sr-only">. </span>
        </strong>
        <span>{copy.body}</span>
        {copy.running && view.runningSince !== null && (
          // Outside what the region reads, so it isn't read every second.
          <span
            aria-hidden="true"
            className="mono"
            style={{ display: 'block', marginTop: 2, fontSize: 10.5, color: 'var(--text-3)' }}
          >
            {formatElapsed(now - view.runningSince)}
          </span>
        )}
        {copy.reference && job && (
          <span className="mono" style={{ display: 'block', marginTop: 2, fontSize: 10.5, color: 'var(--text-4)' }}>
            Reference {job.job_id.slice(0, 8)}
          </span>
        )}
        {(copy.cancel || (copy.retry && view.onRetry)) && (
          <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
            {copy.cancel && (
              <button type="button" onClick={press(view.onCancel)} style={actionStyle}>
                <CircleStop aria-hidden="true" size={12} strokeWidth={1.8} />
                Cancel
              </button>
            )}
            {copy.retry && view.onRetry && (
              <button type="button" onClick={press(view.onRetry)} style={actionStyle}>
                <RotateCcw aria-hidden="true" size={12} strokeWidth={1.8} />
                Retry
              </button>
            )}
          </div>
        )}
      </div>
      {copy.running && <span aria-hidden="true" className="runner-job-progress" />}
    </div>
  );
}
