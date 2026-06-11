// Mention token format: [[type:slug|label]]
//
//   type  — one of the MentionType values below
//   slug  — entity slug (for list filters like behavioral-category:leadership,
//           the slug segment is the category value)
//   label — human-facing text rendered in place of the token
//
// The parser extracts `Mention[]` so callers can keep the array in
// sync on the todo record without re-parsing on read. The renderer
// splits the body into plain-text chunks and mention tokens so
// consumers can wrap tokens with a <Link>.

export type MentionType =
  | 'sd-question'
  | 'coding-question'
  | 'behavioral-question'
  | 'behavioral-category'
  | 'coding-tag'
  | 'sd-tag'
  | 'application'
  | 'round'
  | 'anecdote'
  | 'campaign';

export interface Mention {
  type: MentionType;
  slug: string;
  label: string;
}

export type Chunk =
  | { kind: 'text'; text: string }
  | { kind: 'mention'; mention: Mention };

const TOKEN_RE = /\[\[([a-z-]+):([^\]|]+?)(?:\|([^\]]+?))?\]\]/g;

export function parseMentions(body: string): Mention[] {
  if (!body) return [];
  const out: Mention[] = [];
  const seen = new Set<string>();
  for (const match of body.matchAll(TOKEN_RE)) {
    const [, type, slug, label] = match;
    if (!isMentionType(type)) continue;
    const key = `${type}:${slug}`;
    if (seen.has(key)) continue;
    seen.add(key);
    out.push({ type, slug, label: (label ?? slug).trim() });
  }
  return out;
}

export function splitBody(body: string): Chunk[] {
  if (!body) return [];
  const chunks: Chunk[] = [];
  let lastIndex = 0;
  for (const match of body.matchAll(TOKEN_RE)) {
    const start = match.index ?? 0;
    if (start > lastIndex) {
      chunks.push({ kind: 'text', text: body.slice(lastIndex, start) });
    }
    const [, type, slug, label] = match;
    if (isMentionType(type)) {
      chunks.push({
        kind: 'mention',
        mention: { type, slug, label: (label ?? slug).trim() },
      });
    } else {
      // Unknown type — render as plain text so the user still sees the token.
      chunks.push({ kind: 'text', text: match[0] });
    }
    lastIndex = start + match[0].length;
  }
  if (lastIndex < body.length) {
    chunks.push({ kind: 'text', text: body.slice(lastIndex) });
  }
  return chunks;
}

export function mentionRoute(m: Mention): string {
  const slug = encodeURIComponent(m.slug);
  switch (m.type) {
    case 'sd-question':
      return `/system-design/question/${slug}`;
    case 'coding-question':
      return `/coding/question/${slug}`;
    case 'behavioral-question':
      return `/behavioral/question/${slug}`;
    case 'behavioral-category':
      return `/behavioral?category=${slug}`;
    case 'coding-tag':
      return `/coding?tag=${slug}`;
    case 'sd-tag':
      return `/system-design?tag=${slug}`;
    case 'application':
      return `/applications/${slug}`;
    case 'round':
      return `/interviews/${slug}`;
    case 'anecdote':
      return `/experience/list?anecdote=${slug}`;
    case 'campaign':
      return `/campaigns/${slug}`;
  }
}

export function mentionToken(m: Mention): string {
  return `[[${m.type}:${m.slug}|${m.label}]]`;
}

export function isMentionType(v: string): v is MentionType {
  return (
    v === 'sd-question' ||
    v === 'coding-question' ||
    v === 'behavioral-question' ||
    v === 'behavioral-category' ||
    v === 'coding-tag' ||
    v === 'sd-tag' ||
    v === 'application' ||
    v === 'round' ||
    v === 'anecdote' ||
    v === 'campaign'
  );
}

export function mentionLabelWithPrefix(m: Mention): string {
  // Display prefix that makes the token's category visible in the
  // rendered UI (e.g. "@ coding two-sum") without mistaking a mention
  // for a regular link.
  switch (m.type) {
    case 'sd-question':
      return `system · ${m.label}`;
    case 'coding-question':
      return `coding · ${m.label}`;
    case 'behavioral-question':
      return `behavioral · ${m.label}`;
    case 'behavioral-category':
      return `category · ${m.label}`;
    case 'coding-tag':
      return `#${m.label}`;
    case 'sd-tag':
      return `#${m.label}`;
    case 'application':
      return `app · ${m.label}`;
    case 'round':
      return `round · ${m.label}`;
    case 'anecdote':
      return `story · ${m.label}`;
    case 'campaign':
      return `campaign · ${m.label}`;
  }
}
