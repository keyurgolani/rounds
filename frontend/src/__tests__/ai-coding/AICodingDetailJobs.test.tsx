// AI-coding project runs as durable jobs (ROUNDS-00A-L03): a job shows
// in the notice above the console until it ends, the result of an end
// the run earned shows in the console, a limit shows no FAIL, an end the
// server caused offers Retry under the same command id, once per press,
// and a run that failed without a result shows a fixed sentence, never
// a FAIL it didn't earn.
//
// Grades as durable jobs (PR 3): the notice follows the grade, an
// authoritative end opens the report from the row the server wrote and
// asks for its review once, the page writes no row, mastery needs a
// passed envelope, and a grade that failed without a result shows a
// fixed sentence with no score.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const drafts = vi.hoisted(() => {
  const files = { 'cart.py': 'def add(a, b):\n    return a + b\n' };
  return {
    files,
    savedFiles: files,
    setFile: () => {},
    hydrated: true,
    resetToStarter: () => {},
    persistImmediately: () => Promise.resolve(),
  };
});

const practice = vi.hoisted(() => ({ set: vi.fn() }));

vi.mock('../../lib/pocketbase', () => ({ pb: { authStore: { token: 'test-token-placeholder' } } }));
vi.mock('../../pages/ai-coding/aiCodingApi', async (importOriginal) => ({
  ...((await importOriginal()) as Record<string, unknown>),
  getRound: vi.fn(),
  getLatestAttempt: vi.fn().mockResolvedValue(null),
  runProject: vi.fn(),
  gradeAttempt: vi.fn(),
  persistAttempt: vi.fn(),
  getGradedAttempt: vi.fn(),
  requestGradeReview: vi.fn(),
  upsertInProgressAttempt: vi.fn().mockResolvedValue(undefined),
  deleteInProgressAttempt: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('../../hooks/useAICodingDrafts', () => ({ useAICodingDrafts: () => drafts }));
vi.mock('../../hooks/usePracticeStatus', () => ({ usePracticeStatus: () => [null, practice.set] }));
vi.mock('../../campaign/CampaignContext', () => ({ useCampaign: () => ({ currentId: null }) }));
vi.mock('../../components/shell/AppHeader', () => ({ default: () => <header /> }));
vi.mock('../../components/shell/StatusAction', () => ({ default: () => null }));
vi.mock('../../components/ai/AIChatPanel', () => ({ default: () => null }));
vi.mock('../../components/editor/MultiFileEditor', () => ({
  default: (props: { bottomActions?: React.ReactNode }) => <div>{props.bottomActions}</div>,
}));

import AICodingDetail from '../../pages/ai-coding/AICodingDetail';
import {
  getGradedAttempt,
  getRound,
  gradeAttempt,
  persistAttempt,
  requestGradeReview,
  runProject,
  type AttemptRow,
  type CheckpointResult,
} from '../../pages/ai-coding/aiCodingApi';
import { RunnerError } from '../../lib/runnerFetch';
import { UUID_V7_PATTERN } from '../../lib/idempotency';
import { phoneWidth } from '../../test/media';
import type { JobAnswer, JobEnvelope, JobLimit, OutcomeClass } from '../../lib/executionJobs';
import type { ReviewAnswer } from '../../lib/gradedRows';

const ROUND = {
  id: 'r1',
  slug: 'cart-totals',
  title: 'Cart totals',
  difficulty: 'easy',
  language: 'python',
  description: 'Fix the cart.',
  starter_files: [{ path: 'cart.py', contents: 'def add(a, b):\n    return a + b\n' }],
  checkpoints: [{ label: 'Add', prompt: 'Make add work.', ai_allowed: false, test_command: 'pytest -q' }],
  rubric: { items: [] },
  topics: [],
  companies: [],
};

const RAN = {
  passed: true, passed_count: 3, failed_count: 0, stdout: '3 passed', stderr: '', error: null, duration_ms: 812,
  truncated: false,
};

function job(state: JobAnswer['state'], extra: Partial<JobAnswer> = {}): JobAnswer {
  return { job_id: 'jobaaaaaaaaaaa1', state, outcome_class: null, retryable: false, cancel_requested: false, envelope: null, ...extra };
}

function ended(state: JobAnswer['state'], outcome: OutcomeClass, output: Record<string, unknown> | null,
  extra: Partial<JobAnswer> = {}): JobAnswer {
  const envelope: JobEnvelope = {
    version: 'rounds.execution-envelope/v1', job_id: 'jobaaaaaaaaaaa1', state, outcome_class: outcome,
    authoritative: true, limit: null, parts: [], score: null, definition: null, queued_at: 1, started_at: 2,
    finished_at: 3, cleanup: 'confirmed', rubric: null, output,
  };
  return job(state, { outcome_class: outcome, envelope, ...extra });
}

const fetchMock = vi.fn<typeof fetch>();
let answers: JobAnswer[] = [];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/ai-coding/round/cart-totals']}>
      <Routes>
        <Route path="/ai-coding/round/:slug" element={<AICodingDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
  answers = [];
  vi.mocked(getRound).mockResolvedValue(ROUND as never);
  vi.mocked(runProject).mockReset();
  vi.mocked(gradeAttempt).mockReset();
  vi.mocked(persistAttempt).mockReset();
  vi.mocked(getGradedAttempt).mockReset();
  vi.mocked(requestGradeReview).mockReset();
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

describe('AICodingDetail jobs', () => {
  it('shows a running job above the console, then the result it ended with', async () => {
    vi.mocked(runProject).mockResolvedValue(job('started'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Running'));
    expect(screen.queryByText(/PASS|FAIL/)).not.toBeInTheDocument();
    answers.push(ended('completed', 'passed', RAN));
    await waitFor(() => expect(screen.getAllByText(/PASS/).length).toBeGreaterThan(0));
    expect(screen.getByText('3 passed · 0 failed')).toBeInTheDocument();
  });

  it('retries a run the server couldn\'t finish under the same command id', async () => {
    vi.mocked(runProject).mockResolvedValue(job('queued'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    answers.push(ended('failed', 'infrastructure-degraded', null, { retryable: true }));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent("Couldn't finish"));
    expect(screen.queryByText(/PASS|FAIL/)).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    await waitFor(() => expect(runProject).toHaveBeenCalledTimes(2));
    const [first, second] = vi.mocked(runProject).mock.calls;
    expect(second[1]?.idempotencyKey).toBe(first[1]?.idempotencyKey);
  });

  it('names a time limit with no FAIL, whatever the envelope holds', async () => {
    vi.mocked(runProject).mockResolvedValue(job('started'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Running'));
    // The body the project run answers when its step runs out of time.
    const timedOut = {
      passed: false, passed_count: 0, failed_count: 0, stdout: '', stderr: '', error: 'Time limit exceeded (10s)',
      duration_ms: 10000, truncated: false,
    };
    const limit = ended('timed-out', 'resource-limit', timedOut);
    answers.push({ ...limit, envelope: limit.envelope && { ...limit.envelope, limit: 'wall_time' } });
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Time limit reached'));
    expect(screen.queryByText(/PASS|FAIL|Time limit exceeded/)).not.toBeInTheDocument();
  });

  it('shows Retry once per press: none while the retry is on its way', async () => {
    let answer!: (value: JobAnswer) => void;
    vi.mocked(runProject)
      .mockResolvedValueOnce(job('queued'))
      .mockImplementationOnce(() => new Promise<JobAnswer>((resolve) => { answer = resolve; }));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    answers.push(ended('failed', 'worker-lost', null, { retryable: true }));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Interrupted'));
    await user.click(screen.getByRole('button', { name: 'Retry' }));
    expect(screen.queryByRole('button', { name: 'Retry' })).not.toBeInTheDocument();
    answer(job('queued'));
    await waitFor(() => expect(screen.getByRole('status')).toHaveTextContent('Queued'));
    expect(runProject).toHaveBeenCalledTimes(2);
  });

  it("shows a run that failed without a result as a fixed sentence, never the server's text, with no FAIL", async () => {
    vi.mocked(runProject).mockRejectedValue(new RunnerError({ message: 'run-project 422: Field required', status: 422 }));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    expect(await screen.findByText("The runner couldn't read this run. Reload the page and run it again.")).toBeInTheDocument();
    expect(screen.getByText('RUN ERROR')).toBeInTheDocument();
    expect(screen.queryByText(/Field required|FAIL|0 passed/)).not.toBeInTheDocument();
  });
});

const CHECKPOINT: CheckpointResult = {
  index: 0, label: 'Add', outcome_class: 'passed', limit: null, passed: true, score: 1, executed: 3,
  passed_count: 3, failed_count: 0, outcomes: [{ id: 'r001', outcome: 'passed', reason: 'ok' }], error: null,
};

function gradedRow(results: CheckpointResult[], review: AttemptRow['rubric_review'] = null): AttemptRow {
  return {
    id: 'rowaaaaaaaaaaa1', user: 'useraaaaaaaaaa1', campaign: '', round: 'r1', status: 'graded',
    test_results: results, rubric_review: review, envelope: 'envaaaaaaaaaaa1', updated: '',
  };
}

function gradeEnd(state: JobAnswer['state'], outcome: OutcomeClass, limit: JobLimit | null = null,
  extra: Partial<JobAnswer> = {}): JobAnswer {
  const base = ended(state, outcome, null, extra);
  const authoritative = ['passed', 'candidate-failure', 'resource-limit'].includes(outcome);
  return { ...base, envelope: base.envelope && { ...base.envelope, limit, authoritative } };
}

function reviewAnswer(extra: Partial<ReviewAnswer>): ReviewAnswer {
  return { job_id: 'jobaaaaaaaaaaa1', rubric_state: null, rubric_review: null, unavailable: null, ...extra };
}

const REVIEW = { items: [{ id: 'clarity', score: 0.9, evidence: 'Clear names.', suggestions: [] }], total: 0.9 };

async function submit(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole('button', { name: 'Submit' }));
}

describe('AICodingDetail grade jobs', () => {
  it('follows a grade to the report the server wrote, and asks for its review once', async () => {
    vi.mocked(gradeAttempt).mockResolvedValue(job('queued'));
    vi.mocked(getGradedAttempt).mockResolvedValue(gradedRow([CHECKPOINT]));
    vi.mocked(requestGradeReview).mockResolvedValue(reviewAnswer({ rubric_state: 'completed', rubric_review: REVIEW }));
    const user = userEvent.setup();
    renderPage();
    await submit(user);
    const region = screen.getByTestId('runner-denial');
    await waitFor(() => expect(region).toHaveTextContent('Grading starts when a runner is free.'));
    answers.push(job('started'));
    await waitFor(() => expect(region).toHaveTextContent('Your checkpoints are being graded on the server.'));
    answers.push(gradeEnd('completed', 'passed'));
    const dialog = await screen.findByRole('dialog', { name: 'Submission · Cart totals' });
    expect(within(dialog).getByText('1 of 1 checkpoints passed')).toBeInTheDocument();
    expect(within(dialog).getByText('pass')).toBeInTheDocument();
    await waitFor(() => expect(within(dialog).getAllByText('90 / 100').length).toBeGreaterThan(0));
    expect(getGradedAttempt).toHaveBeenCalledWith('jobaaaaaaaaaaa1');
    expect(requestGradeReview).toHaveBeenCalledTimes(1);
    expect(vi.mocked(requestGradeReview).mock.calls[0].slice(0, 2)).toEqual(['jobaaaaaaaaaaa1', drafts.files]);
    // The server wrote the row; the page writes none.
    expect(persistAttempt).not.toHaveBeenCalled();
    expect(practice.set).toHaveBeenCalledWith('mastered');
    const [req, init] = vi.mocked(gradeAttempt).mock.calls[0];
    expect(req).toMatchObject({ round_slug: 'cart-totals', files: drafts.files, duration_ms: expect.any(Number) });
    expect(init?.idempotencyKey).toMatch(UUID_V7_PATTERN);
  });

  it("names a checkpoint's limit in the report with no fail, and sets no mastery", async () => {
    vi.mocked(gradeAttempt).mockResolvedValue(job('started'));
    const timedOut: CheckpointResult = {
      ...CHECKPOINT, outcome_class: 'resource-limit', limit: 'wall_time', passed: null, score: null, executed: 0,
      passed_count: 0, failed_count: 0, outcomes: [], error: 'This checkpoint ran out of time.',
    };
    vi.mocked(getGradedAttempt).mockResolvedValue(gradedRow([timedOut]));
    vi.mocked(requestGradeReview).mockResolvedValue(reviewAnswer({ unavailable: 'no_provider' }));
    const user = userEvent.setup();
    renderPage();
    await submit(user);
    answers.push(gradeEnd('timed-out', 'resource-limit', 'wall_time'));
    const dialog = await screen.findByRole('dialog');
    expect(screen.getByTestId('runner-denial')).toHaveTextContent('Time limit reached');
    expect(within(dialog).getByText('Time limit reached')).toBeInTheDocument();
    expect(within(dialog).getByText('0 of 1 checkpoints passed · 1 stopped at a limit')).toBeInTheDocument();
    expect(within(dialog).queryByText(/^fail$|0 passed · 0 failed/)).not.toBeInTheDocument();
    await waitFor(() => expect(within(dialog).getByTestId('review-status')).toHaveTextContent('No AI provider set up'));
    expect(practice.set).not.toHaveBeenCalledWith('mastered');
  });

  it('opens a missed grade\'s report and sets no mastery', async () => {
    vi.mocked(gradeAttempt).mockResolvedValue(job('started'));
    const missed: CheckpointResult = { ...CHECKPOINT, outcome_class: 'candidate-failure', passed: false, score: 0.33, passed_count: 1, failed_count: 2 };
    vi.mocked(getGradedAttempt).mockResolvedValue(gradedRow([missed]));
    vi.mocked(requestGradeReview).mockResolvedValue(reviewAnswer({ unavailable: 'files_changed' }));
    const user = userEvent.setup();
    renderPage();
    await submit(user);
    answers.push(gradeEnd('completed', 'candidate-failure'));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('fail')).toBeInTheDocument();
    await waitFor(() => expect(within(dialog).getByTestId('review-status')).toHaveTextContent('Files changed'));
    expect(practice.set).not.toHaveBeenCalledWith('mastered');
  });

  it("retries a grade the server couldn't finish under the same command id, with no report", async () => {
    vi.mocked(gradeAttempt).mockResolvedValue(job('queued'));
    const user = userEvent.setup();
    renderPage();
    await submit(user);
    answers.push(gradeEnd('failed', 'infrastructure-degraded', null, { retryable: true }));
    const region = screen.getByTestId('runner-denial');
    await waitFor(() => expect(region).toHaveTextContent("Couldn't finish"));
    expect(region).toHaveTextContent('Retry grades it again.');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(getGradedAttempt).not.toHaveBeenCalled();
    await user.click(within(region).getByRole('button', { name: 'Retry' }));
    await waitFor(() => expect(gradeAttempt).toHaveBeenCalledTimes(2));
    const [first, second] = vi.mocked(gradeAttempt).mock.calls;
    expect(second[1]?.idempotencyKey).toBe(first[1]?.idempotencyKey);
  });

  it("reads a round the server can't grade as a denial, with nothing graded", async () => {
    vi.mocked(gradeAttempt).mockRejectedValue(
      new RunnerError({ message: "grade 422: This practice item can't be graded on this server.", status: 422, code: 'definition_invalid' }),
    );
    const user = userEvent.setup();
    renderPage();
    await submit(user);
    const region = screen.getByTestId('runner-denial');
    await waitFor(() => expect(region).toHaveTextContent("Can't grade here"));
    expect(region).toHaveTextContent('Nothing was graded.');
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(persistAttempt).not.toHaveBeenCalled();
  });

  it('says a grade that failed without a result in a fixed sentence, with no score or server text', async () => {
    vi.mocked(gradeAttempt).mockRejectedValue(new RunnerError({ message: 'grade 409: Traceback: secret', status: 409 }));
    const user = userEvent.setup();
    renderPage();
    await submit(user);
    const dialog = await screen.findByRole('dialog');
    const problem = within(dialog).getByTestId('report-problem');
    expect(problem).toHaveTextContent("Grading didn't finish");
    expect(problem).toHaveTextContent('Grading failed with status 409, so nothing was graded. Submit again.');
    expect(dialog.textContent).not.toMatch(/Traceback|secret|\d+ ?\/ ?100|checkpoints passed/);
    expect(persistAttempt).not.toHaveBeenCalled();
  });

  it("offers Try again when the report couldn't load, and opens it once it does", async () => {
    vi.mocked(gradeAttempt).mockResolvedValue(job('started'));
    vi.mocked(getGradedAttempt)
      .mockRejectedValueOnce(Object.assign(new Error('x'), { status: 0 }))
      .mockResolvedValueOnce(gradedRow([CHECKPOINT], REVIEW));
    const user = userEvent.setup();
    renderPage();
    await submit(user);
    answers.push(gradeEnd('completed', 'passed'));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByTestId('report-problem')).toHaveTextContent("Couldn't load the report");
    await user.click(within(dialog).getByRole('button', { name: 'Try again' }));
    await waitFor(() => expect(within(dialog).getByText('pass')).toBeInTheDocument());
    // The row already holds its review, so nothing asks for one.
    expect(requestGradeReview).not.toHaveBeenCalled();
  });
});

describe('AICodingDetail jobs on a phone', () => {
  const unmatched = window.matchMedia;
  afterEach(() => {
    window.matchMedia = unmatched;
  });

  /** The page's own state: the notice's slot and the one live region. */
  function notice() {
    const regions = screen.getAllByRole('status');
    expect(regions).toHaveLength(1);
    return regions[0];
  }

  it('shows a queued run, then a grade, at the full width below the body, never in the files column', async () => {
    window.matchMedia = phoneWidth();
    vi.mocked(runProject).mockResolvedValue(job('queued'));
    vi.mocked(gradeAttempt).mockResolvedValue(job('started'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    await waitFor(() => expect(notice()).toHaveTextContent('Queued'));
    expect(notice().closest('[data-ai-coding-pane="notice"]')).not.toBeNull();
    expect(notice().closest('[data-ai-coding-pane="center"]')).toBeNull();

    answers.push(ended('canceled', 'canceled', null));
    await waitFor(() => expect(notice()).toHaveTextContent('Canceled'));
    await submit(user);
    await waitFor(() => expect(notice()).toHaveTextContent('Grading'));
    expect(notice().closest('[data-ai-coding-pane="notice"]')).not.toBeNull();
    expect(notice().closest('[data-ai-coding-pane="center"]')).toBeNull();
  });

  it('keeps a job in the center column on a wider screen', async () => {
    vi.mocked(runProject).mockResolvedValue(job('queued'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    await waitFor(() => expect(notice()).toHaveTextContent('Queued'));
    expect(notice().closest('[data-ai-coding-pane="center"]')).not.toBeNull();
    expect(document.querySelector('[data-ai-coding-pane="notice"]')).toBeNull();
  });
});
