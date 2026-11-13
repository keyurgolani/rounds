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

// frontend/src/lib/demoKeys.ts in #230's shape, with its prefix, the text a
// key drops, or the body of localKey replaced.
const DEMO = 'frontend/src/lib/demoKeys.ts';
const TAB = 'frontend/src/pages/Tab.tsx';
const SHAPED = (drop) => `  if (!isDemo) return key;\n  return DEMO_KEY_PREFIX + (key.startsWith('${drop}') ? key.slice('${drop}'.length) : key);\n`;
const demoKeys = ({ prefix = 'rounds.demo.', body = SHAPED('rounds.') } = {}) => `export const DEMO_KEY_PREFIX = '${prefix}';\n\nexport function localKey(key: string, isDemo: boolean): string {\n${body}}\n`;
const writeThrough = (call) => `import { localKey } from '../lib/demoKeys';\nexport function f(isDemo: boolean) {\n  const k = crypto.randomUUID();\n  localStorage.setItem(${call}, '1');\n}\n`;

describe('browser keys: the demo account\'s prefix', () => {
  it('follows localKey to both keys, through a constant, a template, and a wrapper', () => {
    const out = extract({
      [DEMO]: demoKeys(),
      'frontend/src/hooks/usePersisted.ts': 'export function usePersisted(key: string, v: string) {\n  localStorage.setItem(key, v);\n}\n',
      [TAB]: [
        "import { localKey } from '../lib/demoKeys';",
        "import { usePersisted } from '../hooks/usePersisted';",
        'export function Tab({ id, isDemo }: { id?: string; isDemo: boolean }) {',
        "  const persistKey = localKey(`rounds.tab.${id ?? 'untitled'}`, isDemo);",
        "  usePersisted(`${persistKey}.jd`, '');",
        "  localStorage.setItem(localKey('legacy.flag', isDemo), '1');",
        '  return null;',
        '}',
        '',
      ].join('\n'),
    });
    assert.deepEqual(Object.keys(families(out)), ['legacy.flag', 'rounds.demo.legacy.flag', 'rounds.demo.tab.*.jd', 'rounds.tab.*.jd']);
    assert.deepEqual(out.families.get('rounds.demo.tab.*.jd').writes, ['frontend/src/hooks/usePersisted.ts:2', `${TAB}:5`]);
    assert.deepEqual(out.unresolved, []);
  });

  it('reads the prefix and the dropped text from the module, under any import name', () => {
    const call = "import { localKey as lk } from '../lib/demoKeys';\nexport const f = (d: boolean) => localStorage.setItem(lk('app.notes', d), '1');\n";
    assert.deepEqual(Object.keys(families(extract({ [DEMO]: demoKeys({ prefix: 'visitor.', body: SHAPED('app.') }), [TAB]: call }))), ['app.notes', 'visitor.notes']);
    assert.deepEqual(Object.keys(families(extract({ [DEMO]: demoKeys(), [TAB]: call }))), ['app.notes', 'rounds.demo.app.notes']);
  });

  it('fails closed when localKey changes shape, or a key\'s start leaves the drop undecided', () => {
    const changed = extract({ [DEMO]: demoKeys({ body: '  return isDemo ? `${DEMO_KEY_PREFIX}${key}` : key;\n' }), [TAB]: writeThrough("localKey('rounds.notes', isDemo)") });
    assert.deepEqual(families(changed), {});
    assert.deepEqual(changed.unresolved, [`${TAB}:4`]);
    const undecided = extract({ [DEMO]: demoKeys(), [TAB]: writeThrough('localKey(`${k}.notes`, isDemo)') });
    assert.deepEqual(Object.keys(families(undecided)), ['*.notes']);
    assert.deepEqual(undecided.unresolved, [`${TAB}:4`]);
    const inTemplate = extract({ [DEMO]: demoKeys(), [TAB]: writeThrough("`${localKey('rounds.notes', isDemo)}.v1`") });
    assert.deepEqual(families(inTemplate), {});
    assert.deepEqual(inTemplate.unresolved, [`${TAB}:4`]);
  });

  it('follows only the demo keys module\'s localKey', () => {
    const own = extract({ [DEMO]: demoKeys(), [TAB]: "function localKey(k: string) { return `own.${k}`; }\nlocalStorage.setItem(localKey('x'), '1');\n" });
    assert.deepEqual(Object.keys(families(own)), ['own.x']);
    const other = extract({ [DEMO]: demoKeys(), 'frontend/src/lib/other.ts': 'export function localKey(k: string) { return k; }\n', [TAB]: writeThrough("localKey('rounds.notes', isDemo)").replace('../lib/demoKeys', '../lib/other') });
    assert.deepEqual(families(other), {});
    assert.deepEqual(other.unresolved, [`${TAB}:4`]);
    const absent = extract({ [TAB]: writeThrough("localKey('rounds.notes', isDemo)") });
    assert.deepEqual(families(absent), {});
    assert.deepEqual(absent.unresolved, [`${TAB}:4`]);
  });

  it('follows the module\'s own calls to localKey', () => {
    const own = extract({ [DEMO]: `${demoKeys()}export const remember = (isDemo: boolean) => localStorage.setItem(localKey('rounds.notes', isDemo), '1');\n` });
    assert.deepEqual(Object.keys(families(own)), ['rounds.demo.notes', 'rounds.notes']);
    assert.deepEqual(own.unresolved, []);
  });

  it('fails closed past the key cap, and when the prefix slot names a parameter', () => {
    const pick = (v, c) => `${c} === 0 ? '${v}0' : ${c} === 1 ? '${v}1' : ${c} === 2 ? '${v}2' : '${v}3'`;
    const many = extract({ [DEMO]: demoKeys(), [TAB]: `import { localKey } from '../lib/demoKeys';\nexport function f(p: number, q: number, r: number, isDemo: boolean) {\n  const A = ${pick('a', 'p')}; const B = ${pick('b', 'q')}; const C = ${pick('c', 'r')};\n  localStorage.setItem(localKey(\`rounds.\${A}.\${B}.\${C}\`, isDemo), '1');\n}\n` });
    assert.deepEqual(families(many), {});
    assert.deepEqual(many.unresolved, [`${TAB}:4`]);
    const shadowed = extract({ [DEMO]: demoKeys().replace(/\bkey\b/g, 'DEMO_KEY_PREFIX'), [TAB]: writeThrough("localKey('rounds.notes', isDemo)") });
    assert.deepEqual(families(shadowed), {});
    assert.deepEqual(shadowed.unresolved, [`${TAB}:4`]);
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
