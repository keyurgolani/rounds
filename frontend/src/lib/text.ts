// Returns the first sentence of `text` capped at 140 characters; used
// by the detail-page AppHeader `description` slot so multi-paragraph
// prompts collapse to a single readable line under the title. Returns
// undefined for empty/missing input so callers can pass through cleanly.
export function oneLineSummary(text?: string | null): string | undefined {
  if (!text) return undefined;
  const first = text.split('.')[0]?.trim() ?? '';
  if (!first) return undefined;
  return first.length > 140 ? `${first.slice(0, 137).trimEnd()}…` : first;
}
