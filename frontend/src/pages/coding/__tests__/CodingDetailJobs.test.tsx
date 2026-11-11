// Coding runs as durable jobs (ROUNDS-00A-L03): a run or test run the
// runner answers with a job shows Queued with Cancel while it waits, an
// end the run earned shows through the page's own result views, a limit
// is named with no output, and Retry after an end the server caused sends
// the same command id. A 200 still shows as it did.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

vi.mock('../../../lib/pocketbase', () => ({ pb: { authStore: { token: 'test-token-placeholder' } } }));
vi.mock('../../../content/api', () => ({ getCodingQuestion: vi.fn() }));
vi.mock('../../../lib/codeDraftsApi', () => ({
  listCodeDrafts: vi.fn().mockResolvedValue([]),
  upsertCodeDraft: vi.fn(),
  deleteCodeDraft: vi.fn(),
}));
vi.mock('../runnerApi', () => ({ runCode: vi.fn(), evaluateCode: vi.fn() }));
vi.mock('../../../auth/AuthProvider', () => ({ useAuth: () => ({ user: { id: 'u1' } }) }));
vi.mock('../../../campaign/CampaignContext', () => ({ useCampaign: () => ({ currentId: null }) }));
vi.mock('../../../components/shell/AppHeader', () => ({ default: () => <header /> }));
vi.mock('../../../components/shell/StatusAction', () => ({ default: () => null }));
vi.mock('../../../components/editor/MultiFileEditor', () => ({
  default: (props: { files: Record<string, string>; topRightExtras?: React.ReactNode }) => (
    <div>
      <textarea aria-label="Code" readOnly value={Object.values(props.files)[0] ?? ''} />
      {props.topRightExtras}
    </div>
  ),
}));

import CodingDetail from '../../CodingDetail';
import { getCodingQuestion } from '../../../content/api';
import { evaluateCode, runCode } from '../runnerApi';
import { RunnerError } from '../../../lib/runnerFetch';
import type { JobAnswer, JobEnvelope, JobLimit, OutcomeClass } from '../../../lib/executionJobs';

const QUESTION = {
  id: 7,
  slug: 'two-sum',
  title: 'Two Sum',
  difficulty: 'easy',
  description: 'Find two numbers.',
  hints: [],
  constraints: [],
  starter_code: { python: 'def two_sum(nums, target):\n    return [0, 1]\n' },
  boilerplate_code: {},
  test_cases: [
    { input: { nums: [2, 7], target: 9 }, expected: [0, 1] },
    { input: { nums: [3, 3], target: 6 }, expected: [0, 1] },
  ],
  solutions: [],
  thought_process: [],
  tips: [],
  companies: [],
  topics: [],
  time_complexity: '',
  space_complexity: '',
  entry: {
    kind: 'function',
    name: 'two_sum',
    params: [
      { name: 'nums', type: 'int[]' },
      { name: 'target', type: 'int' },
    ],
    returns: 'int[]',
  },
};

const EVALUATED = {
  passed: 2,
  failed: 0,
  results: [0, 1].map((index) => ({
    index, passed: true, description: '', tags: [], output: [0, 1], expected: [0, 1], error: null, duration_ms: 1,
  })),
};

function job(state: JobAnswer['state'], extra: Partial<JobAnswer> = {}): JobAnswer {
  return { job_id: 'jobaaaaaaaaaaa1', state, outcome_class: null, retryable: false, cancel_requested: false, envelope: null, ...extra };
}

function ended(
  state: JobAnswer['state'],
  outcome: OutcomeClass,
  output: Record<string, unknown> | null,
  extra: Partial<JobAnswer> = {},
  limit: JobLimit | null = null,
): JobAnswer {
  const envelope: JobEnvelope = {
    version: 'rounds.execution-envelope/v1', job_id: 'jobaaaaaaaaaaa1', state, outcome_class: outcome,
    authoritative: true, limit, parts: [], score: null, definition: null, queued_at: 1, started_at: 2, finished_at: 3,
    cleanup: 'confirmed', rubric: null, output,
  };
  return job(state, { outcome_class: outcome, envelope, ...extra });
}

const fetchMock = vi.fn<typeof fetch>();
// Job reads answer from this queue; an empty queue waits until the test
// pushes the next answer.
let answers: JobAnswer[] = [];
let waiting: Array<() => void> = [];

function push(next: JobAnswer) {
  answers.push(next);
  waiting.splice(0).forEach((wake) => wake());
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/coding/question/two-sum']}>
      <Routes>
        <Route path="/coding/question/:slug" element={<CodingDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

function dockRegion() {
  return within(screen.getByTestId('right-dock')).getByRole('status');
}

beforeEach(() => {
  window.localStorage.clear();
  window.sessionStorage.clear();
  answers = [];
  waiting = [];
  vi.mocked(getCodingQuestion).mockResolvedValue(QUESTION as never);
  vi.mocked(evaluateCode).mockReset();
  vi.mocked(runCode).mockReset();
  fetchMock.mockReset().mockImplementation(async (_url, init) => {
    while (answers.length === 0) {
      await new Promise<void>((wake) => {
        waiting.push(wake);
        init?.signal?.addEventListener('abort', () => wake());
      });
      if (init?.signal?.aborted) throw new DOMException('The operation was aborted.', 'AbortError');
    }
    return new Response(JSON.stringify(answers.shift()), { status: 200, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('CodingDetail jobs', () => {
  it('shows a queued test run with Cancel, then the results it ended with', async () => {
    vi.mocked(evaluateCode).mockResolvedValue(job('queued'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run all (2)' }));
    await waitFor(() => expect(dockRegion()).toHaveTextContent('Queued'));
    expect(within(dockRegion()).getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    // Busy until the job ends, so a second test run can't start.
    expect(screen.getByRole('button', { name: 'Running…' })).toBeDisabled();
    push(ended('completed', 'passed', EVALUATED));
    await waitFor(() => expect(screen.getByText('2 / 2 passed')).toBeInTheDocument());
    expect(dockRegion()).toHaveTextContent('Finished. The results are ready.');
    expect(screen.getByRole('button', { name: 'Run all (2)' })).toBeEnabled();
    expect(String(fetchMock.mock.calls[0][0])).toBe('/api/execution/jobs/jobaaaaaaaaaaa1?wait=20');
  });

  it('retries a test run the server lost under the same command id', async () => {
    vi.mocked(evaluateCode).mockResolvedValue(job('queued'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run all (2)' }));
    push(ended('failed', 'worker-lost', null, { retryable: true }));
    await waitFor(() => expect(dockRegion()).toHaveTextContent('Interrupted'));
    // Nothing came back, so no result shows.
    expect(screen.queryByText(/passed$/)).not.toBeInTheDocument();
    await user.click(within(dockRegion()).getByRole('button', { name: 'Retry' }));
    await waitFor(() => expect(evaluateCode).toHaveBeenCalledTimes(2));
    const [first, second] = vi.mocked(evaluateCode).mock.calls;
    expect(second[1]?.idempotencyKey).toBe(first[1]?.idempotencyKey);
    push(ended('completed', 'passed', EVALUATED));
    await waitFor(() => expect(screen.getByText('2 / 2 passed')).toBeInTheDocument());
  });

  it('names the time limit a run reached and shows none of its output', async () => {
    vi.mocked(runCode).mockResolvedValue(job('started'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('tab', { name: 'Run' }));
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    await waitFor(() => expect(dockRegion()).toHaveTextContent('Running'));
    // The run body a limit ends with, if an envelope carried one: only an
    // end the run earned shows its output.
    push(
      ended(
        'timed-out',
        'resource-limit',
        { stdout: 'partial output', stderr: '', return_value: null, error: 'Time limit exceeded (3s)', duration_ms: 3000, truncated: false },
        {},
        'wall_time',
      ),
    );
    await waitFor(() => expect(dockRegion()).toHaveTextContent('Time limit reached'));
    expect(screen.queryByText(/partial output|Time limit exceeded/)).not.toBeInTheDocument();
  });

  it('names the time limit a test run reached and marks no case failed', async () => {
    vi.mocked(evaluateCode).mockResolvedValue(job('started'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run all (2)' }));
    await waitFor(() => expect(dockRegion()).toHaveTextContent('Running'));
    // The evaluate body for a case that ran out of time marks that case
    // failed; the limit, not the code, ended the run.
    const timedOut = {
      passed: 1,
      failed: 1,
      results: [
        { ...EVALUATED.results[0] },
        { ...EVALUATED.results[1], passed: false, output: null, error: 'Time limit exceeded (3s)', duration_ms: 3000 },
      ],
    };
    push(ended('timed-out', 'resource-limit', timedOut, {}, 'wall_time'));
    await waitFor(() => expect(dockRegion()).toHaveTextContent('Time limit reached'));
    expect(screen.queryByText(/1 \/ 2 passed|Time limit exceeded/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run all (2)' })).toBeEnabled();
  });

  it('cancels a queued run', async () => {
    vi.mocked(runCode).mockResolvedValue(job('queued'));
    fetchMock.mockImplementationOnce(async (_url, init) => new Promise<Response>((_resolve, reject) => {
      init?.signal?.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
    }));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('tab', { name: 'Run' }));
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    await waitFor(() => expect(dockRegion()).toHaveTextContent('Queued'));
    fetchMock.mockImplementationOnce(async () =>
      new Response(JSON.stringify(ended('canceled', 'canceled', null)), { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );
    await user.click(within(dockRegion()).getByRole('button', { name: 'Cancel' }));
    await waitFor(() => expect(dockRegion()).toHaveTextContent('Canceled'));
    const cancel = fetchMock.mock.calls.find(([url]) => String(url).endsWith('/cancel'));
    expect(cancel?.[1]?.method).toBe('POST');
  });

  it("shows a run that failed without a result as a fixed sentence, never the server's text", async () => {
    vi.mocked(runCode).mockRejectedValue(new RunnerError({ message: 'run 422: Field required: input.nums', status: 422 }));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('tab', { name: 'Run' }));
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    expect((await screen.findAllByText(/The runner couldn't read this run\./)).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Field required|input\.nums/)).not.toBeInTheDocument();
  });

  it('still shows a result the runner answered in its request', async () => {
    vi.mocked(evaluateCode).mockResolvedValue(EVALUATED);
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run all (2)' }));
    await waitFor(() => expect(screen.getByText('2 / 2 passed')).toBeInTheDocument());
    expect(dockRegion()).toBeEmptyDOMElement();
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
