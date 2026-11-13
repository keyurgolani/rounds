import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import {
  createCampaign as apiCreateCampaign,
  getUserPreferences,
  listCampaigns,
  updateCampaign as apiUpdateCampaign,
  upsertUserPreferences,
} from './api';
import { useAuth } from '../auth/AuthProvider';
import type { Campaign } from './types';
import {
  hydrateCampaignProgress,
  setActiveCampaignForStatus,
} from '../hooks/usePracticeStatus';
import {
  deleteUserProgress,
  listUserProgress,
} from '../hooks/progressApi';
import { deleteCodeDraft, listCodeDrafts } from '../lib/codeDraftsApi';

interface CampaignContextValue {
  campaigns: Campaign[];
  // null means "All active" rollup (nothing filtered).
  currentId: string | null;
  currentCampaign: Campaign | null;
  ready: boolean;
  setCurrent: (id: string | null) => void;
  createCampaign: (input: Partial<Campaign>) => Promise<Campaign>;
  updateCampaign: (id: string, patch: Partial<Campaign>) => Promise<Campaign>;
  wrapCampaign: (id: string) => Promise<void>;
  resetProgress: (id: string) => Promise<void>;
  refresh: () => Promise<void>;
}

const CampaignContext = createContext<CampaignContextValue | null>(null);

const CURRENT_ID_KEY = 'rounds.currentCampaign.v1';
// How often a click or key press in a tab may check its campaign again.
const ACTION_CHECK_MS = 15_000;

function slugify(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64) || 'campaign';
}

async function ensureUniqueSlug(base: string, existing: Campaign[]): Promise<string> {
  const slugs = new Set(existing.map((c) => c.slug));
  if (!slugs.has(base)) return base;
  let i = 2;
  while (slugs.has(`${base}-${i}`)) i += 1;
  return `${base}-${i}`;
}

// The account's campaigns, with a default one made when it has none. Two
// first loads at once (two tabs, or two visitors on the shared demo
// account) can both find none; the second create then fails on the
// unique (user, slug) index, so it lists again and takes the one the
// first made.
async function campaignsWithDefault(): Promise<Campaign[]> {
  const list = await listCampaigns();
  if (list.length > 0) return list;
  try {
    const created = await apiCreateCampaign({
      name: 'Default',
      slug: 'default',
      status: 'active',
      color: 'accent',
      is_default: true,
    });
    return [created];
  } catch (err) {
    const again = await listCampaigns();
    if (again.length > 0) return again;
    throw err;
  }
}

// Which campaign to select: the stored one while it still exists, then
// the server-side preference, then the first default campaign (or the
// first active one).
async function selectFrom(list: Campaign[], stored: string | null): Promise<string> {
  if (stored && list.some((c) => c.id === stored)) return stored;
  try {
    const pref = await getUserPreferences();
    const prefId = pref?.current_campaign_id;
    if (prefId && list.some((c) => c.id === prefId)) return prefId;
  } catch {
    /* ignore */
  }
  const fallback =
    list.find((c) => c.is_default) ?? list.find((c) => c.status === 'active') ?? list[0];
  return fallback.id;
}

export function CampaignProvider({ children }: { children: ReactNode }) {
  const { user, ready: authReady } = useAuth();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [currentId, setCurrentIdState] = useState<string | null>(() => {
    try {
      return localStorage.getItem(CURRENT_ID_KEY);
    } catch {
      return null;
    }
  });
  const [ready, setReady] = useState(false);
  const bootstrappedRef = useRef<string | null>(null);
  // The selection as of now, for checks that run outside a render.
  const currentIdRef = useRef<string | null>(currentId);
  currentIdRef.current = currentId;

  const persistCurrent = useCallback((id: string | null) => {
    try {
      if (id) localStorage.setItem(CURRENT_ID_KEY, id);
      else localStorage.removeItem(CURRENT_ID_KEY);
    } catch {
      /* noop */
    }
  }, []);

  const setCurrent = useCallback(
    (id: string | null) => {
      setCurrentIdState(id);
      persistCurrent(id);
      // Fire-and-forget persist to PB so a cross-device reload lands on
      // the same workspace.
      (async () => {
        try {
          await upsertUserPreferences({ current_campaign_id: id ?? '' });
        } catch {
          /* noop — localStorage still wins for this tab */
        }
      })();
    },
    [persistCurrent],
  );

  // Lists the campaigns again. When the selected one is gone (deleted in
  // another tab, or cleared by another visitor's sign-out on the shared
  // demo account), it runs the bootstrap again, so new rows never point
  // at a campaign that no longer exists. "All active" (no selection)
  // stays as it is while any campaign is left.
  const refresh = useCallback(async () => {
    if (!user) return;
    const list = await listCampaigns();
    const current = currentIdRef.current;
    if (list.length > 0 && (current === null || list.some((c) => c.id === current))) {
      setCampaigns(list);
      return;
    }
    const fresh = list.length > 0 ? list : await campaignsWithDefault();
    const next = await selectFrom(fresh, null);
    setCampaigns(fresh);
    setCurrentIdState(next);
    persistCurrent(next);
  }, [user, persistCurrent]);

  // Bootstrap on auth. Runs once per user session. The ref is flipped
  // to the user id only on successful completion so React's strict-mode
  // "mount → unmount → mount" dance doesn't strand us in a half-started
  // state where the first run was cancelled and the second short-
  // circuits on the ref.
  useEffect(() => {
    if (!authReady) return;
    if (!user) {
      setCampaigns([]);
      setReady(true);
      bootstrappedRef.current = null;
      return;
    }
    if (bootstrappedRef.current === user.id) return;

    let cancelled = false;
    (async () => {
      try {
        const list = await campaignsWithDefault();

        if (cancelled) return;
        setCampaigns(list);

        // Reconcile current selection: prefer stored local value, then
        // server-side user preference, then default to the first default
        // campaign (or first active).
        const next = await selectFrom(list, currentId);

        if (cancelled) return;
        setCurrentIdState(next);
        persistCurrent(next);

        if (cancelled) return;
        bootstrappedRef.current = user.id;
      } finally {
        if (!cancelled) setReady(true);
      }
    })();

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authReady, user]);

  const createCampaign = useCallback(
    async (input: Partial<Campaign>) => {
      const name = (input.name ?? '').trim() || 'New campaign';
      const baseSlug = slugify(input.slug ?? name);
      const slug = await ensureUniqueSlug(baseSlug, campaigns);
      const created = await apiCreateCampaign({
        ...input,
        name,
        slug,
        status: input.status ?? 'active',
        color: input.color ?? 'accent',
        is_default: false,
      });
      setCampaigns((prev) => [created, ...prev]);
      setCurrent(created.id);
      return created;
    },
    [campaigns, setCurrent],
  );

  const updateCampaign = useCallback(
    async (id: string, patch: Partial<Campaign>) => {
      const existing = campaigns.find((c) => c.id === id);
      if (!existing) throw new Error('Campaign not found');
      const merged = { ...existing, ...patch };
      const saved = await apiUpdateCampaign(id, merged);
      setCampaigns((prev) => prev.map((c) => (c.id === id ? saved : c)));
      return saved;
    },
    [campaigns],
  );

  const wrapCampaign = useCallback(
    async (id: string) => {
      await updateCampaign(id, { status: 'wrapped' });
    },
    [updateCampaign],
  );

  const resetProgress = useCallback(async (id: string) => {
    // Server-side bulk delete would be nicer, but PB doesn't expose
    // batch deletes — fetch and delete in parallel. Small per-campaign
    // volume keeps this cheap.
    const [progress, drafts] = await Promise.all([
      listUserProgress(id),
      listCodeDrafts({ campaign_id: id }),
    ]);
    await Promise.all([
      ...progress.map((p) => deleteUserProgress(p.id)),
      ...drafts.map((d) => deleteCodeDraft(d.id)),
    ]);
  }, []);

  // A tab checks that its campaign still exists, once the bootstrap has
  // run: when it comes back into view, and on the next click or key press
  // in it, at most every ACTION_CHECK_MS, since another visitor's sign-out
  // can clear the shared demo account's campaigns while a tab stays in view.
  useEffect(() => {
    if (!user) return;
    const check = () => {
      if (bootstrappedRef.current !== user.id || document.visibilityState !== 'visible') return;
      void refresh().catch(() => {
        /* the next check tries again */
      });
    };
    let lastAction = Date.now();
    const onAction = () => {
      const now = Date.now();
      if (now - lastAction < ACTION_CHECK_MS) return;
      lastAction = now;
      check();
    };
    window.addEventListener('focus', check);
    document.addEventListener('visibilitychange', check);
    window.addEventListener('pointerdown', onAction, true);
    window.addEventListener('keydown', onAction, true);
    return () => {
      window.removeEventListener('focus', check);
      document.removeEventListener('visibilitychange', check);
      window.removeEventListener('pointerdown', onAction, true);
      window.removeEventListener('keydown', onAction, true);
    };
  }, [user, refresh]);

  // Keep the module-level practice-status hooks in sync with the active
  // campaign so reads and writes land in the right slot.
  useEffect(() => {
    setActiveCampaignForStatus(currentId);
    if (currentId) void hydrateCampaignProgress(currentId);
  }, [currentId]);

  const currentCampaign = useMemo(
    () => campaigns.find((c) => c.id === currentId) ?? null,
    [campaigns, currentId],
  );

  const value: CampaignContextValue = useMemo(
    () => ({
      campaigns,
      currentId,
      currentCampaign,
      ready,
      setCurrent,
      createCampaign,
      updateCampaign,
      wrapCampaign,
      resetProgress,
      refresh,
    }),
    [
      campaigns,
      currentId,
      currentCampaign,
      ready,
      setCurrent,
      createCampaign,
      updateCampaign,
      wrapCampaign,
      resetProgress,
      refresh,
    ],
  );

  return <CampaignContext.Provider value={value}>{children}</CampaignContext.Provider>;
}

export function useCampaign(): CampaignContextValue {
  const ctx = useContext(CampaignContext);
  if (!ctx) {
    // A defensive fallback keeps pages renderable at the login screen,
    // where CampaignProvider hasn't been mounted yet.
    return {
      campaigns: [],
      currentId: null,
      currentCampaign: null,
      ready: false,
      setCurrent: () => {},
      createCampaign: async () => ({ id: '', slug: '', name: '' } as unknown as Campaign),
      updateCampaign: async (_id, patch) => patch as Campaign,
      wrapCampaign: async () => {},
      resetProgress: async () => {},
      refresh: async () => {},
    };
  }
  return ctx;
}
