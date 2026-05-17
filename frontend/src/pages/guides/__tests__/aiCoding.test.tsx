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
          <Route path="/ai-coding/guide"        element={<GuidePage track="ai-coding" />} />
          <Route path="/ai-coding/guide/:slug"  element={<GuidePage track="ai-coding" />} />
        </Routes>
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  Element.prototype.scrollTo = vi.fn();
});

describe('ai-coding guide pages', () => {
  it('dashboard renders the flavor matrix and pact', () => {
    renderAt('/ai-coding/guide');
    // whatThisTests is unique body text not in nav
    expect(screen.getByText('Judgment about AI output, not raw coding throughput.')).toBeInTheDocument();
  });

  it('mental model renders the trust-verify stages', () => {
    renderAt('/ai-coding/guide/mental-model');
    // stage name from trustVerifyStages — unique body content
    expect(screen.getByText(/Verify against intent/i)).toBeInTheDocument();
  });

  it('cheatsheet renders a policy-mode expectation', () => {
    renderAt('/ai-coding/guide/cheatsheet');
    // expectation text unique to policy-modes body content (not a nav label)
    expect(screen.getByText(/Pure algorithmic and implementation skill/i)).toBeInTheDocument();
  });

  it('prompt playbook renders the anatomy boxes', () => {
    renderAt('/ai-coding/guide/prompt-playbook');
    // anatomy label "Return shape" plus its body what text
    expect(screen.getByText('Return shape')).toBeInTheDocument();
    // template label unique to body
    expect(screen.getByText('Spec / Prompt-Spec')).toBeInTheDocument();
  });

  it('review habits renders the defects gallery and defense scripts', () => {
    renderAt('/ai-coding/guide/review-habits');
    // defect name from defects array — unique body content
    expect(screen.getByText('Phantom import')).toBeInTheDocument();
    // defense script opener — unique body content
    expect(screen.getByText(/I changed it because the AI/i)).toBeInTheDocument();
  });

  it('companies renders the table with Meta and its policy', () => {
    renderAt('/ai-coding/guide/companies');
    // company name in the table
    expect(screen.getByText('Meta')).toBeInTheDocument();
    // Shopify is also in the table
    expect(screen.getByText('Shopify')).toBeInTheDocument();
    // leanInto text unique to Meta row body
    expect(screen.getByText(/Treat the AI like a junior pair/i)).toBeInTheDocument();
  });
});
