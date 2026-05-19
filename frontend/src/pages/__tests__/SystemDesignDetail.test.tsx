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

// SDPracticeView lazy-loads Excalidraw which doesn't resolve cleanly under
// Node's strict ESM (roughjs import without explicit .js). Replace the
// orchestrator with a stub so the Practice tab renders trivially in tests.
vi.mock('../sd-practice/SDPracticeView', () => ({
  default: () => <div data-testid="sd-practice-stub">practice surface</div>,
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
          <Route path="/system-design/question/:slug/guidance" element={<SystemDesignDetail />} />
        </Routes>
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (getSystemDesignQuestion as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(baseSDQ);
});

describe('SystemDesignDetail — Practice (default) tab', () => {
  it('renders the PromptHeader + Practice surface on the bare URL', async () => {
    renderAt('/system-design/question/design-a-url-shortener');
    await waitFor(() => screen.getByText('Design a URL Shortener'));

    // PromptHeader is always visible — prompt text + requirements live above the tabs.
    expect(screen.getByText('Describe the system.')).toBeInTheDocument();
    expect(screen.getByText('c1')).toBeInTheDocument(); // constraint
    expect(screen.getByText('rf1')).toBeInTheDocument(); // functional req

    // Practice tab is the default — the practice surface stub mounts.
    expect(screen.getByTestId('sd-practice-stub')).toBeInTheDocument();

    // Guidance-only sections are NOT in the DOM on the Practice tab.
    expect(
      screen.queryByRole('heading', { level: 2, name: /approach framework/i }),
    ).toBeNull();
    expect(screen.queryByRole('heading', { level: 2, name: /architecture/i })).toBeNull();
  });

  it('has Practice and Guidance tabs in the tab strip', async () => {
    renderAt('/system-design/question/design-a-url-shortener');
    await waitFor(() => screen.getByText('Design a URL Shortener'));

    const tabs = screen.getAllByRole('tab');
    const labels = tabs.map((t) => t.textContent);
    expect(labels).toContain('Practice');
    expect(labels).toContain('Guidance');
  });
});

describe('SystemDesignDetail — Guidance tab', () => {
  it('renders every guidance section on the /guidance URL', async () => {
    renderAt('/system-design/question/design-a-url-shortener/guidance');
    await waitFor(() => screen.getByText('Design a URL Shortener'));

    expect(
      screen.getByRole('heading', { level: 2, name: /approach framework/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { level: 2, name: /trade-offs/i }),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /architecture/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /database/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /^api$/i })).toBeInTheDocument();

    // Prompt + Requirements moved to the always-visible header, no longer
    // duplicated as H2 sections inside Guidance.
    expect(screen.queryByRole('heading', { level: 2, name: /^prompt$/i })).toBeNull();
    expect(screen.queryByRole('heading', { level: 2, name: /^requirements$/i })).toBeNull();
  });

  it('renders Hints and Tips as inline sections in the main flow', async () => {
    renderAt('/system-design/question/design-a-url-shortener/guidance');
    await waitFor(() => screen.getByText('Design a URL Shortener'));

    // Right-side aside is gone — Hints + Tips now live as their own
    // top-level h2 sections, ordered after the design content so they
    // don't spoil the user before they've worked through the rest.
    expect(screen.getByRole('heading', { level: 2, name: /^hints$/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /^tips$/i })).toBeInTheDocument();
    expect(screen.getByText('h1')).toBeInTheDocument();
    expect(screen.getByText('t1')).toBeInTheDocument();
  });
});

describe('SystemDesignDetail — conditional sections', () => {
  it('hides the Senior topics section and nav entry when senior_topics is null', async () => {
    renderAt('/system-design/question/design-a-url-shortener/guidance');
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
    renderAt('/system-design/question/design-a-url-shortener/guidance');
    await waitFor(() => screen.getByText('hld'));
    expect(
      screen.getByRole('heading', { level: 2, name: /senior topics/i }),
    ).toBeInTheDocument();
  });
});
