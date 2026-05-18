import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

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
import { MemoryRouter } from 'react-router-dom';
import { createRef } from 'react';
import { CommandCenterProvider } from '../../../command-center/CommandCenterProvider';
import CodeKit from '../coding/pages/CodeKit';
import { TRACK_CONFIGS } from '../guideTypes';
import { codingNavGroups } from '../coding/nav';

const STORAGE_KEY = 'rounds:guide:coding:language';

function renderPage() {
  return render(
    <MemoryRouter>
      <CommandCenterProvider>
        <CodeKit
          config={TRACK_CONFIGS.coding}
          navGroups={codingNavGroups}
          scrollRef={createRef<HTMLDivElement>()}
        />
      </CommandCenterProvider>
    </MemoryRouter>
  );
}

describe('CodeKit language tab', () => {
  beforeEach(() => {
    window.localStorage.removeItem(STORAGE_KEY);
  });

  it('defaults to Python', () => {
    renderPage();
    expect(screen.getByRole('tab', { name: 'Python', selected: true })).toBeInTheDocument();
  });

  it('persists the selection to localStorage', () => {
    renderPage();
    fireEvent.click(screen.getByRole('tab', { name: 'JavaScript' }));
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('javascript');
  });

  it('hydrates from localStorage on mount', () => {
    window.localStorage.setItem(STORAGE_KEY, 'java');
    renderPage();
    expect(screen.getByRole('tab', { name: 'Java', selected: true })).toBeInTheDocument();
  });
});
