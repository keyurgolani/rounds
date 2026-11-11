// AI-coding project runs as durable jobs (ROUNDS-00A-L03): a job shows
// in the notice above the console until it ends, the result of an end
// the run earned shows in the console, a limit shows no FAIL, an end the
// server caused offers Retry under the same command id, once per press,
// and a run that failed without a result shows a fixed sentence, never
// a FAIL it didn't earn.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
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

vi.mock('../../lib/pocketbase', () => ({ pb: { authStore: { token: 'test-token-placeholder' } } }));
vi.mock('../../pages/ai-coding/aiCodingApi', async (importOriginal) => ({
  ...((await importOriginal()) as Record<string, unknown>),
  getRound: vi.fn(),
  getLatestAttempt: vi.fn().mockResolvedValue(null),
  runProject: vi.fn(),
  gradeAttempt: vi.fn(),
  persistAttempt: vi.fn(),
  upsertInProgressAttempt: vi.fn().mockResolvedValue(undefined),
  deleteInProgressAttempt: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('../../hooks/useAICodingDrafts', () => ({ useAICodingDrafts: () => drafts }));
vi.mock('../../hooks/usePracticeStatus', () => ({ usePracticeStatus: () => [null, vi.fn()] }));
vi.mock('../../campaign/CampaignContext', () => ({ useCampaign: () => ({ currentId: null }) }));
vi.mock('../../components/shell/AppHeader', () => ({ default: () => <header /> }));
vi.mock('../../components/shell/StatusAction', () => ({ default: () => null }));
vi.mock('../../components/ai/AIChatPanel', () => ({ default: () => null }));
vi.mock('../../components/editor/MultiFileEditor', () => ({
  default: (props: { bottomActions?: React.ReactNode }) => <div>{props.bottomActions}</div>,
}));

import AICodingDetail from '../../pages/ai-coding/AICodingDetail';
import { getRound, runProject } from '../../pages/ai-coding/aiCodingApi';
import { RunnerError } from '../../lib/runnerFetch';
import type { JobAnswer, JobEnvelope, OutcomeClass } from '../../lib/executionJobs';

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
