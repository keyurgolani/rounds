// AI-assisted coding runner denial states (ROUNDS-00A-L01): a refused
// run or grade reads as a denial above the console, opens no fake
// report, keeps the files, and hands focus back to the button.

import { beforeEach, describe, expect, it, vi } from 'vitest';
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
import { getRound, gradeAttempt, persistAttempt, runProject } from '../../pages/ai-coding/aiCodingApi';
import { RunnerError } from '../../lib/runnerFetch';

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

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/ai-coding/round/cart-totals']}>
      <Routes>
        <Route path="/ai-coding/round/:slug" element={<AICodingDetail />} />
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
  vi.mocked(getRound).mockResolvedValue(ROUND as never);
  vi.mocked(runProject).mockReset();
  vi.mocked(gradeAttempt).mockReset();
  vi.mocked(persistAttempt).mockReset();
});

describe('AICodingDetail runner calls', () => {
  it('names the round and checkpoint and leaves the test command to the runner', async () => {
    vi.mocked(runProject).mockResolvedValue({
      passed: true,
      passed_count: 1,
      failed_count: 0,
      stdout: '',
      stderr: '',
      error: null,
      duration_ms: 1,
      truncated: false,
    });
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    await waitFor(() => expect(runProject).toHaveBeenCalledTimes(1));
    expect(runProject).toHaveBeenCalledWith({
      round_slug: 'cart-totals',
      language: 'python',
      checkpoint_index: 0,
      files: { 'cart.py': ROUND.starter_files[0].contents },
    });
  });
});

describe('AICodingDetail denial states', () => {
  it('shows a turned-off run above the console and returns focus to Run', async () => {
    vi.mocked(runProject).mockImplementation(
      blurThenReject(new RunnerError({ message: 'x', status: 503, code: 'route_disabled' })),
    );
    const user = userEvent.setup();
    renderPage();
    const run = await screen.findByRole('button', { name: 'Run' });
    const region = screen.getByRole('status');
    expect(region).toHaveAttribute('aria-live', 'polite');

    run.focus();
    await user.keyboard('{Enter}');

    await waitFor(() => expect(region).toHaveTextContent('Turned off'));
    expect(region).toHaveTextContent('Running code is turned off on this server. Your code is still here.');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Run' })).toHaveFocus());
    expect(screen.queryByTestId('run-dock')).not.toBeInTheDocument();
  });

  it('shows a limit on grading without opening a report or saving an attempt', async () => {
    vi.mocked(gradeAttempt).mockImplementation(
      blurThenReject(
        new RunnerError({ message: 'x', status: 429, code: 'demo_limit_reached', retryAfterSeconds: 300 }),
      ),
    );
    const user = userEvent.setup();
    renderPage();
    const submit = await screen.findByRole('button', { name: 'Submit' });
    submit.focus();
    await user.keyboard(' ');

    const region = screen.getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent('Limit reached'));
    expect(region).toHaveTextContent('Try again in 5 minutes. Your files and notes are still here.');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Submit' })).toHaveFocus());
    expect(persistAttempt).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Open last submission' })).toBeDisabled();
  });

  it('keeps showing a non-denial run failure in the console as before', async () => {
    vi.mocked(runProject).mockRejectedValue(
      new RunnerError({ message: 'run-project 422: Field required', status: 422 }),
    );
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    expect(await screen.findByText('run-project 422: Field required')).toBeInTheDocument();
    expect(screen.getByRole('status')).toBeEmptyDOMElement();
  });
});
