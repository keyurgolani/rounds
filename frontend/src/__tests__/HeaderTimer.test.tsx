import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { formatTimer } from '../components/shell/HeaderTimer';
import HeaderTimer from '../components/shell/HeaderTimer';

vi.mock('../hooks/useQuestionTimer', () => ({
  useQuestionTimer: vi.fn(),
}));

import { useQuestionTimer } from '../hooks/useQuestionTimer';

describe('formatTimer', () => {
  it('formats sub-hour times as MM:SS', () => {
    expect(formatTimer(0)).toBe('00:00');
    expect(formatTimer(1000)).toBe('00:01');
    expect(formatTimer(60_000)).toBe('01:00');
    expect(formatTimer(59 * 60_000 + 59 * 1000)).toBe('59:59');
  });

  it('switches to H:MM:SS once over an hour', () => {
    expect(formatTimer(3600 * 1000)).toBe('1:00:00');
    expect(formatTimer(3661 * 1000)).toBe('1:01:01');
    expect(formatTimer(10 * 3600 * 1000 + 5 * 60_000 + 7 * 1000)).toBe('10:05:07');
  });

  it('clamps negatives to zero', () => {
    expect(formatTimer(-100)).toBe('00:00');
  });
});

describe('HeaderTimer', () => {
  beforeEach(() => {
    (useQuestionTimer as unknown as { mockReset: () => void }).mockReset();
  });

  it('renders a loading placeholder while ready=false', () => {
    (useQuestionTimer as unknown as { mockReturnValue: (v: unknown) => void }).mockReturnValue({
      displayMs: 0, running: false, ready: false, toggle: () => {}, reset: () => {},
    });
    render(<HeaderTimer kind="coding" id={1} />);
    expect(screen.getByText('--:--')).toBeInTheDocument();
  });

  it('renders MM:SS for paused state and Play icon', () => {
    (useQuestionTimer as unknown as { mockReturnValue: (v: unknown) => void }).mockReturnValue({
      displayMs: 90_000, running: false, ready: true, toggle: () => {}, reset: () => {},
    });
    render(<HeaderTimer kind="coding" id={1} />);
    expect(screen.getByText('01:30')).toBeInTheDocument();
    const btn = screen.getByRole('button');
    expect(btn).toHaveAttribute('aria-label', expect.stringContaining('paused'));
  });

  it('toggle on plain click, reset on shift-click', () => {
    const toggle = vi.fn();
    const reset = vi.fn();
    (useQuestionTimer as unknown as { mockReturnValue: (v: unknown) => void }).mockReturnValue({
      displayMs: 0, running: false, ready: true, toggle, reset,
    });
    render(<HeaderTimer kind="coding" id={1} />);
    const btn = screen.getByRole('button');
    fireEvent.click(btn);
    expect(toggle).toHaveBeenCalledTimes(1);
    expect(reset).not.toHaveBeenCalled();
    act(() => {
      fireEvent.click(btn, { shiftKey: true });
    });
    expect(reset).toHaveBeenCalledTimes(1);
  });

  it('right-click resets and prevents default', () => {
    const toggle = vi.fn();
    const reset = vi.fn();
    (useQuestionTimer as unknown as { mockReturnValue: (v: unknown) => void }).mockReturnValue({
      displayMs: 0, running: true, ready: true, toggle, reset,
    });
    render(<HeaderTimer kind="coding" id={1} />);
    fireEvent.contextMenu(screen.getByRole('button'));
    expect(reset).toHaveBeenCalled();
    expect(toggle).not.toHaveBeenCalled();
  });
});
