import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import {
  CommandCenterProvider,
  useCommandCenter,
} from '../../../command-center/CommandCenterProvider';
import AppHeader from '../AppHeader';

function Probe() {
  const cc = useCommandCenter();
  return (
    <div data-testid="cc-state">
      {cc.isOpen ? `open:${cc.viewId ?? 'hub'}` : 'closed'}
    </div>
  );
}

function renderHeader(props: Parameters<typeof AppHeader>[0]) {
  return render(
    <MemoryRouter>
      <CommandCenterProvider>
        <AppHeader {...props} />
        <Probe />
      </CommandCenterProvider>
    </MemoryRouter>,
  );
}

describe('AppHeader', () => {
  beforeEach(() => {
    localStorage.clear();
    // Default: desktop width — matchMedia("(max-width: 640px)") returns false.
    window.matchMedia = ((q: string) => ({
      matches: false,
      media: q,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
  });

  it('renders the title', () => {
    renderHeader({ title: 'Coding' });
    expect(screen.getByRole('heading', { name: 'Coding' })).toBeInTheDocument();
  });

  it('renders eyebrow and description when provided', () => {
    renderHeader({
      title: 'Coding',
      eyebrow: <span>Track 02</span>,
      description: 'Practice patterns.',
    });
    expect(screen.getByText('Track 02')).toBeInTheDocument();
    expect(screen.getByText('Practice patterns.')).toBeInTheDocument();
  });

  it('auto-appends a Command Center button that opens the modal', () => {
    renderHeader({ title: 'Anything' });
    fireEvent.click(screen.getByLabelText(/open command center/i));
    expect(screen.getByTestId('cc-state').textContent).toBe('open:hub');
  });

  it('renders page-specific actions to the left of the CC button', () => {
    renderHeader({
      title: 'X',
      actions: <button>Edit</button>,
    });
    expect(screen.getByText('Edit')).toBeInTheDocument();
    expect(screen.getByLabelText(/open command center/i)).toBeInTheDocument();
  });

  it('focus-mode toggle hides eyebrow and description and persists', () => {
    renderHeader({
      title: 'X',
      eyebrow: <span>EB</span>,
      description: 'desc',
    });
    expect(screen.getByText('EB')).toBeInTheDocument();
    expect(screen.getByText('desc')).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/focus mode|minimize header/i));
    expect(screen.queryByText('EB')).not.toBeInTheDocument();
    expect(screen.queryByText('desc')).not.toBeInTheDocument();
    expect(localStorage.getItem('rounds:header-minimal')).toBe('true');
  });

  it('reads minimal mode from localStorage on mount', () => {
    localStorage.setItem('rounds:header-minimal', 'true');
    renderHeader({
      title: 'X',
      eyebrow: <span>EB</span>,
      description: 'desc',
    });
    expect(screen.queryByText('EB')).not.toBeInTheDocument();
    expect(screen.queryByText('desc')).not.toBeInTheDocument();
  });

  it('renders compactActions in place of actions when minimal', () => {
    localStorage.setItem('rounds:header-minimal', 'true');
    renderHeader({
      title: 'X',
      actions: <button>full-pill</button>,
      compactActions: <button>tiny-glyph</button>,
    });
    expect(screen.queryByText('full-pill')).not.toBeInTheDocument();
    expect(screen.getByText('tiny-glyph')).toBeInTheDocument();
  });

  it('renders actions and not compactActions in expanded mode', () => {
    renderHeader({
      title: 'X',
      actions: <button>full-pill</button>,
      compactActions: <button>tiny-glyph</button>,
    });
    expect(screen.getByText('full-pill')).toBeInTheDocument();
    expect(screen.queryByText('tiny-glyph')).not.toBeInTheDocument();
  });

  it('mobile viewport (< 640px) auto-collapses to minimal', () => {
    window.matchMedia = ((q: string) => ({
      matches: q.includes('640'),
      media: q,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    })) as unknown as typeof window.matchMedia;
    renderHeader({
      title: 'X',
      eyebrow: <span>EB</span>,
      description: 'desc',
    });
    expect(screen.queryByText('EB')).not.toBeInTheDocument();
    expect(screen.queryByText('desc')).not.toBeInTheDocument();
  });
});
