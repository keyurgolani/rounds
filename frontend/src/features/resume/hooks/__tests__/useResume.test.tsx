// useResume's flush (ROUNDS-00A-L04): it waits for a save in flight,
// rejects when a save fails, and resolves with the saved `updated`, which
// server PDF sends as `expected_updated`. A failed save keeps its edits
// pending, so the next save carries them.

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';

vi.mock('../../api', () => ({
  createVersion: vi.fn(),
  ensureUniqueSlug: vi.fn(),
  getResumeBySlug: vi.fn(),
  updateResume: vi.fn(),
}));
vi.mock('../../links/library', () => ({ loadLibrarySnapshot: vi.fn() }));
vi.mock('../../links/resolve', () => ({
  resolveAndSync: (data: unknown, links: unknown) => ({ data, links, changed: false }),
}));

import { useResume } from '../useResume';
import { createVersion, getResumeBySlug, updateResume } from '../../api';
import { loadLibrarySnapshot } from '../../links/library';
import type { Resume, ResumeData } from '../../types';

const LOADED_AT = '2026-11-11 08:00:00.000Z';

function resumeAt(updated: string): Resume {
  return {
    id: 'resume000000001',
    slug: 'jane-doe',
    name: 'Jane Doe',
    data: { personalInfo: { fullName: 'Jane Doe' } },
    links: {},
    template_id: 'modern',
    design: {},
    updated_at: updated,
  } as unknown as Resume;
}

interface Save {
  patch: Record<string, unknown>;
  resolve: (updated: string) => void;
  // No status is a save that got no answer; a status is PocketBase's.
  reject: (status?: number) => void;
}

let saves: Save[];

beforeEach(() => {
  saves = [];
  vi.mocked(getResumeBySlug).mockReset().mockResolvedValue(resumeAt(LOADED_AT));
  vi.mocked(loadLibrarySnapshot).mockReset().mockResolvedValue({ jobs: {}, projects: {}, bullets: {} } as never);
  vi.mocked(createVersion).mockReset().mockResolvedValue(undefined as never);
  vi.mocked(updateResume)
    .mockReset()
    .mockImplementation(
      (_id, patch) =>
        new Promise<Resume>((resolve, reject) => {
          saves.push({
            patch: patch as Record<string, unknown>,
            resolve: (updated) => resolve(resumeAt(updated)),
            reject: (status) =>
              reject(status === undefined ? new Error('offline') : Object.assign(new Error('refused'), { status })),
          });
        }),
    );
});

async function loaded() {
  const hook = renderHook(() => useResume('jane-doe'));
  await waitFor(() => expect(hook.result.current.resume).not.toBeNull());
  return hook;
}

function edit(hook: Awaited<ReturnType<typeof loaded>>, fullName: string) {
  act(() => {
    hook.result.current.setData({ personalInfo: { fullName } } as unknown as ResumeData);
  });
}

// Lets the save queue start the next save.
async function tick() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe('useResume flush', () => {
  it('saves the pending edit and resolves with the saved updated', async () => {
    const hook = await loaded();
    edit(hook, 'Jane Q. Doe');
    let flushed: Promise<string>;
    act(() => {
      flushed = hook.result.current.flush();
    });
    await tick();
    expect(saves).toHaveLength(1);
    expect(saves[0].patch).toEqual({ data: { personalInfo: { fullName: 'Jane Q. Doe' } } });
    await act(async () => saves[0].resolve('2026-11-11 08:00:01.000Z'));
    await expect(flushed!).resolves.toBe('2026-11-11 08:00:01.000Z');
  });

  it('with nothing pending resolves with the updated it loaded', async () => {
    const hook = await loaded();
    await expect(hook.result.current.flush()).resolves.toBe(LOADED_AT);
    expect(updateResume).not.toHaveBeenCalled();
  });

  it('called mid-save waits for that save and the edits after it', async () => {
    const hook = await loaded();
    edit(hook, 'First');
    let first: Promise<string>;
    act(() => {
      first = hook.result.current.flush();
    });
    await tick();
    expect(saves).toHaveLength(1);

    edit(hook, 'Second');
    let second: Promise<string>;
    let settled = false;
    act(() => {
      second = hook.result.current.flush();
      second.then(() => (settled = true), () => (settled = true));
    });
    await tick();
    // One save at a time: the second waits for the first.
    expect(saves).toHaveLength(1);
    expect(settled).toBe(false);

    await act(async () => saves[0].resolve('2026-11-11 08:00:01.000Z'));
    await expect(first!).resolves.toBe('2026-11-11 08:00:01.000Z');
    await tick();
    expect(saves).toHaveLength(2);
    expect(saves[1].patch).toEqual({ data: { personalInfo: { fullName: 'Second' } } });
    expect(settled).toBe(false);
    await act(async () => saves[1].resolve('2026-11-11 08:00:02.000Z'));
    await expect(second!).resolves.toBe('2026-11-11 08:00:02.000Z');
  });

  it('rejects when the save fails and keeps the edit for the next save', async () => {
    const hook = await loaded();
    edit(hook, 'Unsaved');
    let flushed: Promise<string>;
    act(() => {
      flushed = hook.result.current.flush();
    });
    flushed!.catch(() => undefined);
    await tick();
    await act(async () => saves[0].reject());
    await expect(flushed!).rejects.toThrow('offline');
    expect(hook.result.current.saveState).toBe('error');

    let retried: Promise<string>;
    act(() => {
      retried = hook.result.current.flush();
    });
    await tick();
    expect(saves).toHaveLength(2);
    expect(saves[1].patch).toEqual({ data: { personalInfo: { fullName: 'Unsaved' } } });
    await act(async () => saves[1].resolve('2026-11-11 08:00:03.000Z'));
    await expect(retried!).resolves.toBe('2026-11-11 08:00:03.000Z');
  });

  it('rejects when the save it waited on fails, even with nothing left to save', async () => {
    const hook = await loaded();
    edit(hook, 'In flight');
    let first: Promise<string>;
    act(() => {
      first = hook.result.current.flush();
    });
    first!.catch(() => undefined);
    await tick();
    let second: Promise<string>;
    act(() => {
      second = hook.result.current.flush();
    });
    second!.catch(() => undefined);
    await act(async () => saves[0].reject());
    await expect(second!).rejects.toThrow('offline');
    await expect(first!).rejects.toThrow('offline');
  });
});

// No edit sits unsaved or is dropped: a failed save tries again on its
// own, and leaving the Studio saves what's left.
describe('useResume keeps every edit', () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  async function advance(ms: number) {
    await act(async () => {
      await vi.advanceTimersByTimeAsync(ms);
    });
  }

  it('tries a failed save again on its own, waiting longer each time', async () => {
    const hook = await loaded();
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    edit(hook, 'Typed offline');
    await advance(700);
    expect(saves).toHaveLength(1);
    await act(async () => saves[0].reject());

    await advance(1_999);
    expect(saves).toHaveLength(1);
    await advance(1);
    expect(saves).toHaveLength(2);
    expect(saves[1].patch).toEqual({ data: { personalInfo: { fullName: 'Typed offline' } } });
    await act(async () => saves[1].reject());

    // The second wait is twice the first.
    await advance(3_999);
    expect(saves).toHaveLength(2);
    await advance(1);
    expect(saves).toHaveLength(3);
    await act(async () => saves[2].resolve('2026-11-11 08:00:04.000Z'));
    expect(hook.result.current.saveState).toBe('saved');
    expect(hook.result.current.lastSavedAt).toBe('2026-11-11 08:00:04.000Z');
  });

  it('saves an edit typed while a save is in flight once that save lands', async () => {
    const hook = await loaded();
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    edit(hook, 'First');
    await advance(700);
    edit(hook, 'Second');
    // The first save lands while the second edit's debounce is waiting.
    await act(async () => saves[0].resolve('2026-11-11 08:00:01.000Z'));
    await advance(700);
    expect(saves).toHaveLength(2);
    expect(saves[1].patch).toEqual({ data: { personalInfo: { fullName: 'Second' } } });
  });

  it('saves a pending edit when the Studio unmounts', async () => {
    const hook = await loaded();
    edit(hook, 'Typed then left');
    hook.unmount();
    await tick();
    expect(saves).toHaveLength(1);
    expect(saves[0].patch).toEqual({ data: { personalInfo: { fullName: 'Typed then left' } } });
  });

  it('saves the edits of a failed save when the Studio unmounts, once', async () => {
    const hook = await loaded();
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    edit(hook, 'Failed then left');
    await advance(700);
    await act(async () => saves[0].reject());
    hook.unmount();
    await advance(0);
    expect(saves).toHaveLength(2);
    expect(saves[1].patch).toEqual({ data: { personalInfo: { fullName: 'Failed then left' } } });
    await act(async () => saves[1].reject());
    // Unmounted, it doesn't keep trying.
    await advance(60_000);
    expect(saves).toHaveLength(2);
  });

  it('tries once more when the save in flight as the Studio unmounts then fails', async () => {
    const hook = await loaded();
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    edit(hook, 'Saving as I left');
    await advance(700);
    expect(saves).toHaveLength(1);
    hook.unmount();
    await act(async () => saves[0].reject());
    await advance(0);
    expect(saves).toHaveLength(2);
    expect(saves[1].patch).toEqual({ data: { personalInfo: { fullName: 'Saving as I left' } } });
    await act(async () => saves[1].reject());
    await advance(60_000);
    expect(saves).toHaveLength(2);
  });

  it('saves nothing more when the save in flight as the Studio unmounts lands', async () => {
    const hook = await loaded();
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    edit(hook, 'Saved as I left');
    await advance(700);
    hook.unmount();
    await act(async () => saves[0].resolve('2026-11-11 08:00:02.000Z'));
    await advance(60_000);
    expect(saves).toHaveLength(1);
  });

  it.each([400, 401, 403, 404, 413, 422])(
    'leaves a save PocketBase refused with %i for the next edit or export, without retrying',
    async (status) => {
      const hook = await loaded();
      vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
      edit(hook, 'Refused');
      await advance(700);
      await act(async () => saves[0].reject(status));
      await advance(60_000);
      expect(saves).toHaveLength(1);
      expect(hook.result.current.saveState).toBe('error');

      // The edits stay pending: the next edit's save carries them.
      edit(hook, 'Refused, then edited');
      await advance(700);
      expect(saves).toHaveLength(2);
      expect(saves[1].patch).toEqual({ data: { personalInfo: { fullName: 'Refused, then edited' } } });
      // And an export still waits on them and fails with them.
      await act(async () => saves[1].reject(status));
      let flushed: Promise<unknown> | undefined;
      act(() => {
        flushed = hook.result.current.flush().catch((e: unknown) => e);
      });
      await advance(0);
      await act(async () => saves[2].reject(status));
      expect(await flushed).toMatchObject({ message: 'refused', status });
    },
  );

  it.each([408, 429, 500, 503])('still retries a save that failed with %i', async (status) => {
    const hook = await loaded();
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout'] });
    edit(hook, 'Try again');
    await advance(700);
    await act(async () => saves[0].reject(status));
    await advance(2_000);
    expect(saves).toHaveLength(2);
  });
});
