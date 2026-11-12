// A window.matchMedia for a phone: it matches the narrow-screen query the
// practice pages place their runner notice by, and nothing else, as a
// 390 px screen would. Tests restore the setup's own matchMedia after.

import { vi } from 'vitest';
import { NARROW_SCREEN_QUERY } from '../hooks/useMediaQuery';

export function phoneWidth(): typeof window.matchMedia {
  return vi.fn().mockImplementation((query: string) => ({
    matches: query === NARROW_SCREEN_QUERY,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}
