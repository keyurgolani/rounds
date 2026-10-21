// AI-coding runs, grades, and definitions (ROUNDS-00A-L02): calls name
// the round's language and definition version, a replaced version is
// reread and retried once, a refused file shows the server's fixed
// sentence, and a reload saves the files first.

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const reloadPage = vi.hoisted(() => vi.fn());
const drafts = vi.hoisted(() => {
  const files = { 'client.py': 'import httpx\n' };
  return {
    files,
    savedFiles: files,
    setFile: () => {},
    hydrated: true,
    resetToStarter: () => {},
    persistImmediately: () => Promise.resolve(),
    saveNow: vi.fn(async (): Promise<boolean> => true),
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
vi.mock('../../lib/definitions', async (importOriginal) => ({
  ...((await importOriginal()) as Record<string, unknown>),
  reloadPage,
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
  slug: 'hallucinated-http-client',
  title: 'Hallucinated HTTP client',
  difficulty: 'medium',
  language: 'python',
  description: 'Fix the client.',
  starter_files: [{ path: 'client.py', contents: 'import httpx\n' }],
  checkpoints: [{ label: 'Fetch', prompt: 'Make it fetch.', ai_allowed: true, test_command: '' }],
  rubric: { items: [] },
  topics: [],
  companies: [],
  definition_version: 1,
};

const RUN_OK = {
  passed: true,
  passed_count: 1,
  failed_count: 0,
  stdout: '',
  stderr: '',
  error: null,
  duration_ms: 1,
  truncated: false,
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/ai-coding/round/hallucinated-http-client']}>
      <Routes>
        <Route path="/ai-coding/round/:slug" element={<AICodingDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  reloadPage.mockReset();
  drafts.saveNow.mockClear().mockResolvedValue(true);
  vi.mocked(getRound).mockReset();
  vi.mocked(getRound).mockResolvedValue(ROUND as never);
  vi.mocked(runProject).mockReset();
  vi.mocked(gradeAttempt).mockReset();
  vi.mocked(persistAttempt).mockReset();
});

describe('AICodingDetail definition requests', () => {
  it("names the round's definition version on a run", async () => {
    vi.mocked(runProject).mockResolvedValue(RUN_OK);
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    await waitFor(() => expect(runProject).toHaveBeenCalledTimes(1));
    expect(runProject).toHaveBeenCalledWith({
      round_slug: 'hallucinated-http-client',
      language: 'python',
      checkpoint_index: 0,
      files: drafts.files,
      definition_version: 1,
    });
  });

  it('names the language and version on a grade, and retries a replaced version once', async () => {
    vi.mocked(getRound)
      .mockResolvedValueOnce(ROUND as never)
      .mockResolvedValue({ ...ROUND, definition_version: 2 } as never);
    vi.mocked(gradeAttempt)
      .mockRejectedValueOnce(new RunnerError({ message: 'x', status: 409, code: 'definition_superseded' }))
      .mockResolvedValue({
        test_results: [
          {
            passed: true,
            passed_count: 1,
            failed_count: 0,
            error: null,
            outcomes: [{ id: 'fetch_user_against_real_server', outcome: 'passed', reason: 'ok' }],
          },
        ],
        rubric_review: { items: [], total: 0, skipped: true, reason: 'no provider' },
      });
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Submit' }));
    await waitFor(() => expect(gradeAttempt).toHaveBeenCalledTimes(2));
    expect(vi.mocked(gradeAttempt).mock.calls.map(([req]) => [req.language, req.definition_version])).toEqual([
      ['python', 1],
      ['python', 2],
    ]);
    // The outcomes, not harness output, are what the report shows.
    expect(await screen.findByText('fetch_user_against_real_server: pass')).toBeInTheDocument();
    await waitFor(() => expect(persistAttempt).toHaveBeenCalledTimes(1));
  });

  it("shows the server's sentence for a file the grader won't take", async () => {
    const detail =
      'Test and package configuration files, such as conftest.py, pytest.ini, or package.json, ' +
      "can't be sent. Remove it and try again.";
    vi.mocked(gradeAttempt).mockRejectedValue(
      new RunnerError({ message: `grade 422: ${detail}`, status: 422, code: 'path_not_allowed', detail }),
    );
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Submit' }));
    const region = screen.getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent('File not allowed'));
    expect(region).toHaveTextContent(`${detail} Nothing was graded. Your files and notes are still here.`);
    expect(persistAttempt).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Open last submission' })).toBeDisabled();
  });

  it('saves the files before the reload an out-of-date page asks for', async () => {
    vi.mocked(runProject).mockRejectedValue(
      new RunnerError({ message: 'x', status: 422, code: 'legacy_request_rejected' }),
    );
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    const region = screen.getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent('Reload to continue'));
    await user.click(within(region).getByRole('button', { name: 'Reload' }));
    await waitFor(() => expect(reloadPage).toHaveBeenCalledTimes(1));
    expect(drafts.saveNow).toHaveBeenCalledTimes(1);
    expect(drafts.saveNow.mock.invocationCallOrder[0]).toBeLessThan(reloadPage.mock.invocationCallOrder[0]);
  });

  it('stays on the page and says so when the files could not be saved, then reloads on a retry that saves', async () => {
    vi.mocked(runProject).mockRejectedValue(
      new RunnerError({ message: 'x', status: 422, code: 'legacy_request_rejected' }),
    );
    drafts.saveNow.mockResolvedValueOnce(false);
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    const region = screen.getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent('Reload to continue'));
    await user.click(within(region).getByRole('button', { name: 'Reload' }));
    await waitFor(() => expect(region).toHaveTextContent('Draft not saved'));
    expect(region).toHaveTextContent(
      "Your draft couldn't be saved, so the page didn't reload. Your code is still here. Try Reload again.",
    );
    expect(reloadPage).not.toHaveBeenCalled();
    const retry = within(region).getByRole('button', { name: 'Reload' });
    expect(retry).toHaveFocus();

    await user.keyboard('{Enter}');
    await waitFor(() => expect(reloadPage).toHaveBeenCalledTimes(1));
    expect(drafts.saveNow).toHaveBeenCalledTimes(2);
  });
});
