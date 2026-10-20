// The SPA never writes the demo tier or the old demo flags
// (ROUNDS-00A-L01 stage 3). PocketBase refuses a client write to
// `is_demo`, `demo_run_used`, and `demo_evaluate_used`, and the runner's
// demo tier holds the demo limits, so both old writers are gone: the
// coding page's allowance and the demo reset on logout.

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
  const authStore = {
    token: 'test-token-placeholder',
    isValid: true,
    record: demo as Record<string, unknown> | null,
    onChange: () => () => undefined,
    clear: () => {
      authStore.record = null;
      authStore.isValid = false;
    },
    save: () => undefined,
  };
  const collection = (name: string) => ({
    authRefresh: async () => ({ record: authStore.record }),
    getFullList: async () => [],
    delete: async () => true,
    update: async (id: string, payload: Record<string, unknown>) => {
      updates.push({ collection: name, id, payload });
      return { ...demo, ...payload };
    },
  });
  return { demo, updates, authStore, collection };
});

vi.mock('../../lib/pocketbase', () => ({
  pb: { authStore: pbMock.authStore, collection: pbMock.collection, files: { getURL: () => '' } },
}));

import { AuthProvider, useAuth } from '../AuthProvider';
import { evaluateCode, runCode } from '../../pages/coding/runnerApi';

const DEMO_FIELDS = ['is_demo', 'demo_run_used', 'demo_evaluate_used'];
const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  pbMock.updates.length = 0;
  pbMock.authStore.record = pbMock.demo;
  pbMock.authStore.isValid = true;
  fetchMock.mockReset();
  fetchMock.mockImplementation(
    async () => new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }),
  );
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('a demo account', () => {
  it('runs and evaluates without touching its user record', async () => {
    await runCode({ question_slug: 'two-sum', language: 'python', code: 'print(1)', input: {} });
    await evaluateCode({ question_slug: 'two-sum', language: 'python', code: 'print(1)' });
    expect(pbMock.updates).toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('resets only its profile fields on logout', async () => {
    let logout: (() => Promise<void>) | null = null;
    function Probe() {
      logout = useAuth().logout;
      return null;
    }
    render(
      <AuthProvider>
        <Probe />
      </AuthProvider>,
    );
    await act(async () => {
      await logout!();
    });
    const users = pbMock.updates.filter((u) => u.collection === 'users');
    expect(users).toHaveLength(1);
    expect(Object.keys(users[0].payload).sort()).toEqual(['bio', 'name', 'target']);
    expect(pbMock.authStore.record).toBeNull();
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
