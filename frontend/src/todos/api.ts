// Typed PocketBase access for the `todos` collection.
//
// Replaces `api.get/post/put/del('/api/todos/...')` calls that used
// to flow through `frontend/src/api/client.ts`'s adapter shim. Each
// caller now sees a clean `Todo` domain type and a small surface of
// CRUD functions; the relation rename (`campaign → campaign_id`) and
// PB-meta strip lives once, here.

import type { RecordModel } from 'pocketbase';
import { pb } from '../lib/pocketbase';
import type { Mention } from '../lib/mentions';

export interface Todo {
  id: string;
  campaign_id: string;
  body: string;
  mentions: Mention[];
  due_date: string;
  priority: 'low' | 'normal' | 'high';
  completed_at: string;
  created_at?: string;
  updated_at?: string;
}

interface TodoRow extends RecordModel {
  user: string;
  campaign?: string;
  body: string;
  mentions?: Mention[];
  due_date?: string;
  priority?: Todo['priority'];
  completed_at?: string;
}

export interface TodoInput {
  campaign_id?: string;
  body: string;
  mentions?: Mention[];
  due_date?: string;
  priority?: Todo['priority'];
  completed_at?: string;
}

const todosCol = () => pb.collection<TodoRow>('todos');

function userId(): string {
  const id = pb.authStore.record?.id;
  if (!id) throw new Error('Not authenticated');
  return id;
}

function adapt(r: TodoRow): Todo {
  return {
    id: r.id,
    campaign_id: r.campaign ?? '',
    body: r.body ?? '',
    mentions: r.mentions ?? [],
    due_date: r.due_date ?? '',
    priority: r.priority ?? 'normal',
    completed_at: r.completed_at ?? '',
    created_at: r.created,
    updated_at: r.updated,
  };
}

function payload(input: TodoInput, uid: string) {
  return {
    user: uid,
    campaign: input.campaign_id ?? '',
    body: input.body ?? '',
    mentions: input.mentions ?? [],
    due_date: input.due_date ?? '',
    priority: input.priority ?? 'normal',
    completed_at: input.completed_at ?? '',
  };
}

export async function listTodos(campaignId?: string): Promise<Todo[]> {
  const filters = [`user = "${userId()}"`];
  if (campaignId) filters.push(`campaign = "${campaignId}"`);
  const items = await todosCol().getFullList({
    filter: filters.join(' && '),
    sort: '-created',
  });
  return items.map(adapt);
}

export async function createTodo(input: TodoInput): Promise<Todo> {
  return adapt(await todosCol().create(payload(input, userId())));
}

export async function updateTodo(id: string, input: TodoInput): Promise<Todo> {
  return adapt(await todosCol().update(id, payload(input, userId())));
}

export async function deleteTodo(id: string): Promise<void> {
  await todosCol().delete(id);
}
