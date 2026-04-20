import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import SystemDesignDetail from '../SystemDesignDetail';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn() },
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
      <Routes>
        <Route path="/system-design/question/:slug" element={<SystemDesignDetail />} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(baseSDQ);
});

describe('SystemDesignDetail — tab structure', () => {
  it('renders exactly three top-level tabs', async () => {
    renderAt('/system-design/question/design-a-url-shortener');
    await waitFor(() => screen.getByText('Design a URL Shortener'));
    expect(screen.getByRole('button', { name: 'Problem' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Approach' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Solutions' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Requirements' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Database' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'API' })).toBeNull();
    expect(screen.queryByRole('button', { name: 'Hints & Tips' })).toBeNull();
  });

  it('defaults to the Problem tab and shows its sections', async () => {
    renderAt('/system-design/question/design-a-url-shortener');
    await waitFor(() => screen.getByText('c1'));
    expect(screen.getByText('rf1')).toBeInTheDocument();
    expect(screen.getByText('rnf1')).toBeInTheDocument();
    expect(screen.getByText(/qps/i)).toBeInTheDocument();
  });

  it('activates the Approach tab when URL has ?tab=approach', async () => {
    renderAt('/system-design/question/design-a-url-shortener?tab=approach');
    await waitFor(() => screen.getByText('tp1'));
    expect(screen.getByText('t1')).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 2, name: /approach framework/i })).toBeInTheDocument();
  });

  it('activates the Solutions tab when URL has ?tab=solutions', async () => {
    renderAt('/system-design/question/design-a-url-shortener?tab=solutions');
    await waitFor(() => screen.getByText('hld'));
    expect(screen.getByRole('heading', { level: 2, name: /architecture/i })).toBeInTheDocument();
  });
});

describe('SystemDesignDetail — conditional sections', () => {
  it('hides the Senior topics section and nav entry when senior_topics is null', async () => {
    renderAt('/system-design/question/design-a-url-shortener?tab=solutions');
    await waitFor(() => screen.getByText('hld'));
    expect(screen.queryByRole('heading', { level: 2, name: /senior topics/i })).toBeNull();
    const navs = screen.queryAllByRole('navigation', { name: /on this page/i });
    navs.forEach((nav) => {
      expect(nav.textContent).not.toMatch(/senior topics/i);
    });
  });

  it('shows the Senior topics section when data is present', async () => {
    (api.get as unknown as ReturnType<typeof vi.fn>).mockResolvedValue({
      ...baseSDQ,
      senior_topics: [
        { title: 'Caching strategies', summary: 's', bullets: ['b'], callout: null },
      ],
    });
    renderAt('/system-design/question/design-a-url-shortener?tab=solutions');
    await waitFor(() => screen.getByText('hld'));
    expect(screen.getByRole('heading', { level: 2, name: /senior topics/i })).toBeInTheDocument();
  });
});
