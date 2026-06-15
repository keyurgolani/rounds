// src/components/dashboard/__tests__/widgets.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import PracticeReadiness from '../PracticeReadiness';
import type { TrackReadiness } from '../derive';
import BehavioralDepth from '../BehavioralDepth';
import type { BehavioralDepthResult } from '../derive';

const tracks: TrackReadiness[] = [
  { key: 'coding', name: 'Coding', to: '/coding/guide', color: 'var(--forest)', total: 40, mastered: 14, inProgress: 5 },
  { key: 'ai-coding', name: 'AI-Assisted Coding', to: '/ai-coding/guide', color: 'var(--ochre)', total: 8, mastered: 2, inProgress: 1 },
];

describe('PracticeReadiness', () => {
  it('renders a row per track with mastered/total', () => {
    render(<MemoryRouter><PracticeReadiness tracks={tracks} /></MemoryRouter>);
    expect(screen.getByText('Coding')).toBeInTheDocument();
    expect(screen.getByText('AI-Assisted Coding')).toBeInTheDocument();
    expect(screen.getByText('14/40')).toBeInTheDocument();
  });
});

const depth: BehavioralDepthResult = {
  covered: 11, total: 18, storyCount: 9, categoryCount: 6,
  thinCategories: [{ id: 'c1', name: 'Conflict', count: 0 }, { id: 'c2', name: 'Failure', count: 1 }],
};

describe('BehavioralDepth', () => {
  it('shows question coverage and thin categories', () => {
    render(<MemoryRouter><BehavioralDepth depth={depth} /></MemoryRouter>);
    expect(screen.getByText(/11/)).toBeInTheDocument();
    expect(screen.getByText('Conflict · 0')).toBeInTheDocument();
  });
});
