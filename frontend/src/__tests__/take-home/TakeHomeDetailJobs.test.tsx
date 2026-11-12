// Take-home runs as durable jobs (ROUNDS-00A-L03): a job shows in the
// notice above the console until it ends, the harness result of an end
// the run earned shows as before, a limit or an end the harness or the
// infrastructure caused shows its notice with no score, and a run that
// failed without a result shows a fixed sentence and no score.
//
// Submissions as durable jobs (PR 3): the report opens from the row the
// server wrote and asks for its review once, a limit shows no score and
// no criterion verdict, mastery needs a passed envelope, and a submission
// that failed without a result shows a fixed sentence, never a score of 0.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const drafts = vi.hoisted(() => {
  const files = { 'kv.py': 'class KV:\n    pass\n' };
  return { files, savedFiles: files, setFile: () => {}, hydrated: true, resetToStarter: () => {} };
});
const practice = vi.hoisted(() => ({ set: vi.fn() }));

vi.mock('../../lib/pocketbase', () => ({ pb: { authStore: { token: 'test-token-placeholder' } } }));
vi.mock('../../pages/take-home/takeHomeApi', async (importOriginal) => ({
  ...((await importOriginal()) as Record<string, unknown>),
  getAssignment: vi.fn(),
  getLatestTakeHomeAttempt: vi.fn().mockResolvedValue(null),
  runProject: vi.fn(),
  submitAttempt: vi.fn(),
  getGradedTakeHomeAttempt: vi.fn(),
  requestSubmissionReview: vi.fn(),
  upsertInProgressTakeHomeAttempt: vi.fn().mockResolvedValue(undefined),
  deleteInProgressTakeHomeAttempt: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('../../hooks/useTakeHomeDrafts', () => ({ useTakeHomeDrafts: () => drafts }));
vi.mock('../../hooks/usePracticeStatus', () => ({ usePracticeStatus: () => [null, practice.set] }));
vi.mock('../../campaign/CampaignContext', () => ({ useCampaign: () => ({ currentId: null }) }));
vi.mock('../../components/shell/AppHeader', () => ({ default: () => <header /> }));
vi.mock('../../components/shell/StatusAction', () => ({ default: () => null }));
vi.mock('../../components/take-home/TakeHomeChatPanel', () => ({ default: () => null }));
vi.mock('../../components/editor/MultiFileEditor', () => ({
  default: (props: { bottomActions?: React.ReactNode }) => <div>{props.bottomActions}</div>,
}));

import TakeHomeDetail from '../../pages/take-home/TakeHomeDetail';
import {
  getAssignment,
  getGradedTakeHomeAttempt,
  requestSubmissionReview,
  runProject,
  submitAttempt,
  type HarnessOutput,
  type TakeHomeAttemptRow,
} from '../../pages/take-home/takeHomeApi';
import { RunnerError } from '../../lib/runnerFetch';
import { UUID_V7_PATTERN } from '../../lib/idempotency';
import { phoneWidth } from '../../test/media';
import type { JobAnswer, JobEnvelope, JobLimit, OutcomeClass } from '../../lib/executionJobs';
import type { ReviewAnswer } from '../../lib/gradedRows';

const ASSIGNMENT = {
  id: 'a1',
  slug: 'kv-store-py',
  title: 'KV store',
  difficulty: 'medium',
  language: 'python',
  time_budget_min: 90,
  ai_policy: 'off',
  prompt_md: 'Build a KV store.',
  starter_files: [{ path: 'kv.py', contents: 'class KV:\n    pass\n' }],
  rubric: { items: [] },
  topics: [],
  companies: [],
};

const GRADED = {
  score: 0.5,
  passed: false,
  criteria: [
    { id: 'gets', passed: true, weight: 0.5, logs: 'ok' },
    { id: 'sets', passed: false, weight: 0.5, logs: 'assertion' },
  ],
  stdout: '',
  stderr: '',
  error: null,
  duration_ms: 1500,
  truncated: false,
};

function job(state: JobAnswer['state'], extra: Partial<JobAnswer> = {}): JobAnswer {
  return { job_id: 'jobaaaaaaaaaaa1', state, outcome_class: null, retryable: false, cancel_requested: false, envelope: null, ...extra };
}

function ended(state: JobAnswer['state'], outcome: OutcomeClass, output: Record<string, unknown> | null,
  limit: JobLimit | null = null): JobAnswer {
  const envelope: JobEnvelope = {
    version: 'rounds.execution-envelope/v1', job_id: 'jobaaaaaaaaaaa1', state, outcome_class: outcome,
    authoritative: true, limit, parts: [], score: null, definition: null, queued_at: 1, started_at: 2,
    finished_at: 3, cleanup: 'confirmed', rubric: null, output,
  };
  return job(state, { outcome_class: outcome, envelope });
}

const fetchMock = vi.fn<typeof fetch>();
let answers: JobAnswer[] = [];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/take-home/assignment/kv-store-py']}>
      <Routes>
        <Route path="/take-home/assignment/:slug" element={<TakeHomeDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
  answers = [];
  vi.mocked(getAssignment).mockResolvedValue(ASSIGNMENT as never);
  vi.mocked(runProject).mockReset();
  vi.mocked(submitAttempt).mockReset();
  vi.mocked(getGradedTakeHomeAttempt).mockReset();
  vi.mocked(requestSubmissionReview).mockReset();
  practice.set.mockReset();
  fetchMock.mockReset().mockImplementation(async (_url, init) => {
    while (answers.length === 0) {
      await new Promise((wake) => setTimeout(wake, 5));
      if (init?.signal?.aborted) throw new DOMException('The operation was aborted.', 'AbortError');
    }
    return new Response(JSON.stringify(answers.shift()), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('TakeHomeDetail jobs', () => {
  it('shows a queued job above the console, then the harness result it ended with', async () => {
    vi.mocked(runProject).mockResolvedValue(job('queued'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Queued'));
    expect(screen.queryByText(/\/ 100|\/100/)).not.toBeInTheDocument();
    answers.push(ended('completed', 'candidate-failure', GRADED));
    await waitFor(() => expect(screen.getAllByText(/50 ?\/ ?100/).length).toBeGreaterThan(0));
  });

  it('names a time limit with no score', async () => {
    vi.mocked(runProject).mockResolvedValue(job('started'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    answers.push(ended('timed-out', 'resource-limit', null, 'wall_time'));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Time limit reached'));
    expect(screen.queryByText(/\/ 100|\/100/)).not.toBeInTheDocument();
  });

  // The take-home body for a channel that came back empty or malformed:
  // a score of 0 with every criterion failed, which no run earned.
  const UNSCORED = {
    ...GRADED,
    score: 0,
    criteria: GRADED.criteria.map((c) => ({ ...c, passed: false, logs: 'no-result' })),
  };

  it.each([
    ['failed', 'infrastructure-degraded', "Couldn't finish"],
    ['denied', 'definition-invalid', "Can't run here"],
  ] as const)('shows a %s %s end as its notice, with no score', async (state, outcome, notice) => {
    vi.mocked(runProject).mockResolvedValue(job('started'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    answers.push(ended(state, outcome, UNSCORED));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent(notice));
    expect(screen.queryByText(/\/ 100|\/100|gets|sets/)).not.toBeInTheDocument();
  });

  it("shows a run that failed without a result as a fixed sentence, never the server's text, with no score", async () => {
    vi.mocked(runProject).mockRejectedValue(new RunnerError({ message: 'take-home run 422: Field required', status: 422 }));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    expect(await screen.findByText("The runner couldn't read this run. Reload the page and run it again.")).toBeInTheDocument();
    expect(screen.getByText('HARNESS ERROR')).toBeInTheDocument();
    expect(screen.queryByText(/Field required|\/ 100|\/100|criteria/)).not.toBeInTheDocument();
  });
});

const DEFINITION = { track: 'take-home', slug: 'kv-store-py', variant: 'python', version: 1, checksum: 'a'.repeat(64) };

function harness(extra: Partial<HarnessOutput> = {}): HarnessOutput {
  return {
    outcome_class: 'passed', limit: null, score: 1, passed: true,
    criteria: [{ id: 'gets', passed: true, weight: 0.5, logs: 'ok' }, { id: 'sets', passed: true, weight: 0.5, logs: 'ok' }],
    outcomes: [], stdout: '', stderr: '', error: null, duration_ms: 900, truncated: false, definition: DEFINITION as never,
    ...extra,
  };
}

function gradedRow(output: HarnessOutput, review: TakeHomeAttemptRow['rubric_review'] = null): TakeHomeAttemptRow {
  return {
    id: 'rowaaaaaaaaaaa1', user: 'useraaaaaaaaaa1', campaign: '', assignment: 'a1', files: drafts.files, notes: '',
    harness_output: output, rubric_review: review, status: 'graded', envelope: 'envaaaaaaaaaaa1', updated: '',
  };
}

function reviewAnswer(extra: Partial<ReviewAnswer>): ReviewAnswer {
  return { job_id: 'jobaaaaaaaaaaa1', rubric_state: null, rubric_review: null, unavailable: null, ...extra };
}

const REVIEW = { items: [{ id: 'design', score: 0.6, evidence: 'Small API.', suggestions: [] }], total: 0.6 };

describe('TakeHomeDetail submission jobs', () => {
  it('follows a submission to the report the server wrote, and asks for its review once', async () => {
    vi.mocked(submitAttempt).mockResolvedValue(job('queued'));
    vi.mocked(getGradedTakeHomeAttempt).mockResolvedValue(gradedRow(harness()));
    vi.mocked(requestSubmissionReview).mockResolvedValue(reviewAnswer({ rubric_state: 'completed', rubric_review: REVIEW }));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Submit' }));
    const region = screen.getByTestId('runner-denial');
    await waitFor(() => expect(region).toHaveTextContent('Grading starts when a runner is free.'));
    answers.push(job('started'));
    await waitFor(() => expect(region).toHaveTextContent('Your submission is being graded on the server.'));
    answers.push(ended('completed', 'passed', null));
    const dialog = await screen.findByRole('dialog', { name: 'Submission · KV store' });
    await waitFor(() => expect(within(dialog).getByText('Harness 100/100 · Rubric 60/100')).toBeInTheDocument());
    expect(requestSubmissionReview).toHaveBeenCalledTimes(1);
    expect(vi.mocked(requestSubmissionReview).mock.calls[0].slice(0, 2)).toEqual(['jobaaaaaaaaaaa1', drafts.files]);
    expect(practice.set).toHaveBeenCalledWith('mastered');
    expect(vi.mocked(submitAttempt).mock.calls[0][1]?.idempotencyKey).toMatch(UUID_V7_PATTERN);
  });

  it('shows a limit with no harness score and no criterion verdict, and sets no mastery', async () => {
    vi.mocked(submitAttempt).mockResolvedValue(job('started'));
    const limited = harness({
      outcome_class: 'resource-limit', limit: 'wall_time', score: null, passed: null, error: 'The grader ran out of time.',
      criteria: [{ id: 'gets', passed: null, weight: 0.5, logs: 'timeout' }, { id: 'sets', passed: null, weight: 0.5, logs: 'timeout' }],
    });
    vi.mocked(getGradedTakeHomeAttempt).mockResolvedValue(gradedRow(limited));
    vi.mocked(requestSubmissionReview).mockResolvedValue(reviewAnswer({ rubric_state: 'lost' }));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Submit' }));
    answers.push(ended('timed-out', 'resource-limit', null, 'wall_time'));
    const dialog = await screen.findByRole('dialog');
    expect(screen.getByTestId('runner-denial')).toHaveTextContent('The grader reached its time limit, so this submission has no score.');
    expect(within(dialog).getByText('Harness stopped: time limit reached · Rubric not reviewed')).toBeInTheDocument();
    expect(within(dialog).getByText('TIME LIMIT REACHED')).toBeInTheDocument();
    expect(within(dialog).getByText('The grader ran out of time.')).toBeInTheDocument();
    const criteria = dialog.querySelectorAll('[data-criterion]');
    expect([...criteria].map((c) => c.getAttribute('data-criterion'))).toEqual(['not scored', 'not scored']);
    expect(dialog.textContent).not.toMatch(/\d+ ?\/ ?100|✓|✗/);
    await waitFor(() => expect(within(dialog).getByTestId('review-status')).toHaveTextContent("Review didn't finish"));
    expect(practice.set).not.toHaveBeenCalledWith('mastered');
  });

  it("retries a submission the runner lost under the same command id, with no report", async () => {
    vi.mocked(submitAttempt).mockResolvedValue(job('queued'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Submit' }));
    const lost = ended('failed', 'worker-lost', null);
    answers.push({ ...lost, retryable: true, envelope: lost.envelope && { ...lost.envelope, authoritative: false } });
    const region = screen.getByTestId('runner-denial');
    await waitFor(() => expect(region).toHaveTextContent('Interrupted'));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    await user.click(within(region).getByRole('button', { name: 'Retry' }));
    await waitFor(() => expect(submitAttempt).toHaveBeenCalledTimes(2));
    const [first, second] = vi.mocked(submitAttempt).mock.calls;
    expect(second[1]?.idempotencyKey).toBe(first[1]?.idempotencyKey);
    expect(getGradedTakeHomeAttempt).not.toHaveBeenCalled();
  });

  it('says a submission that failed without a result in a fixed sentence, never a score of 0 or the server text', async () => {
    vi.mocked(submitAttempt).mockRejectedValue(new TypeError('Cannot read properties of undefined (reading "harness")'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Submit' }));
    const dialog = await screen.findByRole('dialog');
    const problem = within(dialog).getByTestId('report-problem');
    expect(problem).toHaveTextContent("Grading didn't finish, so nothing was graded. Submit again.");
    expect(dialog.textContent).not.toMatch(/Cannot read|harness"|\b0\b|\/100|Harness/);
  });
});

describe('TakeHomeDetail jobs on a phone', () => {
  const unmatched = window.matchMedia;
  afterEach(() => {
    window.matchMedia = unmatched;
  });

  /** The page's one live region. */
  function notice() {
    const regions = screen.getAllByRole('status');
    expect(regions).toHaveLength(1);
    return regions[0];
  }

  it('shows a queued run, then a submission, at the full width below the body, never in the files column', async () => {
    window.matchMedia = phoneWidth();
    vi.mocked(runProject).mockResolvedValue(job('queued'));
    vi.mocked(submitAttempt).mockResolvedValue(job('started'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    await waitFor(() => expect(notice()).toHaveTextContent('Queued'));
    expect(notice().closest('[data-take-home-pane="notice"]')).not.toBeNull();
    expect(notice().closest('[data-take-home-pane="center"]')).toBeNull();
    // Its buttons are touch targets on a phone.
    expect(within(notice()).getByRole('button', { name: 'Cancel' }).style.minHeight).toBe('44px');

    answers.push(ended('canceled', 'canceled', null));
    await waitFor(() => expect(notice()).toHaveTextContent('Canceled'));
    await user.click(screen.getByRole('button', { name: 'Submit' }));
    await waitFor(() => expect(notice()).toHaveTextContent('Your submission is being graded on the server.'));
    expect(notice().closest('[data-take-home-pane="notice"]')).not.toBeNull();
    expect(notice().closest('[data-take-home-pane="center"]')).toBeNull();
  });

  it('keeps a job in the center column on a wider screen', async () => {
    vi.mocked(runProject).mockResolvedValue(job('queued'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    await waitFor(() => expect(notice()).toHaveTextContent('Queued'));
    expect(notice().closest('[data-take-home-pane="center"]')).not.toBeNull();
    expect(document.querySelector('[data-take-home-pane="notice"]')).toBeNull();
    expect(within(notice()).getByRole('button', { name: 'Cancel' }).style.minHeight).toBe('32px');
  });
});
