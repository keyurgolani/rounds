// The Vite dev proxy denies what production nginx never proxies
// (ROUNDS-00A-L01), so no path works in dev that answers 404 in prod.
// nginx's location choice is modeled here: an exact match, else the
// longest prefix when it's `^~`, else the first matching regex in file
// order, else the longest prefix, all on the path with %XX decoded.

import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { ProxyOptions } from 'vite';
import { describe, expect, it, vi } from 'vitest';

import { devProxy } from '../../devProxy';

interface Location {
  modifier: string;
  pattern: string;
  denies: boolean;
}

function nginxLocations(): Location[] {
  const text = readFileSync(resolve(__dirname, '../../nginx.conf'), 'utf8');
  const out: Location[] = [];
  const header = /location\s+(=|\^~|~\*|~)?\s*([^\s{]+)\s*\{/g;
  for (const m of text.matchAll(header)) {
    // The block runs to its matching brace.
    let depth = 1;
    let end = m.index! + m[0].length;
    while (depth > 0 && end < text.length) {
      if (text[end] === '{') depth += 1;
      if (text[end] === '}') depth -= 1;
      end += 1;
    }
    const body = text.slice(m.index! + m[0].length, end - 1);
    out.push({ modifier: m[1] ?? '', pattern: m[2], denies: /\breturn\s+404\b/.test(body) });
  }
  return out;
}

const LOCATIONS = nginxLocations();

function nginxDenies(url: string): boolean {
  const path = decodeURIComponent(url.split('?')[0]);
  const exact = LOCATIONS.find((l) => l.modifier === '=' && l.pattern === path);
  if (exact) return exact.denies;
  const prefixes = LOCATIONS.filter(
    (l) => (l.modifier === '' || l.modifier === '^~') && !l.pattern.startsWith('@') && path.startsWith(l.pattern),
  ).sort((a, b) => b.pattern.length - a.pattern.length);
  const longest = prefixes[0];
  if (longest?.modifier === '^~') return longest.denies;
  const regex = LOCATIONS.find(
    (l) => (l.modifier === '~' || l.modifier === '~*') && new RegExp(l.pattern, l.modifier === '~*' ? 'i' : '').test(path),
  );
  if (regex) return regex.denies;
  return longest?.denies ?? false;
}

const PROXY: [string, ProxyOptions][] = Object.entries(devProxy);

function viteEntry(url: string): ProxyOptions | undefined {
  const hit = PROXY.find(([context]) =>
    context.startsWith('^') ? new RegExp(context).test(url) : url.startsWith(context),
  );
  return hit?.[1];
}

function viteDenies(url: string): boolean {
  const entry = viteEntry(url);
  return entry?.bypass?.({ url } as never, {} as never, entry) === false;
}

// The socket an upgrade on `url` gets, and whether the entry that takes
// it passed it on.
function upgrade(url: string) {
  const entry = viteEntry(url)!;
  const forward = vi.fn();
  const server = { ws: forward } as { ws: (req: unknown, socket: unknown, head: unknown) => void };
  entry.configure?.(server as never, entry);
  const socket = { end: vi.fn() };
  server.ws({ url }, socket, Buffer.alloc(0));
  return { entry, socket, forwarded: forward.mock.calls.length > 0 };
}

const NEVER_PROXIED = [
  '/_/',
  '/_/images/logo.svg',
  '/api/rounds/admission/admit',
  '/api/rounds/admission/usage?x=1',
  '/api/rounds/execution/enqueue',
  '/api/rounds/execution/claim',
  '/api/rounds/execution/reap?x=1',
  '/api/collections/execution_service/auth-with-password',
  '/api/collections/execution_service/records',
  '/api/collections/Execution_Service/auth-with-password',
  '/api/collections/EXECUTION_SERVICE/records?perPage=1',
  '/api/collections/execution%5Fservice/auth-with-password',
  '/api/collections/Execution%5FService/auth-with-password',
  '/api/admins',
  '/api/admins/auth-with-password',
  '/api/settings',
  '/api/settings?fields=meta',
  '/api/backups/today.zip',
  '/api/logs',
  '/api/collections',
  '/api/collections/',
  '/api/collections?perPage=1',
  '/api/collections/users',
  '/api/collections/users/',
  '/api/collections/users?fields=schema',
  '/api/Collections',
  '/api/COLLECTIONS/users',
  '/api/collections/Users/',
];

const PROXIED = [
  '/',
  '/_',
  '/api/health',
  '/api/realtime',
  '/api/run',
  '/api/evaluate',
  '/api/pdf/render',
  '/api/ai-coding/grade',
  '/api/take-home/submit',
  '/api/rounds/other',
  '/api/settingsx',
  '/api/collections/users/records',
  '/api/collections/users/records?filter=x',
  '/api/collections/users/auth-with-password',
  '/api/collections/Users/records',
  '/api/collections/execution_jobs/records',
];

describe('the dev proxy and production nginx', () => {
  it('found the denials in nginx.conf', () => {
    expect(LOCATIONS.filter((l) => l.denies).length).toBeGreaterThanOrEqual(5);
  });

  it.each(NEVER_PROXIED)('both answer 404 for %s', (url) => {
    expect(nginxDenies(url)).toBe(true);
    expect(viteDenies(url)).toBe(true);
  });

  it.each(PROXIED)('neither denies %s', (url) => {
    expect(nginxDenies(url)).toBe(false);
    expect(viteDenies(url)).toBe(false);
  });

  it.each([
    '/_/',
    '/api/rounds/admission/admit',
    '/api/collections/execution_service/auth-with-password',
    '/api/collections/Execution_Service/auth-with-password',
  ])('refuses a WebSocket upgrade on %s too', (url) => {
    const { entry, socket, forwarded } = upgrade(url);
    expect(entry.ws).toBe(true);
    expect(socket.end).toHaveBeenCalledWith(expect.stringMatching(/^HTTP\/1\.1 404 /));
    expect(forwarded).toBe(false);
  });

  it('passes a WebSocket upgrade on an open path to PocketBase', () => {
    const { entry, socket, forwarded } = upgrade('/api/realtime');
    expect(entry.target).toBe(viteEntry('/api/health')?.target);
    expect(socket.end).not.toHaveBeenCalled();
    expect(forwarded).toBe(true);
  });

  it.each(PROXY.map(([context]) => context))('refuses a denied path in entry %s too', (context) => {
    const entry = devProxy[context];
    const req = { url: '/api/collections/Execution_Service/auth-with-password' };
    expect(entry.bypass?.(req as never, {} as never, entry)).toBe(false);
  });

  it('sends the runner routes to the runner and the rest of /api to PocketBase', () => {
    expect(viteEntry('/api/evaluate')?.target).toBe(viteEntry('/api/run')?.target);
    expect(viteEntry('/api/health')?.target).not.toBe(viteEntry('/api/run')?.target);
  });
});
