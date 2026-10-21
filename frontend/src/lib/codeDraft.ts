// Local-only code draft cache. Remote sync (PocketBase) lands in a later
// commit when the frontend data layer is switched over — for now this is
// enough for the Monaco editor's 10-second autosave cadence.

const keyFor = (userId: string | null, questionId: number, language: string) =>
  `rounds.codeDraft.v1:${userId ?? 'guest'}:${questionId}:${language}`;

// Set when the local copy is newer than PocketBase's draft: a save
// before a reload failed. Cleared once a save lands.
const newerKeyFor = (userId: string | null, questionId: number, language: string) =>
  `rounds.codeDraft.newer.v1:${userId ?? 'guest'}:${questionId}:${language}`;

export function loadLocal(userId: string | null, questionId: number, language: string): string | null {
  try {
    return localStorage.getItem(keyFor(userId, questionId, language));
  } catch {
    return null;
  }
}

export function saveLocal(userId: string | null, questionId: number, language: string, code: string): void {
  try {
    localStorage.setItem(keyFor(userId, questionId, language), code);
  } catch {
    /* noop */
  }
}

/** Marks the local copy as newer than the saved draft, or clears it. */
export function markLocalNewer(userId: string | null, questionId: number, language: string, newer: boolean): void {
  try {
    if (newer) localStorage.setItem(newerKeyFor(userId, questionId, language), '1');
    else localStorage.removeItem(newerKeyFor(userId, questionId, language));
  } catch {
    /* noop */
  }
}

export function localIsNewer(userId: string | null, questionId: number, language: string): boolean {
  try {
    return localStorage.getItem(newerKeyFor(userId, questionId, language)) === '1';
  } catch {
    return false;
  }
}
