import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import SystemDesignDetail from '../SystemDesignDetail';
import { getSystemDesignQuestion } from '../../content/api';
import { CommandCenterProvider } from '../../command-center/CommandCenterProvider';

vi.mock('../../content/api', () => ({
  getSystemDesignQuestion: vi.fn(),
  listSystemDesignQuestions: vi.fn(),
  getCodingQuestion: vi.fn(),
  listCodingQuestions: vi.fn(),
  getBehavioralQuestion: vi.fn(),
  listBehavioralQuestions: vi.fn(),
  listBehavioralCategories: vi.fn(),
  getSystemDesignGuide: vi.fn(),
  getCodingGuide: vi.fn(),
  getBehavioralGuide: vi.fn(),
}));

vi.mock('../../hooks/usePracticeStatus', () => ({
  usePracticeStatus: () => ['todo', vi.fn()],
}));

const baseSDQ = {
  id: 1,
  title: 'Design a URL Shortener',
  difficulty: 'Medium',
  description: 'Describe the system.',
  hints: ['h1'],
  constraints: ['c1'],
  requirements_functional: ['rf1'],
  requirements_nonfunctional: ['rnf1'],
  estimation: { qps: '10,000 req/s' },
  api_design: { endpoints: [{ method: 'POST', path: '/shorten', description: 'd' }] },
  database_schema: { tables: [{ name: 'urls', columns: ['id BIGINT'] }], indexes: [] },
  high_level_design: { description: 'hld', components: [{ name: 'LB', role: 'r' }] },
  detailed_design: { caching: 'c' },
  trade_offs: [{ option: 'Redis', recommendation: 'Use it' }],
  tips: ['t1'],
  thought_process: ['tp1'],
  tags: ['system', 'design'],
  architecture_diagram: null,
  sequence_diagram: null,
  er_diagram: null,
  thought_flow: null,
  tradeoff_visual: null,
  senior_topics: null,
};

function renderAt(url: string) {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <CommandCenterProvider>
        <Routes>
          <Route path="/system-design/question/:slug" element={<SystemDesignDetail />} />
        </Routes>
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (getSystemDesignQuestion as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(baseSDQ);
});

describe('SystemDesignDetail — single-scroll layout', () => {
  it('renders every section in one page (no tab switching)', async () => {
    renderAt('/system-design/question/design-a-url-shortener');
    await waitFor(() => screen.getByText('Design a URL Shortener'));

    // No tab toggles for the old Problem/Approach/Solutions split.
    expect(screen.queryByRole('button', { name: 'Problem' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Approach' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Solutions' })).toBeNull();

    // All primary section headings render together.
    expect(
      screen.getByRole('heading', { level: 2, name: /requirements/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 2, name: /approach framework/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 2, name: /trade-offs/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /architecture/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /database/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /^api$/i })).toBeInTheDocument();
  });

  it('pushes hints and tips to the right rail, not the main flow', async () => {
    renderAt('/system-design/question/design-a-url-shortener');
    await waitFor(() => screen.getByText('Design a URL Shortener'));

    // Hints/Tips no longer get their own SectionHeading — they live in the
    // right rail only. So no H2 heading with that text.
    expect(screen.queryByRole('heading', { level: 2, name: /^hints$/i })).toBeNull();
    expect(screen.queryByRole('heading', { level: 2, name: /^tips$/i })).toBeNull();
    // The content itself still renders (in the rail).
    expect(screen.getAllByText('h1').length).toBeGreaterThan(0);
    expect(screen.getAllByText('t1').length).toBeGreaterThan(0);
  });
});

describe('SystemDesignDetail — conditional sections', () => {
  it('hides the Senior topics section and nav entry when senior_topics is null', async () => {
    renderAt('/system-design/question/design-a-url-shortener');
    await waitFor(() => screen.getByText('hld'));
    expect(screen.queryByRole('heading', { level: 2, name: /senior topics/i })).toBeNull();
    const navs = screen.queryAllByRole('navigation', { name: /on this page/i });
    navs.forEach((nav) => {
      expect(nav.textContent).not.toMatch(/senior topics/i);
    });
  });

  it('shows the Senior topics section when data is present', async () => {
    (getSystemDesignQuestion as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...baseSDQ,
      senior_topics: [
        { title: 'Caching strategies', summary: 's', bullets: ['b'], callout: null },
      ],
    });
    renderAt('/system-design/question/design-a-url-shortener');
    await waitFor(() => screen.getByText('hld'));
    expect(
      screen.getByRole('heading', { level: 2, name: /senior topics/i }),
    ).toBeInTheDocument();
  });
});
