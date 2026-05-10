export function slugify(text: string | undefined | null): string {
  if (!text) return '';
  return text
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '') // strip diacritics
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

// Inverse of slugify for display: turn "main-resume" or "main_resume"
// back into "Main Resume". Used when an exported file (whose name is
// the slug) is re-imported and we need a human-readable title.
export function titleCaseFromSlug(text: string | undefined | null): string {
  if (!text) return '';
  return text
    .replace(/[-_]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .split(' ')
    .map((word) => (word ? word[0].toUpperCase() + word.slice(1) : word))
    .join(' ');
}
