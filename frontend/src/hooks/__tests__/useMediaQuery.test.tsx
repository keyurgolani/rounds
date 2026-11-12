// useMediaQuery: whether a media query matches, kept current as the
// window changes, and false where there's no matchMedia.

import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { NARROW_SCREEN_QUERY, useMediaQuery } from '../useMediaQuery';

const original = window.matchMedia;

afterEach(() => {
  window.matchMedia = original;
});

function mediaList(matches: boolean) {
  const listeners = new Set<(e: MediaQueryListEvent) => void>();
  const list = {
    matches,
    media: NARROW_SCREEN_QUERY,
    addEventListener: vi.fn((_type: string, listener: (e: MediaQueryListEvent) => void) => listeners.add(listener)),
    removeEventListener: vi.fn((_type: string, listener: (e: MediaQueryListEvent) => void) => listeners.delete(listener)),
    change(next: boolean) {
      list.matches = next;
      for (const listener of listeners) listener({ matches: next } as MediaQueryListEvent);
    },
    listeners,
  };
  window.matchMedia = vi.fn(() => list) as unknown as typeof window.matchMedia;
  return list;
}

describe('useMediaQuery', () => {
  it('starts with what the query matches now', () => {
    mediaList(true);
    const { result } = renderHook(() => useMediaQuery(NARROW_SCREEN_QUERY));
    expect(result.current).toBe(true);
    expect(window.matchMedia).toHaveBeenCalledWith(NARROW_SCREEN_QUERY);
  });

  it('follows the query as the window narrows and widens, and stops listening once gone', () => {
    const list = mediaList(false);
    const { result, unmount } = renderHook(() => useMediaQuery(NARROW_SCREEN_QUERY));
    expect(result.current).toBe(false);
    act(() => list.change(true));
    expect(result.current).toBe(true);
    act(() => list.change(false));
    expect(result.current).toBe(false);
    unmount();
    expect(list.listeners.size).toBe(0);
  });

  it('is false where the window has no matchMedia', () => {
    window.matchMedia = undefined as unknown as typeof window.matchMedia;
    const { result } = renderHook(() => useMediaQuery(NARROW_SCREEN_QUERY));
    expect(result.current).toBe(false);
  });
});
