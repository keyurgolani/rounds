// Coding runs and definitions (ROUNDS-00A-L02): a call names the row's
// definition version and case ids, a replaced version is reread and
// retried once, and an out-of-date page asks for a reload that saves the
// draft first. The code never leaves the editor.

import { beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

const reloadPage = vi.hoisted(() => vi.fn());

vi.mock('../../../lib/pocketbase', () => ({ pb: { authStore: { token: 'test-token-placeholder' } } }));
vi.mock('../../../content/api', () => ({ getCodingQuestion: vi.fn() }));
vi.mock('../../../lib/codeDraftsApi', () => ({
  listCodeDrafts: vi.fn().mockResolvedValue([]),
  upsertCodeDraft: vi.fn().mockResolvedValue({ id: 'd1' }),
  deleteCodeDraft: vi.fn(),
}));
vi.mock('../runnerApi', () => ({ runCode: vi.fn(), evaluateCode: vi.fn() }));
vi.mock('../../../lib/definitions', async (importOriginal) => ({
  ...((await importOriginal()) as Record<string, unknown>),
  reloadPage,
}));
vi.mock('../../../auth/AuthProvider', () => ({ useAuth: () => ({ user: { id: 'u1' } }) }));
vi.mock('../../../campaign/CampaignContext', () => ({ useCampaign: () => ({ currentId: 'campaign00000001' }) }));
vi.mock('../../../components/shell/AppHeader', () => ({ default: () => <header /> }));
vi.mock('../../../components/shell/StatusAction', () => ({ default: () => null }));
vi.mock('../../../components/editor/MultiFileEditor', () => ({
  default: (props: {
    files: Record<string, string>;
    onFileChange?: (path: string, contents: string) => void;
    topRightExtras?: React.ReactNode;
  }) => {
    const [path, contents] = Object.entries(props.files)[0] ?? ['solution.py', ''];
    return (
      <div>
        <textarea aria-label="Code" value={contents} onChange={(e) => props.onFileChange?.(path, e.target.value)} />
        {props.topRightExtras}
      </div>
    );
  },
}));

import CodingDetail from '../../CodingDetail';
import { getCodingQuestion } from '../../../content/api';
import { listCodeDrafts, upsertCodeDraft } from '../../../lib/codeDraftsApi';
import { localIsNewer, saveLocal } from '../../../lib/codeDraft';
import { evaluateCode, runCode } from '../runnerApi';
import { RunnerError } from '../../../lib/runnerFetch';

const STARTER = 'def two_sum(nums, target):\n    return []\n';
const QUESTION = {
  id: 7,
  slug: 'two-sum',
  title: 'Two Sum',
  difficulty: 'easy',
  description: 'Find two numbers.',
  hints: [],
  constraints: [],
  starter_code: { python: STARTER },
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
  definition_version: 1,
  definition_case_ids: ['c000', 'c001'],
};

const superseded = () =>
  new RunnerError({ message: 'x', status: 409, code: 'definition_superseded', detail: 'This version was replaced.' });

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
  reloadPage.mockReset();
  vi.mocked(getCodingQuestion).mockReset();
  vi.mocked(getCodingQuestion).mockResolvedValue(QUESTION as never);
  vi.mocked(evaluateCode).mockReset();
  vi.mocked(runCode).mockReset();
  vi.mocked(upsertCodeDraft).mockReset().mockResolvedValue({ id: 'd1' } as never);
  vi.mocked(listCodeDrafts).mockReset().mockResolvedValue([]);
});

function savedDraft(code: string) {
  return {
    id: 'd1',
    user_id: 'u1',
    campaign_id: 'campaign00000001',
    question: '7',
    language: 'python',
    code,
  };
}

describe('CodingDetail definition requests', () => {
  it("names the row's definition version and case ids", async () => {
    vi.mocked(evaluateCode).mockResolvedValue({ passed: 2, failed: 0, results: [] });
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run all (2)' }));
    await waitFor(() => expect(evaluateCode).toHaveBeenCalledTimes(1));
    expect(evaluateCode).toHaveBeenCalledWith({
      question_slug: 'two-sum',
      language: 'python',
      code: STARTER,
      filter: undefined,
      definition_version: 1,
      definition_case_ids: ['c000', 'c001'],
    });
  });

  it('rereads a replaced version and retries once with the current one', async () => {
    vi.mocked(getCodingQuestion)
      .mockResolvedValueOnce(QUESTION as never)
      .mockResolvedValue({ ...QUESTION, definition_version: 2 } as never);
    vi.mocked(evaluateCode)
      .mockRejectedValueOnce(superseded())
      .mockResolvedValue({ passed: 2, failed: 0, results: [] });
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run all (2)' }));
    await waitFor(() => expect(evaluateCode).toHaveBeenCalledTimes(2));
    const versions = vi.mocked(evaluateCode).mock.calls.map(([payload]) => payload.definition_version);
    expect(versions).toEqual([1, 2]);
    const region = within(screen.getByTestId('right-dock')).getByRole('status');
    expect(region).toBeEmptyDOMElement();

    // The next call names the reread version straight away.
    await user.click(screen.getByRole('button', { name: 'Run all (2)' }));
    await waitFor(() => expect(evaluateCode).toHaveBeenCalledTimes(3));
    expect(vi.mocked(evaluateCode).mock.calls[2][0].definition_version).toBe(2);
  });

  it('asks for a reload when the retry is refused too, and keeps the code', async () => {
    vi.mocked(getCodingQuestion)
      .mockResolvedValueOnce(QUESTION as never)
      .mockResolvedValue({ ...QUESTION, definition_version: 2 } as never);
    vi.mocked(evaluateCode).mockRejectedValue(superseded());
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run all (2)' }));
    const region = within(screen.getByTestId('right-dock')).getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent('Reload to continue'));
    expect(evaluateCode).toHaveBeenCalledTimes(2);
    expect(screen.getByLabelText('Code')).toHaveValue(STARTER);
  });

  it('saves the draft before the reload an out-of-date page asks for', async () => {
    vi.mocked(evaluateCode).mockRejectedValue(
      new RunnerError({ message: 'x', status: 422, code: 'legacy_request_rejected' }),
    );
    const user = userEvent.setup();
    renderPage();
    const editor = await screen.findByLabelText('Code');
    await waitFor(() => expect(editor).toHaveValue(STARTER));
    await user.type(editor, '# mine');
    await user.click(screen.getByRole('button', { name: 'Run all (2)' }));
    const region = within(screen.getByTestId('right-dock')).getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent('This page is out of date. No tests ran.'));

    await user.click(within(region).getByRole('button', { name: 'Reload' }));
    await waitFor(() => expect(reloadPage).toHaveBeenCalledTimes(1));
    expect(upsertCodeDraft).toHaveBeenCalledWith({
      campaign_id: 'campaign00000001',
      question: '7',
      language: 'python',
      code: `${STARTER}# mine`,
    });
    expect(vi.mocked(upsertCodeDraft).mock.invocationCallOrder[0]).toBeLessThan(
      reloadPage.mock.invocationCallOrder[0],
    );
  });

  it('loads the local copy, not the older saved draft, after a reload whose save failed', async () => {
    vi.mocked(evaluateCode).mockRejectedValue(
      new RunnerError({ message: 'x', status: 422, code: 'legacy_request_rejected' }),
    );
    vi.mocked(upsertCodeDraft).mockRejectedValue(new Error('offline'));
    const user = userEvent.setup();
    const before = renderPage();
    const editor = await screen.findByLabelText('Code');
    await waitFor(() => expect(editor).toHaveValue(STARTER));
    await user.type(editor, '# mine');
    await user.click(screen.getByRole('button', { name: 'Run all (2)' }));
    const region = within(screen.getByTestId('right-dock')).getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent('This page is out of date. No tests ran.'));
    await user.click(within(region).getByRole('button', { name: 'Reload' }));
    await waitFor(() => expect(reloadPage).toHaveBeenCalledTimes(1));
    expect(localIsNewer('u1', 7, 'python')).toBe(true);
    before.unmount();

    // The reloaded page, with PocketBase still holding an older draft.
    vi.mocked(upsertCodeDraft).mockReset().mockResolvedValue({ id: 'd1' } as never);
    vi.mocked(listCodeDrafts).mockResolvedValue([savedDraft(`${STARTER}# older`)] as never);
    const after = renderPage();
    await waitFor(() => expect(screen.getByLabelText('Code')).toHaveValue(`${STARTER}# mine`));

    // The next sync saves it, and PocketBase's draft is current again.
    after.unmount();
    await waitFor(() => expect(localIsNewer('u1', 7, 'python')).toBe(false));
    expect(upsertCodeDraft).toHaveBeenLastCalledWith({
      campaign_id: 'campaign00000001',
      question: '7',
      language: 'python',
      code: `${STARTER}# mine`,
    });
  });

  it('loads the saved draft over a local copy that is not marked newer', async () => {
    saveLocal('u1', 7, 'python', `${STARTER}# local`);
    vi.mocked(listCodeDrafts).mockResolvedValue([savedDraft(`${STARTER}# saved`)] as never);
    renderPage();
    await waitFor(() => expect(screen.getByLabelText('Code')).toHaveValue(`${STARTER}# saved`));
  });

  it('runs nothing for a retired question and keeps the code', async () => {
    vi.mocked(runCode).mockRejectedValue(new RunnerError({ message: 'x', status: 410, code: 'definition_retired' }));
    vi.mocked(evaluateCode).mockRejectedValue(
      new RunnerError({ message: 'x', status: 410, code: 'definition_retired' }),
    );
    const user = userEvent.setup();
    renderPage();
    await user.click(await screen.findByRole('button', { name: 'Run all (2)' }));
    const region = within(screen.getByTestId('right-dock')).getByRole('status');
    await waitFor(() => expect(region).toHaveTextContent('Retired'));
    expect(region).toHaveTextContent('Your code is still here.');
    expect(within(region).queryByRole('button')).not.toBeInTheDocument();
    expect(screen.getByLabelText('Code')).toHaveValue(STARTER);
  });
});
