// GitHub import AI Enhancement (ROUNDS-00A-L01): it starts off, and an
// enhanced import takes at most 25 projects, the runner's cap.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

vi.mock('../../../ai/client', () => ({ enhanceProjects: vi.fn() }));

import GithubImportDialog, { AI_ENHANCE_MAX_PROJECTS } from '../GithubImportDialog';
import { enhanceProjects } from '../../../ai/client';

function repos(n: number) {
  return Array.from({ length: n }, (_, i) => ({
    id: i + 1,
    name: `repo-${i + 1}`,
    full_name: `octo/repo-${i + 1}`,
    description: null,
    html_url: `https://github.com/octo/repo-${i + 1}`,
    homepage: null,
    language: 'TypeScript',
    topics: [],
    fork: false,
    stargazers_count: 0,
    pushed_at: `2026-01-${String((i % 28) + 1).padStart(2, '0')}T00:00:00Z`,
  }));
}

beforeEach(() => {
  vi.stubGlobal(
    'fetch',
    vi.fn(async () => new Response(JSON.stringify(repos(30)), { status: 200 })),
  );
  vi.mocked(enhanceProjects).mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

async function openWithRepos(onImport = vi.fn()) {
  const user = userEvent.setup();
  render(<GithubImportDialog open onClose={vi.fn()} onImport={onImport} />);
  await user.type(screen.getByPlaceholderText('e.g. octocat'), 'octo');
  await user.click(screen.getByRole('button', { name: 'Fetch repos' }));
  await screen.findByText('repo-1');
  const [, aiToggle, ...repoBoxes] = screen.getAllByRole('checkbox');
  return { user, aiToggle, repoBoxes };
}

describe('GithubImportDialog AI Enhancement', () => {
  it('starts off, so an import makes no AI call', async () => {
    const onImport = vi.fn();
    const { user, aiToggle, repoBoxes } = await openWithRepos(onImport);
    expect(screen.getByRole('checkbox', { name: /AI Enhancement/ })).toBe(aiToggle);
    expect(aiToggle).not.toBeChecked();
    await user.click(repoBoxes[0]);
    await user.click(screen.getByRole('button', { name: /^Import/ }));
    expect(onImport).toHaveBeenCalledTimes(1);
    expect(enhanceProjects).not.toHaveBeenCalled();
  });

  it(`holds an enhanced import of more than ${AI_ENHANCE_MAX_PROJECTS} projects and says why`, async () => {
    expect(AI_ENHANCE_MAX_PROJECTS).toBe(25);
    vi.mocked(enhanceProjects).mockResolvedValue([]);
    const { user, aiToggle, repoBoxes } = await openWithRepos();
    await user.click(aiToggle);
    for (const box of repoBoxes.slice(0, 26)) await user.click(box);

    const importButton = screen.getByRole('button', { name: /^Import/ });
    expect(importButton).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent(
      'AI Enhancement takes up to 25 projects at a time. Select fewer, or turn it off.',
    );

    await user.click(repoBoxes[25]);
    expect(screen.getByRole('status')).toBeEmptyDOMElement();
    expect(importButton).toBeEnabled();
    await user.click(importButton);
    await waitFor(() => expect(enhanceProjects).toHaveBeenCalledTimes(1));
    expect(vi.mocked(enhanceProjects).mock.calls[0][0]).toHaveLength(25);
  });

  it('imports more than 25 projects when AI Enhancement is off', async () => {
    const onImport = vi.fn();
    const { user, repoBoxes } = await openWithRepos(onImport);
    for (const box of repoBoxes.slice(0, 26)) await user.click(box);
    await user.click(screen.getByRole('button', { name: /^Import/ }));
    expect(onImport.mock.calls[0][0]).toHaveLength(26);
    expect(enhanceProjects).not.toHaveBeenCalled();
  });
});
