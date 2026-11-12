// A grading job's report (ROUNDS-00A-L03 PR 3): each checkpoint shows its
// own outcome, so a checkpoint a limit stopped names the limit and shows
// no verdict, no counts, and no score; and the review area says where the
// review stands while the result has none.

import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../components/ai/AIPatchView', () => ({ default: () => null }));

import GradeReport, { gradeSummary } from '../../pages/ai-coding/GradeReport';
import type { CheckpointResult } from '../../pages/ai-coding/aiCodingApi';

const PASSED: CheckpointResult = {
  index: 0, label: 'Fetch the user', outcome_class: 'passed', limit: null, passed: true, score: 1, executed: 3,
  passed_count: 3, failed_count: 0, outcomes: [{ id: 'r001', outcome: 'passed', reason: 'ok' }], error: null,
};
const MISSED: CheckpointResult = {
  index: 1, label: 'Retry on 503', outcome_class: 'candidate-failure', limit: null, passed: false, score: 0.5,
  executed: 2, passed_count: 1, failed_count: 1,
  outcomes: [{ id: 'r002', outcome: 'passed', reason: 'ok' }, { id: 'r003', outcome: 'failed', reason: 'assertion' }],
  error: null,
};
const TIMED_OUT: CheckpointResult = {
  index: 2, label: 'Back off', outcome_class: 'resource-limit', limit: 'wall_time', passed: null, score: null,
  executed: 0, passed_count: 0, failed_count: 0, outcomes: [], error: 'This checkpoint ran out of time.',
};

function renderReport(props: Partial<Parameters<typeof GradeReport>[0]> = {}) {
  return render(
    <MemoryRouter>
      <GradeReport testResults={[PASSED, MISSED, TIMED_OUT]} rubric={{ items: [] }} rubricReview={null} {...props} />
    </MemoryRouter>,
  );
}

describe('GradeReport checkpoints', () => {
  it('names the limit on the checkpoint it stopped, with no verdict, counts, or score', () => {
    renderReport();
    const items = screen.getAllByRole('listitem').filter((li) => li.hasAttribute('data-checkpoint-outcome'));
    expect(items).toHaveLength(3);
    const limited = items[2];
    expect(limited).toHaveAttribute('data-checkpoint-outcome', 'resource-limit');
    expect(within(limited).getByText('Time limit reached')).toBeInTheDocument();
    expect(within(limited).getByText('This checkpoint ran out of time.')).toBeInTheDocument();
    expect(limited.textContent).not.toMatch(/\bfail\b|\bpass\b|passed|failed|\d+ ?\/ ?100/);
    // The checkpoints the run earned keep theirs.
    expect(within(items[0]).getByText('pass')).toBeInTheDocument();
    expect(within(items[1]).getByText('fail')).toBeInTheDocument();
    expect(within(items[1]).getByText('1 passed · 1 failed')).toBeInTheDocument();
  });

  it('numbers checkpoints by their own index and shows their labels', () => {
    renderReport({ testResults: [TIMED_OUT] });
    expect(screen.getByText('Checkpoint 3')).toBeInTheDocument();
    expect(screen.getByText('Back off')).toBeInTheDocument();
  });

  it('sums up how many passed and how many a limit stopped', () => {
    expect(gradeSummary([PASSED, MISSED, TIMED_OUT])).toBe('1 of 3 checkpoints passed · 1 stopped at a limit');
    expect(gradeSummary([PASSED, MISSED])).toBe('1 of 2 checkpoints passed');
    expect(gradeSummary([])).toBeUndefined();
  });
});

describe('GradeReport review states', () => {
  it.each([
    ['reviewing', 'Reviewing'],
    ['no_provider', 'No AI provider set up'],
    ['files_changed', 'Files changed'],
    ['lost', "Review didn't finish"],
    ['not_reviewable', "Can't review here"],
    ['unavailable', 'Review unavailable'],
  ] as const)('shows %s in a polite live region', (status, title) => {
    renderReport({ review: { status } });
    const region = screen.getByTestId('review-status');
    expect(region).toHaveAttribute('role', 'status');
    expect(region).toHaveAttribute('aria-live', 'polite');
    expect(region).toHaveTextContent(title);
    expect(screen.queryByText(/\/ 100/)).not.toBeInTheDocument();
  });

  it('points to Settings when no AI provider is set up', () => {
    renderReport({ review: { status: 'no_provider' } });
    expect(screen.getByRole('link', { name: 'Open settings' })).toHaveAttribute('href', '/settings');
  });

  it('offers Try again where another ask can help, and Request review for a row read on its own', async () => {
    const onRetry = vi.fn();
    const onRequest = vi.fn();
    const user = userEvent.setup();
    const { rerender } = renderReport({ review: { status: 'limit', retryAfterSeconds: 120, onRetry, onRequest } });
    expect(screen.getByTestId('review-status')).toHaveTextContent('Try again in 2 minutes.');
    await user.click(screen.getByRole('button', { name: 'Try again' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
    rerender(
      <MemoryRouter>
        <GradeReport testResults={[PASSED]} rubric={{ items: [] }} rubricReview={null} review={{ status: 'not_requested', onRetry, onRequest }} />
      </MemoryRouter>,
    );
    await user.click(screen.getByRole('button', { name: 'Request review' }));
    expect(onRequest).toHaveBeenCalledTimes(1);
    for (const status of ['reviewing', 'files_changed', 'lost', 'no_provider'] as const) {
      rerender(
        <MemoryRouter>
          <GradeReport testResults={[PASSED]} rubric={{ items: [] }} rubricReview={null} review={{ status, onRetry, onRequest }} />
        </MemoryRouter>,
      );
      expect(screen.queryByRole('button', { name: /Try again|Request review/ })).not.toBeInTheDocument();
    }
  });

  it('shows the review once it lands, and says so to screen readers', () => {
    renderReport({
      rubricReview: { items: [{ id: 'clarity', score: 0.8, evidence: 'Clear names.', suggestions: [] }], total: 0.8 },
      review: { status: 'reviewed' },
    });
    expect(screen.getAllByText('80 / 100').length).toBeGreaterThan(0);
    expect(screen.getByTestId('review-status')).toHaveTextContent('Reviewed. The rubric review is ready.');
  });

  it("keeps a skipped review's fixed sentence, once, and says skipped to screen readers", () => {
    renderReport({
      rubricReview: {
        items: [],
        total: 0,
        skipped: true,
        reason: "The review didn't finish, so this submission has no review.",
      },
      review: { status: 'reviewed' },
    });
    expect(
      screen.getByText("Rubric review skipped: The review didn't finish, so this submission has no review."),
    ).toBeInTheDocument();
    expect(screen.getByTestId('review-status')).toHaveTextContent('Rubric review skipped.');
    expect(screen.getByTestId('review-status')).not.toHaveTextContent('ready');
  });
});
