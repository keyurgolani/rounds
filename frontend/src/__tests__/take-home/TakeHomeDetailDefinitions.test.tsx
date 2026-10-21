// Take-home runs, submits, and definitions (ROUNDS-00A-L02): calls name
// the assignment's language and definition version, a retired
// assignment runs nothing and keeps the files, and a reload saves the
// files first.

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const reloadPage = vi.hoisted(() => vi.fn());
const drafts = vi.hoisted(() => {
  const files = { 'kv.py': 'class KV:\n    pass\n' };
  return {
    files,
    savedFiles: files,
    setFile: () => {},
    hydrated: true,
    resetToStarter: () => {},
    saveNow: vi.fn(async (): Promise<boolean> => true),
  };
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
vi.mock('../../lib/definitions', async (importOriginal) => ({
  ...((await importOriginal()) as Record<string, unknown>),
  reloadPage,
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
  definition_version: 1,
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

beforeEach(() => {
  window.localStorage.clear();
  reloadPage.mockReset();
  drafts.saveNow.mockClear().mockResolvedValue(true);
  vi.mocked(getAssignment).mockReset();
  vi.mocked(getAssignment).mockResolvedValue(ASSIGNMENT as never);
  vi.mocked(runProject).mockReset();
  vi.mocked(submitAttempt).mockReset();
});

describe('TakeHomeDetail definition requests', () => {
  it("names the assignment's language and definition version on a run", async () => {
    vi.mocked(runProject).mockResolvedValue({
      score: 1,
      passed: true,
      criteria: [{ id: 'adds_small', passed: true, weight: 1, logs: 'ok' }],
      outcomes: [{ id: 'adds_small', outcome: 'passed', reason: 'ok' }],
      stdout: '',
      stderr: '',
      error: null,
      duration_ms: 1,
    });
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    await waitFor(() => expect(runProject).toHaveBeenCalledTimes(1));
    expect(runProject).toHaveBeenCalledWith('kv-store-py', drafts.files, {
      language: 'python',
      definition_version: 1,
    });
  });

  it('retries a replaced version once on submit', async () => {
    vi.mocked(getAssignment)
      .mockResolvedValueOnce(ASSIGNMENT as never)
      .mockResolvedValue({ ...ASSIGNMENT, definition_version: 3 } as never);
    vi.mocked(submitAttempt)
      .mockRejectedValueOnce(new RunnerError({ message: 'x', status: 409, code: 'definition_superseded' }))
      .mockResolvedValue({
        harness: { score: 1, criteria: [], stdout: '', stderr: '', error: null, duration_ms: 1 },
        rubric_review: { items: [], total: 0, skipped: true },
      });
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Submit' }));
    await waitFor(() => expect(submitAttempt).toHaveBeenCalledTimes(2));
    expect(vi.mocked(submitAttempt).mock.calls.map(([req]) => [req.language, req.definition_version])).toEqual([
      ['python', 1],
      ['python', 3],
    ]);
  });

  it('runs nothing for a retired assignment and keeps the files', async () => {
    vi.mocked(submitAttempt).mockRejectedValue(
      new RunnerError({ message: 'x', status: 410, code: 'definition_retired' }),
    );
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Submit' }));
    const region = screen.getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent('Retired'));
    expect(region).toHaveTextContent('Your files and notes are still here.');
    expect(screen.getByRole('button', { name: 'Open last submission' })).toBeDisabled();
    expect(drafts.saveNow).not.toHaveBeenCalled();
  });

  it('saves the files before the reload an out-of-date page asks for', async () => {
    vi.mocked(runProject).mockRejectedValue(new RunnerError({ message: 'x', status: 422, code: 'case_unknown' }));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    const region = screen.getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent('Reload to continue'));
    await user.click(within(region).getByRole('button', { name: 'Reload' }));
    await waitFor(() => expect(reloadPage).toHaveBeenCalledTimes(1));
    expect(drafts.saveNow.mock.invocationCallOrder[0]).toBeLessThan(reloadPage.mock.invocationCallOrder[0]);
  });

  it('stays on the page and says so when the files could not be saved, then reloads on a retry that saves', async () => {
    vi.mocked(runProject).mockRejectedValue(new RunnerError({ message: 'x', status: 422, code: 'case_unknown' }));
    drafts.saveNow.mockRejectedValueOnce(new Error('offline'));
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run' }));
    const region = screen.getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent('Reload to continue'));
    await user.click(within(region).getByRole('button', { name: 'Reload' }));
    await waitFor(() => expect(region).toHaveTextContent('Draft not saved'));
    expect(region).toHaveTextContent("Your draft couldn't be saved, so the page didn't reload.");
    expect(region).toHaveTextContent('Try Reload again.');
    expect(reloadPage).not.toHaveBeenCalled();
    expect(within(region).getByRole('button', { name: 'Reload' })).toHaveFocus();

    await user.keyboard('{Enter}');
    await waitFor(() => expect(reloadPage).toHaveBeenCalledTimes(1));
    expect(drafts.saveNow).toHaveBeenCalledTimes(2);
  });
});
