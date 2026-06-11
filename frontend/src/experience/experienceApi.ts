import type { RecordModel } from 'pocketbase';
import { pb } from '../lib/pocketbase';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ExperienceJob {
  id: string;
  company: string;
  role: string;
  location: string;
  employment_type: string;
  start_date: string;
  end_date: string | null;
  description: string;
  tags: string[];
  created_at?: string;
  updated_at?: string;
}

export interface ExperienceProject {
  id: string;
  title: string;
  company: string;
  role: string;
  team_size: number | null;
  tech_stack: string[];
  start_date: string;
  end_date: string | null;
  description: string;
  tags: string[];
  created_at?: string;
  updated_at?: string;
}

export interface ExperienceAnecdote {
  id: string;
  title: string;
  situation: string;
  task: string;
  action: string;
  result: string;
  impact: string;
  company: string;
  project: string;
  date: string;
  tags: string[];
  description: string;
  category_ids: string[];
  linked_question_ids: string[];
  notes: string;
  created_at?: string;
  updated_at?: string;
}

export interface ExperienceBullet {
  id: string;
  title: string;
  impact: string;
  category: string;
  date: string;
  tags: string[];
  created_at?: string;
  updated_at?: string;
}

export type EntityKind = 'job' | 'project' | 'anecdote' | 'bullet';

export type TimelineEntity =
  | ({ kind: 'job' } & ExperienceJob)
  | ({ kind: 'project' } & ExperienceProject)
  | ({ kind: 'anecdote' } & ExperienceAnecdote)
  | ({ kind: 'bullet' } & ExperienceBullet);

// ---------------------------------------------------------------------------
// Internals
// ---------------------------------------------------------------------------

function userId(): string {
  const id = pb.authStore.record?.id;
  if (!id) throw new Error('Not authenticated');
  return id;
}

function ownerFilter() {
  return `user = "${userId()}"`;
}

// ---------------------------------------------------------------------------
// Jobs
// ---------------------------------------------------------------------------

interface JobRow extends RecordModel {
  user: string;
  company: string;
  role: string;
  location?: string;
  employment_type?: string;
  start_date: string;
  end_date?: string;
  description?: string;
  tags?: string[];
}

function adaptJob(r: JobRow): ExperienceJob {
  return {
    id: r.id,
    company: r.company,
    role: r.role,
    location: r.location ?? '',
    employment_type: r.employment_type ?? '',
    start_date: r.start_date,
    end_date: r.end_date ?? null,
    description: r.description ?? '',
    tags: r.tags ?? [],
    created_at: r.created,
    updated_at: r.updated,
  };
}

export async function listJobs(): Promise<ExperienceJob[]> {
  const items = await pb.collection<JobRow>('experience_jobs').getFullList({
    filter: ownerFilter(),
    sort: '-start_date',
  });
  return items.map(adaptJob);
}

export async function createJob(data: Partial<ExperienceJob>): Promise<ExperienceJob> {
  const payload = {
    user: userId(),
    company: data.company ?? '',
    role: data.role ?? '',
    location: data.location ?? '',
    employment_type: data.employment_type ?? '',
    start_date: data.start_date ?? new Date().toISOString().split('T')[0],
    end_date: data.end_date ?? null,
    description: data.description ?? '',
    tags: data.tags ?? [],
  };
  return adaptJob(await pb.collection<JobRow>('experience_jobs').create(payload));
}

export async function updateJob(id: string, data: Partial<ExperienceJob>): Promise<ExperienceJob> {
  return adaptJob(await pb.collection<JobRow>('experience_jobs').update(id, data));
}

export async function deleteJob(id: string): Promise<void> {
  await pb.collection<JobRow>('experience_jobs').delete(id);
}

// ---------------------------------------------------------------------------
// Projects
// ---------------------------------------------------------------------------

interface ProjectRow extends RecordModel {
  user: string;
  title: string;
  company?: string;
  role?: string;
  team_size?: number;
  tech_stack?: string[];
  start_date: string;
  end_date?: string;
  description?: string;
  tags?: string[];
}

function adaptProject(r: ProjectRow): ExperienceProject {
  return {
    id: r.id,
    title: r.title,
    company: r.company ?? '',
    role: r.role ?? '',
    team_size: r.team_size ?? null,
    tech_stack: r.tech_stack ?? [],
    start_date: r.start_date,
    end_date: r.end_date ?? null,
    description: r.description ?? '',
    tags: r.tags ?? [],
    created_at: r.created,
    updated_at: r.updated,
  };
}

export async function listProjects(): Promise<ExperienceProject[]> {
  const items = await pb.collection<ProjectRow>('experience_projects').getFullList({
    filter: ownerFilter(),
    sort: '-start_date',
  });
  return items.map(adaptProject);
}

export async function createProject(data: Partial<ExperienceProject>): Promise<ExperienceProject> {
  const payload = {
    user: userId(),
    title: data.title ?? '',
    company: data.company ?? '',
    role: data.role ?? '',
    team_size: data.team_size ?? null,
    tech_stack: data.tech_stack ?? [],
    start_date: data.start_date ?? new Date().toISOString().split('T')[0],
    end_date: data.end_date ?? null,
    description: data.description ?? '',
    tags: data.tags ?? [],
  };
  return adaptProject(await pb.collection<ProjectRow>('experience_projects').create(payload));
}

export async function updateProject(id: string, data: Partial<ExperienceProject>): Promise<ExperienceProject> {
  return adaptProject(await pb.collection<ProjectRow>('experience_projects').update(id, data));
}

export async function deleteProject(id: string): Promise<void> {
  await pb.collection<ProjectRow>('experience_projects').delete(id);
}

// ---------------------------------------------------------------------------
// Anecdotes
// ---------------------------------------------------------------------------

interface AnecdoteRow extends RecordModel {
  user: string;
  title: string;
  situation?: string;
  task?: string;
  action?: string;
  result?: string;
  impact?: string;
  company?: string;
  project?: string;
  date: string;
  tags?: string[];
  description?: string;
  categories?: string[];
  linked_questions?: string[];
  notes?: string;
}

export function adaptAnecdoteRow(r: AnecdoteRow): ExperienceAnecdote {
  return {
    id: r.id,
    title: r.title,
    situation: r.situation ?? '',
    task: r.task ?? '',
    action: r.action ?? '',
    result: r.result ?? '',
    impact: r.impact ?? '',
    company: r.company ?? '',
    project: r.project ?? '',
    date: r.date,
    tags: r.tags ?? [],
    description: r.description ?? '',
    category_ids: r.categories ?? [],
    linked_question_ids: r.linked_questions ?? [],
    notes: r.notes ?? '',
    created_at: r.created,
    updated_at: r.updated,
  };
}

export function anecdotePayload(data: Partial<ExperienceAnecdote>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  const direct: (keyof ExperienceAnecdote)[] = [
    'title', 'situation', 'task', 'action', 'result', 'impact',
    'company', 'project', 'date', 'tags', 'description', 'notes',
  ];
  for (const k of direct) if (data[k] !== undefined) out[k] = data[k];
  if (data.category_ids !== undefined) out.categories = data.category_ids;
  if (data.linked_question_ids !== undefined) out.linked_questions = data.linked_question_ids;
  return out;
}

export async function listAnecdotes(): Promise<ExperienceAnecdote[]> {
  const items = await pb.collection<AnecdoteRow>('experience_anecdotes').getFullList({
    filter: ownerFilter(),
    sort: '-date',
  });
  return items.map(adaptAnecdoteRow);
}

export async function createAnecdote(data: Partial<ExperienceAnecdote>): Promise<ExperienceAnecdote> {
  const payload = {
    user: userId(),
    title: data.title ?? '',
    situation: data.situation ?? '',
    task: data.task ?? '',
    action: data.action ?? '',
    result: data.result ?? '',
    impact: data.impact ?? '',
    company: data.company ?? '',
    project: data.project ?? '',
    date: data.date ?? new Date().toISOString().split('T')[0],
    tags: data.tags ?? [],
    description: data.description ?? '',
    notes: data.notes ?? '',
    categories: data.category_ids ?? [],
    linked_questions: data.linked_question_ids ?? [],
  };
  return adaptAnecdoteRow(await pb.collection<AnecdoteRow>('experience_anecdotes').create(payload));
}

export async function updateAnecdote(id: string, data: Partial<ExperienceAnecdote>): Promise<ExperienceAnecdote> {
  return adaptAnecdoteRow(await pb.collection<AnecdoteRow>('experience_anecdotes').update(id, anecdotePayload(data)));
}

export async function deleteAnecdote(id: string): Promise<void> {
  await pb.collection<AnecdoteRow>('experience_anecdotes').delete(id);
}

// ---------------------------------------------------------------------------
// Bullets
// ---------------------------------------------------------------------------

interface BulletRow extends RecordModel {
  user: string;
  title: string;
  impact?: string;
  category?: string;
  date: string;
  tags?: string[];
}

function adaptBullet(r: BulletRow): ExperienceBullet {
  return {
    id: r.id,
    title: r.title,
    impact: r.impact ?? '',
    category: r.category ?? '',
    date: r.date,
    tags: r.tags ?? [],
    created_at: r.created,
    updated_at: r.updated,
  };
}

export async function listBullets(): Promise<ExperienceBullet[]> {
  const items = await pb.collection<BulletRow>('experience_bullets').getFullList({
    filter: ownerFilter(),
    sort: '-date',
  });
  return items.map(adaptBullet);
}

export async function createBullet(data: Partial<ExperienceBullet>): Promise<ExperienceBullet> {
  const payload = {
    user: userId(),
    title: data.title ?? '',
    impact: data.impact ?? '',
    category: data.category ?? '',
    date: data.date ?? new Date().toISOString().split('T')[0],
    tags: data.tags ?? [],
  };
  return adaptBullet(await pb.collection<BulletRow>('experience_bullets').create(payload));
}

export async function updateBullet(id: string, data: Partial<ExperienceBullet>): Promise<ExperienceBullet> {
  return adaptBullet(await pb.collection<BulletRow>('experience_bullets').update(id, data));
}

export async function deleteBullet(id: string): Promise<void> {
  await pb.collection<BulletRow>('experience_bullets').delete(id);
}

// ---------------------------------------------------------------------------
// Timeline: merge all entities sorted by date
// ---------------------------------------------------------------------------

export async function listTimelineEntities(): Promise<TimelineEntity[]> {
  const [jobs, projects, anecdotes, bullets] = await Promise.all([
    listJobs(),
    listProjects(),
    listAnecdotes(),
    listBullets(),
  ]);

  const all: TimelineEntity[] = [
    ...jobs.map((j) => ({ kind: 'job' as const, ...j })),
    ...projects.map((p) => ({ kind: 'project' as const, ...p })),
    ...anecdotes.map((a) => ({ kind: 'anecdote' as const, ...a })),
    ...bullets.map((b) => ({ kind: 'bullet' as const, ...b })),
  ];

  all.sort((a, b) => {
    const dateA = a.kind === 'job' || a.kind === 'project' ? a.start_date : a.date;
    const dateB = b.kind === 'job' || b.kind === 'project' ? b.start_date : b.date;
    return +new Date(dateB) - +new Date(dateA);
  });

  return all;
}
