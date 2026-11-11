// A durable job's states (ROUNDS-00A-L03), in the runner notice's one
// polite live region: queued and running with Cancel, stopping, a limit
// by name, Retry after an end the server caused while the job has one
// left, the definition and not-found ends, and never a score or verdict.

import { describe, expect, it, vi } from 'vitest';
import { act, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { RunnerDenialNotice } from '../RunnerDenialNotice';
import { formatElapsed, jobCopy, type RunnerJobView } from '../RunnerJobStatus';
import type { JobAnswer, JobLimit, OutcomeClass } from '../../../lib/executionJobs';

function job(state: JobAnswer['state'], extra: Partial<JobAnswer> = {}): JobAnswer {
  return { job_id: 'jobaaaaaaaaaaa1', state, outcome_class: null, retryable: false, cancel_requested: false, envelope: null, ...extra };
}

function ended(state: JobAnswer['state'], outcome: OutcomeClass, extra: Partial<JobAnswer> = {}, limit: JobLimit | null = null) {
  return job(state, {
    outcome_class: outcome,
    envelope: {
      version: 'rounds.execution-envelope/v1', job_id: 'jobaaaaaaaaaaa1', state, outcome_class: outcome,
      authoritative: true, limit, parts: [], score: null, definition: null, queued_at: 1, started_at: 2,
      finished_at: 3, cleanup: 'confirmed', rubric: null, output: null,
    },
    ...extra,
  });
}

function view(next: JobAnswer | null, extra: Partial<RunnerJobView> = {}): RunnerJobView {
  return {
    job: next, gone: false, reconnecting: false, runningSince: null, action: 'run', onCancel: vi.fn(), onRetry: vi.fn(),
    ...extra,
  };
}

function renderJob(jobView: RunnerJobView) {
  return render(
    <MemoryRouter>
      <button type="button">Run</button>
      <RunnerDenialNotice denial={null} action="run" job={jobView} />
    </MemoryRouter>,
  );
}

describe('RunnerJobStatus', () => {
  it('shows a queued job in the one live region, with Cancel', async () => {
    const jobView = view(job('queued'));
    renderJob(jobView);
    const region = screen.getByRole('status');
    expect(region).toHaveAttribute('aria-live', 'polite');
    expect(region).toHaveTextContent('Queued');
    expect(region).toHaveTextContent('Your run starts when a runner is free.');
    expect(within(region).queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument();
    await userEvent.setup().click(within(region).getByRole('button', { name: 'Cancel' }));
    expect(jobView.onCancel).toHaveBeenCalledTimes(1);
  });

  it('shows a running job with how long it has run, outside what the region reads', () => {
    renderJob(view(job('started'), { runningSince: Date.now() - 12_000, action: 'tests' }));
    const region = screen.getByRole('status');
    expect(region).toHaveTextContent('Running');
    expect(region).toHaveTextContent('Your tests are running on the server.');
    const elapsed = screen.getByText(/^1[23] s$/);
    expect(elapsed).toHaveAttribute('aria-hidden', 'true');
    expect(region.querySelector('.runner-job-progress')).not.toBeNull();
    expect(within(region).getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
  });

  it('shows Stopping once a cancel was asked for, with nothing to press', () => {
    renderJob(view(job('started', { cancel_requested: true })));
    const region = screen.getByRole('status');
    expect(region).toHaveTextContent('Stopping');
    expect(within(region).queryByRole('button')).not.toBeInTheDocument();
  });

  it('says a finished run is ready to screen readers only', () => {
    renderJob(view(ended('completed', 'passed')));
    const region = screen.getByRole('status');
    expect(region).toHaveTextContent('Finished. The results are ready.');
    expect(region.firstElementChild).toHaveClass('sr-only');
    expect(within(region).queryByRole('button')).not.toBeInTheDocument();
  });

  it.each([
    ['wall_time', 'Time limit reached'],
    ['memory', 'Memory limit reached'],
    ['output', 'Output limit reached'],
  ] as const)('names the %s limit', (limit, title) => {
    renderJob(view(ended(limit === 'wall_time' ? 'timed-out' : 'completed', 'resource-limit', {}, limit)));
    expect(screen.getByRole('status')).toHaveTextContent(title);
  });

  it.each([
    ['worker-lost', 'Interrupted'],
    ['infrastructure-degraded', "Couldn't finish"],
  ] as const)('offers Retry after %s while the job has a retry left', async (outcome, title) => {
    const jobView = view(ended('failed', outcome, { retryable: true }));
    renderJob(jobView);
    const region = screen.getByRole('status');
    expect(region).toHaveTextContent(title);
    expect(region).toHaveTextContent('nothing was scored');
    expect(region).toHaveTextContent('Reference jobaaaaa');
    await userEvent.setup().click(within(region).getByRole('button', { name: 'Retry' }));
    expect(jobView.onRetry).toHaveBeenCalledTimes(1);
  });

  it('offers no Retry once the job has none left', () => {
    renderJob(view(ended('failed', 'worker-lost', { retryable: false })));
    const region = screen.getByRole('status');
    expect(region).toHaveTextContent('Try again later.');
    expect(within(region).queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument();
  });

  it.each([
    [ended('denied', 'definition-invalid'), "Can't run here"],
    [ended('canceled', 'canceled'), 'Canceled'],
    [ended('denied', 'policy-violation'), 'Stopped'],
  ])('says how a job ended (%#)', (next, title) => {
    renderJob(view(next));
    expect(screen.getByRole('status')).toHaveTextContent(title);
  });

  it('says a job the server no longer has is gone', () => {
    renderJob(view(null, { gone: true }));
    expect(screen.getByRole('status')).toHaveTextContent('Run not found');
  });

  it('says while the server is out of reach', () => {
    renderJob(view(job('queued'), { reconnecting: true }));
    expect(screen.getByRole('status')).toHaveTextContent("Can't reach the server right now");
  });

  it('never shows a score or a verdict for any end', () => {
    const ends: JobAnswer[] = [
      ended('timed-out', 'resource-limit', {}, 'wall_time'),
      ended('failed', 'worker-lost', { retryable: true }),
      ended('failed', 'infrastructure-degraded', { retryable: true }),
      ended('timed-out', 'infrastructure-degraded'),
      ended('denied', 'definition-invalid'),
      ended('canceled', 'canceled'),
    ];
    for (const next of ends) {
      const copy = jobCopy(view(next))!;
      expect(`${copy.title} ${copy.body}`).not.toMatch(/\bscore[ds]? \d|\d+ ?\/ ?100|\bPASS\b|\bFAIL\b|\bfailed\b|\bpassed\b/);
    }
  });

  it('shows a denial instead of the job when there is one', () => {
    render(
      <MemoryRouter>
        <RunnerDenialNotice
          denial={{ kind: 'turned_off', status: 503, code: 'execution_disabled', retryAfterSeconds: null, correlationId: null }}
          action="run"
          job={view(job('queued'))}
        />
      </MemoryRouter>,
    );
    const region = screen.getByRole('status');
    expect(region).toHaveTextContent('Turned off');
    expect(region).not.toHaveTextContent('Queued');
  });

  it('hands focus back to the control that started the action once it ends', () => {
    const { rerender } = render(
      <MemoryRouter>
        <button type="button">Run</button>
        <RunnerDenialNotice denial={null} action="run" job={view(job('started'))} />
      </MemoryRouter>,
    );
    const trigger = screen.getByRole('button', { name: 'Run' });
    (document.activeElement as HTMLElement | null)?.blur();
    act(() => {
      rerender(
        <MemoryRouter>
          <button type="button">Run</button>
          <RunnerDenialNotice denial={null} action="run" job={view(ended('completed', 'passed'), { trigger })} />
        </MemoryRouter>,
      );
    });
    expect(trigger).toHaveFocus();
  });

  it('keeps focus on the notice while a Cancel is under way', async () => {
    const jobView = view(job('started'));
    const { rerender } = renderJob(jobView);
    await userEvent.setup().click(screen.getByRole('button', { name: 'Cancel' }));
    act(() => {
      rerender(
        <MemoryRouter>
          <button type="button">Run</button>
          <RunnerDenialNotice denial={null} action="run" job={view(job('started', { cancel_requested: true }))} />
        </MemoryRouter>,
      );
    });
    expect(document.activeElement).toHaveAttribute('data-job-state', 'started');
  });
});

describe('formatElapsed', () => {
  it('reads as seconds, then minutes and seconds', () => {
    expect(formatElapsed(0)).toBe('0 s');
    expect(formatElapsed(8_900)).toBe('8 s');
    expect(formatElapsed(60_000)).toBe('1 min');
    expect(formatElapsed(65_000)).toBe('1 min 5 s');
  });
});
