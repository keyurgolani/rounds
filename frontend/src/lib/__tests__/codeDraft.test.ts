import { describe, it, expect, beforeEach } from 'vitest';
import { loadLocal, saveLocal } from '../codeDraft';

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

  it('treats null userId as guest bucket', () => {
    saveLocal(null, 10, 'python', 'guest code');
    expect(loadLocal(null, 10, 'python')).toBe('guest code');
    expect(loadLocal('u1', 10, 'python')).toBeNull();
  });
});
