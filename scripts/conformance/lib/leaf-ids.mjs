// Leaf ID registry access. contracts/vocabulary/leaf-ids.json lists the 176
// filed leaves, the kept refinement proposals, and the rejected (folded) ones.

export const LEAF_IDS_PATH = 'contracts/vocabulary/leaf-ids.json';
export const LEAF_ID_PATTERN = /^ROUNDS-\d{2}[A-Z]?-L\d{2}$/;
// A reference may name a stage: ROUNDS-00A-L01/S3, ROUNDS-32-L10/SB.3.
export const LEAF_REF_PATTERN = /^(ROUNDS-\d{2}[A-Z]?-L\d{2})(\/[A-Za-z0-9.]+)?$/;

export function loadLeafIds(ctx) {
  if (!ctx.exists(LEAF_IDS_PATH)) return null;
  try {
    return ctx.readJson(LEAF_IDS_PATH);
  } catch {
    return null;
  }
}

// Returns a resolver: ref -> { ok, id, status, reason }. A rejected leaf and an
// unknown ID both fail; a stage suffix resolves on the leaf part.
export function leafResolver(registry) {
  const byId = new Map();
  for (const leaf of registry?.leaves || []) byId.set(leaf.id, leaf);
  return (ref) => {
    if (typeof ref !== 'string') return { ok: false, reason: 'not a string' };
    const m = LEAF_REF_PATTERN.exec(ref);
    if (!m) return { ok: false, reason: `"${ref}" is not a leaf ID` };
    const leaf = byId.get(m[1]);
    if (!leaf) return { ok: false, reason: `${m[1]} is not in ${LEAF_IDS_PATH}` };
    if (leaf.status === 'rejected') {
      return { ok: false, reason: `${m[1]} was rejected${leaf.foldedInto ? ` (folded into ${leaf.foldedInto})` : ''}` };
    }
    return { ok: true, id: m[1], status: leaf.status, issue: leaf.issue };
  };
}
