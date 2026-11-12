// The SPA never writes the demo tier or the old demo flags
// (ROUNDS-00A-L01 stage 3). PocketBase refuses a client write to
// `is_demo`, `demo_run_used`, and `demo_evaluate_used`, and the runner's
// demo tier holds the demo limits, so both old writers are gone: the
// coding page's allowance and the demo reset on logout.
//
// The demo's sign-out (ROUNDS-00B-L07) is PocketBase's: every sign-out the
// SPA runs for the demo account, the idle one included, asks the server
// to clear what the account holds, and signs out whatever it answers. The
// browser keeps no demo key past a demo sign-out or a start without a
// demo session.

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { act, render } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const pbMock = vi.hoisted(() => {
  const demo = {
    id: 'demo00000000001',
    collectionId: '_pb_users_auth_',
    collectionName: 'users',
    email: 'demo@example.test',
    name: 'Rounds Demo',
    is_demo: true,
    demo_run_used: true,
    demo_evaluate_used: true,
  };
  const updates: Array<{ collection: string; id: string; payload: Record<string, unknown> }> = [];
  const deletes: Array<{ collection: string; id: string }> = [];
  const refresh = { error: null as { status: number } | null };
  // As PocketBase's store does, a clear tells its subscribers.
  const listeners: Array<() => void> = [];
  const authStore = {
    token: 'test-token-placeholder',
    isValid: true,
    record: demo as Record<string, unknown> | null,
    onChange: (fn: () => void) => {
      listeners.push(fn);
      return () => {
        const at = listeners.indexOf(fn);
        if (at >= 0) listeners.splice(at, 1);
      };
    },
    clear: () => {
      authStore.record = null;
      authStore.isValid = false;
      listeners.slice().forEach((fn) => fn());
    },
    save: () => undefined,
  };
  const collection = (name: string) => ({
    authRefresh: async () => {
      if (refresh.error) throw refresh.error;
      return { record: authStore.record };
    },
    getFullList: async () => [],
    delete: async (id: string) => {
      deletes.push({ collection: name, id });
      return true;
    },
    update: async (id: string, payload: Record<string, unknown>) => {
      updates.push({ collection: name, id, payload });
      return { ...demo, ...payload };
    },
  });
  return { demo, updates, deletes, refresh, authStore, collection };
});

vi.mock('../../lib/pocketbase', () => ({
  pb: {
    authStore: pbMock.authStore,
    collection: pbMock.collection,
    files: { getURL: () => '' },
    buildURL: (path: string) => `http://pb.test${path}`,
  },
}));

import { AuthProvider, clearDemoKeysWithoutADemoSession, useAuth } from '../AuthProvider';
import { evaluateCode, runCode } from '../../pages/coding/runnerApi';

const DEMO_FIELDS = ['is_demo', 'demo_run_used', 'demo_evaluate_used'];
const END_URL = 'http://pb.test/api/rounds/demo/sessions/end';
const fetchMock = vi.fn<typeof fetch>();

// Keys a demo session leaves, and keys that aren't its to clear.
const DEMO_KEYS = [
  'rounds.demo.resume.ats.gone00000000001.jd',
  'rounds.demo.resume.ats.untitled.jd',
  'rounds.demo.resume.tailor.r1.jd',
];
const KEPT_KEYS = ['rounds.resume.ats.user00000000001.jd', 'rounds:guide:capacity-math'];

function seedKeys() {
  for (const key of [...DEMO_KEYS, ...KEPT_KEYS]) window.localStorage.setItem(key, '"x"');
}

function storedKeys(): string[] {
  return Object.keys(window.localStorage).sort();
}

function endCalls() {
  return fetchMock.mock.calls.filter(([url]) => url === END_URL);
}

beforeEach(() => {
  pbMock.updates.length = 0;
  pbMock.deletes.length = 0;
  pbMock.refresh.error = null;
  pbMock.authStore.record = pbMock.demo;
  pbMock.authStore.isValid = true;
  window.localStorage.clear();
  window.sessionStorage.clear();
  fetchMock.mockReset();
  fetchMock.mockImplementation(
    async () => new Response(null, { status: 204 }),
  );
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function renderProvider(): { logout: () => Promise<void> } {
  const handle = { logout: async () => undefined as void };
  function Probe() {
    handle.logout = useAuth().logout;
    return null;
  }
  render(
    <AuthProvider>
      <Probe />
    </AuthProvider>,
  );
  return handle;
}

describe('a demo account', () => {
  it('runs and evaluates without touching its user record', async () => {
    fetchMock.mockImplementation(
      async () => new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }),
    );
    await runCode({ question_slug: 'two-sum', language: 'python', code: 'print(1)', input: {} });
    await evaluateCode({ question_slug: 'two-sum', language: 'python', code: 'print(1)' });
    expect(pbMock.updates).toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('signs out by asking the server to clear the demo account, and writes nothing itself', async () => {
    const handle = renderProvider();
    await act(async () => {
      await handle.logout();
    });
    expect(endCalls()).toHaveLength(1);
    const [, init] = endCalls()[0];
    expect(init?.method).toBe('POST');
    expect((init?.headers as Record<string, string>).Authorization).toBe('test-token-placeholder');
    expect(pbMock.updates).toEqual([]);
    expect(pbMock.deletes).toEqual([]);
    expect(pbMock.authStore.record).toBeNull();
  });

  it('still signs out when the server does not answer', async () => {
    fetchMock.mockImplementation(async () => {
      throw new TypeError('Failed to fetch');
    });
    const handle = renderProvider();
    await act(async () => {
      await handle.logout();
    });
    expect(endCalls()).toHaveLength(1);
    expect(pbMock.authStore.record).toBeNull();
  });

  it('clears its demo keys at sign-out, for a resume already gone and an untitled one too', async () => {
    seedKeys();
    window.sessionStorage.setItem('rounds:job:run:two-sum', '{}');
    const handle = renderProvider();
    await act(async () => {
      await handle.logout();
    });
    expect(storedKeys()).toEqual([...KEPT_KEYS].sort());
    expect(window.sessionStorage.getItem('rounds:job:run:two-sum')).toBeNull();
  });

  it('ends an idle session on the server too, with keepalive', async () => {
    vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval', 'setTimeout', 'clearTimeout', 'Date'] });
    seedKeys();
    renderProvider();
    // The start's session refresh lands first, as it does in the app.
    await act(async () => {
      await Promise.resolve();
    });
    await act(async () => {
      vi.advanceTimersByTime(31 * 60 * 1000);
    });
    expect(endCalls()).toHaveLength(1);
    expect(endCalls()[0][1]?.keepalive).toBe(true);
    expect(pbMock.authStore.record).toBeNull();
    expect(storedKeys()).toEqual([...KEPT_KEYS].sort());
  });

  it('clears its demo keys when the server rejects its session', async () => {
    seedKeys();
    pbMock.refresh.error = { status: 401 };
    renderProvider();
    await act(async () => {
      await Promise.resolve();
    });
    expect(pbMock.authStore.record).toBeNull();
    expect(storedKeys()).toEqual([...KEPT_KEYS].sort());
    // The token is gone, so the sweep clears the account instead.
    expect(endCalls()).toHaveLength(0);
  });
});

describe('a start', () => {
  it('without a demo session clears the demo keys and keeps every other key', () => {
    seedKeys();
    pbMock.authStore.record = null;
    pbMock.authStore.isValid = false;
    clearDemoKeysWithoutADemoSession();
    expect(storedKeys()).toEqual([...KEPT_KEYS].sort());
  });

  it('with an expired demo session clears them too', () => {
    seedKeys();
    pbMock.authStore.isValid = false;
    clearDemoKeysWithoutADemoSession();
    expect(storedKeys()).toEqual([...KEPT_KEYS].sort());
  });

  it('with a live demo session keeps them', () => {
    seedKeys();
    clearDemoKeysWithoutADemoSession();
    expect(storedKeys()).toEqual([...DEMO_KEYS, ...KEPT_KEYS].sort());
  });
});

describe('a standard account', () => {
  it('signs out without the demo sign-out and keeps its keys', async () => {
    seedKeys();
    pbMock.authStore.record = { ...pbMock.demo, id: 'user00000000001', is_demo: false };
    const handle = renderProvider();
    await act(async () => {
      await handle.logout();
    });
    expect(endCalls()).toHaveLength(0);
    expect(pbMock.authStore.record).toBeNull();
    // Its activity clock stays too, as before.
    expect(storedKeys()).toEqual([...DEMO_KEYS, ...KEPT_KEYS, 'rounds:last-activity-at'].sort());
  });
});

describe('the SPA source', () => {
  const SRC = resolve(__dirname, '../..');

  function sources(dir: string): string[] {
    return readdirSync(dir).flatMap((name) => {
      const path = join(dir, name);
      if (statSync(path).isDirectory()) return name === '__tests__' ? [] : sources(path);
      return /\.(ts|tsx)$/.test(name) && !/\.test\.tsx?$/.test(name) ? [path] : [];
    });
  }

  it('never writes the demo tier or the demo flags', () => {
    const writes: string[] = [];
    const pattern = new RegExp(`\\b(${DEMO_FIELDS.join('|')})['"]?\\s*:|\\[\\s*['"](${DEMO_FIELDS.join('|')})['"]\\s*\\]\\s*=`);
    for (const file of sources(SRC)) {
      readFileSync(file, 'utf8')
        .split('\n')
        .forEach((line, index) => {
          if (pattern.test(line)) writes.push(`${relative(SRC, file)}:${index + 1}`);
        });
    }
    expect(writes).toEqual([]);
  });
});
