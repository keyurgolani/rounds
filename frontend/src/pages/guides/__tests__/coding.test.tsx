import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import { CommandCenterProvider } from '../../../command-center/CommandCenterProvider';
import GuidePage from '../GuidePage';

function renderAt(path: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <CommandCenterProvider>
        <Routes>
          <Route path="/coding/guide"        element={<GuidePage track="coding" />} />
          <Route path="/coding/guide/:slug"  element={<GuidePage track="coding" />} />
        </Routes>
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  Element.prototype.scrollTo = vi.fn();
});

describe('coding guide pages', () => {
  it('dashboard renders the round-script timeline', () => {
    renderAt('/coding/guide');
    expect(screen.getByText(/Coding Interview Field Guide/i)).toBeInTheDocument();
    expect(screen.getByText('Restate')).toBeInTheDocument();
    expect(screen.getByText('Prove')).toBeInTheDocument();
  });

  it('mental model renders the invariant loop heading and state examples', () => {
    renderAt('/coding/guide/mental-model');
    expect(screen.getByText(/Invariant first/i)).toBeInTheDocument();
    expect(screen.getByText('Sliding Window')).toBeInTheDocument();
  });

  it('cheatsheet renders the family filter pills', () => {
    renderAt('/coding/guide/cheatsheet');
    expect(screen.getByRole('button', { name: 'All' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'DP' })).toBeInTheDocument();
  });

  it('code kit renders language tabs and at least one shelf', () => {
    renderAt('/coding/guide/code-kit');
    expect(screen.getByRole('button', { name: 'Python', pressed: true })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'JavaScript' })).toBeInTheDocument();
    expect(screen.getByText('ArrayToolkit')).toBeInTheDocument();
  });

  it('patterns renders pattern cards including the binary search variant', () => {
    renderAt('/coding/guide/patterns');
    expect(screen.getByText('Two Pointers')).toBeInTheDocument();
    expect(screen.getByText('Binary Search on the Answer')).toBeInTheDocument();
  });

  it('complexity renders the compass with pass/warn/fail cells', () => {
    renderAt('/coding/guide/complexity');
    expect(screen.getByText('Complexity Compass')).toBeInTheDocument();
    // CSS text-transform:uppercase is not applied by jsdom; match the raw lowercase value
    expect(screen.getAllByText(/^pass$/i).length).toBeGreaterThan(0);
  });
});
