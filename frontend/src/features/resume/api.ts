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
  Resume,
  ResumeData,
  ResumeVariant,
  ResumeVersion,
  ShareLink,
  TemplateConfig,
} from './types';
import { emptyResumeData } from './types';
import { emptyLinks } from './links/types';
import type { ResumeLinks } from './links/types';

// ---- Row shapes -----------------------------------------------------
//
// The PocketBase SDK is generic on the record type: `pb.collection<R>(name)`
// returns a service whose methods return `R`. Declaring the row shape
// once per collection lets every call site stay type-safe without the
// `as unknown as AnyRecord` casts that proliferated when this file was
// first written.

interface ResumeRow extends RecordModel {
  user: string;
  name: string;
  slug: string;
  template_id: string;
  design: TemplateConfig;
  data: ResumeData;
  links?: ResumeLinks;
}

interface VariantRow extends RecordModel {
  user: string;
  resume: string;
  application?: string;
  name: string;
  target_company?: string;
  job_title?: string;
  job_description?: string;
  tone?: string;
  role_focus?: string[];
  data: ResumeData;
  links?: ResumeLinks;
  ats_score?: number;
  ats_breakdown?: ResumeVariant['ats_breakdown'];
}

interface VersionRow extends RecordModel {
  user: string;
  resume?: string;
  variant?: string;
  data: ResumeData;
  links?: ResumeLinks;
  label?: string;
  is_auto: boolean;
}

interface AISettingsRow extends RecordModel {
  user: string;
  provider: AISettings['provider'];
  model: string;
  import_model?: string;
  base_url?: string;
  encrypted_key?: string;
  key_iv?: string;
}

interface ShareLinkRow extends RecordModel {
  user: string;
  variant: string;
  token: string;
  is_password: boolean;
  password_hash?: string;
  expires_at?: string;
}

// ---- Typed collection accessors -------------------------------------

const resumesCol = () => pb.collection<ResumeRow>('resumes');
const variantsCol = () => pb.collection<VariantRow>('resume_variants');
const versionsCol = () => pb.collection<VersionRow>('resume_versions');
const aiSettingsCol = () => pb.collection<AISettingsRow>('ai_settings');
const shareLinksCol = () => pb.collection<ShareLinkRow>('resume_share_links');

function userId(): string {
  const id = pb.authStore.record?.id;
  if (!id) throw new Error('Not authenticated');
  return id;
}

function pbStatus(err: unknown): number | undefined {
  return (err as { status?: number } | null)?.status;
}

// ---- Row → domain adapters ------------------------------------------

function adaptResume(r: ResumeRow): Resume {
  return {
    id: r.id,
    user_id: r.user,
    name: r.name ?? '',
    slug: r.slug ?? '',
    template_id: r.template_id ?? 'modern',
    design: r.design ?? {},
    data: r.data ?? emptyResumeData(),
    links: r.links ?? emptyLinks(),
    created_at: r.created,
    updated_at: r.updated,
  };
}

function adaptVariant(r: VariantRow): ResumeVariant {
  return {
    id: r.id,
    user_id: r.user,
    resume_id: r.resume,
    name: r.name ?? '',
    target_company: r.target_company,
    job_title: r.job_title,
    job_description: r.job_description,
    tone: r.tone,
    role_focus: r.role_focus ?? [],
    data: r.data ?? emptyResumeData(),
    links: r.links ?? emptyLinks(),
    ats_score: r.ats_score,
    ats_breakdown: r.ats_breakdown,
    application_id: r.application || undefined,
    created_at: r.created,
    updated_at: r.updated,
  };
}

function adaptVersion(r: VersionRow): ResumeVersion {
  return {
    id: r.id,
    user_id: r.user,
    resume_id: r.resume || undefined,
    variant_id: r.variant || undefined,
    data: r.data ?? emptyResumeData(),
    links: r.links ?? emptyLinks(),
    label: r.label,
    is_auto: Boolean(r.is_auto),
    created_at: r.created,
  };
}

function adaptAISettings(r: AISettingsRow): AISettings {
  return {
    id: r.id,
    user_id: r.user,
    provider: r.provider ?? 'anthropic',
    model: r.model ?? '',
    import_model: r.import_model,
    base_url: r.base_url,
    encrypted_key: r.encrypted_key,
    key_iv: r.key_iv,
    updated_at: r.updated,
  };
}

function adaptShareLink(r: ShareLinkRow): ShareLink {
  return {
    id: r.id,
    user_id: r.user,
    variant_id: r.variant,
    token: r.token ?? '',
    is_password: Boolean(r.is_password),
    password_hash: r.password_hash,
    expires_at: r.expires_at,
    created_at: r.created,
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
      const existing = await resumesCol().getFirstListItem(
        `user = "${me}" && slug = "${candidate}"`,
      );
      if (excludeId && existing.id === excludeId) return candidate;
      candidate = `${base}-${n++}`;
    } catch (err: unknown) {
      if (pbStatus(err) === 404) return candidate;
      throw err;
    }
  }
}

// --- Resumes ----------------------------------------------------------

export async function listResumes(): Promise<Resume[]> {
  const me = userId();
  const items = await resumesCol().getFullList({
    filter: `user = "${me}"`,
    sort: '-updated',
  });
  return items.map(adaptResume);
}

export async function getResumeBySlug(slug: string): Promise<Resume> {
  const me = userId();
  const safe = slug.replace(/"/g, '');
  const r = await resumesCol().getFirstListItem(
    `user = "${me}" && slug = "${safe}"`,
  );
  return adaptResume(r);
}

export async function getResume(id: string): Promise<Resume> {
  const r = await resumesCol().getOne(id);
  return adaptResume(r);
}

export async function createResume(input: {
  name: string;
  template_id?: string;
  data?: ResumeData;
  design?: TemplateConfig;
}): Promise<Resume> {
  const slug = await ensureUniqueSlug(input.name);
  const r = await resumesCol().create({
    user: userId(),
    name: input.name,
    slug,
    template_id: input.template_id ?? 'modern',
    design: input.design ?? {},
    data: input.data ?? emptyResumeData(),
  });
  return adaptResume(r);
}

export async function updateResume(
  id: string,
  patch: Partial<Pick<Resume, 'name' | 'slug' | 'template_id' | 'design' | 'data' | 'links'>>,
): Promise<Resume> {
  const r = await resumesCol().update(id, patch);
  return adaptResume(r);
}

export async function deleteResume(id: string): Promise<void> {
  await resumesCol().delete(id);
}

// --- Variants ---------------------------------------------------------

export async function listVariants(resumeId?: string): Promise<ResumeVariant[]> {
  const me = userId();
  const filters = [`user = "${me}"`];
  if (resumeId) filters.push(`resume = "${resumeId}"`);
  const items = await variantsCol().getFullList({
    filter: filters.join(' && '),
    sort: '-updated',
  });
  return items.map(adaptVariant);
}

export async function listVariantsForApplication(
  applicationId: string,
): Promise<ResumeVariant[]> {
  const me = userId();
  const items = await variantsCol().getFullList({
    filter: `user = "${me}" && application = "${applicationId}"`,
    sort: '-updated',
  });
  return items.map(adaptVariant);
}

export async function createVariant(input: {
  resume_id: string;
  name: string;
  data: ResumeData;
  links?: ResumeLinks;
  target_company?: string;
  job_title?: string;
  job_description?: string;
  tone?: string;
  role_focus?: string[];
  application_id?: string;
}): Promise<ResumeVariant> {
  const r = await variantsCol().create({
    user: userId(),
    resume: input.resume_id,
    name: input.name,
    data: input.data,
    links: input.links ?? emptyLinks(),
    target_company: input.target_company ?? '',
    job_title: input.job_title ?? '',
    job_description: input.job_description ?? '',
    tone: input.tone ?? '',
    role_focus: input.role_focus ?? [],
    application: input.application_id || undefined,
  });
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
  const r = await variantsCol().update(id, payload);
  return adaptVariant(r);
}

export async function deleteVariant(id: string): Promise<void> {
  await variantsCol().delete(id);
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
  const items = await versionsCol().getFullList({
    filter: filters.join(' && '),
    sort: '-created',
  });
  return items.map(adaptVersion);
}

export async function createVersion(input: {
  resumeId?: string;
  variantId?: string;
  data: ResumeData;
  links?: ResumeLinks;
  label?: string;
  isAuto?: boolean;
}): Promise<ResumeVersion> {
  const r = await versionsCol().create({
    user: userId(),
    resume: input.resumeId || undefined,
    variant: input.variantId || undefined,
    data: input.data,
    links: input.links ?? emptyLinks(),
    label: input.label ?? '',
    is_auto: input.isAuto ?? true,
  });
  return adaptVersion(r);
}

// --- AI Settings ------------------------------------------------------

export async function getAISettings(): Promise<AISettings | null> {
  const me = userId();
  try {
    const r = await aiSettingsCol().getFirstListItem(`user = "${me}"`);
    return adaptAISettings(r);
  } catch (err: unknown) {
    if (pbStatus(err) === 404) return null;
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
    const existing = await aiSettingsCol().getFirstListItem(`user = "${me}"`);
    const r = await aiSettingsCol().update(existing.id, payload);
    return adaptAISettings(r);
  } catch (err: unknown) {
    if (pbStatus(err) !== 404) throw err;
  }
  const r = await aiSettingsCol().create(payload);
  return adaptAISettings(r);
}

// --- Share links ------------------------------------------------------

export async function listShareLinks(variantId?: string): Promise<ShareLink[]> {
  const me = userId();
  const filters = [`user = "${me}"`];
  if (variantId) filters.push(`variant = "${variantId}"`);
  const items = await shareLinksCol().getFullList({
    filter: filters.join(' && '),
    sort: '-created',
  });
  return items.map(adaptShareLink);
}

export async function createShareLink(input: {
  variantId: string;
  token: string;
  isPassword?: boolean;
  passwordHash?: string;
  expiresAt?: string;
}): Promise<ShareLink> {
  const r = await shareLinksCol().create({
    user: userId(),
    variant: input.variantId,
    token: input.token,
    is_password: input.isPassword ?? false,
    password_hash: input.passwordHash ?? '',
    expires_at: input.expiresAt ?? '',
  });
  return adaptShareLink(r);
}

export async function deleteShareLink(id: string): Promise<void> {
  await shareLinksCol().delete(id);
}
