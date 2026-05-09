// Typed PocketBase access for the `anecdotes` collection.
//
// Replaces `api.get/post/put/del('/api/anecdotes/...')`. The shim
// renamed `categories` → `category_ids` and `linked_questions` →
// `linked_question_ids`; that translation lives in the single
// `adapt`/`payload` pair here so each caller sees the clean
// `Anecdote` domain shape.

import type { RecordModel } from 'pocketbase';
import { pb } from '../../lib/pocketbase';
import type { Anecdote } from './types';

interface AnecdoteRow extends RecordModel {
  user: string;
  title?: string;
  description?: string;
  situation?: string;
  task?: string;
  action?: string;
  result?: string;
  categories?: string[];
  linked_questions?: string[];
  notes?: string;
}

export interface AnecdoteInput {
  title?: string;
  description?: string;
  situation?: string;
  task?: string;
  action?: string;
  result?: string;
  category_ids?: string[];
  linked_question_ids?: string[];
  notes?: string;
}

const col = () => pb.collection<AnecdoteRow>('anecdotes');

function userId(): string {
  const id = pb.authStore.record?.id;
  if (!id) throw new Error('Not authenticated');
  return id;
}

function adapt(r: AnecdoteRow): Anecdote {
  return {
    id: r.id,
    title: r.title ?? '',
    description: r.description ?? '',
    situation: r.situation ?? '',
    task: r.task ?? '',
    action: r.action ?? '',
    result: r.result ?? '',
    category_ids: r.categories ?? [],
    linked_question_ids: r.linked_questions ?? [],
    notes: r.notes ?? '',
    created_at: r.created,
    updated_at: r.updated,
  };
}

function payload(input: AnecdoteInput, uid: string) {
  return {
    user: uid,
    title: input.title ?? '',
    description: input.description ?? '',
    situation: input.situation ?? '',
    task: input.task ?? '',
    action: input.action ?? '',
    result: input.result ?? '',
    categories: input.category_ids ?? [],
    linked_questions: input.linked_question_ids ?? [],
    notes: input.notes ?? '',
  };
}

export async function listAnecdotes(): Promise<Anecdote[]> {
  const items = await col().getFullList({
    filter: `user = "${userId()}"`,
    sort: '-updated',
  });
  return items.map(adapt);
}

export async function getAnecdote(id: string): Promise<Anecdote> {
  return adapt(await col().getOne(id));
}

export async function createAnecdote(input: AnecdoteInput): Promise<Anecdote> {
  return adapt(await col().create(payload(input, userId())));
}

export async function updateAnecdote(
  id: string,
  input: AnecdoteInput,
): Promise<Anecdote> {
  return adapt(await col().update(id, payload(input, userId())));
}

export async function deleteAnecdote(id: string): Promise<void> {
  await col().delete(id);
}
