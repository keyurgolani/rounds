// The provider-call scan (ROUNDS-14-L01). Every reference to a provider
// helper in backend Python, a call or the name passed as a value, through a
// local or aliased import too, must sit in a function the purpose registry
// names. Vendor SDK calls and API headers must sit inside a helper. Tests
// are skipped. The scan reads lines: a top-level `def` (or a class's
// method) opens a function that runs until the next top-level statement,
// and docstrings and comments are skipped.

const HELPER_REF = (name) => new RegExp(`(?<![A-Za-z0-9_])${name.replace(/[$]/g, '\\$')}(?![A-Za-z0-9_])`);
const VENDOR_MARKERS = [/\bAsyncOpenAI\s*\(/, /\bAsyncAnthropic\s*\(/, /\.chat\.completions\.create\s*\(/, /\.messages\.create\s*\(/, /["']anthropic-version["']/];
const DEF = /^(?<indent>[ \t]*)(?:async[ \t]+)?def[ \t]+(?<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*\(/;
const CLASS = /^class[ \t]+(?<name>[A-Za-z_][A-Za-z0-9_]*)/;
const IMPORT_AS = /\b([A-Za-z_][A-Za-z0-9_]*)\s+as\s+([A-Za-z_][A-Za-z0-9_]*)/g;

export function backendPythonFiles(ctx) {
  return ctx.files().filter((f) => f.startsWith('backend/') && f.endsWith('.py')
    && !f.startsWith('backend/tests/') && !/(^|\/)(conftest|test_[^/]*)\.py$/.test(f)).sort();
}

// Lines with docstrings, comments, and import statements blanked, each
// with the function it sits in ("" at module level).
export function pythonLines(text) {
  const out = [];
  let fn = '';
  let cls = '';
  let inDoc = null;
  let importing = false;
  for (const raw of text.split('\n')) {
    let line = raw;
    if (inDoc) {
      const end = line.indexOf(inDoc);
      if (end === -1) { out.push({ code: '', fn, raw }); continue; }
      line = line.slice(end + 3);
      inDoc = null;
    }
    // Drop a docstring that opens (and maybe closes) on this line.
    for (;;) {
      const m = /("""|''')/.exec(line);
      if (!m) break;
      const close = line.indexOf(m[1], m.index + 3);
      if (close === -1) { inDoc = m[1]; line = line.slice(0, m.index); break; }
      line = line.slice(0, m.index) + line.slice(close + 3);
    }
    const hash = line.search(/(^|[ \t])#/);
    if (hash !== -1) line = line.slice(0, hash);
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
    out.push({ code: isImport ? '' : line, importLine: isImport ? line : '', fn, raw });
  }
  return out;
}

// [{ path, line, function, name, kind: 'helper' | 'vendor' }]
export function scanProviderCalls(ctx, registry) {
  const helpers = (registry?.providerHelpers || []).map((h) => h.function);
  const refs = [];
  for (const file of backendPythonFiles(ctx)) {
    const text = ctx.read(file);
    if (!text) continue;
    const lines = pythonLines(text);
    const names = new Set(helpers);
    for (const l of lines) {
      if (!l.importLine) continue;
      for (const m of l.importLine.matchAll(IMPORT_AS)) if (helpers.includes(m[1])) names.add(m[2]);
    }
    const patterns = [...names].map((n) => [n, HELPER_REF(n)]);
    lines.forEach((l, i) => {
      if (!l.code) return;
      const def = DEF.exec(l.code);
      for (const [name, re] of patterns) {
        if (!re.test(l.code)) continue;
        if (def && def.groups.name === name) continue;
        refs.push({ path: file, line: i + 1, function: l.fn, name, kind: 'helper' });
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
