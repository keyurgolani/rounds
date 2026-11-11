// Take-home runs as durable jobs (ROUNDS-00A-L03): a job shows in the
// notice above the console until it ends, the harness result of an end
// the run earned shows as before, a limit or an end the harness or the
// infrastructure caused shows its notice with no score, and a run that
// failed without a result shows a fixed sentence and no score.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const drafts = vi.hoisted(() => {
  const files = { 'kv.py': 'class KV:\n    pass\n' };
  return { files, savedFiles: files, setFile: () => {}, hydrated: true, resetToStarter: () => {} };
});

vi.mock('../../lib/pocketbase', () => ({ pb: { authStore: { token: 'test-token-placeholder' } } }));
vi.mock('../../pages/take-home/takeHomeApi', async (importOriginal) => ({
  ...((await importOriginal()) as Record<string, unknown>),
  getAssignment: vi.fn(),
  getLatestTakeHomeAttempt: vi.fn().mockResolvedValue(null),
  runProject: vi.fn(),
  submitAttempt: vi.fn(),
  upsertInProgressTakeHomeAttempt: vi.fn().mockResolvedValue(undefined),
  deleteInProgressTakeHomeAttempt: vi.fn().mockResolvedValue(undefined),
}));
vi.mock('../../hooks/useTakeHomeDrafts', () => ({ useTakeHomeDrafts: () => drafts }));
vi.mock('../../hooks/usePracticeStatus', () => ({ usePracticeStatus: () => [null, vi.fn()] }));
vi.mock('../../campaign/CampaignContext', () => ({ useCampaign: () => ({ currentId: null }) }));
vi.mock('../../components/shell/AppHeader', () => ({ default: () => <header /> }));
vi.mock('../../components/shell/StatusAction', () => ({ default: () => null }));
vi.mock('../../components/take-home/TakeHomeChatPanel', () => ({ default: () => null }));
vi.mock('../../components/editor/MultiFileEditor', () => ({
  default: (props: { bottomActions?: React.ReactNode }) => <div>{props.bottomActions}</div>,
}));

import TakeHomeDetail from '../../pages/take-home/TakeHomeDetail';
import { getAssignment, runProject } from '../../pages/take-home/takeHomeApi';
import { RunnerError } from '../../lib/runnerFetch';
import type { JobAnswer, JobEnvelope, JobLimit, OutcomeClass } from '../../lib/executionJobs';

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
