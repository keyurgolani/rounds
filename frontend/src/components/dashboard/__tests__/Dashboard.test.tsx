import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../../../campaign/CampaignContext', () => ({
  useCampaign: () => ({ currentId: 'camp1', currentCampaign: { id: 'camp1', name: 'Big Tech 2026' }, campaigns: [{ id: 'camp1', name: 'Big Tech 2026' }] }),
}));
vi.mock('../../../auth/AuthProvider', () => ({ useAuth: () => ({ user: { name: 'Keyur Golani' } }) }));
vi.mock('../../../command-center/CommandCenterProvider', () => ({ useCommandCenter: () => ({ openView: vi.fn() }) }));
vi.mock('../../shell/StreakCard', () => ({ default: () => null }));
vi.mock('../../../hooks/usePracticeStatus', () => ({ effectiveStatus: () => 'todo', useStatusMapVersion: () => 0 }));

vi.mock('../../../applications/api', () => ({
  listApplications: vi.fn().mockResolvedValue([
    { id: 'a1', company: 'Stripe', role: 'SWE', status: 'Interviewing', updated_at: '2026-06-13T00:00:00Z' },
  ]),
  listRounds: vi.fn().mockResolvedValue([{ id: 'r1', application_id: 'a1', round_type: 'System Design', date: '2999-01-01T00:00:00Z' }]),
  getOffer: vi.fn().mockResolvedValue(null),
}));
vi.mock('../../../content/api', () => ({
  listCodingQuestions: vi.fn().mockResolvedValue([{ id: 'c1', title: 'LRU Cache', difficulty: 'Medium' }]),
  listSystemDesignQuestions: vi.fn().mockResolvedValue([]),
  listBehavioralQuestions: vi.fn().mockResolvedValue([{ id: 'q1', title: 'Conflict' }]),
  listBehavioralCategories: vi.fn().mockResolvedValue([{ id: 'cat1', name: 'Leadership' }]),
}));
vi.mock('../../../pages/ai-coding/aiCodingApi', () => ({ listRounds: vi.fn().mockResolvedValue([]) }));
vi.mock('../../../pages/take-home/takeHomeApi', () => ({ listAssignments: vi.fn().mockResolvedValue([]) }));
vi.mock('../../../experience/experienceApi', () => ({
  listAnecdotes: vi.fn().mockResolvedValue([]),
  listJobs: vi.fn().mockResolvedValue([{ id: 'j1' }]),
  listProjects: vi.fn().mockResolvedValue([]),
  listBullets: vi.fn().mockResolvedValue([{ id: 'bl1' }]),
}));
vi.mock('../../../experience/connectionApi', () => ({ listAllConnections: vi.fn().mockResolvedValue([]), buildReverseMap: () => ({}) }));
vi.mock('../../../features/resume/api', () => ({
  listResumes: vi.fn().mockResolvedValue([{ updated_at: '2026-06-12T00:00:00Z' }]),
  listVariants: vi.fn().mockResolvedValue([]),
}));
vi.mock('../../../todos/api', () => ({ listTodos: vi.fn().mockResolvedValue([]), updateTodo: vi.fn() }));

import Dashboard from '../../../pages/Dashboard';

beforeEach(() => vi.clearAllMocks());

describe('Dashboard (integration)', () => {
  it('renders the greeting and all status zones after data loads', async () => {
    render(<MemoryRouter><Dashboard /></MemoryRouter>);
    expect(screen.getByText(/Keyur/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('Practice readiness')).toBeInTheDocument());
    expect(screen.getByText('Pipeline pulse')).toBeInTheDocument();
    expect(screen.getByText('Resume coverage')).toBeInTheDocument();
    expect(screen.getByText('Experience library')).toBeInTheDocument();
    expect(screen.getByText('Behavioral prep depth')).toBeInTheDocument();
    // "System Design" renders in several places (track name, next interview, upcoming) — assert presence, not uniqueness:
    expect(screen.getAllByText('System Design').length).toBeGreaterThan(0);
  });
});
