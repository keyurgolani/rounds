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
