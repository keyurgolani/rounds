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
}

// --- Offer ------------------------------------------------------------

export type OfferStatus = 'pending' | 'accepted' | 'declined' | 'expired';
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
  created_at?: string;
  updated_at?: string;
}

interface OfferRow extends RecordModel, OfferTerms {
  user: string;
  application: string;
  status: OfferStatus;
  notes: string;
  trail: TrailEntry[];
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
    created_at: r.created,
    updated_at: r.updated,
  };
}

function offerPayload(input: OfferInput, uid: string, applicationId: string) {
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

export async function getApplication(id: string): Promise<Application> {
  return adaptApplication(await appsCol().getOne(id));
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

// --- Offer CRUD ------------------------------------------------------

// Returns null when no offer exists yet for this user+application —
// callers distinguish "no offer" from a real error.
export async function getOffer(applicationId: string): Promise<Offer | null> {
  try {
    const row = await offersCol().getFirstListItem(
      `user = "${userId()}" && application = "${applicationId}"`,
    );
    return adaptOffer(row);
  } catch (err) {
    if (isNotFound(err)) return null;
    throw err;
  }
}

export async function createOffer(
  applicationId: string,
  input: OfferInput,
): Promise<Offer> {
  return adaptOffer(
    await offersCol().create(offerPayload(input, userId(), applicationId)),
  );
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
