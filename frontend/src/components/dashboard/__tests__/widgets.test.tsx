// src/components/dashboard/__tests__/widgets.test.tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import PracticeReadiness from '../PracticeReadiness';
import type { TrackReadiness } from '../derive';

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
