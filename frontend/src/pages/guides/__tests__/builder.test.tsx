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
          <Route path="/builder/guide"        element={<GuidePage track="builder" />} />
          <Route path="/builder/guide/:slug"  element={<GuidePage track="builder" />} />
          <Route path="/take-home/guide"      element={<GuidePage track="take-home" />} />
        </Routes>
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  Element.prototype.scrollTo = vi.fn();
});

describe('builder guide pages', () => {
  it('dashboard renders the flavor matrix and submission pact', () => {
    renderAt('/builder/guide');
    // submissionPact body — only renders on the dashboard
    expect(
      screen.getByText(/A working, well-documented 80% solution beats an over-engineered 100%/i),
    ).toBeInTheDocument();
  });

  it('mental-model renders the ship-means cards', () => {
    renderAt('/builder/guide/mental-model');
    // mentalModel.shipMeans[0] — unique body content for this page
    expect(
      screen.getByText(/Clones and runs in under 2 minutes from a fresh terminal/i),
    ).toBeInTheDocument();
  });

  it('cheatsheet renders the AI policy move for candidate-choice', () => {
    renderAt('/builder/guide/cheatsheet');
    // aiPolicyMoves candidate-choice "behave" text — unique body content
    expect(
      screen.getByText(/Use AI deliberately and own the output/i),
    ).toBeInTheDocument();
  });

  it('time-plan renders the active plan whatSlipsFirst', () => {
    renderAt('/builder/guide/time-plan');
    // The active preset defaults to '1 week' (w1). The w1 whatSlipsFirst contains this phrase.
    expect(
      screen.getByText(/Premature abstraction/i),
    ).toBeInTheDocument();
  });

  it('submission renders a commit-hygiene line', () => {
    renderAt('/builder/guide/submission');
    // commitHygiene[0] — unique body content for this page
    expect(
      screen.getByText(/Small, focused commits — one logical change per commit/i),
    ).toBeInTheDocument();
  });

  it('domain-cheats renders a primer domain name', () => {
    renderAt('/builder/guide/domain-cheats');
    // primer.domain[0] — unique body content for this page
    expect(screen.getByText('Shopping cart pricing engine')).toBeInTheDocument();
  });

  it('redirects /take-home/guide to /builder/guide', () => {
    renderAt('/take-home/guide');
    // After redirect, the dashboard renders. Assert on dashboard-only body content.
    expect(
      screen.getByText(/A working, well-documented 80% solution beats an over-engineered 100%/i),
    ).toBeInTheDocument();
  });
});
