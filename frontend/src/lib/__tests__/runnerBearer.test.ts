// Every runner call from the SPA carries the caller's bearer
// (ROUNDS-00A-L01). Only the anonymous public-share read opts out.

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const authStore = vi.hoisted(() => ({ token: '', record: null as null | Record<string, unknown> }));
vi.mock('../pocketbase', () => ({ pb: { authStore } }));

import { evaluateCode, runCode } from '../../pages/coding/runnerApi';
import { runProject } from '../../pages/ai-coding/aiCodingApi';
import { isRunnerError } from '../runnerFetch';
import type { Entry } from '../../pages/coding/types';

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  authStore.token = '';
  authStore.record = null;
  fetchMock.mockReset();
  fetchMock.mockResolvedValue(new Response('{}', { status: 200 }));
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const ENTRY: Entry = { kind: 'function', name: 'f', params: [], returns: 'int' };

const CALLS: Array<[string, () => Promise<unknown>]> = [
  ['run', () => runCode({ code: 'print(1)', language: 'python', entry: ENTRY, input: {} })],
  ['evaluate', () => evaluateCode({ code: 'print(1)', language: 'python', entry: ENTRY, test_cases: [] })],
  ['run-project', () => runProject({ files: {}, language: 'python', test_command: 'pytest' })],
];

describe('runner calls', () => {
  it.each(CALLS)('%s sends nothing without a signed-in caller', async (_name, call) => {
    const err = await call().catch((e: unknown) => e);
    expect(isRunnerError(err)).toBe(true);
    expect(err).toMatchObject({ code: 'unauthenticated', status: 0 });
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it.each(CALLS)('%s sends the bearer when there is one', async (_name, call) => {
    authStore.token = 'test-token-placeholder';
    await call();
    const headers = fetchMock.mock.calls[0][1]!.headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer test-token-placeholder');
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

  it("never opts a runner call out of the bearer except the public share read", () => {
    const optOuts: string[] = [];
    for (const file of sources(SRC)) {
      const text = readFileSync(file, 'utf8');
      for (const match of text.matchAll(/auth:\s*['"](optional|none)['"]/g)) {
        optOuts.push(`${relative(SRC, file)}:${match[1]}`);
      }
    }
    expect(optOuts).toEqual(['features/resume/share/client.ts:none']);
  });

  it('sends no runner request from a bare fetch', () => {
    const bare: string[] = [];
    for (const file of sources(SRC)) {
      if (file.endsWith('runnerFetch.ts')) continue;
      const text = readFileSync(file, 'utf8');
      if (/fetch\(\s*['"`]\/api\/(run|evaluate|pdf|ai|ai-coding|take-home|share|sd-practice)\b/.test(text)) {
        bare.push(relative(SRC, file));
      }
    }
    expect(bare).toEqual([]);
  });
});
