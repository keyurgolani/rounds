// Take-home drafts (ROUNDS-00A-L02): saveNow saves every file the server
// hasn't confirmed, waiting out an autosave that's part way through its
// one-at-a-time saves.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';

vi.mock('../../pages/take-home/takeHomeApi', async (importOriginal) => ({
  ...((await importOriginal()) as Record<string, unknown>),
  listDrafts: vi.fn(),
  upsertDraft: vi.fn(),
  deleteAllDrafts: vi.fn(),
}));

import { useTakeHomeDrafts } from '../useTakeHomeDrafts';
import { listDrafts, upsertDraft, type TakeHomeAssignment } from '../../pages/take-home/takeHomeApi';

const ASSIGNMENT: TakeHomeAssignment = {
  id: 'assign000000001',
  slug: 'kv-store-py',
  title: 'Key-value store',
  difficulty: 'medium',
  language: 'python',
  time_budget_min: 60,
  ai_policy: 'off',
  prompt_md: '',
  starter_files: [{ path: 'store.py', contents: 'starter' }],
  rubric: { items: [] },
};

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

async function hydrated() {
  const hook = renderHook(() => useTakeHomeDrafts(ASSIGNMENT, 'campaign00000001'));
  await settle();
  expect(hook.result.current.hydrated).toBe(true);
  return hook;
}

async function autosaveTick() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(10_000);
  });
}

describe('useTakeHomeDrafts saveNow', () => {
  it('waits for an autosave part way through and saves the files it had not reached', async () => {
    const { result } = await hydrated();
    act(() => {
      result.current.setFile('store.py', 'mine');
      result.current.setFile('tests/test_store.py', 'my test');
    });
    await autosaveTick();
    expect(pending.map((p) => p.path)).toEqual(['store.py']);

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
    expect(pending[1]).toMatchObject({ path: 'tests/test_store.py', contents: 'my test' });
    expect(settled).toBeNull();
    await act(async () => {
      pending[1].resolve();
      await now;
    });
    expect(settled).toBe(true);
    expect(result.current.savedFiles).toMatchObject({ 'store.py': 'mine', 'tests/test_store.py': 'my test' });
  });

  it('saves a file whose autosave failed, and reports a save that fails again', async () => {
    const { result } = await hydrated();
    act(() => result.current.setFile('store.py', 'mine'));
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
    expect(pending[1]).toMatchObject({ path: 'store.py', contents: 'mine' });
    await act(async () => {
      pending[1].reject();
    });
    await expect(now).resolves.toBe(false);
  });
});
