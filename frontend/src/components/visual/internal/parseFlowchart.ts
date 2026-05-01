// Small parser for the Mermaid `graph TD` / `flowchart TD` subset used in
// seed content. Supports rectangle `[..]` and diamond `{..}` node shapes
// (plus rounded `(..)` and circle `((..))`), plain `-->` edges and
// labeled `-->|text|` edges. Unknown syntax causes the caller to fall
// back to the default Mermaid renderer.

export type FlowShape = 'rect' | 'diamond' | 'round' | 'circle';

export interface FlowNode {
  id: string;
  label: string;
  shape: FlowShape;
}

export interface FlowEdge {
  source: string;
  target: string;
  label?: string;
  dashed?: boolean;
}

export interface FlowchartData {
  nodes: FlowNode[];
  edges: FlowEdge[];
}

const HEADER_RE = /^(graph|flowchart)\s+(TB|TD|BT|RL|LR)\s*$/i;

// Match an id followed by a shape decorator. Captures shape + raw label.
// We parse each line left-to-right extracting up to two nodes and one edge.
const NODE_RE =
  /^([A-Za-z_][A-Za-z0-9_]*)(?:(\[\[|\(\(|\{|\[|\()([^\]\)\}]*)(\]\]|\)\)|\}|\]|\)))?/;

const EDGE_RE = /^\s*(-\.->|==>|-->|---|-\.-|==|--)(?:\|([^|]+)\|)?\s*/;

function decodeLabel(raw: string): string {
  const trimmed = raw.trim();
  if (trimmed.length >= 2 && trimmed.startsWith('"') && trimmed.endsWith('"')) {
    return trimmed.slice(1, -1);
  }
  return trimmed;
}

function shapeFor(open: string | undefined): FlowShape {
  if (!open) return 'rect';
  if (open === '{') return 'diamond';
  if (open === '((') return 'circle';
  if (open === '(') return 'round';
  return 'rect';
}

// Attempt to parse a single (already-trimmed) body line. A line is either
// - an isolated node declaration: `A[...]` or just `A`
// - an edge chain: `A[..] --> B{..} -->|lbl| C` (we support at most two
//   nodes per line, chained lines are split by the caller).
function parseLine(
  line: string,
  nodes: Map<string, FlowNode>,
): FlowEdge[] {
  let rest = line.trim();
  if (!rest) return [];

  const edges: FlowEdge[] = [];
  let lastId: string | null = null;
  let pendingEdge: { dashed: boolean; label?: string } | null = null;

  while (rest.length > 0) {
    const nodeMatch = rest.match(NODE_RE);
    if (!nodeMatch) return []; // unparseable — drop line (caller decides fallback)

    const [whole, id, open, rawLabel] = nodeMatch;
    const shape = shapeFor(open);
    const label = open ? decodeLabel(rawLabel ?? '') : id;

    if (!nodes.has(id)) {
      nodes.set(id, { id, label, shape });
    } else if (open) {
      // Update shape/label the first time a shape decorator appears.
      const existing = nodes.get(id)!;
      if (!existing.label || existing.label === existing.id) {
        nodes.set(id, { id, label, shape });
      }
    }

    if (lastId !== null && pendingEdge) {
      edges.push({
        source: lastId,
        target: id,
        label: pendingEdge.label,
        dashed: pendingEdge.dashed,
      });
    }

    lastId = id;
    pendingEdge = null;
    rest = rest.slice(whole.length);

    const edgeMatch = rest.match(EDGE_RE);
    if (!edgeMatch) break;
    const [eWhole, op, eLabel] = edgeMatch;
    pendingEdge = {
      dashed: op.startsWith('-.'),
      label: eLabel?.trim() || undefined,
    };
    rest = rest.slice(eWhole.length);
  }

  return edges;
}

export function parseFlowchart(source: string): FlowchartData | null {
  const lines = source.split(/\r?\n/);
  if (lines.length === 0) return null;

  // First non-empty line must be the header.
  let headerOk = false;
  const body: string[] = [];
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith('%%')) continue; // Mermaid comments
    if (!headerOk) {
      if (!HEADER_RE.test(line)) return null;
      headerOk = true;
      continue;
    }
    // Skip subgraph/end/style lines — we do not support them and want
    // callers to fall back to Mermaid for those diagrams.
    const lower = line.toLowerCase();
    if (
      lower.startsWith('subgraph') ||
      lower === 'end' ||
      lower.startsWith('style ') ||
      lower.startsWith('classdef ') ||
      lower.startsWith('class ') ||
      lower.startsWith('click ')
    ) {
      return null;
    }
    body.push(line);
  }
  if (!headerOk) return null;

  const nodes = new Map<string, FlowNode>();
  const edges: FlowEdge[] = [];
  for (const line of body) {
    const lineEdges = parseLine(line, nodes);
    edges.push(...lineEdges);
  }

  if (nodes.size === 0) return null;
  return { nodes: [...nodes.values()], edges };
}
