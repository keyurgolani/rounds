// Local-only code draft cache. Remote sync (PocketBase) lands in a later
// commit when the frontend data layer is switched over — for now this is
// enough for the Monaco editor's 10-second autosave cadence.

const keyFor = (userId: string | null, questionId: number, language: string) =>
  `rounds.codeDraft.v1:${userId ?? 'guest'}:${questionId}:${language}`;

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
