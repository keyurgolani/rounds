// Pretty-printer for run/eval values.
//
// JSON.stringify(v, null, 2) puts every array element on its own line,
// which makes the cards in the Result view tall and scroll-heavy for
// short lists like `[1, 2, 3]`. The user prefers list elements to stay
// inline. This formatter:
//
//   - renders arrays inline (`[1, 2, 3]`) regardless of length
//   - renders objects pretty-printed when long, inline when short
//   - leaves primitives to JSON.stringify (correct quoting/escaping)
//
// Long inline arrays still wrap visually because the consumer renders
// inside a <pre> with `white-space: pre-wrap`.

const INLINE_OBJECT_LIMIT = 60;

export function formatValue(v: unknown, indent = 0): string {
  if (v === undefined) return 'undefined';
  if (v === null || typeof v !== 'object') return JSON.stringify(v);

  if (Array.isArray(v)) {
    return '[' + v.map((item) => formatInline(item)).join(', ') + ']';
  }

  const entries = Object.entries(v as Record<string, unknown>);
  if (entries.length === 0) return '{}';

  const inline =
    '{ ' +
    entries.map(([k, val]) => `${JSON.stringify(k)}: ${formatInline(val)}`).join(', ') +
    ' }';
  if (inline.length <= INLINE_OBJECT_LIMIT) return inline;

  const padInner = '  '.repeat(indent + 1);
  const padOuter = '  '.repeat(indent);
  return (
    '{\n' +
    entries
      .map(([k, val]) => `${padInner}${JSON.stringify(k)}: ${formatValue(val, indent + 1)}`)
      .join(',\n') +
    `\n${padOuter}}`
  );
}

function formatInline(v: unknown): string {
  if (v === undefined) return 'undefined';
  if (v === null || typeof v !== 'object') return JSON.stringify(v);
  if (Array.isArray(v)) {
    return '[' + v.map(formatInline).join(', ') + ']';
  }
  const entries = Object.entries(v as Record<string, unknown>);
  return (
    '{' +
    entries.map(([k, val]) => `${JSON.stringify(k)}: ${formatInline(val)}`).join(', ') +
    '}'
  );
}
