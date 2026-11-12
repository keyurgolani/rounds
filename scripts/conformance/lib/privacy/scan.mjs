// The provider-call scan (ROUNDS-14-L01). Every reference to a provider
// helper in backend Python, a call or the name passed as a value, through a
// local or aliased import too, must sit in a function the purpose registry
// names. A registered call site counts as a helper as well, matched in its
// own module and through imports of it, so a new caller of a registered
// wrapper fails until it is registered too. Vendor SDK calls and API
// headers must sit inside a helper. Tests are skipped. The scan reads
// lines: a top-level `def` (or a class's method) opens a function that runs
// until the next top-level statement, and comments and triple-quoted
// strings are skipped, outside ordinary strings only.

const NAME = (name) => name.replace(/[$.]/g, '\\$&');
// A helper's name is distinctive, so `module._call_complete` counts too. A
// wrapper's name may be common (`_call`, `review`) and shadowed by a local,
// so a bare name counts only as a call, never as an attribute of some other
// object; `alias.name` counts whenever `alias` is the wrapper's module.
const HELPER_REF = (name) => new RegExp(`(?<![A-Za-z0-9_])${NAME(name)}(?![A-Za-z0-9_])`);
const WRAPPER_REF = (name) => new RegExp(`(?<![A-Za-z0-9_.])${NAME(name)}\\s*\\(`);
const DOTTED_REF = (prefix, name) => new RegExp(`(?<![A-Za-z0-9_.])${NAME(prefix)}\\.${NAME(name)}(?![A-Za-z0-9_])`);
const VENDOR_MARKERS = [
  /\bAsyncOpenAI\s*\(/, /\bAsyncAnthropic\s*\(/, /\bOpenAI\s*\(/, /\bAnthropic\s*\(/,
  /\.chat\.completions\.create\s*\(/, /\.messages\.create\s*\(/, /\/chat\/completions\b/,
  /["']anthropic-version["']/, /["']x-api-key["']/i,
];
const DEF = /^(?<indent>[ \t]*)(?:async[ \t]+)?def[ \t]+(?<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*\(/;
const CLASS = /^class[ \t]+(?<name>[A-Za-z_][A-Za-z0-9_]*)/;
const IMPORT_AS = /\b([A-Za-z_][A-Za-z0-9_]*)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)/g;

export function backendPythonFiles(ctx) {
  return ctx.files().filter((f) => f.startsWith('backend/') && f.endsWith('.py')
    && !f.startsWith('backend/tests/') && !/(^|\/)(conftest|test_[^/]*)\.py$/.test(f)).sort();
}

// A line's code: comments and triple-quoted strings dropped, ordinary
// strings kept (a quoted helper name or API header still counts), so a
// `#` or `"""` inside an ordinary string hides nothing. `bare` also
// empties the ordinary strings, for names that count only as code.
// `triple` is the triple quote still open from an earlier line, if any.
function codeOf(raw, triple) {
  let code = '';
  let bare = '';
  let i = 0;
  let open = triple;
  while (i < raw.length) {
    if (open) {
      const end = raw.indexOf(open, i);
      if (end === -1) return { code, bare, open };
      i = end + 3;
      open = null;
      continue;
    }
    const ch = raw[i];
    if (ch === '#') break;
    if (ch === '"' || ch === "'") {
      if (raw.startsWith(ch.repeat(3), i)) { open = ch.repeat(3); i += 3; continue; }
      let j = i + 1;
      while (j < raw.length && raw[j] !== ch) j += raw[j] === '\\' ? 2 : 1;
      code += raw.slice(i, j + 1);
      bare += `${ch}${ch}`;
      i = j + 1;
      continue;
    }
    code += ch;
    bare += ch;
    i += 1;
  }
  return { code, bare, open };
}

// Lines with comments, triple-quoted strings, and import statements
// blanked, each with the function it sits in ("" at module level).
export function pythonLines(text) {
  const out = [];
  let fn = '';
  let cls = '';
  let triple = null;
  let importing = false;
  for (const raw of text.split('\n')) {
    const { code: line, bare, open } = codeOf(raw, triple);
    triple = open;
    const trimmed = line.trim();
    if (trimmed && !/^[ \t]/.test(line) && !trimmed.startsWith('@') && !trimmed.startsWith(')') && !trimmed.startsWith(']')) {
      const c = CLASS.exec(line);
      const d = DEF.exec(line);
      if (c) { cls = c.groups.name; fn = ''; }
      else if (d) { cls = ''; fn = d.groups.name; }
      else if (!importing) { cls = ''; fn = ''; }
    } else if (cls) {
      const d = DEF.exec(line);
      if (d && d.groups.indent.length <= 4) fn = `${cls}.${d.groups.name}`;
    }
    const startsImport = /^\s*(from\s+\S+\s+)?import\b/.test(line);
    const isImport = importing || startsImport;
    if (startsImport && /\(\s*$/.test(line)) importing = true;
    if (importing && /\)/.test(line)) importing = false;
    out.push({ code: isImport ? '' : line, bare: isImport ? '' : bare, importLine: isImport ? line : '', startsImport, fn, raw });
  }
  return out;
}

// backend/execution/review.py -> execution.review
export function moduleOf(file) {
  return file.slice('backend/'.length).replace(/\.py$/, '').replace(/\/__init__$/, '').split('/').join('.');
}

// The names a file's imports bind: { names: Map(local -> { module, name }),
// modules: Map(local or dotted prefix -> module) }.
function importsOf(file, lines, modules) {
  const statements = [];
  for (const l of lines) {
    if (!l.importLine) continue;
    if (l.startsImport) statements.push(l.importLine.trim());
    else if (statements.length) statements[statements.length - 1] += ` ${l.importLine.trim()}`;
  }
  const pkg = moduleOf(file).split('.').slice(0, file.endsWith('/__init__.py') ? undefined : -1);
  const absolute = (dots, name) => {
    if (!dots) return name;
    const base = pkg.slice(0, pkg.length - (dots.length - 1));
    return [...base, ...(name ? [name] : [])].join('.');
  };
  const names = new Map();
  const aliases = new Map();
  for (const s of statements) {
    const from = /^from\s+(\.*)([\w.]*)\s+import\s+(.+)$/.exec(s);
    if (from) {
      const mod = absolute(from[1], from[2]);
      for (const part of from[3].replace(/[()]/g, '').split(',')) {
        const m = /^\s*([\w]+)(?:\s+as\s+([\w]+))?\s*$/.exec(part);
        if (!m) continue;
        const local = m[2] || m[1];
        const sub = mod ? `${mod}.${m[1]}` : m[1];
        if (modules.has(sub)) aliases.set(local, sub);
        else names.set(local, { module: mod, name: m[1] });
      }
      continue;
    }
    const imp = /^import\s+(.+)$/.exec(s);
    if (!imp) continue;
    for (const part of imp[1].split(',')) {
      const m = /^\s*([\w.]+)(?:\s+as\s+([\w]+))?\s*$/.exec(part);
      if (m) aliases.set(m[2] || m[1], m[1]);
    }
  }
  return { names, modules: aliases };
}

// [{ path, line, function, name, kind: 'helper' | 'wrapper' | 'vendor' }]
export function scanProviderCalls(ctx, registry) {
  const helpers = (registry?.providerHelpers || []).map((h) => h.function);
  const wrappers = [];
  for (const p of registry?.purposes || []) {
    for (const s of p.callSites || []) {
      if (!s.function.includes('.') && !wrappers.some((w) => w.path === s.path && w.function === s.function)) wrappers.push(s);
    }
  }
  const files = backendPythonFiles(ctx);
  const modules = new Set(files.map(moduleOf));
  const refs = [];
  for (const file of files) {
    const text = ctx.read(file);
    if (!text) continue;
    const lines = pythonLines(text);
    const names = new Set(helpers);
    for (const l of lines) {
      if (!l.importLine) continue;
      for (const m of l.importLine.matchAll(IMPORT_AS)) if (helpers.includes(m[1])) names.add(m[2]);
    }
    const patterns = [...names].map((n) => [n, HELPER_REF(n)]);
    const imports = importsOf(file, lines, modules);
    const wrapped = [];
    for (const w of wrappers) {
      const module = moduleOf(w.path);
      const label = `${w.path}::${w.function}`;
      if (w.path === file) wrapped.push({ label, def: w.function, re: WRAPPER_REF(w.function) });
      for (const [local, target] of imports.names) {
        if (target.module === module && target.name === w.function) wrapped.push({ label, re: WRAPPER_REF(local) });
      }
      for (const [local, target] of imports.modules) {
        if (target === module) wrapped.push({ label, re: DOTTED_REF(local, w.function) });
      }
    }
    lines.forEach((l, i) => {
      if (!l.code) return;
      const def = DEF.exec(l.code);
      for (const [name, re] of patterns) {
        if (!re.test(l.code)) continue;
        if (def && def.groups.name === name) continue;
        refs.push({ path: file, line: i + 1, function: l.fn, name, kind: 'helper' });
      }
      for (const w of wrapped) {
        if (!w.re.test(l.bare)) continue;
        if (def && w.def && def.groups.name === w.def) continue;
        refs.push({ path: file, line: i + 1, function: l.fn, name: w.label, kind: 'wrapper' });
      }
      for (const re of VENDOR_MARKERS) {
        if (re.test(l.code)) refs.push({ path: file, line: i + 1, function: l.fn, name: re.source, kind: 'vendor' });
      }
    });
  }
  return refs;
}

// Top-level function and class-method names a Python file defines.
export function definedFunctions(text) {
  const out = new Set();
  let cls = '';
  for (const line of (text || '').split('\n')) {
    const c = CLASS.exec(line);
    if (c) { cls = c.groups.name; continue; }
    const d = DEF.exec(line);
    if (!d) { if (/^\S/.test(line) && !line.startsWith('@') && !line.startsWith('#')) cls = ''; continue; }
    if (d.groups.indent.length === 0) { out.add(d.groups.name); cls = ''; }
    else if (cls && d.groups.indent.length <= 4) out.add(`${cls}.${d.groups.name}`);
  }
  return out;
}
