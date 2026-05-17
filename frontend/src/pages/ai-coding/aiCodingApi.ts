import { pb } from '../../lib/pocketbase';
import { runnerJSON } from '../../lib/runnerFetch';

export type AICodingRound = {
  id: string;
  slug: string;
  title: string;
  difficulty: string;
  language: string;
  description: string;
  starter_files: Array<{ path: string; contents: string; readonly?: boolean }>;
  checkpoints: Array<{
    label: string;
    prompt: string;
    ai_allowed: boolean;
    test_command: string;
    /** Reserved for Phase 2 (critical-verification flavor). Visible-only in MVP. */
    tests_hidden?: boolean;
  }>;
  rubric: { items: Array<{ id: string; label: string; weight: number; prompt: string }> };
  topics: string[];
  companies: string[];
};

export async function listRounds(): Promise<AICodingRound[]> {
  const res = await pb.collection('ai_coding_rounds').getFullList<AICodingRound>({
    sort: 'title',
  });
  return res;
}

export async function getRound(slug: string): Promise<AICodingRound> {
  const safe = slug.replace(/"/g, '');
  try {
    return await pb
      .collection('ai_coding_rounds')
      .getFirstListItem<AICodingRound>(`slug="${safe}"`);
  } catch {
    return await pb.collection('ai_coding_rounds').getOne<AICodingRound>(slug);
  }
}

export type DraftRow = {
  id: string;
  round: string;
  campaign?: string;
  file_path: string;
  contents: string;
};

export async function listDrafts(roundId: string, campaignId?: string): Promise<DraftRow[]> {
  const safeRound = roundId.replace(/"/g, '');
  const safeCampaign = (campaignId ?? '').replace(/"/g, '');
  const filter = campaignId
    ? `round="${safeRound}" && campaign="${safeCampaign}"`
    : `round="${safeRound}" && campaign=""`;
  return pb.collection('ai_coding_drafts').getFullList<DraftRow>({ filter });
}

/**
 * Delete every draft row this user has for `roundId` (within the
 * current campaign scope). Used by the "Reset files" button — caller
 * is responsible for the confirm prompt and for re-hydrating local
 * file state from the round's starter files.
 */
export async function deleteAllDrafts(
  roundId: string,
  campaignId?: string,
): Promise<void> {
  const rows = await listDrafts(roundId, campaignId);
  await Promise.all(
    rows.map((r) =>
      pb
        .collection('ai_coding_drafts')
        .delete(r.id)
        .catch(() => {
          /* swallow — best-effort reset */
        }),
    ),
  );
}

export async function upsertDraft(input: {
  roundId: string;
  campaignId?: string;
  filePath: string;
  contents: string;
}): Promise<void> {
  const { roundId, campaignId, filePath, contents } = input;
  const userId = pb.authStore.model?.id;
  if (!userId) throw new Error('Not authenticated');
  const safeRound = roundId.replace(/"/g, '');
  const safeCampaign = (campaignId ?? '').replace(/"/g, '');
  const safePath = filePath.replace(/"/g, '');
  const filter = campaignId
    ? `round="${safeRound}" && campaign="${safeCampaign}" && file_path="${safePath}"`
    : `round="${safeRound}" && campaign="" && file_path="${safePath}"`;
  try {
    const existing = await pb.collection('ai_coding_drafts').getFirstListItem<DraftRow>(filter);
    await pb.collection('ai_coding_drafts').update(existing.id, { contents });
  } catch (err: any) {
    if (err?.status === 404) {
      await pb.collection('ai_coding_drafts').create({
        user: userId,
        round: roundId,
        campaign: campaignId ?? '',
        file_path: filePath,
        contents,
      });
    } else {
      throw err;
    }
  }
}

export type RunProjectResult = {
  passed: boolean;
  passed_count: number;
  failed_count: number;
  stdout: string;
  stderr: string;
  error: string | null;
  duration_ms: number;
  truncated: boolean;
};

export async function runProject(input: {
  files: Record<string, string>;
  language: string;
  test_command: string;
  timeout_s?: number;
}): Promise<RunProjectResult> {
  return runnerJSON<RunProjectResult>('/api/ai-coding/run-project', {
    method: 'POST',
    body: input,
    auth: 'optional',
    errorPrefix: 'run-project',
  });
}

export type GradeResponse = {
  test_results: Array<{
    passed: boolean;
    passed_count: number;
    failed_count: number;
    stdout: string;
    error: string | null;
  }>;
  rubric_review: {
    items: Array<{ id: string; score: number; evidence: string; suggestions: string[] }>;
    total: number;
    skipped?: boolean;
    reason?: string;
  };
};

export type AIChatLogEntry = {
  checkpoint: number;
  role: string;
  content: string;
  ts: number;
};

export type GradeRequest = {
  round_slug: string;
  files: Record<string, string>;
  ai_chats: AIChatLogEntry[];
};

export async function gradeAttempt(req: GradeRequest): Promise<GradeResponse> {
  return runnerJSON<GradeResponse>('/api/ai-coding/grade', {
    method: 'POST',
    body: req,
    auth: 'required',
    errorPrefix: 'grade',
  });
}

/**
 * Most recent attempt row for the current user + round + campaign,
 * regardless of status. Used on mount to rehydrate chat log and the
 * last submission report so refresh doesn't lose them.
 */
export type AttemptRow = {
  id: string;
  user: string;
  campaign: string;
  round: string;
  current_checkpoint?: number;
  ai_chats?: AIChatLogEntry[];
  test_results?: GradeResponse['test_results'];
  rubric_review?: GradeResponse['rubric_review'];
  status: 'in-progress' | 'submitted' | 'graded';
  duration_ms?: number;
  updated: string;
};

export async function getLatestAttempt(
  roundId: string,
  campaignId?: string,
): Promise<AttemptRow | null> {
  const userId = pb.authStore.model?.id;
  if (!userId) return null;
  const safeRound = roundId.replace(/"/g, '');
  const safeUser = userId.replace(/"/g, '');
  const safeCampaign = (campaignId ?? '').replace(/"/g, '');
  const filter = campaignId
    ? `user="${safeUser}" && round="${safeRound}" && campaign="${safeCampaign}"`
    : `user="${safeUser}" && round="${safeRound}" && campaign=""`;
  try {
    const row = await pb
      .collection('ai_coding_attempts')
      .getFirstListItem<AttemptRow>(filter, { sort: '-updated' });
    return row;
  } catch (err: any) {
    if (err?.status === 404) return null;
    throw err;
  }
}

/**
 * Upsert the in-progress attempt for the current (user, round, campaign).
 * Used to persist the chat log between message turns so a refresh
 * doesn't lose the conversation. Once the user submits, persistAttempt
 * creates a new graded row alongside this one (we leave the in-progress
 * row in place — it's a chronological audit trail).
 */
export async function upsertInProgressAttempt(input: {
  roundId: string;
  campaignId?: string;
  currentCheckpoint: number;
  chats: AIChatLogEntry[];
}): Promise<void> {
  const userId = pb.authStore.model?.id;
  if (!userId) return;
  const { roundId, campaignId, currentCheckpoint, chats } = input;
  const safeRound = roundId.replace(/"/g, '');
  const safeUser = userId.replace(/"/g, '');
  const safeCampaign = (campaignId ?? '').replace(/"/g, '');
  const filter = campaignId
    ? `user="${safeUser}" && round="${safeRound}" && campaign="${safeCampaign}" && status="in-progress"`
    : `user="${safeUser}" && round="${safeRound}" && campaign="" && status="in-progress"`;
  const payload = {
    user: userId,
    round: roundId,
    campaign: campaignId ?? '',
    current_checkpoint: currentCheckpoint,
    ai_chats: chats,
    test_results: [],
    rubric_review: { items: [], total: 0 },
    status: 'in-progress' as const,
    duration_ms: 0,
  };
  try {
    const existing = await pb
      .collection('ai_coding_attempts')
      .getFirstListItem<AttemptRow>(filter);
    await pb.collection('ai_coding_attempts').update(existing.id, payload);
  } catch (err: any) {
    if (err?.status === 404) {
      await pb.collection('ai_coding_attempts').create(payload);
    } else {
      throw err;
    }
  }
}

export async function deleteInProgressAttempt(
  roundId: string,
  campaignId?: string,
): Promise<void> {
  const userId = pb.authStore.model?.id;
  if (!userId) return;
  const safeRound = roundId.replace(/"/g, '');
  const safeUser = userId.replace(/"/g, '');
  const safeCampaign = (campaignId ?? '').replace(/"/g, '');
  const filter = campaignId
    ? `user="${safeUser}" && round="${safeRound}" && campaign="${safeCampaign}" && status="in-progress"`
    : `user="${safeUser}" && round="${safeRound}" && campaign="" && status="in-progress"`;
  try {
    const existing = await pb
      .collection('ai_coding_attempts')
      .getFirstListItem<AttemptRow>(filter);
    await pb.collection('ai_coding_attempts').delete(existing.id);
  } catch (err: any) {
    if (err?.status === 404) return;
    /* swallow other errors — best-effort */
  }
}

export async function persistAttempt(input: {
  roundId: string;
  campaignId?: string;
  currentCheckpoint: number;
  files: Record<string, string>;
  test_results: GradeResponse['test_results'];
  rubric_review: GradeResponse['rubric_review'];
  ai_chats: AIChatLogEntry[];
  duration_ms: number;
}): Promise<void> {
  const userId = pb.authStore.model?.id;
  if (!userId) throw new Error('Not authenticated');
  await pb.collection('ai_coding_attempts').create({
    user: userId,
    round: input.roundId,
    campaign: input.campaignId ?? '',
    current_checkpoint: input.currentCheckpoint,
    ai_chats: input.ai_chats,
    test_results: input.test_results,
    rubric_review: input.rubric_review,
    status: 'graded',
    duration_ms: input.duration_ms,
  });
}

export type AICodingModel = {
  provider_id: string;
  provider_label: string;
  kind: string;
  model: string;
};

export async function listAICodingModels(): Promise<AICodingModel[]> {
  return runnerJSON<AICodingModel[]>('/api/ai-coding/models', { auth: 'required' });
}

/**
 * All attempt rows belonging to the current user, optionally scoped to a campaign.
 * Used by the study-page progress strip to show "X rounds started · Y graded".
 */
export async function listMyAttempts(campaignId?: string): Promise<AttemptRow[]> {
  const userId = pb.authStore.model?.id;
  if (!userId) return [];
  const safeUser = userId.replace(/"/g, '');
  const filter = campaignId
    ? `user="${safeUser}" && campaign="${campaignId.replace(/"/g, '')}"`
    : `user="${safeUser}"`;
  try {
    return await pb.collection('ai_coding_attempts').getFullList<AttemptRow>({ filter });
  } catch {
    return [];
  }
}
