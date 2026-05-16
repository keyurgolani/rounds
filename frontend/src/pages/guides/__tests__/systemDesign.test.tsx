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
          <Route path="/system-design/guide"        element={<GuidePage track="system-design" />} />
          <Route path="/system-design/guide/:slug"  element={<GuidePage track="system-design" />} />
        </Routes>
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

describe('system design guide pages', () => {
  beforeEach(() => {
    Element.prototype.scrollTo = vi.fn();
  });

  it('dashboard renders title + timeline phases + pressure menu', () => {
    renderAt('/system-design/guide');
    expect(screen.getByText(/System Design Interview Field Guide/i)).toBeInTheDocument();
    expect(screen.getAllByText('Requirements').length).toBeGreaterThan(0);
    expect(screen.getByText('Users')).toBeInTheDocument();
    expect(screen.getByText('QPS')).toBeInTheDocument();
  });

  it('mental model renders the forces-to-components heading', () => {
    renderAt('/system-design/guide/mental-model');
    expect(screen.getByText(/Pressure before components/i)).toBeInTheDocument();
  });

  it('cheatsheet renders decision-deck triggers', () => {
    renderAt('/system-design/guide/cheatsheet');
    expect(screen.getByText(/read pressure or expensive recompute/i)).toBeInTheDocument();
  });

  it('round-flow renders phase labels', () => {
    renderAt('/system-design/guide/round-flow');
    expect(screen.getAllByText('Requirements').length).toBeGreaterThan(0);
    expect(screen.getByText('Close')).toBeInTheDocument();
  });

  it('capacity-math renders inputs and outputs labels', () => {
    renderAt('/system-design/guide/capacity-math');
    expect(screen.getByText('Daily Active Users')).toBeInTheDocument();
    expect(screen.getAllByText('Avg QPS').length).toBeGreaterThan(0);
  });

  it('building-blocks renders storage rows', () => {
    renderAt('/system-design/guide/building-blocks');
    expect(screen.getByText('Relational')).toBeInTheDocument();
    expect(screen.getByText('Graph')).toBeInTheDocument();
  });

  it('reliability renders failure rows', () => {
    renderAt('/system-design/guide/reliability');
    expect(screen.getByText('Duplicate write')).toBeInTheDocument();
    expect(screen.getByText('Hot key')).toBeInTheDocument();
  });
});
