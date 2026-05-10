import { pb } from '../../lib/pocketbase';
import { runnerJSON } from '../../lib/runnerFetch';

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
};

export type SubmitResponse = {
  harness: RunResult;
  rubric_review: {
    items: Array<{ id: string; score: number; evidence: string; suggestions: string[] }>;
    total: number;
    skipped?: boolean;
    reason?: string;
    parse_error?: string;
  };
};

export type SubmitRequest = {
  assignment_slug: string;
  files: Record<string, string>;
  notes?: string;
  ai_chats?: Array<{ checkpoint: number; role: string; content: string; ts: number }>;
  campaign_id?: string;
  duration_ms?: number;
};

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
): Promise<RunResult> {
  return runnerJSON<RunResult>('/api/take-home/run', {
    method: 'POST',
    auth: 'required',
    body: { assignment_slug, files },
    errorPrefix: 'take-home run',
  });
}

export async function submitAttempt(req: SubmitRequest): Promise<SubmitResponse> {
  return runnerJSON<SubmitResponse>('/api/take-home/submit', {
    method: 'POST',
    auth: 'required',
    body: req,
    errorPrefix: 'take-home submit',
  });
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
