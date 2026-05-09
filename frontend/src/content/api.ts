// Typed PocketBase access for the seven content collections:
// system_design_questions, coding_questions, behavioral_questions,
// behavioral_categories, system_design_guides, coding_guides,
// behavioral_guides.
//
// Replaces `api.get('/api/system-design/...')`,
// `api.get('/api/coding/...')`, `api.get('/api/behavioral/...')`,
// `api.get('/api/behavioral-categories')`, and the three
// `/api/<track>/guide[/:slug]` paths that used to flow through the
// adapter shim.
//
// Why generics: each caller defines its own narrow row type for the
// content it actually consumes (CodingDetail's CQ, SystemDesignList's
// SDQ, etc). The functions here return the PB record minus the PB-
// only meta fields (collectionId, collectionName, expand) so the
// caller's structural type checks against whatever it asks for.

import type { RecordModel } from 'pocketbase';
import { pb } from '../lib/pocketbase';

// PB-only fields that no caller cares about. Strip them once at the
// boundary so they don't pollute downstream types.
function stripPbMeta(r: RecordModel): Record<string, unknown> {
  const { collectionId, collectionName, expand, ...rest } =
    r as unknown as Record<string, unknown>;
  void collectionId;
  void collectionName;
  void expand;
  return rest;
}

async function listContent<T>(
  collection: string,
  sort = 'title',
): Promise<T[]> {
  const items = await pb.collection(collection).getFullList({ sort });
  return items.map((r) => stripPbMeta(r) as unknown as T);
}

// Look up by `slug` first (the human-friendly identifier in the URL),
// fall back to PB record id for the rare case where a caller passes
// the raw id. Mirrors what the legacy shim did via `byIdOrSlug`.
async function getContentByIdOrSlug<T>(
  collection: string,
  ref: string,
): Promise<T> {
  const safe = ref.replace(/"/g, '');
  try {
    const row = await pb
      .collection(collection)
      .getFirstListItem(`slug = "${safe}"`);
    return stripPbMeta(row) as unknown as T;
  } catch {
    const row = await pb.collection(collection).getOne(ref);
    return stripPbMeta(row) as unknown as T;
  }
}

// --- System Design --------------------------------------------------

export function listSystemDesignQuestions<T>(): Promise<T[]> {
  return listContent<T>('system_design_questions');
}

export function getSystemDesignQuestion<T>(slug: string): Promise<T> {
  return getContentByIdOrSlug<T>('system_design_questions', slug);
}

// --- Coding ---------------------------------------------------------

export function listCodingQuestions<T>(): Promise<T[]> {
  return listContent<T>('coding_questions');
}

export function getCodingQuestion<T>(slug: string): Promise<T> {
  return getContentByIdOrSlug<T>('coding_questions', slug);
}

// --- Behavioral -----------------------------------------------------

// Behavioral questions store their category links in PB as a relation
// field named `categories`. Every caller in the app reads this as
// `category_ids` (the SQLAlchemy-era flat array shape), so do the
// rename once here at the adapter.
function adaptBehavioralQuestion<T>(r: RecordModel): T {
  const base = stripPbMeta(r);
  base.category_ids = (r as unknown as { categories?: string[] }).categories ?? [];
  delete base.categories;
  return base as unknown as T;
}

export async function listBehavioralQuestions<T>(): Promise<T[]> {
  const items = await pb.collection('behavioral_questions').getFullList({ sort: 'title' });
  return items.map((r) => adaptBehavioralQuestion<T>(r));
}

export async function getBehavioralQuestion<T>(slug: string): Promise<T> {
  const safe = slug.replace(/"/g, '');
  try {
    const row = await pb
      .collection('behavioral_questions')
      .getFirstListItem(`slug = "${safe}"`);
    return adaptBehavioralQuestion<T>(row);
  } catch {
    const row = await pb.collection('behavioral_questions').getOne(slug);
    return adaptBehavioralQuestion<T>(row);
  }
}

export function listBehavioralCategories<T>(): Promise<T[]> {
  return listContent<T>('behavioral_categories', 'name');
}

// --- Guides ---------------------------------------------------------

// Each track has a "master" guide (the one served when no slug is on
// the URL). Slug fallback constants match the legacy shim's behavior.
const MASTER_SLUGS = {
  system_design_guides: 'master-system-design-interview-guide',
  coding_guides: 'master-coding-interview-guide',
  behavioral_guides: 'master-behavioral-interview-guide',
} as const;

async function getGuide<T>(
  collection: keyof typeof MASTER_SLUGS,
  slug?: string,
): Promise<T> {
  return getContentByIdOrSlug<T>(collection, slug ?? MASTER_SLUGS[collection]);
}

export function getSystemDesignGuide<T>(slug?: string): Promise<T> {
  return getGuide<T>('system_design_guides', slug);
}

export function getCodingGuide<T>(slug?: string): Promise<T> {
  return getGuide<T>('coding_guides', slug);
}

export function getBehavioralGuide<T>(slug?: string): Promise<T> {
  return getGuide<T>('behavioral_guides', slug);
}
