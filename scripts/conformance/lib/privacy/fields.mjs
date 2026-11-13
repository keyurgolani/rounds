// Field ids and their resolution (ROUNDS-14-L01), as the evaluators read
// them: pb:<collection>[.<field>[#<pointer>]], storage:<family>,
// def:<schema>#<pointer>, request:<purpose>#<pointer>, and <entity>.<field>.

export const ID_FORMS = {
  pb: /^pb:([a-z_][a-z0-9_]*)(?:\.([A-Za-z_][A-Za-z0-9_]*)(#(?:\/[^/#]+)+)?)?$/,
  storage: /^storage:(\S+)$/,
  def: /^def:([a-z][a-z0-9-]*)(#(?:\/[^/#]+)+)$/,
  request: /^request:([a-z][a-z0-9_]*\.[a-z][a-z0-9_]*)(#(?:\/[^/#]+)+)$/,
  entity: /^([a-z][a-z0-9_]*)\.([a-z][a-z0-9_]*)$/,
};
export const SYSTEM_FIELDS = ['id', 'created', 'updated'];

export function idForm(id) {
  for (const [form, re] of Object.entries(ID_FORMS)) if (re.test(id)) return form;
  return null;
}

// Why a caller's id (a purpose input, or what a sink owner asks the
// evaluators about) is refused, or null. It takes one of the forms above
// and names one path: a `*` pointer segment is the map's pattern syntax,
// not a caller's, so it's refused outside a storage key. The evaluators
// refuse the same ids with INPUT_INVALID.
export function callerIdError(id) {
  if (typeof id !== 'string' || !idForm(id)) return 'is not a pb:, storage:, def:, request:, or <entity>.<field> id';
  if (id.startsWith('storage:')) return null;
  const hash = id.indexOf('#');
  if (hash !== -1 && id.slice(hash + 1).split('/').slice(1).includes('*')) return 'has a * pointer segment; a caller names one path, not a pattern';
  return null;
}

export function split(id) {
  const i = id.indexOf('#');
  return i === -1 ? [id, null] : [id.slice(0, i), id.slice(i + 1)];
}

export function segments(pointer) {
  if (!pointer) return [];
  return pointer.split('/').slice(1).map((s) => s.replace(/~1/g, '/').replace(/~0/g, '~'));
}

export function pointerMatch(pattern, segs) {
  return pattern.length <= segs.length && pattern.every((p, i) => p === '*' || p === segs[i]);
}

export function familyCovers(wide, narrow) {
  const re = new RegExp(`^${wide.split('*').map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('.*')}$`, 's');
  return re.test(narrow);
}

// A resolver over the field map's entries, matching backend/app/privacy/evaluator.py.
export function fieldResolver(entries) {
  const byId = new Map(entries.map((e) => [e.id, e]));
  const pointerEntries = new Map();
  for (const e of entries) {
    const [base, pointer] = split(e.id);
    if (pointer === null) continue;
    if (!pointerEntries.has(base)) pointerEntries.set(base, []);
    pointerEntries.get(base).push({ entry: e, pattern: segments(pointer) });
  }
  const storage = entries.filter((e) => e.id.startsWith('storage:'));
  const columns = (base) => {
    const alias = byId.get(base)?.pathsFrom;
    return alias ? [base, alias] : [base];
  };
  const resolve = (id) => {
    if (typeof id !== 'string' || !id) return null;
    if (byId.has(id)) return byId.get(id);
    if (id.startsWith('storage:')) {
      const key = id.slice('storage:'.length);
      const hits = storage.filter((e) => familyCovers(e.id.slice('storage:'.length), key));
      hits.sort((a, b) => (a.id.split('*').length - b.id.split('*').length) || (b.id.length - a.id.length));
      return hits[0] || null;
    }
    const [base, pointer] = split(id);
    if (pointer === null) {
      const m = /^pb:([a-z_][a-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$/.exec(base);
      if (m && SYSTEM_FIELDS.includes(m[2])) return byId.get(`pb:${m[1]}`) || null;
      return null;
    }
    const segs = segments(pointer);
    for (const column of columns(base)) {
      let best = null;
      for (const { entry, pattern } of pointerEntries.get(column) || []) {
        if (!pointerMatch(pattern, segs)) continue;
        const rank = [pattern.length, -pattern.filter((p) => p === '*').length];
        if (!best || rank[0] > best.rank[0] || (rank[0] === best.rank[0] && rank[1] > best.rank[1])) best = { rank, entry };
      }
      if (best) return best.entry;
    }
    return byId.get(base) || null;
  };
  return { resolve, byId, columns };
}

// The nearest entry above `id` (a pointer entry's column or a shorter
// pointer), for the tighten-only check on descendants.
export function ancestorOf(id, byId) {
  const [base, pointer] = split(id);
  if (pointer === null) return null;
  const segs = segments(pointer);
  for (let n = segs.length - 1; n >= 1; n--) {
    for (const [other, e] of byId) {
      if (other === id) continue;
      const [b, p] = split(other);
      if (b !== base || p === null) continue;
      const pattern = segments(p);
      if (pattern.length === n && pointerMatch(pattern, segs.slice(0, n).map((s, i) => (pattern[i] === '*' ? '*' : s)))) return e;
    }
  }
  return byId.get(base) || null;
}

const STORE = /^pb:[a-z_][a-z0-9_]*$/;

// The entries below `id`, as [{ id, entry }] in map order, where `id` is
// the descendant seen from `id` (a path read through `pathsFrom` keeps the
// caller's column): a store's fields and their paths, a column's paths, or
// the deeper paths under a pointer. A `*` in an entry matches any one
// segment; a caller's id has none (callerIdError). Matches the evaluators'
// `descendants`.
export function descendantsOf(id, entries, byId) {
  if (typeof id !== 'string' || id.startsWith('storage:')) return [];
  const out = [];
  const seen = new Set();
  const add = (did, entry) => { if (!seen.has(did)) { seen.add(did); out.push({ id: did, entry }); } };
  const aliasPaths = (column) => {
    const alias = byId.get(column)?.pathsFrom;
    if (!alias) return;
    for (const e of entries) {
      const [b, p] = split(e.id);
      if (p !== null && b === alias) add(`${column}#${p}`, e);
    }
  };
  const [base, pointer] = split(id);
  if (pointer === null) {
    if (STORE.test(base)) {
      for (const e of entries) if (e.id.startsWith(`${base}.`)) add(e.id, e);
      for (const e of entries) if (e.id.startsWith(`${base}.`) && !e.id.includes('#')) aliasPaths(e.id);
      return out;
    }
    for (const e of entries) {
      const [b, p] = split(e.id);
      if (p !== null && b === base) add(e.id, e);
    }
    aliasPaths(base);
    return out;
  }
  const segs = segments(pointer);
  const below = (p) => {
    const pattern = segments(p);
    return pattern.length > segs.length && segs.every((s, i) => s === '*' || pattern[i] === '*' || pattern[i] === s);
  };
  const alias = byId.get(base)?.pathsFrom;
  for (const e of entries) {
    const [b, p] = split(e.id);
    if (p === null || !below(p)) continue;
    if (b === base) add(e.id, e);
  }
  if (alias) {
    for (const e of entries) {
      const [b, p] = split(e.id);
      if (p !== null && b === alias && below(p)) add(`${base}#${p}`, e);
    }
  }
  return out;
}

// True when `inner` is `outer` or sits below it, by the same rule.
export function within(inner, outer) {
  if (inner === outer) return true;
  const [ob, op] = split(outer);
  const [ib, ip] = split(inner);
  if (op === null) {
    if (STORE.test(ob)) return inner.startsWith(`${ob}.`);
    return ib === ob && ip !== null;
  }
  if (ib !== ob || ip === null) return false;
  const o = segments(op);
  const n = segments(ip);
  return n.length >= o.length && o.every((s, i) => s === '*' || n[i] === '*' || n[i] === s);
}
