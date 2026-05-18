import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

// Stub the MultiFileEditor (and indirectly Monaco). The real editor +
// FileExplorer hang jsdom on mount.
vi.mock('../../../components/editor/MultiFileEditor', () => ({
  default: ({ activePath, files }: { activePath: string; files: Record<string, string> }) => (
    <div data-testid="mock-multi-file-editor">
      <span data-testid="active-path">{activePath}</span>
      <pre>{files[activePath] ?? ''}</pre>
    </div>
  ),
}));
import { CommandCenterProvider } from '../../../command-center/CommandCenterProvider';
import GuidePage from '../GuidePage';
import type { GuideTrack } from '../guideTypes';

beforeEach(() => {
  Element.prototype.scrollTo = vi.fn();
});

function renderGuide(
  track: GuideTrack,
  basePath: string,
  initialEntry: string,
) {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <CommandCenterProvider>
        <Routes>
          <Route path={basePath} element={<GuidePage track={track} />} />
          <Route path={`${basePath}/:slug`} element={<GuidePage track={track} />} />
        </Routes>
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

describe('GuidePage track routing', () => {
  it.each([
    ['coding',        '/coding/guide',        /Coding Interview Field Guide/i],
    ['system-design', '/system-design/guide', /System Design Interview Field Guide/i],
    ['behavioral',    '/behavioral/guide',    /Behavioral Interview Field Guide/i],
  ] as const)('renders the %s dashboard at %s', (track, path, expected) => {
    renderGuide(track, path, path);
    expect(screen.getByText(expected)).toBeInTheDocument();
  });

  it.each([
    ['coding',        '/coding/guide',        '/coding/guide/not-a-real-slug',        /Coding Interview Field Guide/i],
    ['system-design', '/system-design/guide', '/system-design/guide/not-a-real-slug', /System Design Interview Field Guide/i],
    ['behavioral',    '/behavioral/guide',    '/behavioral/guide/not-a-real-slug',    /Behavioral Interview Field Guide/i],
  ] as const)('falls back to dashboard when %s slug is unknown', (track, base, full, expected) => {
    renderGuide(track, base, full);
    expect(screen.getByText(expected)).toBeInTheDocument();
  });
});

describe('GuidePage legacy slug redirects', () => {
  // Each row: track, base path, legacy slug URL, marker assertion that's unique to the redirect destination.
  it.each([
    // coding (4)
    ['coding',        '/coding/guide',        '/coding/guide/interview-strategy',   () => expect(screen.getByRole('button', { name: 'All' })).toBeInTheDocument()],
    ['coding',        '/coding/guide',        '/coding/guide/pattern-playbook',     () => expect(screen.getByText('Pattern Playbook')).toBeInTheDocument()],
    ['coding',        '/coding/guide',        '/coding/guide/optimization-testing', () => expect(screen.getByText('Complexity Compass')).toBeInTheDocument()],
    ['coding',        '/coding/guide',        '/coding/guide/practice-plan',        () => expect(screen.getByText('Pattern Playbook')).toBeInTheDocument()],
    // system-design (6) — assertions key on body text unique to the destination page
    ['system-design', '/system-design/guide', '/system-design/guide/interview-strategy',      () => expect(screen.getByText(/Useful lines for the round/i)).toBeInTheDocument()],
    ['system-design', '/system-design/guide', '/system-design/guide/requirements-estimation', () => expect(screen.getByText(/Tune the inputs/i)).toBeInTheDocument()],
    ['system-design', '/system-design/guide', '/system-design/guide/core-components',         () => expect(screen.getByText(/Pick storage from access pattern/i)).toBeInTheDocument()],
    ['system-design', '/system-design/guide', '/system-design/guide/data-storage',            () => expect(screen.getByText(/Pick storage from access pattern/i)).toBeInTheDocument()],
    ['system-design', '/system-design/guide', '/system-design/guide/tradeoffs-reliability',   () => expect(screen.getByText(/Pick the failure that hurts/i)).toBeInTheDocument()],
    ['system-design', '/system-design/guide', '/system-design/guide/practice-playbook',       () => expect(screen.getByText(/Useful lines for the round/i)).toBeInTheDocument()],
    // behavioral (4) — assertions key on body text unique to the destination page
    ['behavioral',    '/behavioral/guide',    '/behavioral/guide/story-crafting',    () => expect(screen.getByText(/Build your portfolio/i)).toBeInTheDocument()],
    ['behavioral',    '/behavioral/guide',    '/behavioral/guide/signal-rubric',     () => expect(screen.getByText(/Question opener → signal/i)).toBeInTheDocument()],
    ['behavioral',    '/behavioral/guide',    '/behavioral/guide/senior-behavioral', () => expect(screen.getByText(/Show scope in numbers/i)).toBeInTheDocument()],
    ['behavioral',    '/behavioral/guide',    '/behavioral/guide/practice-playbook', () => expect(screen.getByText(/Score yourself 1.{1,2}3/i)).toBeInTheDocument()],
  ] as const)('redirects %s legacy slug to its new destination (%s)', (track, base, full, assertion) => {
    renderGuide(track, base, full);
    assertion();
  });
});
