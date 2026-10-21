// Which saved drafts an AI-coding workspace restores (ROUNDS-00A-L02).

import { describe, expect, it, vi } from 'vitest';

vi.mock('../../lib/pocketbase', () => ({ pb: { authStore: { token: 'test-token-placeholder' } } }));

import { draftPathFilter, isProjectPath, type AICodingRoundRaw } from '../../pages/ai-coding/aiCodingApi';

function round(starter: AICodingRoundRaw['starter_files'], checkpoints: AICodingRoundRaw['checkpoints']): AICodingRoundRaw {
  return {
    id: 'round0000000001',
    slug: 'r',
    title: 'R',
    difficulty: 'easy',
    language: 'python',
    description: '',
    starter_files: starter,
    checkpoints,
    rubric: { items: [] },
    topics: [],
    companies: [],
  };
}

describe('isProjectPath', () => {
  it.each(['client.py', 'lib/helpers.py', 'tests/checkpoint_0/test_visible.py', 'a'.repeat(255)])('takes %s', (path) => {
    expect(isProjectPath(path)).toBe(true);
  });

  it.each(['', '/etc/passwd', '../x.py', 'a/../b.py', 'a//b.py', './a.py', 'a\\b.py', 'a\0b', 'a'.repeat(256)])(
    'refuses %j',
    (path) => {
      expect(isProjectPath(path)).toBe(false);
    },
  );
});

describe('draftPathFilter', () => {
  it('keeps every project path on a single-language round', () => {
    const keep = draftPathFilter(round([{ path: 'client.py', contents: '' }], []), 'python');
    expect(['client.py', 'helpers.py', 'utils.ts', 'notes.md'].filter(keep)).toEqual([
      'client.py',
      'helpers.py',
      'utils.ts',
      'notes.md',
    ]);
    expect(keep('../outside.py')).toBe(false);
  });

  it("keeps a language's own and created files, and none of another language's", () => {
    const raw = round(
      {
        python: [{ path: 'client.py', contents: '' }],
        typescript: [
          { path: 'client.ts', contents: '' },
          { path: 'package.json', contents: '' },
        ],
      },
      { python: [], typescript: [] },
    );
    const paths = ['client.py', 'helpers.py', 'stubs.pyi', 'client.ts', 'utils.tsx', 'package.json', 'notes.md', 'Makefile'];
    expect(paths.filter(draftPathFilter(raw, 'python'))).toEqual(['client.py', 'helpers.py', 'stubs.pyi', 'notes.md', 'Makefile']);
    expect(paths.filter(draftPathFilter(raw, 'typescript'))).toEqual(['client.ts', 'utils.tsx', 'package.json', 'notes.md', 'Makefile']);
  });
});
