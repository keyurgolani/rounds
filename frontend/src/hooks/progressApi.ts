// Typed PocketBase access for the `user_progress` collection.
//
// Two callers today:
//   - hooks/usePracticeStatus.ts — hydrates the local-storage rollup
//     map for one campaign + persists status flips.
//   - settings/DataSection — backup/restore (deferred to its own
//     port, will switch to listUserProgress/createUserProgress when
//     that batch lands).

import type { RecordModel } from 'pocketbase';
import { pb } from '../lib/pocketbase';
import type { PracticeStatus } from '../components/shell/StatusDot';

export type PracticeKind = 'system' | 'coding' | 'behavioral';

export interface UserProgress {
  id: string;
  user_id: string;
  campaign_id: string;
  question_type: PracticeKind;
  question_slug: string;
  status: PracticeStatus;
  notes?: string;
  confidence?: number | null;
  completed_at?: string | null;
  created_at?: string;
  updated_at?: string;
}

interface UserProgressRow extends RecordModel {
  user: string;
  campaign?: string;
  question_type: PracticeKind;
  question_slug: string;
  status: PracticeStatus;
  notes?: string;
  confidence?: number | null;
  completed_at?: string | null;
}

export interface UserProgressInput {
  campaign_id: string;
  question_type: PracticeKind;
  question_slug: string;
  status: PracticeStatus;
  notes?: string;
  confidence?: number | null;
  completed_at?: string | null;
}

const col = () => pb.collection<UserProgressRow>('user_progress');

function userId(): string {
  const id = pb.authStore.record?.id;
  if (!id) throw new Error('Not authenticated');
  return id;
}

function adapt(r: UserProgressRow): UserProgress {
  return {
    id: r.id,
    user_id: r.user,
    campaign_id: r.campaign ?? '',
    question_type: r.question_type,
    question_slug: r.question_slug,
    status: r.status,
    notes: r.notes,
    confidence: r.confidence ?? null,
    completed_at: r.completed_at ?? null,
    created_at: r.created,
    updated_at: r.updated,
  };
}

function payload(input: UserProgressInput, uid: string) {
  return {
    user: uid,
    campaign: input.campaign_id ?? '',
    question_type: input.question_type,
    question_slug: input.question_slug,
    status: input.status,
    notes: input.notes ?? '',
    confidence: input.confidence ?? null,
    completed_at: input.completed_at ?? null,
  };
}

export async function listUserProgress(campaignId?: string): Promise<UserProgress[]> {
  const filters = [`user = "${userId()}"`];
  if (campaignId) filters.push(`campaign = "${campaignId}"`);
  const items = await col().getFullList({
    filter: filters.join(' && '),
    sort: '-updated',
  });
  return items.map(adapt);
}

export async function createUserProgress(input: UserProgressInput): Promise<UserProgress> {
  return adapt(await col().create(payload(input, userId())));
}

export async function updateUserProgress(
  id: string,
  input: UserProgressInput,
): Promise<UserProgress> {
  return adapt(await col().update(id, payload(input, userId())));
}

export async function deleteUserProgress(id: string): Promise<void> {
  await col().delete(id);
}
