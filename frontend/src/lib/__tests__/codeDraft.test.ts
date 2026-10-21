import { describe, it, expect, beforeEach } from 'vitest';
import { loadLocal, localIsNewer, markLocalNewer, saveLocal } from '../codeDraft';

describe('codeDraft local storage', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('round-trips a draft per (user, question, language)', () => {
    saveLocal('u1', 10, 'python', 'print(1)');
    saveLocal('u1', 10, 'javascript', 'console.log(1)');
    saveLocal('u2', 10, 'python', 'print(2)');

    expect(loadLocal('u1', 10, 'python')).toBe('print(1)');
    expect(loadLocal('u1', 10, 'javascript')).toBe('console.log(1)');
    expect(loadLocal('u2', 10, 'python')).toBe('print(2)');
    expect(loadLocal('u1', 11, 'python')).toBeNull();
  });

  it('returns null when no draft exists', () => {
    expect(loadLocal('u1', 10, 'python')).toBeNull();
  });

  it('marks a local copy newer than the saved draft per (user, question, language)', () => {
    expect(localIsNewer('u1', 10, 'python')).toBe(false);
    markLocalNewer('u1', 10, 'python', true);
    expect(localIsNewer('u1', 10, 'python')).toBe(true);
    expect(localIsNewer('u1', 10, 'javascript')).toBe(false);
    expect(localIsNewer('u2', 10, 'python')).toBe(false);
    markLocalNewer('u1', 10, 'python', false);
    expect(localIsNewer('u1', 10, 'python')).toBe(false);
  });

  it('treats null userId as guest bucket', () => {
    saveLocal(null, 10, 'python', 'guest code');
    expect(loadLocal(null, 10, 'python')).toBe('guest code');
    expect(loadLocal('u1', 10, 'python')).toBeNull();
  });
});
