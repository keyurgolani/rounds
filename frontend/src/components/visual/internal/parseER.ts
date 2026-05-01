// Parser for the Mermaid `erDiagram` subset used in seed content.
// Supports entity blocks (`ENTITY { type name KEY }`) and relationship
// lines with cardinality markers (`||--o{`, `||--||`, `}o--o{`, etc.).

export type ERCardinality = 'one' | 'many' | 'zero-or-one' | 'zero-or-many';

export interface ERColumn {
  type: string;
  name: string;
  keys: ('PK' | 'FK' | 'UK')[];
  comment?: string;
}

export interface EREntity {
  name: string;
  columns: ERColumn[];
}

export interface ERRelation {
  source: string;
  target: string;
  sourceCard: ERCardinality;
  targetCard: ERCardinality;
  label?: string;
  identifying: boolean;
}

export interface ERData {
  entities: EREntity[];
  relations: ERRelation[];
}

const HEADER_RE = /^erDiagram\s*$/i;

// Cardinality token (source side is mirrored: `||` reads right-to-left).
// Source tokens appear on the LEFT of the connector (reading away from the
// entity), so for source `||` both pipes touch the entity — one/one.
const SRC_CARD: Record<string, ERCardinality> = {
  '||': 'one',
  '|o': 'zero-or-one',
  'o|': 'zero-or-one',
  '}o': 'zero-or-many',
  '}|': 'many',
};
const TGT_CARD: Record<string, ERCardinality> = {
  '||': 'one',
  'o|': 'zero-or-one',
  '|o': 'zero-or-one',
  'o{': 'zero-or-many',
  '|{': 'many',
};

// Relation: ENTITY_A <srcCard><line><tgtCard> ENTITY_B : label
// Line is `--` (identifying) or `..` (non-identifying).
const REL_RE =
  /^([A-Za-z_][A-Za-z0-9_-]*)\s+([|}o]{2})(--|\.\.)([|o{]{2})\s+([A-Za-z_][A-Za-z0-9_-]*)(?:\s*:\s*(.+))?$/;

const ENTITY_HEADER_RE = /^([A-Za-z_][A-Za-z0-9_-]*)\s*\{\s*$/;

function parseColumn(line: string): ERColumn | null {
  // `bigint id PK` / `varchar email "user email"` / `text long_url`
  // Split on whitespace but keep quoted comments intact.
  const quoteIdx = line.indexOf('"');
  const head = quoteIdx === -1 ? line : line.slice(0, quoteIdx).trim();
  const comment =
    quoteIdx === -1
      ? undefined
      : line
          .slice(quoteIdx)
          .replace(/^"|"$/g, '')
          .trim() || undefined;
  const parts = head.split(/\s+/).filter(Boolean);
  if (parts.length < 2) return null;
  const [type, name, ...flags] = parts;
  const keys: ERColumn['keys'] = [];
  for (const f of flags) {
    const upper = f.toUpperCase();
    if (upper === 'PK' || upper === 'FK' || upper === 'UK') keys.push(upper);
  }
  return { type, name, keys, comment };
}

export function parseER(source: string): ERData | null {
  const lines = source.split(/\r?\n/);
  let headerOk = false;
  const bodyLines: string[] = [];
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    if (line.startsWith('%%')) continue;
    if (!headerOk) {
      if (!HEADER_RE.test(line)) return null;
      headerOk = true;
      continue;
    }
    bodyLines.push(line);
  }
  if (!headerOk) return null;

  const entities = new Map<string, EREntity>();
  const relations: ERRelation[] = [];

  function ensureEntity(name: string): EREntity {
    if (!entities.has(name)) entities.set(name, { name, columns: [] });
    return entities.get(name)!;
  }

  let currentEntity: EREntity | null = null;

  for (const line of bodyLines) {
    if (currentEntity) {
      if (line === '}') {
        currentEntity = null;
        continue;
      }
      const col = parseColumn(line);
      if (col) currentEntity.columns.push(col);
      continue;
    }

    const entMatch = line.match(ENTITY_HEADER_RE);
    if (entMatch) {
      currentEntity = ensureEntity(entMatch[1]);
      continue;
    }

    const relMatch = line.match(REL_RE);
    if (relMatch) {
      const [, srcName, srcTok, lineTok, tgtTok, tgtName, label] = relMatch;
      const sourceCard = SRC_CARD[srcTok];
      const targetCard = TGT_CARD[tgtTok];
      if (!sourceCard || !targetCard) return null;
      ensureEntity(srcName);
      ensureEntity(tgtName);
      relations.push({
        source: srcName,
        target: tgtName,
        sourceCard,
        targetCard,
        label: label?.trim(),
        identifying: lineTok === '--',
      });
      continue;
    }

    // Unknown statement — bail so the caller can fall back to Mermaid.
    return null;
  }

  if (entities.size === 0) return null;
  return { entities: [...entities.values()], relations };
}
