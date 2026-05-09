import type { NodeTemplate } from '../types';

export type NodeRef = number | null | NodeRef[];

export interface VerboseNode {
  id: number;
  fields: Record<string, unknown>;
  links: Record<string, NodeRef>;
}

export interface VerboseGraph {
  nodes: VerboseNode[];
  entry: number | null;
}

/** Walk a singly-linked verbose graph, returning the field values in order. */
export function fromVerboseChain(
  v: VerboseGraph,
  linkName: string,
  fieldName: string,
): unknown[] {
  if (v.entry === null) return [];
  const byId = new Map<number, VerboseNode>();
  for (const n of v.nodes) byId.set(n.id, n);
  const out: unknown[] = [];
  let cur: number | null = v.entry;
  while (cur !== null && cur !== undefined) {
    const node = byId.get(cur);
    if (!node) break;
    out.push(node.fields[fieldName]);
    const next = node.links[linkName];
    cur = typeof next === 'number' ? next : null;
  }
  return out;
}

/** Walk a verbose tree level-order, emitting nulls for missing children. */
export function fromVerboseLevelOrder(
  v: VerboseGraph,
  leftName: string,
  rightName: string,
  fieldName: string,
): (unknown | null)[] {
  if (v.entry === null) return [];
  const byId = new Map<number, VerboseNode>();
  for (const n of v.nodes) byId.set(n.id, n);
  const out: (unknown | null)[] = [];
  const queue: (number | null)[] = [v.entry];
  while (queue.length > 0) {
    const cur = queue.shift();
    if (cur === undefined) break;
    if (cur === null) {
      out.push(null);
      continue;
    }
    const node = byId.get(cur);
    if (!node) {
      out.push(null);
      continue;
    }
    out.push(node.fields[fieldName]);
    const left = node.links[leftName];
    const right = node.links[rightName];
    queue.push(typeof left === 'number' ? left : null);
    queue.push(typeof right === 'number' ? right : null);
  }
  while (out.length > 0 && out[out.length - 1] === null) out.pop();
  return out;
}

/**
 * Serialize a verbose chain as a flat value array — what the build-time
 * `_linked_list_array` produced. Inverse of `fromChainShorthand`.
 */
export function toChainShorthand(
  v: VerboseGraph,
  linkName: string,
  fieldName: string,
): unknown[] {
  return fromVerboseChain(v, linkName, fieldName);
}

/**
 * Parse a flat-value-array string (e.g. "[2, 4, 3]") into a verbose
 * singly-linked chain. Mirrors the build-time `_linked_list_array`.
 */
export function fromChainShorthand(
  raw: string,
  template: NodeTemplate,
): VerboseGraph {
  const trimmed = raw.trim();
  if (!trimmed) return { nodes: [], entry: null };
  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed.replace(/\bNone\b/g, 'null'));
  } catch {
    throw new Error('paste must be a JSON array, e.g. [2, 4, 3]');
  }
  if (!Array.isArray(parsed)) {
    throw new Error('paste must be a JSON array');
  }
  const values = parsed as unknown[];
  if (values.length === 0) return { nodes: [], entry: null };

  const fieldName = template.fields[0]?.name ?? 'val';
  const linkName = template.links[0]?.name ?? 'next';
  const nodes: VerboseNode[] = values.map((v, i) => ({
    id: i,
    fields: { [fieldName]: v },
    links: { [linkName]: i + 1 < values.length ? i + 1 : null },
  }));
  return { nodes, entry: 0 };
}

/**
 * Serialize a verbose tree as a LeetCode-style level-order array
 * (`[1, null, 2, 3]`). Trailing nulls are trimmed. The inverse of
 * `fromLevelOrderShorthand` — used by the TreeCanvas "Copy as shorthand"
 * button so authors can paste the result into another problem or share it.
 */
export function toLevelOrderShorthand(
  v: VerboseGraph,
  leftName: string,
  rightName: string,
  fieldName: string,
): (unknown | null)[] {
  return fromVerboseLevelOrder(v, leftName, rightName, fieldName);
}

/**
 * Parse a LeetCode-style level-order array string (e.g. "[1, null, 2, 3]")
 * into a verbose tree. Mirrors the build-time
 * `pocketbase/seeds/builder/_shorthand.py::_tree_level_order` so
 * paste-shorthand is round-trip-stable with seed data.
 */
export function fromLevelOrderShorthand(
  raw: string,
  template: NodeTemplate,
): VerboseGraph {
  const trimmed = raw.trim();
  if (!trimmed) return { nodes: [], entry: null };
  let parsed: unknown;
  try {
    // Tolerate Python `None` and `null` interchangeably.
    parsed = JSON.parse(trimmed.replace(/\bNone\b/g, 'null'));
  } catch {
    throw new Error('paste must be a JSON array, e.g. [1, null, 2, 3]');
  }
  if (!Array.isArray(parsed)) {
    throw new Error('paste must be a JSON array');
  }
  const values = parsed as (unknown | null)[];
  if (values.length === 0) return { nodes: [], entry: null };

  const fieldName = template.fields[0]?.name ?? 'val';
  const linkNames = template.links.map((l) => l.name);
  if (linkNames.length !== 2) {
    throw new Error('tree shorthand requires exactly 2 links (left, right)');
  }

  // Build node objects in source order, skipping nulls.
  const nodes: VerboseNode[] = [];
  const idForPos = new Map<number, number>();
  for (let pos = 0; pos < values.length; pos++) {
    const v = values[pos];
    if (v === null || v === undefined) continue;
    const id = nodes.length;
    idForPos.set(pos, id);
    nodes.push({
      id,
      fields: { [fieldName]: v },
      links: { [linkNames[0]]: null, [linkNames[1]]: null },
    });
  }
  if (!idForPos.has(0)) return { nodes: [], entry: null };

  // BFS-assign children, mirroring the Python build-time helper exactly.
  const queue: [number, number][] = [[0, idForPos.get(0)!]];
  let cursor = 1;
  while (queue.length > 0 && cursor < values.length) {
    const [, parentId] = queue.shift()!;
    for (const linkName of linkNames) {
      if (cursor >= values.length) break;
      const childPos = cursor;
      cursor += 1;
      const v = values[childPos];
      if (v === null || v === undefined) continue;
      const childId = idForPos.get(childPos)!;
      nodes[parentId].links[linkName] = childId;
      queue.push([childPos, childId]);
    }
  }
  return { nodes, entry: 0 };
}

/**
 * Serialize a verbose graph as an adjacency dict keyed by stringified
 * node values. Mirrors the build-time `_graph_adjacency` shorthand so
 * Copy/Paste round-trip-stably with seeded test cases.
 */
export function toAdjacencyShorthand(
  v: VerboseGraph,
  linkName: string,
  fieldName: string,
): Record<string, unknown[]> {
  const out: Record<string, unknown[]> = {};
  const byId = new Map<number, VerboseNode>();
  for (const n of v.nodes) byId.set(n.id, n);
  for (const node of v.nodes) {
    const key = String(node.fields[fieldName]);
    const links = node.links[linkName];
    const neighborIds: number[] = Array.isArray(links) ? (links.filter((x): x is number => typeof x === 'number')) : [];
    out[key] = neighborIds.map((nid) => byId.get(nid)?.fields[fieldName] ?? nid);
  }
  return out;
}

/**
 * Parse an adjacency-dict string (e.g. '{"1":[2,3], "2":[1]}') into a
 * verbose graph. Keys are stringified node values; entry is the first key.
 */
export function fromAdjacencyShorthand(
  raw: string,
  template: NodeTemplate,
): VerboseGraph {
  const trimmed = raw.trim();
  if (!trimmed) return { nodes: [], entry: null };
  let parsed: unknown;
  try {
    parsed = JSON.parse(trimmed);
  } catch {
    throw new Error('paste must be JSON, e.g. {"1": [2], "2": [1]}');
  }
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('paste must be a JSON object');
  }
  const adj = parsed as Record<string, unknown>;
  const fieldName = template.fields[0]?.name ?? 'val';
  const fieldType = template.fields[0]?.type ?? 'int';
  const linkName = template.links[0]?.name ?? 'neighbors';

  const keys = Object.keys(adj);
  const idForKey = new Map<string, number>();
  keys.forEach((k, i) => idForKey.set(k, i));

  const nodes: VerboseNode[] = keys.map((k, i) => {
    const raw = adj[k];
    const neighbors: number[] = Array.isArray(raw)
      ? (raw as unknown[]).flatMap((n) => {
          const idx = idForKey.get(String(n));
          return idx === undefined ? [] : [idx];
        })
      : [];
    let val: unknown = k;
    if (fieldType === 'int') {
      const n = parseInt(k, 10);
      if (!Number.isNaN(n)) val = n;
    } else if (fieldType === 'float') {
      const n = parseFloat(k);
      if (!Number.isNaN(n)) val = n;
    }
    return {
      id: i,
      fields: { [fieldName]: val },
      links: { [linkName]: neighbors },
    };
  });
  return { nodes, entry: nodes.length > 0 ? 0 : null };
}

/**
 * Type-narrow an unknown value to `VerboseGraph`.
 *
 * Previously this module also accepted shorthand inputs (level-order
 * arrays, adjacency dicts, flat lists) and converted them. That path is
 * gone — node-typed test inputs MUST now arrive as canonical verbose
 * JSON (the seed builder converts authoring shorthand at build time via
 * `pocketbase/seeds/builder/_shorthand.py`). If a test case shows up
 * with a legacy shape, this guard returns an empty graph and the editor
 * surfaces it as such, which is what we want — fail loudly instead of
 * silently re-shaping.
 */
export function asVerbose(value: unknown, _template: NodeTemplate): VerboseGraph {
  if (
    value &&
    typeof value === 'object' &&
    !Array.isArray(value) &&
    'nodes' in value &&
    'entry' in value
  ) {
    return value as VerboseGraph;
  }
  return { nodes: [], entry: null };
}
