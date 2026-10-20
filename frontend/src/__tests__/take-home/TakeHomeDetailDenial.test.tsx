// Take-home detail denial states (ROUNDS-00A-L01): a refused run shows
// no score of 0, a refused submission opens no fake report, and focus
// returns to the button that started it.

import { beforeEach, describe, expect, it, vi } from 'vitest';
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
import { getAssignment, runProject, submitAttempt } from '../../pages/take-home/takeHomeApi';
import { RunnerError } from '../../lib/runnerFetch';

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

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/take-home/assignment/kv-store-py']}>
      <Routes>
        <Route path="/take-home/assignment/:slug" element={<TakeHomeDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

function blurThenReject(error: RunnerError) {
  return async () => {
    (document.activeElement as HTMLElement | null)?.blur();
    throw error;
  };
}

beforeEach(() => {
  window.localStorage.clear();
  vi.mocked(getAssignment).mockResolvedValue(ASSIGNMENT as never);
  vi.mocked(runProject).mockReset();
  vi.mocked(submitAttempt).mockReset();
});

describe('TakeHomeDetail denial states', () => {
  it('shows an unavailable run instead of a score of 0 and returns focus to Run', async () => {
    vi.mocked(runProject).mockImplementation(
      blurThenReject(new RunnerError({ message: 'take-home run 503: x', status: 503, code: 'worker_unavailable' })),
    );
    const user = userEvent.setup();
    renderPage();
    const run = await screen.findByRole('button', { name: 'Run' });
    const region = screen.getByRole('status');
    expect(region).toHaveAttribute('aria-live', 'polite');

    run.focus();
    await user.keyboard('{Enter}');

    await waitFor(() => expect(region).toHaveTextContent('Unavailable right now'));
    expect(region).toHaveTextContent('Nothing ran. Your code is still here. Try again in a moment.');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Run' })).toHaveFocus());
    expect(screen.queryByText(/HARNESS/)).not.toBeInTheDocument();
    expect(screen.queryByTestId('run-dock')).not.toBeInTheDocument();
  });

  it('asks to sign in again on a refused submission and opens no report', async () => {
    vi.mocked(submitAttempt).mockImplementation(
      blurThenReject(new RunnerError({ message: 'take-home submit 401: x', status: 401 })),
    );
    const user = userEvent.setup();
    renderPage();
    const submit = await screen.findByRole('button', { name: 'Submit' });
    submit.focus();
    await user.keyboard('{Enter}');

    const region = screen.getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent('Sign in again'));
    expect(region).toHaveTextContent('Nothing was graded. Your files and notes are still here.');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Submit' })).toHaveFocus());
    expect(screen.getByRole('button', { name: 'Open last submission' })).toBeDisabled();
    expect(screen.getByRole('link', { name: 'Sign in' })).toHaveAttribute('href', '/login');
  });

  it('marks an oversized submission too large', async () => {
    vi.mocked(submitAttempt).mockRejectedValue(
      new RunnerError({ message: 'x', status: 413, code: 'payload_too_large' }),
    );
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Submit' }));
    await waitFor(() =>
      expect(screen.getByRole('status')).toHaveTextContent('Your files are over the size limit, so nothing was graded.'),
    );
  });
});
