import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import BehavioralDetail from '../BehavioralDetail';
import { api } from '../../api/client';
import { CommandCenterProvider } from '../../command-center/CommandCenterProvider';

vi.mock('../../api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn() },
}));

vi.mock('../../hooks/usePracticeStatus', () => ({
  usePracticeStatus: () => ['todo', vi.fn()],
}));

vi.mock('../behavioral/MyAnecdotesPanel', () => ({
  MyAnecdotesPanel: () => <div>[MyAnecdotesPanel]</div>,
}));

const baseBQ = {
  id: 'bq1',
  title: 'Tell me about a conflict',
  question_text: 'Describe a time you disagreed with a teammate.',
  category_ids: ['cat1'],
  star_guide: {
    situation: 'sit',
    task: 'tsk',
    action: 'act',
    result: 'res',
    framework_tips: ['ft1'],
  },
  sample_response: {
    situation: 'sample sit',
    task: 'sample tsk',
    action: 'sample act',
    result: 'sample res',
    key_strengths_shown: ['Empathy', 'Ownership'],
  },
  tips: ['do this'],
  common_pitfalls: ["don't do that"],
  follow_up_questions: ['follow up?'],
  what_interviewers_look_for: ['structure'],
  tags: ['conflict'],
};

function renderAt(url: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <CommandCenterProvider>
        <Routes>
          <Route path="/behavioral/question/:slug" element={<BehavioralDetail />} />
        </Routes>
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (api.get as unknown as ReturnType<typeof vi.fn>).mockImplementation((path: string) => {
    if (path.startsWith('/api/behavioral/')) return Promise.resolve(baseBQ);
    if (path === '/api/behavioral-categories') return Promise.resolve([]);
    if (path === '/api/behavioral') return Promise.resolve([]);
    return Promise.resolve(null);
  });
});

describe('BehavioralDetail — single-scroll layout', () => {
  it('renders all sections in one page (no tab switching)', async () => {
    renderAt('/behavioral/question/tell-me-about-a-conflict');
    await waitFor(() => screen.getByText('Tell me about a conflict'));

    // No tab toggles for the old Question/STAR/Sample split.
    expect(screen.queryByRole('button', { name: 'Question & Anecdotes' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'STAR Guide & Tips' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Sample Response' })).toBeNull();

    // Primary section headings all appear together.
    expect(screen.getByRole('heading', { level: 2, name: /prompt/i })).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 2, name: /star guide/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 2, name: /sample response/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 2, name: /your anecdotes/i }),
    ).toBeInTheDocument();
  });

  it('anecdotes panel mounts alongside the question content', async () => {
    renderAt('/behavioral/question/tell-me-about-a-conflict');
    await waitFor(() => screen.getByText('Tell me about a conflict'));
    expect(screen.getByText('[MyAnecdotesPanel]')).toBeInTheDocument();
  });

  it('pushes follow-ups, tips, pitfalls, and interviewer cues to the right rail', async () => {
    renderAt('/behavioral/question/tell-me-about-a-conflict');
    await waitFor(() => screen.getByText('Tell me about a conflict'));

    // No H2 for rail-only content.
    expect(screen.queryByRole('heading', { level: 2, name: /likely follow-ups/i })).toBeNull();
    expect(screen.queryByRole('heading', { level: 2, name: /tips & pitfalls/i })).toBeNull();

    // The content itself is still rendered somewhere on the page.
    expect(screen.getAllByText('follow up?').length).toBeGreaterThan(0);
    expect(screen.getAllByText('do this').length).toBeGreaterThan(0);
    expect(screen.getAllByText("don't do that").length).toBeGreaterThan(0);
    expect(screen.getAllByText('structure').length).toBeGreaterThan(0);
    expect(screen.getAllByText('Empathy').length).toBeGreaterThan(0);
  });

  it('does not render emoji markers for Do/Don\'t in the rail', async () => {
    renderAt('/behavioral/question/tell-me-about-a-conflict');
    await waitFor(() => screen.getByText('Tell me about a conflict'));
    const bodyText = document.body.textContent ?? '';
    expect(bodyText).not.toContain('✓');
    expect(bodyText).not.toContain('✕');
  });
});
