// Browser keys that hold what a visitor types in the resume studio's ATS
// and Tailor tabs (ROUNDS-00B-L07). While the demo account is signed in,
// they live under a demo-only prefix, whatever resume they name, untitled
// included. Every demo sign-out the SPA runs, and any start without a demo
// session, clears that prefix, so one visitor's job text never waits in a
// shared browser for the next one. Other accounts keep their own keys.

export const DEMO_KEY_PREFIX = 'rounds.demo.';

/** `key` as the demo account keeps it: under the demo-only prefix. Other
 *  accounts keep `key` as it is. */
export function localKey(key: string, isDemo: boolean): string {
  if (!isDemo) return key;
  return DEMO_KEY_PREFIX + (key.startsWith('rounds.') ? key.slice('rounds.'.length) : key);
}

function local(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.localStorage;
  } catch {
    return null;
  }
}

/** Removes every key under the demo-only prefix. */
export function clearDemoKeys(storage: Storage | null = local()): void {
  if (!storage) return;
  try {
    const keys: string[] = [];
    for (let i = 0; i < storage.length; i += 1) {
      const key = storage.key(i);
      if (key && key.startsWith(DEMO_KEY_PREFIX)) keys.push(key);
    }
    for (const key of keys) storage.removeItem(key);
  } catch {
    /* storage may be unavailable */
  }
}
