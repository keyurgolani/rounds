// Coding run dock denial states (ROUNDS-00A-L01): a refused test run
// reads as a denial in the dock, the code stays in the editor, and focus
// returns to Run all.

import { beforeEach, describe, expect, it, vi } from 'vitest';
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
import { evaluateCode } from '../runnerApi';
import { RunnerError } from '../../../lib/runnerFetch';

const QUESTION = {
  id: 7,
  slug: 'two-sum',
  title: 'Two Sum',
  difficulty: 'easy',
  description: 'Find two numbers.',
  hints: [],
  constraints: [],
  starter_code: { python: 'def two_sum(nums, target):\n    return []\n' },
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

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/coding/question/two-sum']}>
      <Routes>
        <Route path="/coding/question/:slug" element={<CodingDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  vi.mocked(getCodingQuestion).mockResolvedValue(QUESTION as never);
  vi.mocked(evaluateCode).mockReset();
});

describe('CodingDetail runner calls', () => {
  it('names the question by slug and leaves the test cases to the runner', async () => {
    vi.mocked(evaluateCode).mockResolvedValue({ passed: 0, failed: 0, results: [] });
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run all (2)' }));
    await waitFor(() => expect(evaluateCode).toHaveBeenCalledTimes(1));
    expect(evaluateCode).toHaveBeenCalledWith({
      question_slug: 'two-sum',
      language: 'python',
      code: QUESTION.starter_code.python,
      filter: undefined,
    });
  });
});

describe('CodingDetail denial states', () => {
  it('shows a limit denial in the dock and returns focus to Run all', async () => {
    vi.mocked(evaluateCode).mockImplementation(async () => {
      (document.activeElement as HTMLElement | null)?.blur();
      throw new RunnerError({ message: 'x', status: 429, code: 'quota_exceeded', retryAfterSeconds: 45 });
    });
    const user = userEvent.setup();
    renderPage();
    const runAll = await screen.findByRole('button', { name: 'Run all (2)' });
    const dock = screen.getByTestId('right-dock');
    const region = within(dock).getByRole('status');
    expect(region).toHaveAttribute('aria-live', 'polite');
    expect(region).toBeEmptyDOMElement();

    runAll.focus();
    await user.keyboard('{Enter}');

    await waitFor(() => expect(region).toHaveTextContent('Limit reached'));
    expect(region).toHaveTextContent('Try again in 45 seconds.');
    expect(region).toHaveTextContent('Your code is still here.');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Run all (2)' })).toHaveFocus());
    expect(screen.getByLabelText('Code')).toHaveValue(QUESTION.starter_code.python);
  });

  it.each([
    [new RunnerError({ message: 'Not authenticated.', status: 0, code: 'unauthenticated' }), 'Sign in again'],
    [new RunnerError({ message: 'x', status: 503, code: 'route_disabled' }), 'Running tests is turned off on this server.'],
    [new RunnerError({ message: 'Failed to fetch', status: 0 }), 'No tests ran.'],
    [new RunnerError({ message: 'x', status: 413, code: 'payload_too_large' }), 'Your code is over the size limit'],
  ])('reads %o as a denial, not an error dump', async (error, text) => {
    vi.mocked(evaluateCode).mockRejectedValue(error);
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run all (2)' }));
    const region = within(screen.getByTestId('right-dock')).getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent(text));
  });

  it('shows the denial above the editor in focus mode, where the dock is hidden', async () => {
    window.localStorage.setItem('rounds:editor-focus', 'true');
    vi.mocked(evaluateCode).mockImplementation(async () => {
      (document.activeElement as HTMLElement | null)?.blur();
      throw new RunnerError({ message: 'x', status: 503, code: 'route_disabled' });
    });
    const user = userEvent.setup();
    renderPage();
    const runAll = await screen.findByRole('button', { name: 'Run all tests' });
    expect(screen.queryByTestId('right-dock')).not.toBeInTheDocument();
    runAll.focus();
    await user.keyboard('{Enter}');
    const region = screen.getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent('Running tests is turned off on this server.'));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Run all tests' })).toHaveFocus());
  });

  it('clears the denial when the next run is accepted', async () => {
    vi.mocked(evaluateCode)
      .mockRejectedValueOnce(new RunnerError({ message: 'x', status: 503, code: 'worker_unavailable' }))
      .mockResolvedValueOnce({ passed: 2, failed: 0, results: [] });
    const user = userEvent.setup();
    renderPage();
    const region = within(await screen.findByTestId('right-dock')).getByRole('status');
    await user.click(await screen.findByRole('button', { name: 'Run all (2)' }));
    await waitFor(() => expect(region).toHaveTextContent('Unavailable right now'));
    await user.click(screen.getByRole('button', { name: 'Run all (2)' }));
    await waitFor(() => expect(region).toBeEmptyDOMElement());
  });
});
