import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
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

  it('renders MM:SS for paused state and surfaces a Resume aria-label', () => {
    (useQuestionTimer as unknown as { mockReturnValue: (v: unknown) => void }).mockReturnValue({
      displayMs: 90_000, running: false, ready: true, toggle: () => {}, reset: () => {},
    });
    render(<HeaderTimer kind="coding" id={1} />);
    expect(screen.getByText('01:30')).toBeInTheDocument();
    // With elapsed > 0 the impl renders TWO buttons (toggle + reset);
    // assert specifically against the toggle's aria-label rather than
    // a generic getByRole('button').
    const toggle = screen.getByRole('button', { name: /Resume question timer/i });
    expect(toggle).toBeInTheDocument();
  });

  it('clicking the toggle button calls toggle (no shift-key special case)', () => {
    const toggle = vi.fn();
    const reset = vi.fn();
    (useQuestionTimer as unknown as { mockReturnValue: (v: unknown) => void }).mockReturnValue({
      displayMs: 0, running: false, ready: true, toggle, reset,
    });
    render(<HeaderTimer kind="coding" id={1} />);
    // displayMs=0 → no reset button rendered, only the start toggle.
    fireEvent.click(screen.getByRole('button', { name: /Start question timer/i }));
    expect(toggle).toHaveBeenCalledTimes(1);
    expect(reset).not.toHaveBeenCalled();
  });

  it('clicking the reset button (visible once elapsed) calls reset', () => {
    const toggle = vi.fn();
    const reset = vi.fn();
    (useQuestionTimer as unknown as { mockReturnValue: (v: unknown) => void }).mockReturnValue({
      displayMs: 5000, running: true, ready: true, toggle, reset,
    });
    render(<HeaderTimer kind="coding" id={1} />);
    fireEvent.click(screen.getByRole('button', { name: /Reset question timer/i }));
    expect(reset).toHaveBeenCalledTimes(1);
    expect(toggle).not.toHaveBeenCalled();
  });
});
