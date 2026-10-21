// AI-coding drafts (ROUNDS-00A-L02): saveNow saves every file the server
// hasn't confirmed, waiting out an autosave that's part way through its
// one-at-a-time saves, and hydration brings back the files the candidate
// created in this language.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';

vi.mock('../../pages/ai-coding/aiCodingApi', async (importOriginal) => ({
  ...((await importOriginal()) as Record<string, unknown>),
  listDrafts: vi.fn(),
  upsertDraft: vi.fn(),
  deleteAllDrafts: vi.fn(),
}));

import { useAICodingDrafts } from '../useAICodingDrafts';
import {
  listDrafts,
  resolveRound,
  upsertDraft,
  type AICodingRoundRaw,
  type DraftRow,
} from '../../pages/ai-coding/aiCodingApi';

const RAW: AICodingRoundRaw = {
  id: 'round0000000001',
  slug: 'hallucinated-http-client',
  title: 'Hallucinated HTTP client method',
  difficulty: 'easy',
  language: 'python',
  description: '',
  starter_files: {
    python: [
      { path: 'client.py', contents: 'starter py' },
      { path: 'tests/test_visible.py', contents: 'test py' },
    ],
    typescript: [
      { path: 'client.ts', contents: 'starter ts' },
      { path: 'package.json', contents: '{}' },
    ],
  },
  checkpoints: { python: [], typescript: [] },
  rubric: { items: [] },
  topics: [],
  companies: [],
};

function draft(path: string, contents: string): DraftRow {
  return { id: `d-${path}`, round: RAW.id, file_path: path, contents };
}

interface Pending {
  path: string;
  contents: string;
  resolve: () => void;
  reject: () => void;
}

let pending: Pending[];

beforeEach(() => {
  pending = [];
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] });
  vi.mocked(listDrafts).mockReset().mockResolvedValue([]);
  vi.mocked(upsertDraft)
    .mockReset()
    .mockImplementation(
      (input) =>
        new Promise<void>((resolve, reject) => {
          pending.push({ path: input.filePath, contents: input.contents, resolve: () => resolve(), reject: () => reject(new Error('offline')) });
        }),
    );
});

afterEach(() => {
  vi.useRealTimers();
});

// Every answer here is a promise the test settles, so flushing the
// microtask queue is enough; the autosave interval is the only timer.
async function settle() {
  for (let i = 0; i < 10; i += 1) {
    await act(async () => {
      await Promise.resolve();
    });
  }
}

async function hydrated(language = 'python') {
  const round = resolveRound(RAW, language);
  const hook = renderHook(() => useAICodingDrafts(round, 'campaign00000001', RAW));
  await settle();
  expect(hook.result.current.hydrated).toBe(true);
  return hook;
}

async function autosaveTick() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10_000);
  });
}

describe('useAICodingDrafts saveNow', () => {
  it('waits for an autosave part way through and saves the files it had not reached', async () => {
    const { result } = await hydrated();
    act(() => {
      result.current.setFile('client.py', 'mine');
      result.current.setFile('helpers.py', 'new file');
    });
    await autosaveTick();
    // The autosave saves one file at a time: the first is in flight.
    expect(pending.map((p) => p.path)).toEqual(['client.py']);

    let settled: boolean | null = null;
    let now!: Promise<void>;
    act(() => {
      now = result.current.saveNow().then((ok) => {
        settled = ok;
      });
    });
    await act(async () => {
      pending[0].resolve();
    });
    await settle();
    expect(pending).toHaveLength(2);
    expect(pending[1]).toMatchObject({ path: 'helpers.py', contents: 'new file' });
    expect(settled).toBeNull();
    await act(async () => {
      pending[1].resolve();
      await now;
    });
    expect(settled).toBe(true);
    expect(result.current.savedFiles).toMatchObject({ 'client.py': 'mine', 'helpers.py': 'new file' });
  });

  it('saves the latest contents of a file edited while the autosave saved it', async () => {
    const { result } = await hydrated();
    act(() => result.current.setFile('client.py', 'first'));
    await autosaveTick();
    act(() => result.current.setFile('client.py', 'second'));
    let now!: Promise<boolean>;
    act(() => {
      now = result.current.saveNow();
    });
    await act(async () => {
      pending[0].resolve();
    });
    await settle();
    expect(pending).toHaveLength(2);
    expect(pending[1]).toMatchObject({ path: 'client.py', contents: 'second' });
    await act(async () => {
      pending[1].resolve();
    });
    await expect(now).resolves.toBe(true);
  });

  it('saves a file whose autosave failed, and reports a save that fails again', async () => {
    const { result } = await hydrated();
    act(() => result.current.setFile('client.py', 'mine'));
    await autosaveTick();
    let now!: Promise<boolean>;
    act(() => {
      now = result.current.saveNow();
    });
    await act(async () => {
      pending[0].reject();
    });
    await settle();
    expect(pending).toHaveLength(2);
    expect(pending[1]).toMatchObject({ path: 'client.py', contents: 'mine' });
    await act(async () => {
      pending[1].reject();
    });
    await expect(now).resolves.toBe(false);
  });

  it('answers at once when the server has every file', async () => {
    const { result } = await hydrated();
    await expect(result.current.saveNow()).resolves.toBe(true);
    expect(upsertDraft).not.toHaveBeenCalled();
  });
});

describe('useAICodingDrafts hydration', () => {
  const drafts = [
    draft('client.py', 'edited py'),
    draft('helpers.py', 'created py'),
    draft('notes.md', 'notes'),
    draft('client.ts', 'edited ts'),
    draft('utils.ts', 'created ts'),
    draft('package.json', '{"edited": true}'),
    draft('../outside.py', 'x'),
  ];

  it("keeps the files the candidate created in this language and none of another language's", async () => {
    vi.mocked(listDrafts).mockResolvedValue(drafts);
    const { result } = await hydrated('python');
    expect(result.current.files).toEqual({
      'client.py': 'edited py',
      'tests/test_visible.py': 'test py',
      'helpers.py': 'created py',
      'notes.md': 'notes',
    });
  });

  it('keeps the other language its own files', async () => {
    vi.mocked(listDrafts).mockResolvedValue(drafts);
    const { result } = await hydrated('typescript');
    expect(result.current.files).toEqual({
      'client.ts': 'edited ts',
      'package.json': '{"edited": true}',
      'utils.ts': 'created ts',
      'notes.md': 'notes',
    });
  });
});
