// Compact, stable JSON for generated files: a value stays on one line when
// it fits in `width` columns at its indent; otherwise its members go one per
// line. Key order is the caller's.

export function prettyJson(value, width = 140) {
  const fmt = (v, indent, prefix) => {
    const one = JSON.stringify(v);
    if (one === undefined) return 'null';
    if (v === null || typeof v !== 'object' || indent.length + prefix.length + one.length <= width) return one;
    const inner = `${indent}  `;
    if (Array.isArray(v)) {
      if (!v.length) return '[]';
      return `[\n${v.map((x) => `${inner}${fmt(x, inner, '')}`).join(',\n')}\n${indent}]`;
    }
    const keys = Object.keys(v);
    if (!keys.length) return '{}';
    return `{\n${keys.map((k) => {
      const p = `${JSON.stringify(k)}: `;
      return `${inner}${p}${fmt(v[k], inner, p)}`;
    }).join(',\n')}\n${indent}}`;
  };
  return `${fmt(value, '', '')}\n`;
}
