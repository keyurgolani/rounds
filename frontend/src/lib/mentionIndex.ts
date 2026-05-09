import { listApplications, listRounds } from '../applications/api';
import { listCampaigns } from '../campaign/api';
import {
  listBehavioralCategories,
  listBehavioralQuestions,
  listCodingQuestions,
  listSystemDesignQuestions,
} from '../content/api';
import { listAnecdotes } from '../pages/behavioral/anecdotesApi';
import type { Mention, MentionType } from './mentions';

export interface MentionEntry extends Mention {
  // Optional search-only hint shown as a secondary line in the
  // autocomplete dropdown.
  sub?: string;
}

interface RawQuestion {
  id?: string;
  slug: string;
  title: string;
  difficulty?: string;
  tags?: string[];
  topics?: string[];
}

interface RawCategory {
  id?: string;
  name: string;
}

export async function buildMentionIndex(): Promise<MentionEntry[]> {
  const [sd, coding, behavioral, categories, campaigns, anecdotes, applications] =
    await Promise.all([
      listSystemDesignQuestions<RawQuestion>().catch(() => []),
      listCodingQuestions<RawQuestion>().catch(() => []),
      listBehavioralQuestions<RawQuestion>().catch(() => []),
      listBehavioralCategories<RawCategory>().catch(() => []),
      listCampaigns().catch(() => []),
      listAnecdotes().catch(() => []),
      listApplications().catch(() => []),
    ]);

  const out: MentionEntry[] = [];

  for (const q of sd) {
    out.push({
      type: 'sd-question',
      slug: q.slug,
      label: q.title,
      sub: q.difficulty,
    });
  }
  for (const q of coding) {
    out.push({
      type: 'coding-question',
      slug: q.slug,
      label: q.title,
      sub: q.difficulty,
    });
  }
  for (const q of behavioral) {
    out.push({
      type: 'behavioral-question',
      slug: q.slug,
      label: q.title,
    });
  }
  for (const c of categories) {
    out.push({
      type: 'behavioral-category',
      slug: slugify(c.name),
      label: c.name,
    });
  }
  const tagSeen = new Set<string>();
  pushTags(sd, 'sd-tag', tagSeen, out);
  pushTags(coding, 'coding-tag', tagSeen, out);
  for (const c of campaigns) {
    out.push({
      type: 'campaign',
      slug: c.slug,
      label: c.name,
      sub: c.target_role_level,
    });
  }
  for (const a of anecdotes) {
    out.push({
      type: 'anecdote',
      slug: slugify(a.title),
      label: a.title,
    });
  }
  for (const a of applications) {
    out.push({
      type: 'application',
      slug: a.id,
      label: `${a.company} · ${a.role}`,
    });
  }
  // Rounds — pulled per application because PB exposes them as a
  // separate collection scoped by `application`. Cheap even with
  // dozens of applications.
  for (const a of applications) {
    try {
      const rounds = await listRounds(a.id);
      for (const r of rounds) {
        out.push({
          type: 'round',
          slug: r.id,
          label: `${a.company} · ${r.round_type || 'round'}${r.date ? ` · ${r.date}` : ''}`,
        });
      }
    } catch {
      /* skip that app's rounds */
    }
  }

  return out;
}

function pushTags(
  questions: RawQuestion[],
  type: MentionType,
  seen: Set<string>,
  out: MentionEntry[],
) {
  for (const q of questions) {
    const raws = [...(q.tags ?? []), ...(q.topics ?? [])];
    for (const t of raws) {
      const slug = slugify(t);
      const key = `${type}:${slug}`;
      if (seen.has(key)) continue;
      seen.add(key);
      out.push({ type, slug, label: t });
    }
  }
}

function slugify(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64);
}

export function filterIndex(entries: MentionEntry[], query: string): MentionEntry[] {
  const q = query.trim().toLowerCase();
  if (!q) return entries.slice(0, 30);
  return entries
    .map((e) => ({ e, score: scoreMatch(e, q) }))
    .filter((r) => r.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 30)
    .map((r) => r.e);
}

function scoreMatch(entry: MentionEntry, q: string): number {
  const label = entry.label.toLowerCase();
  const slug = entry.slug.toLowerCase();
  const type = entry.type;

  if (label === q || slug === q) return 100;
  if (label.startsWith(q)) return 60;
  if (slug.startsWith(q)) return 40;
  if (label.includes(q)) return 25;
  if (type.includes(q)) return 10;
  return 0;
}
