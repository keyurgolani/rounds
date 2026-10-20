import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { createContext } from '../lib/context.mjs';
import { SDK_AUTH_KEY, covers, extractBrowserKeys } from '../lib/authority/browser-keys.mjs';
import { REPO_ROOT } from './helpers.mjs';

// Extracts from an in-memory tree: { [path]: source }.
const extract = (files) => extractBrowserKeys(createContext(REPO_ROOT, { trees: { t: { files } } }).tree('t'));
const families = (out) => Object.fromEntries([...out.families].map(([k, v]) => [k, { api: v.api, writes: v.writes, reads: v.reads }]));
const SRC = 'frontend/src/a.ts';

describe('browser keys: resolution', () => {
  it('reads literal keys and splits writes from reads', () => {
    const out = extract({ [SRC]: "localStorage.setItem('a.b', '1');\nexport const r = () => localStorage.getItem('a.b');\n" });
    assert.deepEqual(families(out), { 'a.b': { api: 'localStorage', writes: [`${SRC}:1`], reads: [`${SRC}:2`] } });
    assert.deepEqual(out.unresolved, []);
  });

  it('turns template parts into a wildcard and keeps the storage API', () => {
    const out = extract({ [SRC]: 'const id = crypto.randomUUID();\nsessionStorage.setItem(`rounds.x.${id}`, "1");\n' });
    assert.deepEqual(Object.keys(families(out)), ['rounds.x.*']);
    assert.equal(out.families.get('rounds.x.*').api, 'sessionStorage');
  });

  it('follows constants, same-file functions, and conditional alternatives', () => {
    assert.deepEqual(Object.keys(families(extract({ [SRC]: "const KEY = 'k1';\nlocalStorage.setItem(KEY, '1');\n" }))), ['k1']);
    assert.deepEqual(Object.keys(families(extract({ [SRC]: 'function keyFor(u: string) { return `d:${u}`; }\nconst user = crypto.randomUUID();\nlocalStorage.setItem(keyFor(user), "1");\n' }))), ['d:*']);
    assert.deepEqual(Object.keys(families(extract({ [SRC]: "const flag = Math.random() > 0.5;\nlocalStorage.setItem(flag ? 'a' : 'b', '1');\n" }))), ['a', 'b']);
  });

  it('resolves a wrapper parameter at its imported call sites, not at a same-named local function', () => {
    const out = extract({
      'frontend/src/hooks/usePersisted.ts': 'export function usePersisted(key: string, v: string) {\n  localStorage.setItem(key, v);\n}\n',
      'frontend/src/pages/A.tsx': "import { usePersisted } from '../hooks/usePersisted';\nexport function A() { usePersisted('rounds.apps.sort', 'x'); return null; }\n",
      'frontend/src/pages/B.tsx': "function usePersisted(key: string) { return key; }\nexport function B() { usePersisted('not.a.key'); return null; }\n",
    });
    assert.deepEqual(families(out), { 'rounds.apps.sort': { api: 'localStorage', writes: ['frontend/src/hooks/usePersisted.ts:2', 'frontend/src/pages/A.tsx:2'], reads: [] } });
  });

  it('resolves a component prop at its JSX call sites', () => {
    const out = extract({
      'frontend/src/components/Persist.tsx': "export function Persist({ storageKey }: { storageKey: string }) {\n  localStorage.setItem(storageKey, '1');\n  return null;\n}\n",
      'frontend/src/pages/C.tsx': "import { Persist } from '../components/Persist';\nexport const C = () => <Persist storageKey=\"rounds.panel.width\" />;\n",
    });
    assert.deepEqual(Object.keys(families(out)), ['rounds.panel.width']);
  });

  it('records the SDK auth store, an enumerating purge, and folds a family into a wider one', () => {
    const sdk = extract({ 'frontend/src/lib/pb.ts': "import PocketBase from 'pocketbase';\nexport const pb = new PocketBase('/');\nexport const other = new PocketBase('/', store);\n" });
    assert.deepEqual(Object.keys(families(sdk)), [SDK_AUTH_KEY]);
    assert.deepEqual(sdk.unresolved, ['frontend/src/lib/pb.ts:3']);
    const purge = extract({ [SRC]: 'export function clear() {\n  const keys = Object.keys(localStorage);\n  for (const k of keys) localStorage.removeItem(k);\n}\n' });
    assert.deepEqual(purge.purges, [`${SRC}:3`]);
    const folded = extract({ [SRC]: "const id = crypto.randomUUID();\nlocalStorage.setItem(`rounds.x.${id}.jd`, '1');\nlocalStorage.setItem('rounds.x.untitled.jd', '1');\n" });
    assert.deepEqual(families(folded), { 'rounds.x.*.jd': { api: 'localStorage', writes: [`${SRC}:2`, `${SRC}:3`], reads: [] } });
    assert.ok(covers('rounds.x.*.jd', 'rounds.x.untitled.jd'));
    assert.ok(!covers('rounds.x.*.jd', 'rounds.y.untitled.jd'));
  });

  it('fails closed on a key it cannot resolve, and skips test files', () => {
    const out = extract({ [SRC]: "export function read(custom?: string) { return localStorage.getItem(custom ?? 'def'); }\n" });
    assert.deepEqual(Object.keys(families(out)), ['def']);
    assert.deepEqual(out.unresolved, [`${SRC}:1`]);
    assert.deepEqual(families(extract({ 'frontend/src/__tests__/a.test.ts': "localStorage.setItem('only.in.tests', '1');\n" })), {});
  });
});

describe('browser keys: the audited revision', () => {
  it('resolves every storage call at 62d4eae, the login streak included', () => {
    const out = extractBrowserKeys(createContext(REPO_ROOT).tree('62d4eae'));
    assert.deepEqual(out.unresolved, []);
    assert.equal(out.families.size, 82);
    for (const k of [SDK_AUTH_KEY, 'rounds.loginStreak.v1', 'rounds.loginStreak.v1:*', 'rounds.currentCampaign.v1', 'rounds.practiceStatus.v1']) assert.ok(out.families.has(k), k);
  });
});
