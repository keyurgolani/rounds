import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { CommandCenterProvider } from '../../../command-center/CommandCenterProvider';
import GuidePage from '../GuidePage';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <CommandCenterProvider>
        <Routes>
          <Route path="/behavioral/guide"        element={<GuidePage track="behavioral" />} />
          <Route path="/behavioral/guide/:slug"  element={<GuidePage track="behavioral" />} />
        </Routes>
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

describe('behavioral guide pages', () => {
  beforeEach(() => {
    Element.prototype.scrollTo = vi.fn();
  });

  it('dashboard renders STAR(R) strip and signal grid', () => {
    renderAt('/behavioral/guide');
    expect(screen.getByText(/Behavioral Interview Field Guide/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Situation/).length).toBeGreaterThan(0);
    expect(screen.getByText('Impact')).toBeInTheDocument();
    expect(screen.getByText('Ownership')).toBeInTheDocument();
  });

  it('mental model renders the signal decoder table', () => {
    renderAt('/behavioral/guide/mental-model');
    expect(screen.getAllByText(/Evidence beats adjectives/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Tell me about a failure/)).toBeInTheDocument();
  });

  it('cheatsheet renders the 8-card question deck', () => {
    renderAt('/behavioral/guide/cheatsheet');
    expect(screen.getByText(/Eight openers/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Tell me about/).length).toBeGreaterThanOrEqual(7);
  });

  it('story bank renders 8 signal cards', () => {
    renderAt('/behavioral/guide/story-bank');
    expect(screen.getByText(/Eight signals/i)).toBeInTheDocument();
    expect(screen.getByText('Customer focus')).toBeInTheDocument();
  });

  it('senior scope renders the 4-tier ladder', () => {
    renderAt('/behavioral/guide/senior-scope');
    expect(screen.getByText('Mid-level')).toBeInTheDocument();
    expect(screen.getByText('Principal')).toBeInTheDocument();
  });

  it('repair renders rewrites + scorecard', () => {
    renderAt('/behavioral/guide/repair');
    expect(screen.getByText(/We improved performance/)).toBeInTheDocument();
    expect(screen.getByText(/Specificity/)).toBeInTheDocument();
  });
});
