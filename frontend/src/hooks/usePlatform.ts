// OS detection for shortcut display.
//
// macOS users expect ⌘ for the primary modifier; Linux/Windows users
// expect Ctrl. We pick the symbol once at first call and cache it —
// the underlying platform doesn't change mid-session. Same module is
// imported by AppHeader's ⌘K pill, the Command Center hint, and any
// in-app shortcut chip.

import { useEffect, useState } from 'react';

function detectIsMac(): boolean {
  if (typeof navigator === 'undefined') return false;
  // userAgentData is the modern API; userAgent is the fallback. Both
  // expose enough to distinguish macOS reliably for shortcut display.
  const platform =
    (navigator as Navigator & { userAgentData?: { platform?: string } }).userAgentData?.platform ??
    navigator.platform ??
    navigator.userAgent;
  return /Mac|iPhone|iPad|iPod/i.test(platform);
}

export function getModifierSymbol(): string {
  return detectIsMac() ? '⌘' : 'Ctrl';
}

export function getModifierLabel(): string {
  // Spoken/aria form. Use a hyphen so screen readers say "Control K"
  // not "Control space K".
  return detectIsMac() ? 'Cmd' : 'Ctrl';
}

export function usePlatform() {
  const [isMac, setIsMac] = useState(false);
  useEffect(() => {
    setIsMac(detectIsMac());
  }, []);
  return {
    isMac,
    modifierSymbol: isMac ? '⌘' : 'Ctrl',
    modifierLabel: isMac ? 'Cmd' : 'Ctrl',
  };
}
