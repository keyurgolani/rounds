// Browser storage key families in frontend/src at a pinned revision
// (ROUNDS-01-L02). Finds every localStorage and sessionStorage call and the
// PocketBase SDK's default auth store, then resolves each key argument to a
// family: literal text with `*` wherever the key varies.
//
// A key argument resolves through string and template literals, constants
// and functions in the same file, conditional and `||` / `??` alternatives,
// and wrapper parameters: when a hook, function, or component passes its own
// parameter or prop to storage, the key resolves at each of its call sites
// (calls and JSX elements), up to a few levels deep. Node built-ins only.

import path from 'node:path';
import { readJsxOpeningElement, tokenize } from '../js-scan.mjs';

const SOURCE = /^frontend\/src\/.+\.(ts|tsx|js|jsx|mjs)$/;
const TEST_PATH = /(\/__tests__\/|\.test\.|\.spec\.|\/test\/|setupTests\.)/;
const STORAGE = new Set(['localStorage', 'sessionStorage']);
const METHODS = { getItem: 'read', setItem: 'write', removeItem: 'write' };
// PocketBase JS SDK: `new PocketBase(url)` without an auth store argument
// persists the session in a LocalAuthStore under this localStorage key.
export const SDK_AUTH_KEY = 'pocketbase_auth';
const MAX_DEPTH = 6;

export function sourceFiles(tree) {
  return tree.files().filter((f) => SOURCE.test(f) && !TEST_PATH.test(f));
}

// ------------------------------------------------------------ file analysis

const OPEN = { '(': ')', '[': ']', '{': '}' };
const CLOSE = new Set([')', ']', '}']);

function closeOf(tokens, i) {
  const open = tokens[i].value;
  const close = OPEN[open];
  let depth = 0;
  for (let j = i; j < tokens.length; j++) {
    const t = tokens[j];
    if (t.type !== 'punct') continue;
    if (t.value === open) depth++;
    else if (t.value === close && --depth === 0) return j;
  }
  return tokens.length - 1;
}

const CONTINUES_AFTER = new Set(['=', '+', '-', '*', '/', '%', '?', ':', '|', '&', ',', '(', '[', '{', '.', '<', '>', '!', '=>', '...']);
const CONTINUES_BEFORE = new Set(['.', '?', ':', '|', '&', '+', '-', '*', '/', '%', '=', '>', '<', ')', ']', '}', ',', '=>']);
const CONTINUE_WORDS = new Set(['return', 'typeof', 'new', 'await', 'in', 'of', 'instanceof', 'as', 'void']);

// End (exclusive) of the expression starting at tokens[start].
export function expressionEnd(tokens, start, limit = tokens.length) {
  let depth = 0;
  for (let j = start; j < limit; j++) {
    const t = tokens[j];
    if (t.type === 'punct') {
      if (OPEN[t.value]) { depth++; continue; }
      if (CLOSE.has(t.value)) { if (depth === 0) return j; depth--; continue; }
      if (depth === 0 && (t.value === ';' || t.value === ',')) return j;
    }
    if (depth === 0 && j > start && t.line > tokens[j - 1].line) {
      const prev = tokens[j - 1];
      const prevContinues = (prev.type === 'punct' && CONTINUES_AFTER.has(prev.value)) || (prev.type === 'ident' && CONTINUE_WORDS.has(prev.value));
      const nextContinues = t.type === 'punct' && CONTINUES_BEFORE.has(t.value);
      if (!prevContinues && !nextContinues) return j;
    }
  }
  return limit;
}

// Splits a parenthesized list (tokens[open] is '(') into top-level items,
// treating `<...>` inside type annotations as brackets.
function listItems(tokens, open) {
  const close = closeOf(tokens, open);
  const items = [];
  let start = open + 1;
  let depth = 0;
  let angle = 0;
  let inType = false;
  for (let j = open + 1; j < close; j++) {
    const t = tokens[j];
    if (t.type !== 'punct') continue;
    if (OPEN[t.value]) depth++;
    else if (CLOSE.has(t.value)) depth--;
    else if (depth === 0 && t.value === ':') inType = true;
    else if (depth === 0 && inType && t.value === '<') angle++;
    else if (depth === 0 && inType && t.value === '>' && angle > 0) angle--;
    else if (depth === 0 && angle === 0 && t.value === '=') inType = false;
    else if (depth === 0 && angle === 0 && t.value === ',') {
      if (j > start) items.push([start, j]);
      start = j + 1;
      inType = false;
    }
  }
  if (close > start) items.push([start, close]);
  return { items, close };
}

function parseParams(tokens, open) {
  const { items, close } = listItems(tokens, open);
  const params = [];
  items.forEach(([s], pos) => {
    const t = tokens[s];
    if (!t) return;
    if (t.type === 'ident') { params.push({ name: t.value, pos }); return; }
    if (t.type === 'punct' && t.value === '{') {
      const end = closeOf(tokens, s);
      const { items: props } = listItems([{ type: 'punct', value: '(' }, ...tokens.slice(s + 1, end), { type: 'punct', value: ')' }], 0);
      const inner = tokens.slice(s + 1, end);
      for (const [a, b] of props) {
        const key = inner[a - 1];
        if (!key || key.type !== 'ident') continue;
        const colon = inner[a] && inner[a].value === ':' && a < b - 1 ? inner[a + 1] : null;
        const local = colon && colon.type === 'ident' ? colon.value : key.value;
        params.push({ name: local, pos, prop: key.value });
      }
    }
  });
  return { params, close };
}

function bodyAfterArrowOrParams(tokens, j) {
  // Skips an optional `: Type` annotation to the '{' or '=>' that follows.
  let k = j;
  let depth = 0;
  for (; k < tokens.length; k++) {
    const t = tokens[k];
    if (t.type === 'punct' && depth === 0 && (t.value === '{' || t.value === '=>')) break;
    if (t.type === 'punct' && (t.value === '<' || t.value === '(' || t.value === '[')) depth++;
    if (t.type === 'punct' && (t.value === '>' || t.value === ')' || t.value === ']')) depth--;
    if (t.type === 'punct' && t.value === ';') return null;
  }
  return k < tokens.length ? k : null;
}

function analyzeFile(file, text) {
  const tokens = tokenize(text);
  const fns = [];
  const consts = [];
  const addFn = (name, paramsOpen, at) => {
    const { params, close } = parseParams(tokens, paramsOpen);
    const k = bodyAfterArrowOrParams(tokens, close + 1);
    if (k === null) return;
    let bodyStart;
    let bodyEnd;
    let exprBody = false;
    if (tokens[k].value === '=>') {
      if (tokens[k + 1] && tokens[k + 1].value === '{') { bodyStart = k + 1; bodyEnd = closeOf(tokens, k + 1); }
      else { bodyStart = k + 1; bodyEnd = expressionEnd(tokens, k + 1); exprBody = true; }
    } else {
      bodyStart = k;
      bodyEnd = closeOf(tokens, k);
    }
    fns.push({ name, params, start: at, bodyStart, bodyEnd, exprBody });
  };
  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    if (t.type === 'ident' && t.value === 'function') {
      let j = i + 1;
      if (tokens[j] && tokens[j].value === '*') j++;
      let name = null;
      if (tokens[j] && tokens[j].type === 'ident') { name = tokens[j].value; j++; }
      if (tokens[j] && tokens[j].value === '<') { while (j < tokens.length && tokens[j].value !== '(') j++; }
      if (tokens[j] && tokens[j].value === '(') {
        const before = fns.length;
        addFn(name, j, i);
        if (fns.length > before) fns[fns.length - 1].isDefault = tokens[i - 1]?.value === 'default' && tokens[i - 2]?.value === 'export';
      }
      continue;
    }
    if (t.type === 'ident' && (t.value === 'const' || t.value === 'let' || t.value === 'var')) {
      const nameTok = tokens[i + 1];
      if (!nameTok || nameTok.type !== 'ident') continue;
      let j = i + 2;
      // Skip a type annotation up to '='.
      if (tokens[j] && tokens[j].value === ':') {
        let depth = 0;
        for (j = j + 1; j < tokens.length; j++) {
          const v = tokens[j].value;
          if (tokens[j].type === 'punct' && (v === '<' || OPEN[v])) depth++;
          else if (tokens[j].type === 'punct' && (v === '>' || CLOSE.has(v))) depth--;
          else if (depth === 0 && v === '=') break;
          if (depth === 0 && v === ';') break;
        }
      }
      if (!tokens[j] || tokens[j].value !== '=') continue;
      const initStart = j + 1;
      const initEnd = expressionEnd(tokens, initStart);
      consts.push({ name: nameTok.value, at: i, initStart, initEnd });
      // `const name = (params) => ...`, `async (...) =>`, `x => ...`, `function (...)`.
      let k = initStart;
      if (tokens[k] && tokens[k].type === 'ident' && tokens[k].value === 'async') k++;
      if (tokens[k] && tokens[k].value === '(') {
        const close = closeOf(tokens, k);
        const after = bodyAfterArrowOrParams(tokens, close + 1);
        if (after !== null && tokens[after].value === '=>') addFn(nameTok.value, k, i);
      } else if (tokens[k] && tokens[k].type === 'ident' && tokens[k + 1] && tokens[k + 1].value === '=>') {
        const p = tokens[k].value;
        const bodyStart = k + 2;
        const block = tokens[bodyStart] && tokens[bodyStart].value === '{';
        const bodyEnd = block ? closeOf(tokens, bodyStart) : expressionEnd(tokens, bodyStart);
        fns.push({ name: nameTok.value, params: [{ name: p, pos: 0 }], start: i, bodyStart: block ? bodyStart : bodyStart, bodyEnd, exprBody: !block });
      }
      continue;
    }
    // Anonymous arrows with parenthesized params: `(a, b) => ...` (for scope only).
    if (t.type === 'punct' && t.value === '(' && (i === 0 || tokens[i - 1].type !== 'ident' || ['return', 'await'].includes(tokens[i - 1].value))) {
      const close = closeOf(tokens, i);
      if (tokens[close + 1] && tokens[close + 1].value === '=>' && !fns.some((f) => f.start === i)) {
        const prevConst = i >= 2 && tokens[i - 1].value === '=' ? null : true;
        if (prevConst) addFn(null, i, i);
      }
    }
  }
  fns.sort((a, b) => a.bodyStart - b.bodyStart);
  return { file, text, tokens, fns, consts };
}

function enclosing(info, index) {
  // Innermost function whose params or body contain index.
  let best = null;
  for (const f of info.fns) {
    if (index >= f.start && index <= f.bodyEnd) {
      if (!best || f.start >= best.start) best = f;
    }
  }
  return best;
}

function chainOf(info, index) {
  const chain = [];
  for (const f of info.fns) if (index >= f.start && index <= f.bodyEnd) chain.push(f);
  return chain.sort((a, b) => b.start - a.start);
}

function lookupConst(info, name, index) {
  // Innermost const visible at index: same function scope first, then module.
  const chain = chainOf(info, index);
  for (const f of chain) {
    const hit = info.consts.filter((c) => c.name === name && c.at > f.bodyStart && c.at < f.bodyEnd && enclosing(info, c.at) === f);
    if (hit.length) return hit[hit.length - 1];
  }
  const top = info.consts.filter((c) => c.name === name && !enclosing(info, c.at));
  return top.length ? top[0] : null;
}

function lookupParam(info, name, index) {
  for (const f of chainOf(info, index)) {
    const p = f.params.find((x) => x.name === name);
    if (p) return { fn: f, param: p };
  }
  return null;
}

function returnRanges(info, fn) {
  if (fn.exprBody) return [[fn.bodyStart, fn.bodyEnd]];
  const out = [];
  for (let i = fn.bodyStart + 1; i < fn.bodyEnd; i++) {
    const t = info.tokens[i];
    if (t.type === 'ident' && t.value === 'return' && enclosing(info, i) === fn) {
      const end = expressionEnd(info.tokens, i + 1, fn.bodyEnd);
      if (end > i + 1) out.push([i + 1, end]);
    }
  }
  return out;
}

// ------------------------------------------------------------- resolution
//
// A key is an array of parts: { lit } text, { any: true } for a varying part,
// or { param } for a wrapper parameter still to resolve at call sites.

const LIT = (v) => ({ lit: v });
const ANY = { any: true };

function stripRange(tokens, s, e) {
  let a = s;
  let b = e;
  for (let changed = true; changed;) {
    changed = false;
    if (b - a >= 2 && tokens[a].value === '(' && closeOf(tokens, a) === b - 1) { a++; b--; changed = true; }
    if (b - a >= 3 && tokens[b - 2].type === 'ident' && tokens[b - 2].value === 'as') { b -= 2; changed = true; }
    if (b - a >= 2 && tokens[b - 1].value === '!' ) { b--; changed = true; }
  }
  return [a, b];
}

function topLevel(tokens, s, e, pred) {
  let depth = 0;
  for (let j = s; j < e; j++) {
    const t = tokens[j];
    if (t.type === 'punct') {
      if (OPEN[t.value]) { depth++; continue; }
      if (CLOSE.has(t.value)) { depth--; continue; }
    }
    if (depth === 0 && pred(t, j)) return j;
  }
  return -1;
}

class Resolver {
  constructor(infos) {
    this.infos = infos; // Map file -> info
    this.byName = new Map(); // function name -> [{ info, fn }]
    for (const info of infos.values()) {
      for (const fn of info.fns) {
        if (!fn.name) continue;
        if (!this.byName.has(fn.name)) this.byName.set(fn.name, []);
        this.byName.get(fn.name).push({ info, fn });
      }
    }
    this.callSiteCache = new Map();
  }

  // Resolves tokens[s, e) of info at scope index; returns keys or null.
  resolve(info, s, e, depth = 0) {
    if (depth > MAX_DEPTH || e <= s) return null;
    const tokens = info.tokens;
    [s, e] = stripRange(tokens, s, e);
    if (e <= s) return null;
    // a ? b : c (only punctuation tokens count; a template's text never does)
    const isPunct = (t, v) => t && t.type === 'punct' && t.value === v;
    const ternary = (j) => isPunct(tokens[j], '?') && !isPunct(tokens[j + 1], '.') && !isPunct(tokens[j + 1], '?') && !isPunct(tokens[j - 1], '?');
    const q = topLevel(tokens, s, e, (t, j) => ternary(j));
    if (q !== -1) {
      let depth2 = 0;
      let nested = 0;
      let colon = -1;
      for (let j = q + 1; j < e; j++) {
        const t = tokens[j];
        if (t.type === 'punct' && OPEN[t.value]) depth2++;
        else if (t.type === 'punct' && CLOSE.has(t.value)) depth2--;
        else if (depth2 === 0 && ternary(j)) nested++;
        else if (depth2 === 0 && isPunct(t, ':')) {
          if (nested === 0) { colon = j; break; }
          nested--;
        }
      }
      if (colon !== -1) return this.union(this.resolve(info, q + 1, colon, depth + 1), this.resolve(info, colon + 1, e, depth + 1));
    }
    // a || b, a ?? b
    const or = topLevel(tokens, s, e, (t, j) => (isPunct(t, '|') && isPunct(tokens[j + 1], '|')) || (isPunct(t, '?') && isPunct(tokens[j + 1], '?')));
    if (or !== -1) return this.union(this.resolve(info, s, or, depth + 1), this.resolve(info, or + 2, e, depth + 1));
    if (e - s === 1) {
      const t = tokens[s];
      if (t.type === 'string') return t.value === '' ? [] : [[LIT(t.value)]];
      if (t.type === 'template') return this.template(info, t, s, depth);
      if (t.type === 'ident') return this.identifier(info, t.value, s, depth);
      return null;
    }
    // name.prop where name is a parameter: props.storageKey
    if (e - s === 3 && tokens[s].type === 'ident' && tokens[s + 1].value === '.' && tokens[s + 2].type === 'ident') {
      const hit = lookupParam(info, tokens[s].value, s);
      if (hit && !hit.param.prop) return [[{ param: { info, fn: hit.fn, pos: hit.param.pos, prop: tokens[s + 2].value } }]];
      return null;
    }
    // f(args) with f a function in this file.
    if (tokens[s].type === 'ident' && tokens[s + 1] && tokens[s + 1].value === '(' && closeOf(tokens, s + 1) === e - 1) {
      return this.call(info, tokens[s].value, s + 1, depth);
    }
    return null;
  }

  union(a, b) {
    if (a === null && b === null) return null;
    return [...(a || [[ANY]]), ...(b || [[ANY]])];
  }

  template(info, t, index, depth) {
    let keys = [[]];
    for (const part of t.parts || [{ text: t.value }]) {
      if (part.text !== undefined) { keys = keys.map((k) => [...k, LIT(part.text)]); continue; }
      const sub = analyzeFragment(part.expr);
      // Resolve the expression in the template's scope by splicing scope.
      const resolved = sub ? this.resolveFragment(info, sub, index, depth + 1) : null;
      const options = resolved && resolved.length ? resolved : [[ANY]];
      const next = [];
      for (const k of keys) for (const o of options) next.push([...k, ...o]);
      keys = next.slice(0, 64);
    }
    return keys;
  }

  resolveFragment(info, fragTokens, scopeIndex, depth) {
    // fragTokens come from a ${...} source; resolve identifiers in info's scope.
    const proxy = { ...info, tokens: fragTokens, fns: [], consts: [] };
    if (fragTokens.length === 1 && fragTokens[0].type === 'ident') return this.identifier(info, fragTokens[0].value, scopeIndex, depth);
    if (fragTokens.length === 3 && fragTokens[0].type === 'ident' && fragTokens[1].value === '.' && fragTokens[2].type === 'ident') {
      const hit = lookupParam(info, fragTokens[0].value, scopeIndex);
      if (hit && !hit.param.prop) return [[{ param: { info, fn: hit.fn, pos: hit.param.pos, prop: fragTokens[2].value } }]];
      return null;
    }
    if (fragTokens.length >= 3 && fragTokens[0].type === 'ident' && fragTokens[1].value === '(' && closeOf(fragTokens, 1) === fragTokens.length - 1) {
      return this.callWithArgs(info, fragTokens[0].value, [], depth);
    }
    return this.resolve(proxy, 0, fragTokens.length, depth);
  }

  identifier(info, name, index, depth) {
    const param = lookupParam(info, name, index);
    const c = lookupConst(info, name, index);
    if (c && (!param || c.at > param.fn.start)) {
      if (c.initEnd <= c.initStart) return null;
      const init = info.tokens[c.initStart];
      if (init && (init.value === '(' || init.value === 'async')) {
        // A function value, not a key.
        const fn = info.fns.find((f) => f.start === c.at);
        if (fn) return null;
      }
      return this.resolve(info, c.initStart, c.initEnd, depth + 1);
    }
    if (param) return [[{ param: { info, fn: param.fn, pos: param.param.pos, prop: param.param.prop || null, name } }]];
    return null;
  }

  call(info, name, openIndex, depth) {
    const { items } = listItems(info.tokens, openIndex);
    const args = items.map(([a, b]) => ({ info, s: a, e: b }));
    return this.callWithArgs(info, name, args, depth);
  }

  callWithArgs(info, name, args, depth) {
    const fn = info.fns.find((f) => f.name === name);
    if (!fn) return null;
    let out = [];
    for (const [a, b] of returnRanges(info, fn)) {
      const keys = this.resolve(info, a, b, depth + 1);
      if (!keys) continue;
      // Substitute this function's own params with the call's arguments.
      for (const key of keys) out.push(...this.substitute(key, fn, args, depth));
    }
    return out.length ? out : null;
  }

  substitute(key, fn, args, depth) {
    let keys = [[]];
    for (const part of key) {
      if (part.param && part.param.fn === fn) {
        const arg = args[part.param.pos];
        let options = null;
        if (arg && !part.param.prop) options = this.resolve(arg.info, arg.s, arg.e, depth + 1);
        options = options && options.length ? options : [[ANY]];
        const next = [];
        for (const k of keys) for (const o of options) next.push([...k, ...o]);
        keys = next.slice(0, 64);
      } else {
        keys = keys.map((k) => [...k, part]);
      }
    }
    return keys;
  }

  // Expands wrapper parameters through every call site of the wrapper.
  expand(key, depth = 0, via = []) {
    const idx = key.findIndex((p) => p.param);
    if (idx === -1) return [{ key, via }];
    const { info: home, fn, pos, prop } = key[idx].param;
    if (depth > MAX_DEPTH || !fn.name) return [{ key: key.map((p) => (p.param ? ANY : p)), via, unresolved: true }];
    const sites = this.callSites(fn, home);
    if (!sites.length) return [{ key: key.map((p) => (p.param ? ANY : p)), via, unresolved: true }];
    const out = [];
    for (const site of sites) {
      const options = this.argumentAt(site, pos, prop, depth);
      const opts = options && options.length ? options : [[ANY]];
      for (const o of opts) {
        const next = [...key.slice(0, idx), ...o, ...key.slice(idx + 1)];
        out.push(...this.expand(next, depth + 1, [...via, site]));
      }
    }
    return out;
  }

  // Call and JSX sites of fn (defined in `home`): in its own file, and in
  // files that import it from there under any local name. A file that
  // declares its own function of that name is not a caller.
  callSites(fn, home) {
    const cacheKey = `${home.file}\u0000${fn.name}\u0000${fn.start}`;
    if (this.callSiteCache.has(cacheKey)) return this.callSiteCache.get(cacheKey);
    const sites = [];
    for (const info of this.infos.values()) {
      const names = info === home ? [fn.name] : importedNames(info, home.file, fn);
      for (const name of names) {
        if (info !== home && info.fns.some((f) => f.name === name)) continue;
        sites.push(...this.sitesIn(info, name));
      }
    }
    this.callSiteCache.set(cacheKey, sites);
    return sites;
  }

  sitesIn(info, name) {
    const sites = [];
    {
      const { tokens } = info;
      for (let i = 0; i < tokens.length - 1; i++) {
        const t = tokens[i];
        if (t.type !== 'ident' || t.value !== name) continue;
        let open = i + 1;
        if (tokens[open].value === '<') {
          // Generic type arguments: name<T>(...)
          let depth = 0;
          for (; open < tokens.length; open++) {
            if (tokens[open].value === '<') depth++;
            else if (tokens[open].value === '>' && --depth === 0) break;
          }
          open++;
        }
        if (!tokens[open] || tokens[open].value !== '(') continue;
        const prev = tokens[i - 1];
        if (prev && (prev.value === 'function' || prev.value === '.')) continue;
        if (info.fns.some((f) => f.name === name && f.start <= i && i <= f.start + 2)) continue;
        sites.push({ kind: 'call', info, index: i, open, line: t.line });
      }
      // JSX elements: <Name ...>
      const re = new RegExp(`<${name}(?=[\\s/>])`, 'g');
      for (const m of info.text.matchAll(re)) {
        const el = readJsxOpeningElement(info.text, m.index);
        const index = tokenIndexAt(tokens, m.index);
        const line = info.text.slice(0, m.index).split('\n').length;
        sites.push({ kind: 'jsx', info, index, element: el, line });
      }
    }
    return sites;
  }

  argumentAt(site, pos, prop, depth) {
    const { info } = site;
    if (site.kind === 'jsx') {
      if (pos !== 0 || !prop) return null;
      const attr = site.element.attributes.find((a) => a.name === prop);
      if (!attr) return null;
      if (attr.kind === 'string') return attr.literal === '' ? [] : [[LIT(attr.literal)]];
      if (attr.kind === 'expression') {
        const frag = analyzeFragment(attr.expression);
        return frag ? this.resolveFragment(info, frag, site.index, depth + 1) : null;
      }
      return null;
    }
    const { items } = listItems(info.tokens, site.open);
    const item = items[pos];
    if (!item) return null;
    if (!prop) return this.resolve(info, item[0], item[1], depth + 1);
    // Destructured option object: name({ storageKey: X })
    const [a, b] = item;
    if (info.tokens[a].value !== '{') return null;
    const close = closeOf(info.tokens, a);
    if (close !== b - 1) return null;
    const { items: props } = listItems([{ type: 'punct', value: '(' }, ...info.tokens.slice(a + 1, close), { type: 'punct', value: ')' }], 0);
    for (const [ps, pe] of props) {
      const key = info.tokens[a + ps];
      if (!key || key.value !== prop) continue;
      if (pe - ps === 1) return this.identifier(info, prop, a + ps, depth + 1);
      if (info.tokens[a + ps + 1].value === ':') return this.resolve(info, a + ps + 2, a + pe, depth + 1);
    }
    return null;
  }
}

const IMPORT = /import\s+(?:type\s+)?(?:([A-Za-z_$][\w$]*)\s*,?\s*)?(?:\{([^}]*)\})?\s*from\s*['"]([^'"]+)['"]/g;

function importCandidates(fromFile, spec) {
  if (!spec.startsWith('.')) return [];
  const base = path.posix.normalize(path.posix.join(path.posix.dirname(fromFile), spec));
  return [base, `${base}.ts`, `${base}.tsx`, `${base}.js`, `${base}.jsx`, `${base}/index.ts`, `${base}/index.tsx`];
}

// Local names under which info's file imports fn from homeFile.
function importedNames(info, homeFile, fn) {
  const names = [];
  for (const m of info.text.matchAll(IMPORT)) {
    if (!importCandidates(info.file, m[3]).includes(homeFile)) continue;
    if (m[1] && fn.isDefault) names.push(m[1]);
    for (const part of (m[2] || '').split(',')) {
      const entry = part.trim().replace(/^type\s+/, '');
      if (!entry) continue;
      const [orig, alias] = entry.split(/\s+as\s+/);
      if (orig === fn.name || (orig === 'default' && fn.isDefault)) names.push(alias || orig);
    }
  }
  return [...new Set(names)];
}

function tokenIndexAt(tokens, offset) {
  let lo = 0;
  let hi = tokens.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (tokens[mid].start < offset) lo = mid + 1;
    else hi = mid;
  }
  return lo;
}

function analyzeFragment(src) {
  try {
    const tokens = tokenize(src);
    return tokens.length ? tokens : null;
  } catch {
    return null;
  }
}

export function familyOf(key) {
  let out = '';
  for (const p of key) out += p.lit !== undefined ? p.lit : '*';
  return out.replace(/\*+/g, '*');
}

// ------------------------------------------------------------------ public

// Returns { families: Map family -> { api, writes: [site], reads: [site] },
// purges: [site], unresolved: [site] } where site is "path:line".
export function extractBrowserKeys(tree) {
  const files = sourceFiles(tree);
  if (tree.prefetch) tree.prefetch(files);
  const infos = new Map();
  for (const file of files) {
    const text = tree.read(file);
    if (text === null) continue;
    if (!/localStorage|sessionStorage|new PocketBase\(|usePersisted|storageKey|Storage/.test(text) && !/export/.test(text)) continue;
    infos.set(file, analyzeFile(file, text));
  }
  const resolver = new Resolver(infos);
  const families = new Map();
  const purges = [];
  const unresolved = [];
  const add = (family, api, kind, site) => {
    if (!families.has(family)) families.set(family, { api, writes: new Set(), reads: new Set() });
    const entry = families.get(family);
    (kind === 'read' ? entry.reads : entry.writes).add(site);
  };
  for (const info of infos.values()) {
    const { tokens } = info;
    for (let i = 0; i < tokens.length - 3; i++) {
      const t = tokens[i];
      if (t.type === 'ident' && t.value === 'new' && tokens[i + 1].value === 'PocketBase' && tokens[i + 2].value === '(') {
        const { items } = listItems(tokens, i + 2);
        if (items.length < 2) add(SDK_AUTH_KEY, 'localStorage', 'write', `${info.file}:${t.line}`);
        else unresolved.push(`${info.file}:${t.line}`);
        continue;
      }
      if (t.type !== 'ident' || !STORAGE.has(t.value)) continue;
      if (tokens[i + 1].value !== '.' || tokens[i + 3].value !== '(') continue;
      const method = tokens[i + 2].value;
      if (!METHODS[method]) continue;
      const api = t.value;
      const { items } = listItems(tokens, i + 3);
      const site = `${info.file}:${t.line}`;
      if (!items.length) { unresolved.push(site); continue; }
      const [a, b] = items[0];
      // Keys read back from localStorage.key(i) are an enumerating purge.
      if (b - a === 1 && tokens[a].type === 'ident') {
        const c = lookupConst(info, tokens[a].value, a);
        if (c && tokens.slice(c.initStart, c.initEnd).some((x, k, arr) => STORAGE.has(x.value) && arr[k + 2] && arr[k + 2].value === 'key')) {
          purges.push(site);
          continue;
        }
        const loopVar = /for\s*\(\s*const\s+(\w+)\s+of/.exec(info.text.split('\n')[t.line - 1] || '');
        if (loopVar && loopVar[1] === tokens[a].value) { purges.push(site); continue; }
      }
      const keys = resolver.resolve(info, a, b);
      if (!keys || !keys.length) { unresolved.push(site); continue; }
      for (const key of keys) {
        for (const { key: done, via, unresolved: partial } of resolver.expand(key)) {
          const family = familyOf(done);
          if (!family || family === '*' || partial) { unresolved.push(via.length ? `${via[via.length - 1].info.file}:${via[via.length - 1].line}` : site); if (!family || family === '*') continue; }
          const origin = via.length ? `${via[via.length - 1].info.file}:${via[via.length - 1].line}` : site;
          add(family, api, METHODS[method], origin);
          if (via.length) add(family, api, METHODS[method] === 'write' ? 'write' : 'read', site);
        }
      }
    }
  }
  const sortSites = (set) => [...set].sort((x, y) => {
    const [px, lx] = [x.slice(0, x.lastIndexOf(':')), Number(x.slice(x.lastIndexOf(':') + 1))];
    const [py, ly] = [y.slice(0, y.lastIndexOf(':')), Number(y.slice(y.lastIndexOf(':') + 1))];
    return px < py ? -1 : px > py ? 1 : lx - ly;
  });
  // A family that a wider one already covers (rounds.x.untitled.jd under
  // rounds.x.*.jd) folds into it, sites included.
  for (const name of [...families.keys()]) {
    const wider = [...families.keys()].find((other) => other !== name && other.includes('*') && families.get(other).api === families.get(name).api && covers(other, name));
    if (!wider) continue;
    const from = families.get(name);
    const to = families.get(wider);
    for (const s of from.writes) to.writes.add(s);
    for (const s of from.reads) to.reads.add(s);
    families.delete(name);
  }
  const out = new Map();
  for (const name of [...families.keys()].sort()) {
    const f = families.get(name);
    out.set(name, { api: f.api, writes: sortSites(f.writes), reads: sortSites(f.reads) });
  }
  return { families: out, purges: sortSites(new Set(purges)), unresolved: sortSites(new Set(unresolved)) };
}

// True when glob family `wide` (with `*`) matches every key of `narrow`.
export function covers(wide, narrow) {
  const re = new RegExp(`^${wide.split('*').map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('.*')}$`, 's');
  return re.test(narrow);
}
