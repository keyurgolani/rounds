// Typed PocketBase access for applications, interview_rounds, and offers.
//
// Replaces `api.get/post/put/del('/api/applications/...')` calls that
// used to flow through `frontend/src/api/client.ts`'s adapter shim.
// Each caller now sees clean domain types and a small surface of CRUD
// functions; the relation rename (`application → application_id`,
// `user → user_id`, `campaign → campaign_id`) and PB-meta strip lives
// once, here.

import type { RecordModel } from 'pocketbase';
import { pb } from '../lib/pocketbase';

// --- Application -----------------------------------------------------

export interface Application {
  id: string;
  company: string;
  role: string;
  status: string;
  applied_date: string;
  notes: string;
  resume_variant: string;
  url: string;
  job_description: string;
  campaign_id?: string;
  last_activity_at?: string;
  created_at?: string;
  updated_at?: string;
}

interface ApplicationRow extends RecordModel {
  user: string;
  campaign?: string;
  company?: string;
  role?: string;
  status?: string;
  applied_date?: string;
  notes?: string;
  resume_variant?: string;
  url?: string;
  job_description?: string;
  last_activity_at?: string;
}

export interface ApplicationInput {
  company?: string;
  role?: string;
  status?: string;
  applied_date?: string;
  notes?: string;
  resume_variant?: string;
  url?: string;
  job_description?: string;
  campaign_id?: string;
  last_activity_at?: string;
}

// --- InterviewRound --------------------------------------------------

export interface InterviewRound {
  id: string;
  application_id: string;
  campaign_id?: string;
  round_type: string;
  date: string;
  interviewer: string;
  questions_asked: string[];
  notes: string;
  result: string;
  scheduled_status: 'scheduled' | 'completed' | 'canceled';
  preparation_notes: string;
  /** Optional label that groups rounds into an interview loop. Rounds
   *  sharing the same loop_label on the same application render under
   *  a single loop header. Empty string = one-off round. */
  loop_label: string;
  /** Scheduled round length in minutes. 0 / undefined renders as "—". */
  duration_minutes: number;
  created_at?: string;
  updated_at?: string;
}

interface InterviewRoundRow extends RecordModel {
  user: string;
  application: string;
  campaign?: string;
  round_type?: string;
  date?: string;
  interviewer?: string;
  questions_asked?: string[];
  notes?: string;
  result?: string;
  scheduled_status?: InterviewRound['scheduled_status'];
  preparation_notes?: string;
  loop_label?: string;
  duration_minutes?: number;
}

export interface InterviewRoundInput {
  round_type?: string;
  date?: string;
  interviewer?: string;
  questions_asked?: string[];
  notes?: string;
  result?: string;
  scheduled_status?: InterviewRound['scheduled_status'];
  preparation_notes?: string;
  campaign_id?: string;
  loop_label?: string;
  duration_minutes?: number;
}

// --- Offer ------------------------------------------------------------

export type OfferStatus =
  | 'pending'
  | 'accepted'
  | 'declined'
  | 'expired'
  | 'superseded';
export type VisaOption = 'yes' | 'no' | 'n/a';

export interface OfferTerms {
  base_salary: number | null;
  equity_type: string;
  equity_amount: string;
  equity_vest_schedule: string;
  sign_on: number | null;
  annual_bonus_target_pct: number | null;
  relocation: string;
  visa_sponsorship: VisaOption;
  remote_policy: string;
  pto: string;
  decision_deadline: string;
  letter_url: string;
}

export interface TrailEntry {
  timestamp: string;
  author_note: string;
  snapshot: OfferTerms;
}

export interface Offer extends OfferTerms {
  id: string;
  application_id: string;
  status: OfferStatus;
  notes: string;
  trail: TrailEntry[];
  /** PB id of the prior round this row superseded. Empty string when
   *  this is the very first round on the application. */
  previous_offer_id: string;
  created_at?: string;
  updated_at?: string;
}

interface OfferRow extends RecordModel, OfferTerms {
  user: string;
  application: string;
  status: OfferStatus;
  notes: string;
  trail: TrailEntry[];
  previous_offer?: string;
}

export type OfferInput = Partial<Offer>;

// --- Internals -------------------------------------------------------

const appsCol = () => pb.collection<ApplicationRow>('applications');
const roundsCol = () => pb.collection<InterviewRoundRow>('interview_rounds');
const offersCol = () => pb.collection<OfferRow>('offers');

function userId(): string {
  const id = pb.authStore.record?.id;
  if (!id) throw new Error('Not authenticated');
  return id;
}

function adaptApplication(r: ApplicationRow): Application {
  return {
    id: r.id,
    company: r.company ?? '',
    role: r.role ?? '',
    status: r.status ?? 'Applied',
    applied_date: r.applied_date ?? '',
    notes: r.notes ?? '',
    resume_variant: r.resume_variant ?? '',
    url: r.url ?? '',
    job_description: r.job_description ?? '',
    campaign_id: r.campaign,
    last_activity_at: r.last_activity_at,
    created_at: r.created,
    updated_at: r.updated,
  };
}

function applicationPayload(input: ApplicationInput, uid: string) {
  const campaign = input.campaign_id ?? '';
  return {
    user: uid,
    company: input.company ?? '',
    role: input.role ?? '',
    status: input.status ?? 'Applied',
    applied_date: input.applied_date ?? '',
    notes: input.notes ?? '',
    resume_variant: input.resume_variant ?? '',
    url: input.url ?? '',
    job_description: input.job_description ?? '',
    campaign: campaign ? campaign : null,
    last_activity_at: input.last_activity_at ?? new Date().toISOString(),
  };
}

function adaptRound(r: InterviewRoundRow): InterviewRound {
  return {
    id: r.id,
    application_id: r.application,
    campaign_id: r.campaign,
    round_type: r.round_type ?? '',
    date: r.date ?? '',
    interviewer: r.interviewer ?? '',
    questions_asked: r.questions_asked ?? [],
    notes: r.notes ?? '',
    result: r.result ?? 'Pending',
    scheduled_status: r.scheduled_status ?? 'scheduled',
    preparation_notes: r.preparation_notes ?? '',
    loop_label: r.loop_label ?? '',
    duration_minutes: r.duration_minutes ?? 0,
    created_at: r.created,
    updated_at: r.updated,
  };
}

function roundPayload(input: InterviewRoundInput, uid: string, applicationId: string) {
  const campaign = input.campaign_id ?? '';
  return {
    user: uid,
    application: applicationId,
    round_type: input.round_type ?? '',
    date: input.date ?? '',
    interviewer: input.interviewer ?? '',
    questions_asked: input.questions_asked ?? [],
    notes: input.notes ?? '',
    result: input.result ?? 'Pending',
    scheduled_status: input.scheduled_status ?? 'scheduled',
    preparation_notes: input.preparation_notes ?? '',
    loop_label: input.loop_label ?? '',
    duration_minutes: input.duration_minutes ?? 0,
    campaign: campaign ? campaign : null,
  };
}

function adaptOffer(r: OfferRow): Offer {
  return {
    id: r.id,
    application_id: r.application,
    status: r.status,
    base_salary: r.base_salary,
    equity_type: r.equity_type ?? '',
    equity_amount: r.equity_amount ?? '',
    equity_vest_schedule: r.equity_vest_schedule ?? '',
    sign_on: r.sign_on,
    annual_bonus_target_pct: r.annual_bonus_target_pct,
    relocation: r.relocation ?? '',
    visa_sponsorship: r.visa_sponsorship ?? 'n/a',
    remote_policy: r.remote_policy ?? '',
    pto: r.pto ?? '',
    decision_deadline: r.decision_deadline ?? '',
    letter_url: r.letter_url ?? '',
    notes: r.notes ?? '',
    trail: r.trail ?? [],
    previous_offer_id: r.previous_offer ?? '',
    created_at: r.created,
    updated_at: r.updated,
  };
}

function offerPayload(input: OfferInput, uid: string, applicationId: string) {
  // PB rejects empty-string for relation fields — they need `null`.
  const prev = input.previous_offer_id ?? '';
  return {
    user: uid,
    application: applicationId,
    status: input.status ?? 'pending',
    base_salary: input.base_salary ?? null,
    equity_type: input.equity_type ?? '',
    equity_amount: input.equity_amount ?? '',
    equity_vest_schedule: input.equity_vest_schedule ?? '',
    sign_on: input.sign_on ?? null,
    annual_bonus_target_pct: input.annual_bonus_target_pct ?? null,
    relocation: input.relocation ?? '',
    visa_sponsorship: input.visa_sponsorship ?? 'n/a',
    remote_policy: input.remote_policy ?? '',
    pto: input.pto ?? '',
    decision_deadline: input.decision_deadline ?? '',
    letter_url: input.letter_url ?? '',
    notes: input.notes ?? '',
    trail: input.trail ?? [],
    previous_offer: prev ? prev : null,
  };
}

function isNotFound(err: unknown): boolean {
  return (err as { status?: number } | null)?.status === 404;
}

// --- Application CRUD ------------------------------------------------

export async function listApplications(campaignId?: string): Promise<Application[]> {
  const filters = [`user = "${userId()}"`];
  if (campaignId) filters.push(`campaign = "${campaignId}"`);
  const items = await appsCol().getFullList({
    filter: filters.join(' && '),
    sort: '-updated',
  });
  return items.map(adaptApplication);
}

/**
 * Resolve an Application by either its PocketBase id (the canonical
 * url-safe form) OR a human-readable slug like "meta-software-engineer".
 *
 * Slugs aren't stored on the row — they're derived client-side from
 * `slugify(company + " " + role)` so the URL is readable. When the
 * caller hands us a slug, getOne() 404s; we fall back to listing the
 * user's applications and matching by the same slug rule the link
 * generator used.
 */
export async function getApplication(idOrSlug: string): Promise<Application> {
  try {
    return adaptApplication(await appsCol().getOne(idOrSlug));
  } catch (err) {
    const status = (err as { status?: number; data?: { status?: number } })?.status
      ?? (err as { data?: { status?: number } })?.data?.status;
    if (status !== 404) throw err;
  }
  // Fall back to slug resolution.
  const { slugify } = await import('../lib/slug');
  const all = await listApplications();
  const match = all.find(
    (a) => slugify(`${a.company} ${a.role}`) === idOrSlug,
  );
  if (!match) {
    throw new Error(`Application not found: ${idOrSlug}`);
  }
  return match;
}

/**
 * Same idea for rounds: callers may have a slug (from the URL) instead
 * of a PB id. We resolve the slug to an application id, then load
 * rounds normally.
 */
export async function listRoundsBySlugOrId(
  idOrSlug: string,
): Promise<InterviewRound[]> {
  const app = await getApplication(idOrSlug);
  return listRounds(app.id);
}

export async function createApplication(input: ApplicationInput): Promise<Application> {
  return adaptApplication(await appsCol().create(applicationPayload(input, userId())));
}

export async function updateApplication(
  id: string,
  input: ApplicationInput,
): Promise<Application> {
  return adaptApplication(await appsCol().update(id, applicationPayload(input, userId())));
}

export async function deleteApplication(id: string): Promise<void> {
  await appsCol().delete(id);
}

/**
 * Patch-style update for a single application. Read-modify-write so
 * callers can pass just one field and we won't accidentally clear
 * the others. Used by the inline-edit affordances on
 * ApplicationDetail.
 */
export async function updateApplicationField(
  id: string,
  patch: Partial<ApplicationInput>,
): Promise<Application> {
  const current = adaptApplication(await appsCol().getOne(id));
  const merged: ApplicationInput = {
    company: current.company,
    role: current.role,
    status: current.status,
    applied_date: current.applied_date,
    notes: current.notes,
    resume_variant: current.resume_variant,
    url: current.url,
    job_description: current.job_description,
    campaign_id: current.campaign_id,
    last_activity_at: new Date().toISOString(),
    ...patch,
  };
  return adaptApplication(
    await appsCol().update(id, applicationPayload(merged, userId())),
  );
}

// --- Round CRUD ------------------------------------------------------

export async function listRounds(applicationId: string): Promise<InterviewRound[]> {
  const items = await roundsCol().getFullList({
    filter: `application = "${applicationId}"`,
    sort: 'date',
  });
  return items.map(adaptRound);
}

export async function createRound(
  applicationId: string,
  input: InterviewRoundInput,
): Promise<InterviewRound> {
  return adaptRound(
    await roundsCol().create(roundPayload(input, userId(), applicationId)),
  );
}

export async function deleteRound(id: string): Promise<void> {
  await roundsCol().delete(id);
}

/**
 * Patch-style update for a round. Pass only the fields you want to
 * change; everything else is read-modify-written from the live PB row
 * so we don't accidentally clear sibling fields.
 */
export async function updateRound(
  id: string,
  patch: Partial<InterviewRoundInput>,
): Promise<InterviewRound> {
  const current = adaptRound(await roundsCol().getOne(id));
  const merged: InterviewRoundInput = {
    round_type: current.round_type,
    date: current.date,
    interviewer: current.interviewer,
    questions_asked: current.questions_asked,
    notes: current.notes,
    result: current.result,
    scheduled_status: current.scheduled_status,
    preparation_notes: current.preparation_notes,
    campaign_id: current.campaign_id,
    loop_label: current.loop_label,
    duration_minutes: current.duration_minutes,
    ...patch,
  };
  const updated = await roundsCol().update(
    id,
    roundPayload(merged, userId(), current.application_id),
  );
  return adaptRound(updated);
}

// --- Offer CRUD ------------------------------------------------------

// Offers are a chain of rounds — see migration 1700001800. The "active"
// offer is the latest non-superseded row; everything older with
// status='superseded' is history.

/**
 * Full chain of offers for an application, newest first. Includes
 * superseded rounds — callers that only want the active row should use
 * `getOffer`, which is the head of the chain.
 */
export async function listOffers(applicationId: string): Promise<Offer[]> {
  const items = await offersCol().getFullList({
    filter: `user = "${userId()}" && application = "${applicationId}"`,
    sort: '-created',
  });
  return items.map(adaptOffer);
}

// Returns the active offer (latest non-superseded round) or null when
// the application has no offer rounds at all.
export async function getOffer(applicationId: string): Promise<Offer | null> {
  try {
    const row = await offersCol().getFirstListItem(
      `user = "${userId()}" && application = "${applicationId}" && status != "superseded"`,
      { sort: '-created' },
    );
    return adaptOffer(row);
  } catch (err) {
    if (isNotFound(err)) return null;
    throw err;
  }
}

/**
 * Record a new round. If the application already has an active
 * (non-superseded) offer, that row is flipped to status='superseded'
 * first and the new row's `previous_offer` links back to it.
 */
export async function createOffer(
  applicationId: string,
  input: OfferInput,
): Promise<Offer> {
  const prior = await getOffer(applicationId);
  if (prior && prior.status !== 'superseded') {
    await offersCol().update(prior.id, { status: 'superseded' });
  }
  const payload = offerPayload(
    { ...input, previous_offer_id: prior?.id ?? '' },
    userId(),
    applicationId,
  );
  return adaptOffer(await offersCol().create(payload));
}

export async function updateOffer(
  offerId: string,
  applicationId: string,
  input: OfferInput,
): Promise<Offer> {
  return adaptOffer(
    await offersCol().update(offerId, offerPayload(input, userId(), applicationId)),
  );
}

/**
 * Discard the latest round. If a previous round exists, it's
 * un-superseded back to 'pending' so the offer chain has an active
 * head again. With no prior round, this leaves the application
 * offer-less (caller's responsibility to flip status back to
 * Interviewing).
 */
export async function deleteOffer(offerId: string): Promise<Offer | null> {
  // Read the row before deleting so we know whether to revive a prior.
  let priorId = '';
  try {
    const row = await offersCol().getOne(offerId);
    priorId = row.previous_offer ?? '';
  } catch (err) {
    if (!isNotFound(err)) throw err;
  }
  await offersCol().delete(offerId);
  if (!priorId) return null;
  const revived = await offersCol().update(priorId, { status: 'pending' });
  return adaptOffer(revived);
}
