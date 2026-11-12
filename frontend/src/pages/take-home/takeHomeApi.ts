import { definitionRef, definitionsEnforced } from '../../lib/definitions';
import type { JobAnswer, JobLimit, OutcomeClass, RunnerCallInit } from '../../lib/executionJobs';
import { readGradedRow, requestReview, type ReviewAnswer, type RubricReview } from '../../lib/gradedRows';
import { pb } from '../../lib/pocketbase';
import { runnerJSON } from '../../lib/runnerFetch';
import type { DefinitionReceipt } from '../coding/types';

// ---- Types -----------------------------------------------------------

export type TakeHomeAssignment = {
  id: string;
  slug: string;
  title: string;
  difficulty: string;
  language: string;
  time_budget_min: number;
  ai_policy: 'off' | 'on' | 'candidate-choice';
  prompt_md: string;
  starter_files: Array<{ path: string; contents: string; readonly?: boolean }>;
  // harness_files is on the PB row but the frontend never references it
  // (it's editor-hidden by convention; the backend uses it server-side).
  rubric: { items: Array<{ id: string; label: string; weight: number; prompt: string }> };
  topics?: string[];
  companies?: string[];
  /** The compiled harness revision's version (ROUNDS-00A-L02); runs and
   *  submits name it at enforce. */
  definition_version?: number | null;
};

export type RubricCriterion = {
  id: string;
  passed: boolean;
  weight: number;
  logs: string;
};

export type RunResult = {
  score: number;
  criteria: RubricCriterion[];
  stdout: string;
  stderr: string;
  error: string | null;
  duration_ms: number;
  truncated?: boolean;
  /** At enforce: the server's verdict and each result id's outcome. */
  passed?: boolean | null;
  outcomes?: Array<{ id: string; outcome: string; reason: string }> | null;
  definition?: DefinitionReceipt | null;
};

/** A submission's harness result as its graded row keeps it. A grading
 *  job's row (ROUNDS-00A-L03 PR 3) also names its outcome class and
 *  limit, and keeps the score and each criterion's verdict only where the
 *  run earned them: a submission a limit stopped has neither. */
export type HarnessOutput = Omit<RunResult, 'score' | 'criteria'> & {
  score: number | null;
  criteria: Array<Omit<RubricCriterion, 'passed'> & { passed: boolean | null }>;
  outcome_class?: OutcomeClass;
  limit?: JobLimit | null;
};

export type SubmitResponse = {
  harness: RunResult;
  rubric_review: RubricReview;
  definition?: DefinitionReceipt | null;
};

export type SubmitRequest = {
  assignment_slug: string;
  files: Record<string, string>;
  notes?: string;
  ai_chats?: Array<{ checkpoint: number; role: string; content: string; ts: number }>;
  campaign_id?: string;
  duration_ms?: number;
  /** The assignment's language and its row's definition_version; sent
   *  only at enforce, where the definition names the variant. */
  language?: string;
  definition_version?: number | null;
};

/** Which compiled revision a take-home run names at enforce. */
export type TakeHomeDefinition = { language: string; definition_version?: number | null };

/** The body /api/take-home/run takes under
 *  ROUNDS_GATE_EXECUTION_DEFINITIONS (lib/definitions). */
export function takeHomeRunBody(
  assignment_slug: string,
  files: Record<string, string>,
  definition?: TakeHomeDefinition,
): Record<string, unknown> {
  if (!definitionsEnforced()) return { assignment_slug, files };
  return {
    definition: definitionRef(
      'take-home',
      assignment_slug,
      definition?.language ?? '',
      definition?.definition_version,
    ),
    files,
  };
}

/** The body /api/take-home/submit takes under the current gate value. */
export function takeHomeSubmitBody(req: SubmitRequest): Record<string, unknown> {
  const { assignment_slug, language, definition_version, ...rest } = req;
  if (!definitionsEnforced()) return { assignment_slug, ...rest };
  return {
    definition: definitionRef('take-home', assignment_slug, language ?? '', definition_version),
    ...rest,
  };
}

// ---- API helpers -----------------------------------------------------

export async function listAssignments(): Promise<TakeHomeAssignment[]> {
  const res = await pb.collection('take_home_assignments').getFullList<TakeHomeAssignment>({
    sort: 'title',
  });
  return res;
}

export async function getAssignment(slug: string): Promise<TakeHomeAssignment> {
  // Strip quotes (defense vs filter-injection — same pattern as aiCodingApi.getRound).
  const safe = slug.replace(/"/g, '');
  try {
    return await pb
      .collection('take_home_assignments')
      .getFirstListItem<TakeHomeAssignment>(`slug="${safe}"`);
  } catch {
    return await pb.collection('take_home_assignments').getOne<TakeHomeAssignment>(slug);
  }
}

export async function runProject(
  assignment_slug: string,
  files: Record<string, string>,
  definition?: TakeHomeDefinition,
  init: RunnerCallInit = {},
): Promise<RunResult | JobAnswer> {
  return runnerJSON<RunResult | JobAnswer>('/api/take-home/run', {
    method: 'POST',
    auth: 'required',
    body: takeHomeRunBody(assignment_slug, files, definition),
    errorPrefix: 'take-home run',
    idempotencyKey: init.idempotencyKey,
  });
}

/** A submission. While ROUNDS_GATE_EXECUTION_GRADING is on it answers a
 *  job (lib/executionJobs), whose end the server writes as the graded
 *  row; otherwise the graded submission itself. */
export async function submitAttempt(
  req: SubmitRequest,
  init: RunnerCallInit = {},
): Promise<SubmitResponse | JobAnswer> {
  return runnerJSON<SubmitResponse | JobAnswer>('/api/take-home/submit', {
    method: 'POST',
    auth: 'required',
    body: takeHomeSubmitBody(req),
    errorPrefix: 'take-home submit',
    idempotencyKey: init.idempotencyKey,
  });
}

/** The graded row submission job `jobId` wrote, as the account reads it. */
export async function getGradedTakeHomeAttempt(jobId: string): Promise<TakeHomeAttemptRow | null> {
  return readGradedRow<TakeHomeAttemptRow>(jobId, 'take_home_attempts');
}

/** Asks for the rubric review of submission job `jobId`'s result
 *  (lib/gradedRows). */
export async function requestSubmissionReview(
  jobId: string,
  files: Record<string, string>,
  idempotencyKey: string,
  signal?: AbortSignal,
): Promise<ReviewAnswer> {
  return requestReview('/api/take-home/submit', jobId, files, idempotencyKey, signal);
}

// ---- Attempt persistence (chat log + last submission) ---------------

export type TakeHomeChatEntry = {
  checkpoint: number;
  role: string;
  content: string;
  ts: number;
};

export type TakeHomeAttemptRow = {
  id: string;
  user: string;
  campaign: string;
  assignment: string;
  files?: Record<string, string>;
  ai_assist_used?: boolean;
  ai_chats?: TakeHomeChatEntry[];
  notes?: string;
  harness_output?: HarnessOutput | null;
  /** Null on a row the server wrote, until its review finishes. */
  rubric_review?: SubmitResponse['rubric_review'] | null;
  status: 'in-progress' | 'submitted' | 'graded';
  duration_ms?: number;
  /** The envelope of the grading job that wrote this row, when the
   *  server wrote it (ROUNDS-00A-L03 PR 3). */
  envelope?: string;
  updated: string;
};

/** Most recent attempt for the current user + assignment + campaign. */
export async function getLatestTakeHomeAttempt(
  assignmentId: string,
  campaignId?: string,
): Promise<TakeHomeAttemptRow | null> {
  const userId = pb.authStore.model?.id;
  if (!userId) return null;
  const safeUser = userId.replace(/"/g, '');
  const safeAssignment = assignmentId.replace(/"/g, '');
  const safeCampaign = (campaignId ?? '').replace(/"/g, '');
  const filter = campaignId
    ? `user="${safeUser}" && assignment="${safeAssignment}" && campaign="${safeCampaign}"`
    : `user="${safeUser}" && assignment="${safeAssignment}" && campaign=""`;
  try {
    return await pb
      .collection('take_home_attempts')
      .getFirstListItem<TakeHomeAttemptRow>(filter, { sort: '-updated' });
  } catch (err: any) {
    if (err?.status === 404) return null;
    throw err;
  }
}

export async function upsertInProgressTakeHomeAttempt(input: {
  assignmentId: string;
  campaignId?: string;
  chats: TakeHomeChatEntry[];
}): Promise<void> {
  const userId = pb.authStore.model?.id;
  if (!userId) return;
  const { assignmentId, campaignId, chats } = input;
  const safeUser = userId.replace(/"/g, '');
  const safeAssignment = assignmentId.replace(/"/g, '');
  const safeCampaign = (campaignId ?? '').replace(/"/g, '');
  const filter = campaignId
    ? `user="${safeUser}" && assignment="${safeAssignment}" && campaign="${safeCampaign}" && status="in-progress"`
    : `user="${safeUser}" && assignment="${safeAssignment}" && campaign="" && status="in-progress"`;
  const payload = {
    user: userId,
    assignment: assignmentId,
    campaign: campaignId ?? '',
    ai_chats: chats,
    ai_assist_used: chats.length > 0,
    files: {},
    notes: '',
    harness_output: null,
    rubric_review: null,
    status: 'in-progress' as const,
    duration_ms: 0,
  };
  try {
    const existing = await pb
      .collection('take_home_attempts')
      .getFirstListItem<TakeHomeAttemptRow>(filter);
    await pb.collection('take_home_attempts').update(existing.id, payload);
  } catch (err: any) {
    if (err?.status === 404) {
      await pb.collection('take_home_attempts').create(payload);
    } else {
      throw err;
    }
  }
}

export async function deleteInProgressTakeHomeAttempt(
  assignmentId: string,
  campaignId?: string,
): Promise<void> {
  const userId = pb.authStore.model?.id;
  if (!userId) return;
  const safeUser = userId.replace(/"/g, '');
  const safeAssignment = assignmentId.replace(/"/g, '');
  const safeCampaign = (campaignId ?? '').replace(/"/g, '');
  const filter = campaignId
    ? `user="${safeUser}" && assignment="${safeAssignment}" && campaign="${safeCampaign}" && status="in-progress"`
    : `user="${safeUser}" && assignment="${safeAssignment}" && campaign="" && status="in-progress"`;
  try {
    const existing = await pb
      .collection('take_home_attempts')
      .getFirstListItem<TakeHomeAttemptRow>(filter);
    await pb.collection('take_home_attempts').delete(existing.id);
  } catch (err: any) {
    if (err?.status === 404) return;
    /* swallow — best-effort */
  }
}

// ---- Drafts (autosave per-file) -------------------------------------

export type TakeHomeDraftRow = {
  id: string;
  user: string;
  campaign?: string;
  assignment: string;
  file_path: string;
  contents: string;
};

export async function listDrafts(
  assignmentId: string,
  campaignId?: string,
): Promise<TakeHomeDraftRow[]> {
  const safeAssignment = assignmentId.replace(/"/g, '');
  const safeCampaign = (campaignId ?? '').replace(/"/g, '');
  const filter = campaignId
    ? `assignment="${safeAssignment}" && campaign="${safeCampaign}"`
    : `assignment="${safeAssignment}" && campaign=""`;
  return pb.collection('take_home_drafts').getFullList<TakeHomeDraftRow>({ filter });
}

/**
 * Delete every draft row this user has for `assignmentId` (within the
 * current campaign scope). Used by the "Reset files" button — caller
 * is responsible for the confirm prompt and for re-hydrating local
 * file state from the assignment's starter files.
 */
export async function deleteAllDrafts(
  assignmentId: string,
  campaignId?: string,
): Promise<void> {
  const rows = await listDrafts(assignmentId, campaignId);
  await Promise.all(
    rows.map((r) =>
      pb
        .collection('take_home_drafts')
        .delete(r.id)
        .catch(() => {
          /* swallow — best-effort reset */
        }),
    ),
  );
}

export async function upsertDraft(input: {
  assignmentId: string;
  campaignId?: string;
  filePath: string;
  contents: string;
}): Promise<void> {
  const { assignmentId, campaignId, filePath, contents } = input;
  const userId = pb.authStore.model?.id;
  if (!userId) throw new Error('Not authenticated');
  const safeAssignment = assignmentId.replace(/"/g, '');
  const safeCampaign = (campaignId ?? '').replace(/"/g, '');
  const safePath = filePath.replace(/"/g, '');
  const filter = campaignId
    ? `assignment="${safeAssignment}" && campaign="${safeCampaign}" && file_path="${safePath}"`
    : `assignment="${safeAssignment}" && campaign="" && file_path="${safePath}"`;
  try {
    const existing = await pb
      .collection('take_home_drafts')
      .getFirstListItem<TakeHomeDraftRow>(filter);
    await pb.collection('take_home_drafts').update(existing.id, { contents });
  } catch (err: any) {
    if (err?.status === 404) {
      await pb.collection('take_home_drafts').create({
        user: userId,
        assignment: assignmentId,
        campaign: campaignId ?? '',
        file_path: filePath,
        contents,
      });
    } else {
      throw err;
    }
  }
}

/**
 * All take-home attempt rows belonging to the current user, optionally scoped
 * to a campaign. Used by the Real-World study-page progress strip.
 */
export async function listMyTakeHomeAttempts(
  campaignId?: string,
): Promise<TakeHomeAttemptRow[]> {
  const userId = pb.authStore.model?.id;
  if (!userId) return [];
  const safeUser = userId.replace(/"/g, '');
  const filter = campaignId
    ? `user="${safeUser}" && campaign="${campaignId.replace(/"/g, '')}"`
    : `user="${safeUser}"`;
  try {
    return await pb.collection('take_home_attempts').getFullList<TakeHomeAttemptRow>({ filter });
  } catch {
    return [];
  }
}
