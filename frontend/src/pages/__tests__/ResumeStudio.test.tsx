// The Studio page and a failed save (ROUNDS-00A-L04): the Studio stays on
// screen with the save's state in the header, so the Export tab can say
// server PDF is on hold while the client formats keep working. A save
// refused for good says it isn't retrying. Only a resume that didn't load
// puts its error where the Studio would be.

import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ResumeStudio from '../ResumeStudio';
import { useResume, type UseResumeResult } from '../../features/resume/hooks/useResume';
import { CommandCenterProvider } from '../../command-center/CommandCenterProvider';
import { emptyResumeData } from '../../features/resume/types';

vi.mock('../../features/resume/hooks/useResume', () => ({ useResume: vi.fn() }));
vi.mock('../../features/resume/studio/StudioShell', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../features/resume/studio/StudioShell')>()),
  default: () => <div data-testid="studio-shell">studio</div>,
}));

function result(over: Partial<UseResumeResult>): UseResumeResult {
  return {
    resume: null,
    data: emptyResumeData(),
    templateId: 'modern',
    design: {},
    loading: false,
    error: null,
    saveState: 'idle',
    lastSavedAt: null,
    setData: vi.fn(),
    setTemplateId: vi.fn(),
    setDesign: vi.fn(),
    links: {} as UseResumeResult['links'],
    setLinks: vi.fn(),
    rename: vi.fn(),
    flush: vi.fn(),
    ...over,
  };
}

const RESUME = { id: 'resumeaaaaaaaa1', slug: 'jane', name: 'Jane Doe' } as unknown as NonNullable<UseResumeResult['resume']>;

function renderStudio() {
  return render(
    <MemoryRouter initialEntries={['/resumes/jane?tab=export']}>
      <CommandCenterProvider>
        <Routes>
          <Route path="/resumes/:slug" element={<ResumeStudio />} />
        </Routes>
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => vi.mocked(useResume).mockReset());

describe('ResumeStudio', () => {
  it('keeps the Studio on screen when a save fails, and says so in the header', () => {
    vi.mocked(useResume).mockReturnValue(result({ resume: RESUME, saveState: 'error' }));
    renderStudio();
    expect(screen.getByTestId('studio-shell')).toBeInTheDocument();
    expect(screen.getByText(/Save failed/)).toBeInTheDocument();
  });

  it('says when a refused save is not retrying, so the page stays open', () => {
    vi.mocked(useResume).mockReturnValue(result({ resume: RESUME, saveState: 'refused' }));
    renderStudio();
    expect(screen.getByTestId('studio-shell')).toBeInTheDocument();
    expect(
      screen.getByText(/Save failed, not retrying\. Keep this page open; your next edit or export tries again\./),
    ).toBeInTheDocument();
    expect(screen.queryByText(/retrying$/)).not.toBeInTheDocument();
  });

  it('says when a rename failed and nothing retries it', () => {
    vi.mocked(useResume).mockReturnValue(result({ resume: RESUME, saveState: 'renameFailed' }));
    renderStudio();
    expect(screen.getByText(/Rename failed, not retrying\. The old name is kept\./)).toBeInTheDocument();
  });

  it('shows the error in place of the Studio when the resume did not load', () => {
    vi.mocked(useResume).mockReturnValue(result({ error: 'Not found.' }));
    renderStudio();
    expect(screen.getByText('Not found.')).toBeInTheDocument();
    expect(screen.queryByTestId('studio-shell')).not.toBeInTheDocument();
  });

  it('shows a failed load in place of the Studio even with a resume still in hand', () => {
    vi.mocked(useResume).mockReturnValue(result({ resume: RESUME, error: 'Not found.' }));
    renderStudio();
    expect(screen.getByText('Not found.')).toBeInTheDocument();
    expect(screen.queryByTestId('studio-shell')).not.toBeInTheDocument();
  });

  it('shows the Studio once the resume loads', () => {
    vi.mocked(useResume).mockReturnValue(result({ resume: RESUME }));
    renderStudio();
    expect(screen.getByTestId('studio-shell')).toBeInTheDocument();
  });
});
