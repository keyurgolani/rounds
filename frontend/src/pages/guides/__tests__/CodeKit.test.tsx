import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
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
    expect(screen.getByRole('button', { name: 'Python', pressed: true })).toBeInTheDocument();
  });

  it('persists the selection to localStorage', () => {
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: 'JavaScript' }));
    expect(window.localStorage.getItem(STORAGE_KEY)).toBe('javascript');
  });

  it('hydrates from localStorage on mount', () => {
    window.localStorage.setItem(STORAGE_KEY, 'java');
    renderPage();
    expect(screen.getByRole('button', { name: 'Java', pressed: true })).toBeInTheDocument();
  });
});
