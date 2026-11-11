// The Studio page and a failed save (ROUNDS-00A-L04): the Studio stays on
// screen with the save's state in the header, so the Export tab can say
// server PDF is on hold while the client formats keep working. Only a
// resume that didn't load puts its error where the Studio would be.

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
    vi.mocked(useResume).mockReturnValue(result({ resume: RESUME, error: 'Something went wrong.', saveState: 'error' }));
    renderStudio();
    expect(screen.getByTestId('studio-shell')).toBeInTheDocument();
    expect(screen.queryByText('Something went wrong.')).not.toBeInTheDocument();
    expect(screen.getByText(/Save failed/)).toBeInTheDocument();
  });

  it('shows the error in place of the Studio when the resume did not load', () => {
    vi.mocked(useResume).mockReturnValue(result({ error: 'Not found.' }));
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
