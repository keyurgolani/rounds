import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import BehavioralDetail from '../BehavioralDetail';
import { api } from '../../api/client';

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
  id: 1,
  title: 'Tell me about a conflict',
  question_text: 'Describe a time you disagreed with a teammate.',
  category_ids: [1],
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
      <Routes>
        <Route path="/behavioral/question/:slug" element={<BehavioralDetail />} />
      </Routes>
    </MemoryRouter>
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

describe('BehavioralDetail — tab structure', () => {
  it('renders exactly 3 tabs', async () => {
    renderAt('/behavioral/question/tell-me-about-a-conflict');
    await waitFor(() => screen.getByText('Tell me about a conflict'));

    // New tabs should be present
    expect(screen.getByRole('button', { name: 'Question & Anecdotes' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'STAR Guide & Tips' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sample Response' })).toBeInTheDocument();

    // Old standalone tabs should NOT be present
    expect(screen.queryByRole('button', { name: 'Question' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'My Anecdotes' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'STAR Guide' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Tips & Pitfalls' })).toBeNull();
  });

  it('defaults to the Question & Anecdotes tab', async () => {
    renderAt('/behavioral/question/tell-me-about-a-conflict');
    await waitFor(() => screen.getByText('Tell me about a conflict'));

    // Question prompt should be visible (appears in header and in card — use getAllByText)
    expect(screen.getAllByText(/Describe a time you disagreed with a teammate/).length).toBeGreaterThan(0);
    // MyAnecdotesPanel sentinel should be visible
    expect(screen.getByText('[MyAnecdotesPanel]')).toBeInTheDocument();
  });

  it('STAR & Tips tab renders both STAR cards and Do/Don\'t cards', async () => {
    renderAt('/behavioral/question/tell-me-about-a-conflict');
    await waitFor(() => screen.getByText('Tell me about a conflict'));

    // Click the STAR Guide & Tips tab
    fireEvent.click(screen.getByRole('button', { name: 'STAR Guide & Tips' }));

    await waitFor(() => {
      // STAR cards: letter 'S' should be present as STAR accent
      const sLetters = screen.getAllByText('S');
      expect(sLetters.length).toBeGreaterThan(0);
    });

    // Do and Don't eyebrows should be present
    expect(screen.getByText('Do')).toBeInTheDocument();
    expect(screen.getByText("Don't")).toBeInTheDocument();

    // Tips & Pitfalls eyebrow section heading
    expect(screen.getByText('Tips & Pitfalls')).toBeInTheDocument();

    // Actual tip content
    expect(screen.getByText('do this')).toBeInTheDocument();
    expect(screen.getByText("don't do that")).toBeInTheDocument();
  });

  it('Sample Response tab renders a redesigned card layout', async () => {
    renderAt('/behavioral/question/tell-me-about-a-conflict');
    await waitFor(() => screen.getByText('Tell me about a conflict'));

    // Click the Sample Response tab
    fireEvent.click(screen.getByRole('button', { name: 'Sample Response' }));

    await waitFor(() => {
      // Eyebrow "Sample response" card should be present
      expect(screen.getByText('Sample response')).toBeInTheDocument();
    });

    // STAR letter accents — S, T, A, R
    expect(screen.getByText('S')).toBeInTheDocument();
    expect(screen.getByText('T')).toBeInTheDocument();
    expect(screen.getByText('A')).toBeInTheDocument();
    expect(screen.getByText('R')).toBeInTheDocument();

    // Key strengths pills should be present
    expect(screen.getByText('Empathy')).toBeInTheDocument();
    expect(screen.getByText('Ownership')).toBeInTheDocument();

    // Key strengths demonstrated eyebrow
    expect(screen.getByText('Key strengths demonstrated')).toBeInTheDocument();
  });

  it('no emoji characters on STAR & Tips tab', async () => {
    renderAt('/behavioral/question/tell-me-about-a-conflict');
    await waitFor(() => screen.getByText('Tell me about a conflict'));

    // Click the STAR Guide & Tips tab
    fireEvent.click(screen.getByRole('button', { name: 'STAR Guide & Tips' }));

    await waitFor(() => {
      expect(screen.getByText('Do')).toBeInTheDocument();
    });

    // Assert no checkmark or cross emoji characters in DOM text
    const bodyText = document.body.textContent ?? '';
    expect(bodyText).not.toContain('✓');
    expect(bodyText).not.toContain('✕');
  });
});
