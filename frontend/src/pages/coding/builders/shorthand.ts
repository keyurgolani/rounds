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
