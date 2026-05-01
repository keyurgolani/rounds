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

export type Shape =
  | 'linked_list_array'
  | 'tree_level_order'
  | 'graph_adjacency'
  | 'verbose';

export function toVerbose(
  value: unknown,
  shape: Shape,
  template: NodeTemplate,
): VerboseGraph {
  if (shape === 'verbose') return value as VerboseGraph;
  if (shape === 'linked_list_array') return linkedListArray(value as unknown[], template);
  if (shape === 'tree_level_order') return treeLevelOrder(value as unknown[], template);
  if (shape === 'graph_adjacency')
    return graphAdjacency(value as Record<string, unknown[]>, template);
  throw new Error(`Unsupported shape: ${shape}`);
}

function linkedListArray(values: unknown[], t: NodeTemplate): VerboseGraph {
  if (!values || values.length === 0) return { nodes: [], entry: null };
  const f = t.fields[0].name;
  const l = t.links[0].name;
  return {
    nodes: values.map((v, i) => ({
      id: i,
      fields: { [f]: v },
      links: { [l]: i + 1 < values.length ? i + 1 : null },
    })),
    entry: 0,
  };
}

function treeLevelOrder(values: unknown[], t: NodeTemplate): VerboseGraph {
  if (!values || values.length === 0) return { nodes: [], entry: null };
  const f = t.fields[0].name;
  const linkNames = t.links.map((x) => x.name);
  if (linkNames.length !== 2) {
    throw new Error('tree_level_order requires exactly 2 links');
  }
  const nodes: VerboseNode[] = [];
  const idForPos: Record<number, number> = {};
  for (let pos = 0; pos < values.length; pos++) {
    if (values[pos] === null) continue;
    idForPos[pos] = nodes.length;
    const linkInit: Record<string, NodeRef> = {};
    for (const ln of linkNames) linkInit[ln] = null;
    nodes.push({ id: nodes.length, fields: { [f]: values[pos] }, links: linkInit });
  }
  if (idForPos[0] === undefined) return { nodes: [], entry: null };
  const queue: [number, number][] = [[0, idForPos[0]]];
  let cursor = 1;
  while (queue.length > 0 && cursor < values.length) {
    const next = queue.shift()!;
    const parentId = next[1];
    for (const ln of linkNames) {
      if (cursor >= values.length) break;
      const childPos = cursor++;
      if (values[childPos] === null) continue;
      const childId = idForPos[childPos];
      nodes[parentId].links[ln] = childId;
      queue.push([childPos, childId]);
    }
  }
  return { nodes, entry: 0 };
}

function graphAdjacency(adj: Record<string, unknown[]>, t: NodeTemplate): VerboseGraph {
  const f = t.fields[0].name;
  const l = t.links[0].name;
  const keys = Object.keys(adj);
  const idForKey: Record<string, number> = {};
  keys.forEach((k, i) => {
    idForKey[k] = i;
  });
  const nodes: VerboseNode[] = keys.map((k, i) => {
    const parsed = parseInt(k, 10);
    const val: unknown = Number.isNaN(parsed) ? k : parsed;
    const neighborIds = adj[k]
      .filter((n) => idForKey[String(n)] !== undefined)
      .map((n) => idForKey[String(n)]);
    return { id: i, fields: { [f]: val }, links: { [l]: neighborIds } };
  });
  return { nodes, entry: nodes.length > 0 ? 0 : null };
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
