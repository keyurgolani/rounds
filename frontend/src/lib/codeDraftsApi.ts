// Typed PocketBase access for the `code_drafts` collection.
//
// The collection has a unique index on (user, campaign, question,
// language) — `upsertCodeDraft` mirrors the same find-then-update-or-
// create semantics the legacy api shim provided so callers don't have
// to remember it.

import type { RecordModel } from 'pocketbase';
import { pb } from './pocketbase';

export interface CodeDraft {
  id: string;
  user_id: string;
  campaign_id: string;
  question: string;
  language: string;
  code: string;
  created_at?: string;
  updated_at?: string;
}

interface CodeDraftRow extends RecordModel {
  user: string;
  campaign?: string;
  question: string;
  language: string;
  code: string;
}

export interface CodeDraftKey {
  campaign_id: string;
  question: string;
  language: string;
}

export interface CodeDraftInput extends CodeDraftKey {
  code: string;
}

const col = () => pb.collection<CodeDraftRow>('code_drafts');

function userId(): string {
  const id = pb.authStore.record?.id;
  if (!id) throw new Error('Not authenticated');
  return id;
}

function adapt(r: CodeDraftRow): CodeDraft {
  return {
    id: r.id,
    user_id: r.user,
    campaign_id: r.campaign ?? '',
    question: r.question,
    language: r.language,
    code: r.code,
    created_at: r.created,
    updated_at: r.updated,
  };
}

function payload(input: CodeDraftInput, uid: string) {
  return {
    user: uid,
    campaign: input.campaign_id ?? '',
    question: input.question,
    language: input.language,
    code: input.code,
  };
}

function pbStatus(err: unknown): number | undefined {
  return (err as { status?: number } | null)?.status;
}

export async function listCodeDrafts(filter: {
  campaign_id?: string;
  question?: string;
  language?: string;
}): Promise<CodeDraft[]> {
  const filters = [`user = "${userId()}"`];
  if (filter.campaign_id) filters.push(`campaign = "${filter.campaign_id}"`);
  if (filter.question) filters.push(`question = "${filter.question}"`);
  if (filter.language) filters.push(`language = "${filter.language}"`);
  const items = await col().getFullList({
    filter: filters.join(' && '),
    sort: '-updated',
  });
  return items.map(adapt);
}

/** Upsert against the `(user, campaign, question, language)` unique
 *  index. Returns the resulting row. */
export async function upsertCodeDraft(input: CodeDraftInput): Promise<CodeDraft> {
  const uid = userId();
  const filter = (
    `user = "${uid}" && ` +
    `campaign = "${input.campaign_id}" && ` +
    `question = "${input.question}" && ` +
    `language = "${input.language}"`
  );
  try {
    const existing = await col().getFirstListItem(filter);
    return adapt(await col().update(existing.id, payload(input, uid)));
  } catch (err) {
    if (pbStatus(err) !== 404) throw err;
  }
  return adapt(await col().create(payload(input, uid)));
}

export async function deleteCodeDraft(id: string): Promise<void> {
  await col().delete(id);
}
