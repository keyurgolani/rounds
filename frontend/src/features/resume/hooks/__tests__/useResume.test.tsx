// useResume's flush (ROUNDS-00A-L04): it waits for a save in flight,
// rejects when a save fails, and resolves with the saved `updated`, which
// server PDF sends as `expected_updated`. A failed save keeps its edits
// pending, so the next save carries them.

import { beforeEach, describe, expect, it, vi } from 'vitest';
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
  reject: () => void;
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
            reject: () => reject(new Error('offline')),
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
