import type { PatchProposal } from './AIPatchView';

/**
 * Walks `content` to find the first JSON-array span — the `[..]`
 * tail that the model emits at the end of an /edit response. Uses a
 * proper bracket-aware scanner that respects JSON string escapes,
 * so brackets inside `"contents": "arr[i]"` don't confuse the parser
 * (the original lastIndexOf-based approach silently broke whenever
 * the patch's contents contained a `[`).
 */
export function findJsonArraySpan(
  content: string,
): { start: number; end: number } | null {
  // Prefer a fenced block when present.
  const fence = content.match(/```(?:json)?\s*(\[)/);
  let cursor = -1;
  if (fence && fence.index !== undefined) {
    cursor = fence.index + fence[0].length - 1;
  } else {
    cursor = content.indexOf('[');
  }
  if (cursor === -1) return null;
  let depth = 0;
  let inString = false;
  let escape = false;
  for (let i = cursor; i < content.length; i++) {
    const ch = content[i];
    if (inString) {
      if (escape) {
        escape = false;
      } else if (ch === '\\') {
        escape = true;
      } else if (ch === '"') {
        inString = false;
      }
      continue;
    }
    if (ch === '"') inString = true;
    else if (ch === '[') depth++;
    else if (ch === ']') {
      depth--;
      if (depth === 0) return { start: cursor, end: i + 1 };
    }
  }
  return null;
}

/**
 * Splits an assistant message into the prose preamble and a
 * (possibly empty) list of patches. Returns patches=null when the
 * content has no parseable JSON-array tail. Matches the live
 * AIChatPanel parsing logic — extracted into a shared helper so the
 * GradeReport modal AND the chat panel's rehydration path use the
 * same source of truth (otherwise refresh would render raw JSON
 * because the rehydrated message keeps the JSON in `content`).
 */
export function splitPatches(content: string): {
  prose: string;
  patches: PatchProposal[] | null;
} {
  const span = findJsonArraySpan(content);
  if (!span) return { prose: content, patches: null };
  const tail = content.slice(span.start, span.end);
  let parsed: unknown;
  try {
    parsed = JSON.parse(tail);
  } catch {
    return { prose: content, patches: null };
  }
  if (!Array.isArray(parsed)) return { prose: content, patches: null };
  const patches: PatchProposal[] = [];
  for (const item of parsed) {
    if (
      item &&
      typeof item === 'object' &&
      typeof (item as PatchProposal).file === 'string' &&
      typeof (item as PatchProposal).contents === 'string'
    ) {
      patches.push({
        file: (item as PatchProposal).file,
        patch_kind: 'replace',
        contents: (item as PatchProposal).contents,
      });
    }
  }
  if (patches.length === 0) return { prose: content, patches: null };
  // Discard everything from the JSON tail onward (and any stray
  // ```json fence markers that lead into it).
  const prose = content
    .slice(0, span.start)
    .replace(/```(?:json)?\s*$/, '')
    .trimEnd();
  return { prose, patches };
}
