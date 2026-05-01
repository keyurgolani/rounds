import { useCallback, useEffect, useState } from 'react';
import type { PracticeStatus } from '../components/shell/StatusDot';
import { api } from '../api/client';

const STATUS_KEY = 'rounds.practiceStatus.v1';

export type PracticeKind = 'system' | 'coding' | 'behavioral';
type Track = PracticeKind;

type AllMaps = Record<string, Record<string, PracticeStatus>>;

// Current campaign ID keying the active slot. Updated by CampaignProvider
// so the hook and its module-level helpers (effectiveStatus) agree on
// which workspace they're reading. `null` = no campaign selected (yet),
// which maps to a single unsubscoped slot so pre-bootstrap reads don't
// crash.
let CURRENT_CAMPAIGN: string | null = null;

function loadAll(): AllMaps {
  try {
    const raw = localStorage.getItem(STATUS_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    // Legacy single-slot shape — migrate inline into the rollup slot so
    // nothing is lost while CampaignProvider bootstraps.
    if (parsed && typeof parsed === 'object' && !isNested(parsed)) {
      return { __rollup__: parsed };
    }
    return parsed;
  } catch {
    return {};
  }
}

function isNested(obj: unknown): boolean {
  if (!obj || typeof obj !== 'object') return false;
  const first = Object.values(obj)[0];
  return typeof first === 'object' && first !== null;
}

function saveAll(m: AllMaps) {
  try {
    localStorage.setItem(STATUS_KEY, JSON.stringify(m));
  } catch {
    /* noop */
  }
}

function slotKey(campaignId: string | null): string {
  return campaignId ?? '__rollup__';
}

function loadSlot(campaignId: string | null): Record<string, PracticeStatus> {
  const all = loadAll();
  return all[slotKey(campaignId)] ?? {};
}

function saveSlot(campaignId: string | null, m: Record<string, PracticeStatus>) {
  const all = loadAll();
  all[slotKey(campaignId)] = m;
  saveAll(all);
}

export function setActiveCampaignForStatus(id: string | null) {
  CURRENT_CAMPAIGN = id;
  // Broadcast so the hooks re-read against the new slot.
  window.dispatchEvent(new CustomEvent('rounds:status'));
}

export async function hydrateCampaignProgress(campaignId: string) {
  try {
    const rows = await api.get<
      {
        question_type: Track;
        question_slug: string;
        status: PracticeStatus;
      }[]
    >(`/api/user-progress?campaign=${campaignId}`);
    const m: Record<string, PracticeStatus> = {};
    for (const r of rows) {
      if (!r.question_type || !r.question_slug) continue;
      m[`${r.question_type}:${r.question_slug}`] = r.status;
    }
    saveSlot(campaignId, m);
    window.dispatchEvent(new CustomEvent('rounds:status'));
  } catch {
    /* best-effort — local state remains the fast path */
  }
}

async function persistSingle(
  campaignId: string | null,
  track: Track,
  slugOrId: string,
  status: PracticeStatus,
) {
  if (!campaignId) return;
  try {
    const existing = await api.get<
      { id: string; question_type: Track; question_slug: string }[]
    >(`/api/user-progress?campaign=${campaignId}`);
    const match = existing.find(
      (r) => r.question_type === track && r.question_slug === slugOrId,
    );
    if (match) {
      await api.put(`/api/user-progress/${match.id}`, {
        campaign_id: campaignId,
        question_type: track,
        question_slug: slugOrId,
        status,
      });
    } else {
      await api.post('/api/user-progress', {
        campaign_id: campaignId,
        question_type: track,
        question_slug: slugOrId,
        status,
      });
    }
  } catch {
    /* swallow — localStorage remains the user-visible source of truth */
  }
}

export function usePracticeStatus(
  track: Track,
  id: number | string,
  fallback: PracticeStatus = 'todo',
): [PracticeStatus, (s: PracticeStatus) => void] {
  const key = `${track}:${id}`;
  const [status, setStatus] = useState<PracticeStatus>(() => {
    return loadSlot(CURRENT_CAMPAIGN)[key] ?? fallback;
  });

  useEffect(() => {
    const on = () => {
      setStatus(loadSlot(CURRENT_CAMPAIGN)[key] ?? fallback);
    };
    window.addEventListener('rounds:status', on);
    return () => window.removeEventListener('rounds:status', on);
  }, [key, fallback]);

  const set = useCallback(
    (s: PracticeStatus) => {
      const m = loadSlot(CURRENT_CAMPAIGN);
      m[key] = s;
      saveSlot(CURRENT_CAMPAIGN, m);
      setStatus(s);
      window.dispatchEvent(new CustomEvent('rounds:status', { detail: { key, status: s } }));
      // Fire-and-forget server sync.
      void persistSingle(CURRENT_CAMPAIGN, track, String(id), s);
    },
    [key, track, id],
  );

  return [status, set];
}

export function useStatusMapVersion() {
  const [v, setV] = useState(0);
  useEffect(() => {
    const on = () => setV((x) => x + 1);
    window.addEventListener('rounds:status', on);
    return () => window.removeEventListener('rounds:status', on);
  }, []);
  return v;
}

export function effectiveStatus(
  track: Track,
  id: number | string,
  fallback: PracticeStatus = 'todo',
) {
  return loadSlot(CURRENT_CAMPAIGN)[`${track}:${id}`] ?? fallback;
}
