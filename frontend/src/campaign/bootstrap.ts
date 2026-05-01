// One-time sweep of pre-campaign localStorage state into PocketBase,
// scoped to the user's implicit Default campaign. Idempotent via the
// MIGRATED_FLAG so refreshes after the first run are free.

import { api } from '../api/client';

const MIGRATED_FLAG = 'rounds.migratedV1';
const STATUS_KEY = 'rounds.practiceStatus.v1';
const DRAFT_PREFIX = 'rounds.codeDraft.v1:';

type PracticeStatus = 'todo' | 'in-progress' | 'mastered';

type Track = 'system' | 'coding' | 'behavioral';

const TRACK_FROM_PREFIX: Record<string, Track> = {
  system: 'system',
  coding: 'coding',
  behavioral: 'behavioral',
};

export async function runOneTimeMigration(
  userId: string,
  defaultCampaignId: string,
): Promise<void> {
  try {
    if (localStorage.getItem(MIGRATED_FLAG) === '1') return;
  } catch {
    return; // storage disabled — don't try to migrate
  }

  try {
    await sweepPracticeStatus(defaultCampaignId);
    await sweepCodeDrafts(userId, defaultCampaignId);
    await sweepExistingApplications(defaultCampaignId);
    localStorage.setItem(MIGRATED_FLAG, '1');
  } catch {
    // Leave the flag unset so the sweep retries on next boot — a
    // transient network hiccup shouldn't permanently skip it.
  }
}

async function sweepPracticeStatus(campaignId: string): Promise<void> {
  let raw: string | null = null;
  try {
    raw = localStorage.getItem(STATUS_KEY);
  } catch {
    return;
  }
  if (!raw) return;
  let map: Record<string, PracticeStatus>;
  try {
    map = JSON.parse(raw);
  } catch {
    return;
  }

  for (const [key, status] of Object.entries(map)) {
    const [trackPrefix, rawSlug] = key.split(':');
    const track = TRACK_FROM_PREFIX[trackPrefix];
    if (!track || !rawSlug) continue;
    try {
      await api.post('/api/user-progress', {
        campaign_id: campaignId,
        question_type: track,
        question_slug: rawSlug,
        status,
      });
    } catch {
      /* one failure shouldn't block the rest */
    }
  }
}

async function sweepCodeDrafts(
  userId: string,
  campaignId: string,
): Promise<void> {
  const prefix = `${DRAFT_PREFIX}${userId}:`;
  const keys: string[] = [];
  try {
    for (let i = 0; i < localStorage.length; i += 1) {
      const k = localStorage.key(i);
      if (k && k.startsWith(prefix)) keys.push(k);
    }
  } catch {
    return;
  }

  for (const key of keys) {
    const rest = key.slice(prefix.length);
    const [qidPart, langPart] = rest.split(':');
    if (!qidPart || !langPart) continue;
    let code: string | null = null;
    try {
      code = localStorage.getItem(key);
    } catch {
      continue;
    }
    if (!code) continue;
    try {
      await api.post('/api/code-drafts', {
        campaign_id: campaignId,
        question: qidPart,
        language: langPart,
        code,
      });
    } catch {
      /* skip on error */
    }
  }
}

async function sweepExistingApplications(campaignId: string): Promise<void> {
  // Applications (and their rounds) that existed before the campaign
  // feature have no campaign relation. Assign them to the default
  // campaign so they remain visible under the active workspace.
  try {
    const apps = await api.get<{
      id: string;
      company?: string;
      role?: string;
      status?: string;
      applied_date?: string;
      notes?: string;
      resume_variant?: string;
      url?: string;
      job_description?: string;
      campaign?: string | null;
    }[]>('/api/applications');
    for (const app of apps) {
      if (app.campaign) continue;
      try {
        await api.put(`/api/applications/${app.id}`, {
          ...app,
          campaign_id: campaignId,
        });
      } catch {
        /* skip */
      }
    }
  } catch {
    /* skip */
  }
}
