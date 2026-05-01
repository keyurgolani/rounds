// Thin shim over the PocketBase SDK that preserves the legacy
// `api.get/post/put/del(path, body)` contract the rest of the app uses.
// Every /api/* path except the two code-runner endpoints (/api/run,
// /api/evaluate) is dispatched to PocketBase; those two pass through
// to the FastAPI runner at VITE_API_URL (or same-origin /api/* when a
// reverse proxy is in front).
//
// Why a shim and not rewritten call sites: ~15 pages and components
// already fetch through `api.*`, and the response shape they expect is
// the flat SQLAlchemy-style dict. The shim converts PocketBase records
// to that shape (renames relation fields, flattens categories /
// linked_questions arrays back to `*_ids`) so each caller stays put.

import { pb } from '../lib/pocketbase';
import type { RecordModel } from 'pocketbase';

// --- Runner passthrough ---------------------------------------------------

const RUNNER_BASE = (import.meta.env.VITE_API_URL as string | undefined) || '';

async function runnerRequest<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${RUNNER_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...opts?.headers },
    ...opts,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Record shape adapters -----------------------------------------------

type AnyRecord = RecordModel & Record<string, unknown>;

function stripPbMeta<T extends AnyRecord>(r: T) {
  const { collectionId, collectionName, expand, ...rest } = r as Record<string, unknown>;
  void collectionId;
  void collectionName;
  void expand;
  return rest;
}

function adaptContent(r: AnyRecord) {
  return stripPbMeta(r);
}

function adaptBehavioralQuestion(r: AnyRecord) {
  const base = stripPbMeta(r) as Record<string, unknown>;
  base.category_ids = (r.categories as string[]) ?? [];
  delete base.categories;
  return base;
}

function adaptAnecdote(r: AnyRecord) {
  const base = stripPbMeta(r) as Record<string, unknown>;
  base.category_ids = (r.categories as string[]) ?? [];
  base.linked_question_ids = (r.linked_questions as string[]) ?? [];
  base.user_id = r.user as string | undefined;
  base.updated_at = r.updated as string | undefined;
  base.created_at = r.created as string | undefined;
  delete base.categories;
  delete base.linked_questions;
  delete base.user;
  return base;
}

function adaptApplication(r: AnyRecord) {
  const base = stripPbMeta(r) as Record<string, unknown>;
  base.user_id = r.user as string | undefined;
  base.updated_at = r.updated as string | undefined;
  base.created_at = r.created as string | undefined;
  delete base.user;
  return base;
}

function adaptRound(r: AnyRecord) {
  const base = stripPbMeta(r) as Record<string, unknown>;
  base.application_id = r.application as string | undefined;
  base.user_id = r.user as string | undefined;
  base.updated_at = r.updated as string | undefined;
  base.created_at = r.created as string | undefined;
  delete base.application;
  delete base.user;
  return base;
}

function adaptOffer(r: AnyRecord) {
  const base = stripPbMeta(r) as Record<string, unknown>;
  base.application_id = r.application as string | undefined;
  base.user_id = r.user as string | undefined;
  base.updated_at = r.updated as string | undefined;
  base.created_at = r.created as string | undefined;
  delete base.application;
  delete base.user;
  return base;
}

function adaptCampaign(r: AnyRecord) {
  const base = stripPbMeta(r) as Record<string, unknown>;
  base.user_id = r.user as string | undefined;
  base.updated_at = r.updated as string | undefined;
  base.created_at = r.created as string | undefined;
  delete base.user;
  return base;
}

function adaptProgress(r: AnyRecord) {
  const base = stripPbMeta(r) as Record<string, unknown>;
  base.user_id = r.user as string | undefined;
  base.campaign_id = r.campaign as string | undefined;
  base.updated_at = r.updated as string | undefined;
  base.created_at = r.created as string | undefined;
  delete base.user;
  delete base.campaign;
  return base;
}

function adaptDraft(r: AnyRecord) {
  const base = stripPbMeta(r) as Record<string, unknown>;
  base.user_id = r.user as string | undefined;
  base.campaign_id = r.campaign as string | undefined;
  base.updated_at = r.updated as string | undefined;
  base.created_at = r.created as string | undefined;
  delete base.user;
  delete base.campaign;
  return base;
}

function adaptPref(r: AnyRecord) {
  const base = stripPbMeta(r) as Record<string, unknown>;
  base.user_id = r.user as string | undefined;
  base.current_campaign_id = r.current_campaign as string | undefined;
  base.updated_at = r.updated as string | undefined;
  base.created_at = r.created as string | undefined;
  delete base.user;
  delete base.current_campaign;
  return base;
}

function adaptTodo(r: AnyRecord) {
  const base = stripPbMeta(r) as Record<string, unknown>;
  base.user_id = r.user as string | undefined;
  base.campaign_id = r.campaign as string | undefined;
  base.updated_at = r.updated as string | undefined;
  base.created_at = r.created as string | undefined;
  delete base.user;
  delete base.campaign;
  return base;
}

// --- Route matchers ------------------------------------------------------

const SDG = /^\/api\/system-design\/guide(?:\/(.+))?$/;
const CG = /^\/api\/coding\/guide(?:\/(.+))?$/;
const BG = /^\/api\/behavioral\/guide(?:\/(.+))?$/;
const SDQ = /^\/api\/system-design(?:\/(.+))?$/;
const CQ = /^\/api\/coding(?:\/(.+))?$/;
const BQ = /^\/api\/behavioral(?:\/(.+))?$/;
const BC = /^\/api\/behavioral-categories\/?$/;
const AN = /^\/api\/anecdotes(?:\/(.+))?$/;
const APPS = /^\/api\/applications(?:\/([^/]+))?(?:\/(rounds)(?:\/(.+))?)?$/;
const OFFER = /^\/api\/applications\/([^/]+)\/offer\/?$/;
const CAMPAIGNS = /^\/api\/campaigns(?:\/(.+))?$/;
const PROGRESS = /^\/api\/user-progress(?:\/(.+))?$/;
const DRAFTS = /^\/api\/code-drafts(?:\/(.+))?$/;
const PREFS = /^\/api\/user-preferences\/?$/;
const TODOS = /^\/api\/todos(?:\/(.+))?$/;

async function fetchAllItems(
  collection: string,
  filter?: string,
  sort?: string,
): Promise<AnyRecord[]> {
  const all = await pb.collection(collection).getFullList({
    filter: filter ?? '',
    sort: sort ?? '-created',
  });
  return all as unknown as AnyRecord[];
}

async function byIdOrSlug(collection: string, ref: string): Promise<AnyRecord> {
  const safe = ref.replace(/"/g, '');
  try {
    return (await pb
      .collection(collection)
      .getFirstListItem(`slug = "${safe}"`)) as unknown as AnyRecord;
  } catch {
    return (await pb.collection(collection).getOne(ref)) as unknown as AnyRecord;
  }
}

function splitPath(path: string): { base: string; query: URLSearchParams } {
  const [base, qs] = path.split('?', 2);
  return { base, query: new URLSearchParams(qs ?? '') };
}

// --- Dispatch ------------------------------------------------------------

async function dispatchGet<T>(path: string): Promise<T> {
  const { base, query } = splitPath(path);
  const campaignFilter = query.get('campaign');

  if (CAMPAIGNS.test(base)) {
    const userId = pb.authStore.record?.id;
    if (!userId) throw new Error('Not authenticated');
    const m = base.match(CAMPAIGNS)!;
    if (!m[1]) {
      const items = await fetchAllItems(
        'campaigns',
        `user = "${userId}"`,
        '-created',
      );
      return items.map(adaptCampaign) as unknown as T;
    }
    const one = await byIdOrSlug('campaigns', m[1]);
    return adaptCampaign(one) as unknown as T;
  }

  if (PREFS.test(base)) {
    const userId = pb.authStore.record?.id;
    if (!userId) throw new Error('Not authenticated');
    try {
      const one = (await pb
        .collection('user_preferences')
        .getFirstListItem(`user = "${userId}"`)) as unknown as AnyRecord;
      return adaptPref(one) as unknown as T;
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status === 404) return null as unknown as T;
      throw err;
    }
  }

  if (PROGRESS.test(base)) {
    const userId = pb.authStore.record?.id;
    if (!userId) throw new Error('Not authenticated');
    const filters = [`user = "${userId}"`];
    if (campaignFilter) filters.push(`campaign = "${campaignFilter}"`);
    const items = await fetchAllItems(
      'user_progress',
      filters.join(' && '),
      '-updated',
    );
    return items.map(adaptProgress) as unknown as T;
  }

  if (DRAFTS.test(base)) {
    const userId = pb.authStore.record?.id;
    if (!userId) throw new Error('Not authenticated');
    const question = query.get('question');
    const language = query.get('language');
    const filters = [`user = "${userId}"`];
    if (campaignFilter) filters.push(`campaign = "${campaignFilter}"`);
    if (question) filters.push(`question = "${question}"`);
    if (language) filters.push(`language = "${language}"`);
    const items = await fetchAllItems('code_drafts', filters.join(' && '), '-updated');
    return items.map(adaptDraft) as unknown as T;
  }

  if (TODOS.test(base)) {
    const userId = pb.authStore.record?.id;
    if (!userId) throw new Error('Not authenticated');
    const m = base.match(TODOS)!;
    if (m[1]) {
      const one = (await pb.collection('todos').getOne(m[1])) as unknown as AnyRecord;
      return adaptTodo(one) as unknown as T;
    }
    const filters = [`user = "${userId}"`];
    if (campaignFilter) filters.push(`campaign = "${campaignFilter}"`);
    const items = await fetchAllItems('todos', filters.join(' && '), '-created');
    return items.map(adaptTodo) as unknown as T;
  }

  if (BC.test(base)) {
    const items = await fetchAllItems('behavioral_categories', '', 'name');
    return items.map(adaptContent) as unknown as T;
  }

  let m = path.match(SDG);
  if (m) {
    if (!m[1]) {
      const one = await byIdOrSlug('system_design_guides', 'master-system-design-interview-guide');
      return adaptContent(one) as unknown as T;
    }
    const one = await byIdOrSlug('system_design_guides', m[1]);
    return adaptContent(one) as unknown as T;
  }

  m = path.match(CG);
  if (m) {
    if (!m[1]) {
      const one = await byIdOrSlug('coding_guides', 'master-coding-interview-guide');
      return adaptContent(one) as unknown as T;
    }
    const one = await byIdOrSlug('coding_guides', m[1]);
    return adaptContent(one) as unknown as T;
  }

  m = path.match(BG);
  if (m) {
    if (!m[1]) {
      const one = await byIdOrSlug('behavioral_guides', 'master-behavioral-interview-guide');
      return adaptContent(one) as unknown as T;
    }
    const one = await byIdOrSlug('behavioral_guides', m[1]);
    return adaptContent(one) as unknown as T;
  }

  m = path.match(SDQ);
  if (m) {
    if (!m[1]) {
      const items = await fetchAllItems('system_design_questions', '', 'title');
      return items.map(adaptContent) as unknown as T;
    }
    const one = await byIdOrSlug('system_design_questions', m[1]);
    return adaptContent(one) as unknown as T;
  }

  m = path.match(CQ);
  if (m) {
    if (!m[1]) {
      const items = await fetchAllItems('coding_questions', '', 'title');
      return items.map(adaptContent) as unknown as T;
    }
    const one = await byIdOrSlug('coding_questions', m[1]);
    return adaptContent(one) as unknown as T;
  }

  m = path.match(BQ);
  if (m) {
    if (!m[1]) {
      const items = await fetchAllItems('behavioral_questions', '', 'title');
      return items.map(adaptBehavioralQuestion) as unknown as T;
    }
    const one = await byIdOrSlug('behavioral_questions', m[1]);
    return adaptBehavioralQuestion(one) as unknown as T;
  }

  m = path.match(AN);
  if (m) {
    const userId = pb.authStore.record?.id;
    if (!userId) throw new Error('Not authenticated');
    if (!m[1]) {
      const items = await fetchAllItems(
        'anecdotes',
        `user = "${userId}"`,
        '-updated',
      );
      return items.map(adaptAnecdote) as unknown as T;
    }
    const one = (await pb.collection('anecdotes').getOne(m[1])) as unknown as AnyRecord;
    return adaptAnecdote(one) as unknown as T;
  }

  m = path.match(OFFER);
  if (m) {
    const userId = pb.authStore.record?.id;
    if (!userId) throw new Error('Not authenticated');
    const appId = m[1];
    try {
      const one = (await pb
        .collection('offers')
        .getFirstListItem(
          `user = "${userId}" && application = "${appId}"`,
        )) as unknown as AnyRecord;
      return adaptOffer(one) as unknown as T;
    } catch (err: unknown) {
      // PB throws 404 when no matching record exists — normalize to null
      // so callers can distinguish "no offer yet" from a real error.
      const status = (err as { status?: number })?.status;
      if (status === 404) return null as unknown as T;
      throw err;
    }
  }

  m = base.match(APPS);
  if (m) {
    const userId = pb.authStore.record?.id;
    if (!userId) throw new Error('Not authenticated');
    const appRef = m[1];
    const isRoundsPath = m[2] === 'rounds';

    if (!appRef) {
      const filters = [`user = "${userId}"`];
      if (campaignFilter) filters.push(`campaign = "${campaignFilter}"`);
      const items = await fetchAllItems(
        'applications',
        filters.join(' && '),
        '-updated',
      );
      return items.map(adaptApplication) as unknown as T;
    }
    if (isRoundsPath) {
      const items = await fetchAllItems(
        'interview_rounds',
        `application = "${appRef}"`,
        'date',
      );
      return items.map(adaptRound) as unknown as T;
    }
    const one = (await pb
      .collection('applications')
      .getOne(appRef)) as unknown as AnyRecord;
    return adaptApplication(one) as unknown as T;
  }

  return runnerRequest<T>(path);
}

type Body = Record<string, unknown>;

function anecdotePayload(b: Body, userId: string) {
  return {
    user: userId,
    title: b.title ?? '',
    description: b.description ?? '',
    situation: b.situation ?? '',
    task: b.task ?? '',
    action: b.action ?? '',
    result: b.result ?? '',
    categories: (b.category_ids as string[] | undefined) ?? [],
    linked_questions: (b.linked_question_ids as string[] | undefined) ?? [],
    notes: b.notes ?? '',
  };
}

function applicationPayload(b: Body, userId: string) {
  const campaign = (b.campaign_id ?? b.campaign ?? '') as string;
  return {
    user: userId,
    company: b.company ?? '',
    role: b.role ?? '',
    status: b.status ?? 'Applied',
    applied_date: b.applied_date ?? '',
    notes: b.notes ?? '',
    resume_variant: b.resume_variant ?? '',
    url: b.url ?? '',
    job_description: b.job_description ?? '',
    campaign: campaign ? campaign : null,
    last_activity_at: b.last_activity_at ?? new Date().toISOString(),
  };
}

function campaignPayload(b: Body, userId: string) {
  return {
    user: userId,
    name: b.name ?? '',
    slug: b.slug ?? '',
    description: b.description ?? '',
    target_role_level: b.target_role_level ?? '',
    target_companies: b.target_companies ?? [],
    start_date: b.start_date ?? '',
    end_date: b.end_date ?? '',
    status: b.status ?? 'active',
    color: b.color ?? 'accent',
    is_default: b.is_default ?? false,
  };
}

function progressPayload(b: Body, userId: string) {
  return {
    user: userId,
    campaign: b.campaign_id ?? b.campaign ?? '',
    question_type: b.question_type ?? 'coding',
    question_slug: b.question_slug ?? '',
    status: b.status ?? 'todo',
    notes: b.notes ?? '',
    confidence: b.confidence ?? null,
    completed_at: b.completed_at ?? null,
  };
}

function draftPayload(b: Body, userId: string) {
  return {
    user: userId,
    campaign: b.campaign_id ?? b.campaign ?? '',
    question: b.question ?? '',
    language: b.language ?? '',
    code: b.code ?? '',
  };
}

function todoPayload(b: Body, userId: string) {
  return {
    user: userId,
    campaign: (b.campaign_id ?? b.campaign ?? '') as string,
    body: b.body ?? '',
    mentions: b.mentions ?? [],
    due_date: b.due_date ?? '',
    priority: b.priority ?? 'normal',
    completed_at: b.completed_at ?? '',
  };
}

function prefPayload(b: Body, userId: string) {
  // PocketBase relation fields reject `""` for an unset relation — use
  // `null` explicitly so the user_preferences row can clear its
  // current_campaign pointer when asked.
  const current = b.current_campaign_id ?? b.current_campaign;
  return {
    user: userId,
    theme: b.theme ?? '',
    accent: b.accent ?? '',
    type_variant: b.type_variant ?? '',
    density: b.density ?? '',
    nav_style: b.nav_style ?? '',
    card_treatment: b.card_treatment ?? '',
    sans_font: b.sans_font ?? '',
    radius: b.radius ?? '',
    shadow: b.shadow ?? '',
    card_accent: b.card_accent ?? '',
    app_background: b.app_background ?? '',
    glass_transparency: b.glass_transparency ?? null,
    glass_frost: b.glass_frost ?? null,
    glass_shadow: b.glass_shadow ?? null,
    current_campaign: current ? current : null,
  };
}

function offerPayload(b: Body, userId: string, applicationId: string) {
  return {
    user: userId,
    application: applicationId,
    status: b.status ?? 'pending',
    base_salary: b.base_salary ?? null,
    equity_type: b.equity_type ?? '',
    equity_amount: b.equity_amount ?? '',
    equity_vest_schedule: b.equity_vest_schedule ?? '',
    sign_on: b.sign_on ?? null,
    annual_bonus_target_pct: b.annual_bonus_target_pct ?? null,
    relocation: b.relocation ?? '',
    visa_sponsorship: b.visa_sponsorship ?? 'n/a',
    remote_policy: b.remote_policy ?? '',
    pto: b.pto ?? '',
    decision_deadline: b.decision_deadline ?? '',
    letter_url: b.letter_url ?? '',
    notes: b.notes ?? '',
    trail: b.trail ?? [],
  };
}

function roundPayload(b: Body, userId: string, applicationId: string) {
  const campaign = (b.campaign_id ?? b.campaign ?? '') as string;
  return {
    user: userId,
    application: applicationId,
    round_type: b.round_type ?? '',
    date: b.date ?? '',
    interviewer: b.interviewer ?? '',
    questions_asked: b.questions_asked ?? [],
    notes: b.notes ?? '',
    result: b.result ?? 'Pending',
    campaign: campaign ? campaign : null,
    scheduled_status: b.scheduled_status ?? 'scheduled',
    preparation_notes: b.preparation_notes ?? '',
  };
}

async function dispatchPost<T>(path: string, body: unknown): Promise<T> {
  if (path === '/api/run' || path === '/api/evaluate') {
    return runnerRequest<T>(path, { method: 'POST', body: JSON.stringify(body) });
  }

  const userId = pb.authStore.record?.id;
  if (!userId) throw new Error('Not authenticated');

  const { base } = splitPath(path);

  if (/^\/api\/campaigns\/?$/.test(base)) {
    const record = (await pb
      .collection('campaigns')
      .create(campaignPayload(body as Body, userId))) as unknown as AnyRecord;
    return adaptCampaign(record) as unknown as T;
  }

  if (/^\/api\/user-progress\/?$/.test(base)) {
    const record = (await pb
      .collection('user_progress')
      .create(progressPayload(body as Body, userId))) as unknown as AnyRecord;
    return adaptProgress(record) as unknown as T;
  }

  if (/^\/api\/todos\/?$/.test(base)) {
    const record = (await pb
      .collection('todos')
      .create(todoPayload(body as Body, userId))) as unknown as AnyRecord;
    return adaptTodo(record) as unknown as T;
  }

  if (/^\/api\/code-drafts\/?$/.test(base)) {
    // Upsert: code_drafts has a unique index on
    // (user, campaign, question, language) — so on conflict we update
    // in place instead of bubbling the PB uniqueness error.
    const body_ = body as Body;
    const campaign = (body_.campaign_id ?? body_.campaign ?? '') as string;
    const question = (body_.question ?? '') as string;
    const language = (body_.language ?? '') as string;
    try {
      const existing = (await pb
        .collection('code_drafts')
        .getFirstListItem(
          `user = "${userId}" && campaign = "${campaign}" && question = "${question}" && language = "${language}"`,
        )) as unknown as AnyRecord;
      const updated = (await pb
        .collection('code_drafts')
        .update(existing.id as string, draftPayload(body_, userId))) as unknown as AnyRecord;
      return adaptDraft(updated) as unknown as T;
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status !== 404) throw err;
    }
    const record = (await pb
      .collection('code_drafts')
      .create(draftPayload(body as Body, userId))) as unknown as AnyRecord;
    return adaptDraft(record) as unknown as T;
  }

  if (/^\/api\/anecdotes\/?$/.test(path)) {
    const record = (await pb
      .collection('anecdotes')
      .create(anecdotePayload(body as Body, userId))) as unknown as AnyRecord;
    return adaptAnecdote(record) as unknown as T;
  }

  if (/^\/api\/applications\/?$/.test(path)) {
    const record = (await pb
      .collection('applications')
      .create(applicationPayload(body as Body, userId))) as unknown as AnyRecord;
    return adaptApplication(record) as unknown as T;
  }

  const roundsMatch = path.match(/^\/api\/applications\/([^/]+)\/rounds\/?$/);
  if (roundsMatch) {
    const record = (await pb
      .collection('interview_rounds')
      .create(roundPayload(body as Body, userId, roundsMatch[1]))) as unknown as AnyRecord;
    return adaptRound(record) as unknown as T;
  }

  const offerMatch = path.match(OFFER);
  if (offerMatch) {
    const record = (await pb
      .collection('offers')
      .create(offerPayload(body as Body, userId, offerMatch[1]))) as unknown as AnyRecord;
    return adaptOffer(record) as unknown as T;
  }

  return runnerRequest<T>(path, { method: 'POST', body: JSON.stringify(body) });
}

async function dispatchPut<T>(path: string, body: unknown): Promise<T> {
  const userId = pb.authStore.record?.id;
  if (!userId) throw new Error('Not authenticated');

  const { base } = splitPath(path);

  if (/^\/api\/user-preferences\/?$/.test(base)) {
    // Upsert: one preferences row per user.
    try {
      const existing = (await pb
        .collection('user_preferences')
        .getFirstListItem(`user = "${userId}"`)) as unknown as AnyRecord;
      const updated = (await pb
        .collection('user_preferences')
        .update(existing.id as string, prefPayload(body as Body, userId))) as unknown as AnyRecord;
      return adaptPref(updated) as unknown as T;
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status !== 404) throw err;
    }
    const created = (await pb
      .collection('user_preferences')
      .create(prefPayload(body as Body, userId))) as unknown as AnyRecord;
    return adaptPref(created) as unknown as T;
  }

  const campaignPut = base.match(/^\/api\/campaigns\/([^/]+)\/?$/);
  if (campaignPut) {
    const record = (await pb
      .collection('campaigns')
      .update(campaignPut[1], campaignPayload(body as Body, userId))) as unknown as AnyRecord;
    return adaptCampaign(record) as unknown as T;
  }

  const progressPut = base.match(/^\/api\/user-progress\/([^/]+)\/?$/);
  if (progressPut) {
    const record = (await pb
      .collection('user_progress')
      .update(progressPut[1], progressPayload(body as Body, userId))) as unknown as AnyRecord;
    return adaptProgress(record) as unknown as T;
  }

  const todoPut = base.match(/^\/api\/todos\/([^/]+)\/?$/);
  if (todoPut) {
    const record = (await pb
      .collection('todos')
      .update(todoPut[1], todoPayload(body as Body, userId))) as unknown as AnyRecord;
    return adaptTodo(record) as unknown as T;
  }

  const anecdoteMatch = path.match(/^\/api\/anecdotes\/([^/]+)\/?$/);
  if (anecdoteMatch) {
    const record = (await pb
      .collection('anecdotes')
      .update(anecdoteMatch[1], anecdotePayload(body as Body, userId))) as unknown as AnyRecord;
    return adaptAnecdote(record) as unknown as T;
  }

  const appMatch = path.match(/^\/api\/applications\/([^/]+)\/?$/);
  if (appMatch) {
    const record = (await pb
      .collection('applications')
      .update(appMatch[1], applicationPayload(body as Body, userId))) as unknown as AnyRecord;
    return adaptApplication(record) as unknown as T;
  }

  const offerMatch = path.match(OFFER);
  if (offerMatch) {
    // PB requires the record ID for updates. The body must carry the
    // existing offer's `id` — the OfferPanel passes it through.
    const offerId = (body as Body).id as string | undefined;
    if (!offerId) throw new Error('Offer id required for update');
    const record = (await pb
      .collection('offers')
      .update(offerId, offerPayload(body as Body, userId, offerMatch[1]))) as unknown as AnyRecord;
    return adaptOffer(record) as unknown as T;
  }

  return runnerRequest<T>(path, { method: 'PUT', body: JSON.stringify(body) });
}

async function dispatchDel(path: string): Promise<void> {
  const { base } = splitPath(path);

  const campaignDel = base.match(/^\/api\/campaigns\/([^/]+)\/?$/);
  if (campaignDel) {
    await pb.collection('campaigns').delete(campaignDel[1]);
    return;
  }

  const progressDel = base.match(/^\/api\/user-progress\/([^/]+)\/?$/);
  if (progressDel) {
    await pb.collection('user_progress').delete(progressDel[1]);
    return;
  }

  const draftDel = base.match(/^\/api\/code-drafts\/([^/]+)\/?$/);
  if (draftDel) {
    await pb.collection('code_drafts').delete(draftDel[1]);
    return;
  }

  const todoDel = base.match(/^\/api\/todos\/([^/]+)\/?$/);
  if (todoDel) {
    await pb.collection('todos').delete(todoDel[1]);
    return;
  }

  const anecdoteMatch = path.match(/^\/api\/anecdotes\/([^/]+)\/?$/);
  if (anecdoteMatch) {
    await pb.collection('anecdotes').delete(anecdoteMatch[1]);
    return;
  }

  const appMatch = path.match(/^\/api\/applications\/([^/]+)\/?$/);
  if (appMatch) {
    await pb.collection('applications').delete(appMatch[1]);
    return;
  }

  const roundMatch = path.match(/^\/api\/applications\/[^/]+\/rounds\/([^/]+)\/?$/);
  if (roundMatch) {
    await pb.collection('interview_rounds').delete(roundMatch[1]);
    return;
  }

  const offerMatch = path.match(OFFER);
  if (offerMatch) {
    const userId = pb.authStore.record?.id;
    if (!userId) throw new Error('Not authenticated');
    try {
      const record = (await pb
        .collection('offers')
        .getFirstListItem(
          `user = "${userId}" && application = "${offerMatch[1]}"`,
        )) as unknown as AnyRecord;
      await pb.collection('offers').delete(record.id as string);
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      if (status !== 404) throw err;
    }
    return;
  }

  await runnerRequest(path, { method: 'DELETE' });
}

// If a request fails because the server rejected the auth token (key
// rotation, user deleted, account disabled), drop the cached store so
// AuthProvider sees `authStore.isValid === false` on the next tick and
// the UI falls back to /login. Network errors and ordinary 4xx/5xx
// don't trigger logout.
function handleAuthError<T>(p: Promise<T>): Promise<T> {
  return p.catch((err: unknown) => {
    const status = (err as { status?: number } | null)?.status ?? 0;
    if ((status === 401 || status === 403) && pb.authStore.isValid) {
      pb.authStore.clear();
    }
    throw err;
  });
}

export const api = {
  get: <T>(path: string) => handleAuthError(dispatchGet<T>(path)),
  post: <T>(path: string, body: unknown) => handleAuthError(dispatchPost<T>(path, body)),
  put: <T>(path: string, body: unknown) => handleAuthError(dispatchPut<T>(path, body)),
  del: (path: string) => handleAuthError(dispatchDel(path)),
};
