// Resume Studio API.
//
// Talks to PocketBase directly (via `pb`) instead of going through the
// `api.*` shim — the shim is a per-route adapter, and the resume feature
// is self-contained enough that adding seven more match arms there would
// just bloat the dispatcher. Each function in here returns the
// flat-record shape consumed by the rest of the app (snake_case +
// `_id` suffixes for relation fields).

import type { RecordModel } from 'pocketbase';
import { pb } from '../../lib/pocketbase';
import { slugify } from '../../lib/slug';
import type {
  AISettings,
  Bullet,
  Resume,
  ResumeData,
  ResumeVariant,
  ResumeVersion,
  ShareLink,
  TemplateConfig,
} from './types';
import { emptyResumeData } from './types';

type AnyRecord = RecordModel & Record<string, unknown>;

function userId(): string {
  const id = pb.authStore.record?.id;
  if (!id) throw new Error('Not authenticated');
  return id;
}

function strip<T extends AnyRecord>(r: T): Record<string, unknown> {
  const { collectionId, collectionName, expand, ...rest } = r as Record<string, unknown>;
  void collectionId;
  void collectionName;
  void expand;
  return rest;
}

// --- Adapters: PocketBase row → typed snake_case object ---------------

function adaptResume(r: AnyRecord): Resume {
  const base = strip(r);
  return {
    id: base.id as string,
    user_id: r.user as string,
    name: (base.name as string) ?? '',
    slug: (base.slug as string) ?? '',
    template_id: ((base.template_id as string) ?? 'modern'),
    design: ((base.design as TemplateConfig) ?? {}),
    data: ((base.data as ResumeData) ?? emptyResumeData()),
    created_at: r.created as string,
    updated_at: r.updated as string,
  };
}

function adaptVariant(r: AnyRecord): ResumeVariant {
  const base = strip(r);
  return {
    id: base.id as string,
    user_id: r.user as string,
    resume_id: r.resume as string,
    name: (base.name as string) ?? '',
    target_company: base.target_company as string | undefined,
    job_title: base.job_title as string | undefined,
    job_description: base.job_description as string | undefined,
    tone: base.tone as string | undefined,
    role_focus: (base.role_focus as string[] | undefined) ?? [],
    data: ((base.data as ResumeData) ?? emptyResumeData()),
    ats_score: base.ats_score as number | undefined,
    ats_breakdown: base.ats_breakdown as ResumeVariant['ats_breakdown'],
    application_id: (r.application as string | undefined) || undefined,
    created_at: r.created as string,
    updated_at: r.updated as string,
  };
}

function adaptVersion(r: AnyRecord): ResumeVersion {
  const base = strip(r);
  return {
    id: base.id as string,
    user_id: r.user as string,
    resume_id: (r.resume as string | undefined) || undefined,
    variant_id: (r.variant as string | undefined) || undefined,
    data: (base.data as ResumeData) ?? emptyResumeData(),
    label: base.label as string | undefined,
    is_auto: Boolean(base.is_auto),
    created_at: r.created as string,
  };
}

function adaptBullet(r: AnyRecord): Bullet {
  const base = strip(r);
  return {
    id: base.id as string,
    user_id: r.user as string,
    text: (base.text as string) ?? '',
    tags: (base.tags as string[] | undefined) ?? [],
    source_anecdote_id: (r.source_anecdote as string | undefined) || undefined,
    metrics: (base.metrics as Bullet['metrics']) ?? [],
    created_at: r.created as string,
    updated_at: r.updated as string,
  };
}

function adaptAISettings(r: AnyRecord): AISettings {
  const base = strip(r);
  return {
    id: base.id as string,
    user_id: r.user as string,
    provider: (base.provider as AISettings['provider']) ?? 'anthropic',
    model: (base.model as string) ?? '',
    import_model: base.import_model as string | undefined,
    base_url: base.base_url as string | undefined,
    encrypted_key: base.encrypted_key as string | undefined,
    key_iv: base.key_iv as string | undefined,
    updated_at: r.updated as string,
  };
}

function adaptShareLink(r: AnyRecord): ShareLink {
  const base = strip(r);
  return {
    id: base.id as string,
    user_id: r.user as string,
    variant_id: r.variant as string,
    token: (base.token as string) ?? '',
    is_password: Boolean(base.is_password),
    password_hash: base.password_hash as string | undefined,
    expires_at: base.expires_at as string | undefined,
    created_at: r.created as string,
  };
}

// --- Slug uniqueness --------------------------------------------------

export async function ensureUniqueSlug(
  seed: string,
  excludeId?: string,
): Promise<string> {
  const me = userId();
  const base = slugify(seed) || 'resume';
  let candidate = base;
  let n = 2;
  while (true) {
    try {
      const existing = (await pb
        .collection('resumes')
        .getFirstListItem(
          `user = "${me}" && slug = "${candidate}"`,
        )) as unknown as { id?: string };
      // If the only collision is the resume being renamed itself,
      // its current slug is fine to keep / land on.
      if (excludeId && existing?.id === excludeId) return candidate;
      candidate = `${base}-${n++}`;
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 404) return candidate;
      throw err;
    }
  }
}

// --- Resumes ----------------------------------------------------------

export async function listResumes(): Promise<Resume[]> {
  const me = userId();
  const items = (await pb.collection('resumes').getFullList({
    filter: `user = "${me}"`,
    sort: '-updated',
  })) as unknown as AnyRecord[];
  return items.map(adaptResume);
}

export async function getResumeBySlug(slug: string): Promise<Resume> {
  const me = userId();
  const safe = slug.replace(/"/g, '');
  const r = (await pb
    .collection('resumes')
    .getFirstListItem(`user = "${me}" && slug = "${safe}"`)) as unknown as AnyRecord;
  return adaptResume(r);
}

export async function getResume(id: string): Promise<Resume> {
  const r = (await pb.collection('resumes').getOne(id)) as unknown as AnyRecord;
  return adaptResume(r);
}

export async function createResume(input: {
  name: string;
  template_id?: string;
  data?: ResumeData;
  design?: TemplateConfig;
}): Promise<Resume> {
  const slug = await ensureUniqueSlug(input.name);
  const r = (await pb.collection('resumes').create({
    user: userId(),
    name: input.name,
    slug,
    template_id: input.template_id ?? 'modern',
    design: input.design ?? {},
    data: input.data ?? emptyResumeData(),
  })) as unknown as AnyRecord;
  return adaptResume(r);
}

export async function updateResume(
  id: string,
  patch: Partial<Pick<Resume, 'name' | 'slug' | 'template_id' | 'design' | 'data'>>,
): Promise<Resume> {
  const r = (await pb.collection('resumes').update(id, patch)) as unknown as AnyRecord;
  return adaptResume(r);
}

export async function deleteResume(id: string): Promise<void> {
  await pb.collection('resumes').delete(id);
}

// --- Variants ---------------------------------------------------------

export async function listVariants(resumeId?: string): Promise<ResumeVariant[]> {
  const me = userId();
  const filters = [`user = "${me}"`];
  if (resumeId) filters.push(`resume = "${resumeId}"`);
  const items = (await pb.collection('resume_variants').getFullList({
    filter: filters.join(' && '),
    sort: '-updated',
  })) as unknown as AnyRecord[];
  return items.map(adaptVariant);
}

export async function listVariantsForApplication(
  applicationId: string,
): Promise<ResumeVariant[]> {
  const me = userId();
  const items = (await pb.collection('resume_variants').getFullList({
    filter: `user = "${me}" && application = "${applicationId}"`,
    sort: '-updated',
  })) as unknown as AnyRecord[];
  return items.map(adaptVariant);
}

export async function createVariant(input: {
  resume_id: string;
  name: string;
  data: ResumeData;
  target_company?: string;
  job_title?: string;
  job_description?: string;
  tone?: string;
  role_focus?: string[];
  application_id?: string;
}): Promise<ResumeVariant> {
  const r = (await pb.collection('resume_variants').create({
    user: userId(),
    resume: input.resume_id,
    name: input.name,
    data: input.data,
    target_company: input.target_company ?? '',
    job_title: input.job_title ?? '',
    job_description: input.job_description ?? '',
    tone: input.tone ?? '',
    role_focus: input.role_focus ?? [],
    application: input.application_id || null,
  })) as unknown as AnyRecord;
  return adaptVariant(r);
}

export async function updateVariant(
  id: string,
  patch: Partial<Omit<ResumeVariant, 'id' | 'user_id' | 'resume_id' | 'created_at' | 'updated_at'>>,
): Promise<ResumeVariant> {
  const payload: Record<string, unknown> = { ...patch };
  if ('application_id' in patch) {
    payload.application = patch.application_id || null;
    delete payload.application_id;
  }
  const r = (await pb.collection('resume_variants').update(id, payload)) as unknown as AnyRecord;
  return adaptVariant(r);
}

export async function deleteVariant(id: string): Promise<void> {
  await pb.collection('resume_variants').delete(id);
}

// --- Versions ---------------------------------------------------------

export async function listVersions(opts: {
  resumeId?: string;
  variantId?: string;
}): Promise<ResumeVersion[]> {
  const me = userId();
  const filters = [`user = "${me}"`];
  if (opts.resumeId) filters.push(`resume = "${opts.resumeId}"`);
  if (opts.variantId) filters.push(`variant = "${opts.variantId}"`);
  const items = (await pb.collection('resume_versions').getFullList({
    filter: filters.join(' && '),
    sort: '-created',
  })) as unknown as AnyRecord[];
  return items.map(adaptVersion);
}

export async function createVersion(input: {
  resumeId?: string;
  variantId?: string;
  data: ResumeData;
  label?: string;
  isAuto?: boolean;
}): Promise<ResumeVersion> {
  const r = (await pb.collection('resume_versions').create({
    user: userId(),
    resume: input.resumeId || null,
    variant: input.variantId || null,
    data: input.data,
    label: input.label ?? '',
    is_auto: input.isAuto ?? true,
  })) as unknown as AnyRecord;
  return adaptVersion(r);
}

// --- Bullets ----------------------------------------------------------

export async function listBullets(): Promise<Bullet[]> {
  const me = userId();
  const items = (await pb.collection('resume_bullets').getFullList({
    filter: `user = "${me}"`,
    sort: '-updated',
  })) as unknown as AnyRecord[];
  return items.map(adaptBullet);
}

export async function createBullet(input: {
  text: string;
  tags?: string[];
  source_anecdote_id?: string;
  metrics?: Bullet['metrics'];
}): Promise<Bullet> {
  const r = (await pb.collection('resume_bullets').create({
    user: userId(),
    text: input.text,
    tags: input.tags ?? [],
    source_anecdote: input.source_anecdote_id || null,
    metrics: input.metrics ?? [],
  })) as unknown as AnyRecord;
  return adaptBullet(r);
}

export async function updateBullet(
  id: string,
  patch: Partial<Pick<Bullet, 'text' | 'tags' | 'metrics'>>,
): Promise<Bullet> {
  const r = (await pb.collection('resume_bullets').update(id, patch)) as unknown as AnyRecord;
  return adaptBullet(r);
}

export async function deleteBullet(id: string): Promise<void> {
  await pb.collection('resume_bullets').delete(id);
}

// --- AI Settings ------------------------------------------------------

export async function getAISettings(): Promise<AISettings | null> {
  const me = userId();
  try {
    const r = (await pb
      .collection('ai_settings')
      .getFirstListItem(`user = "${me}"`)) as unknown as AnyRecord;
    return adaptAISettings(r);
  } catch (err: unknown) {
    const status = (err as { status?: number })?.status;
    if (status === 404) return null;
    throw err;
  }
}

export async function upsertAISettings(input: {
  provider: AISettings['provider'];
  model: string;
  import_model?: string;
  base_url?: string;
  encrypted_key?: string;
  key_iv?: string;
}): Promise<AISettings> {
  const me = userId();
  const payload = {
    user: me,
    provider: input.provider,
    model: input.model,
    import_model: input.import_model ?? '',
    base_url: input.base_url ?? '',
    encrypted_key: input.encrypted_key ?? '',
    key_iv: input.key_iv ?? '',
  };
  try {
    const existing = (await pb
      .collection('ai_settings')
      .getFirstListItem(`user = "${me}"`)) as unknown as AnyRecord;
    const r = (await pb
      .collection('ai_settings')
      .update(existing.id as string, payload)) as unknown as AnyRecord;
    return adaptAISettings(r);
  } catch (err: unknown) {
    const status = (err as { status?: number })?.status;
    if (status !== 404) throw err;
  }
  const r = (await pb.collection('ai_settings').create(payload)) as unknown as AnyRecord;
  return adaptAISettings(r);
}

// --- Share links ------------------------------------------------------

export async function listShareLinks(variantId?: string): Promise<ShareLink[]> {
  const me = userId();
  const filters = [`user = "${me}"`];
  if (variantId) filters.push(`variant = "${variantId}"`);
  const items = (await pb.collection('resume_share_links').getFullList({
    filter: filters.join(' && '),
    sort: '-created',
  })) as unknown as AnyRecord[];
  return items.map(adaptShareLink);
}

export async function createShareLink(input: {
  variantId: string;
  token: string;
  isPassword?: boolean;
  passwordHash?: string;
  expiresAt?: string;
}): Promise<ShareLink> {
  const r = (await pb.collection('resume_share_links').create({
    user: userId(),
    variant: input.variantId,
    token: input.token,
    is_password: input.isPassword ?? false,
    password_hash: input.passwordHash ?? '',
    expires_at: input.expiresAt ?? '',
  })) as unknown as AnyRecord;
  return adaptShareLink(r);
}

export async function deleteShareLink(id: string): Promise<void> {
  await pb.collection('resume_share_links').delete(id);
}
