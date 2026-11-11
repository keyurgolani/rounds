// Owning hook for the Studio's editing experience.
//
// Loads a Resume by slug, holds local data in state, and persists
// changes back to PocketBase with a debounced save. Each successful
// save also stamps an auto `resume_versions` row so the History tab
// has a restore point. The 700ms debounce is taken straight from the
// reference ResumeBuilder — short enough that "save status" feels
// live, long enough that fast typing doesn't swamp the API.

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  createVersion,
  ensureUniqueSlug,
  getResumeBySlug,
  updateResume,
} from '../api';
import type { Resume, ResumeData, TemplateConfig } from '../types';
import { resolveAndSync, type LibrarySnapshot } from '../links/resolve';
import { loadLibrarySnapshot } from '../links/library';
import { emptyLinks, type ResumeLinks } from '../links/types';

const DEBOUNCE_MS = 700;
// Keep a short-lived save in flight from kicking another version row
// per keystroke — coalesce auto-versions to one per minute of activity.
const VERSION_COALESCE_MS = 60_000;
// After a failed save: the first retry's wait, doubling to this cap.
const RETRY_FIRST_MS = 2_000;
const RETRY_MAX_MS = 30_000;

// A save PocketBase refused for a reason another try can't change: the
// request itself (400, 413, 422), the session (401), the account's rights
// (403), or a resume that's gone (404). Those aren't retried on their own;
// the edits stay pending, and the next edit or export tries once more.
// No answer, a timeout (408), a limit (429), or a server error is retried.
const PERMANENT_STATUSES = new Set([400, 401, 403, 404, 413, 422]);

function retriable(err: unknown): boolean {
  const status = (err as { status?: unknown } | null)?.status;
  return !(typeof status === 'number' && PERMANENT_STATUSES.has(status));
}

// 'error' is a failed save that tries again on its own; 'refused' is one
// PocketBase refused (PERMANENT_STATUSES), which nothing retries until the
// next edit or export.
export type SaveState = 'idle' | 'saving' | 'saved' | 'error' | 'refused';

export type UseResumeResult = {
  resume: Resume | null;
  data: ResumeData;
  templateId: string;
  design: TemplateConfig;
  loading: boolean;
  // Why the slug on screen didn't load, or null. A failed save never sets
  // it: saveState says so, and the Studio stays on screen.
  error: string | null;
  saveState: SaveState;
  lastSavedAt: string | null;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
  setTemplateId: (id: string) => void;
  setDesign: (next: TemplateConfig | ((prev: TemplateConfig) => TemplateConfig)) => void;
  links: ResumeLinks;
  setLinks: (next: ResumeLinks | ((p: ResumeLinks) => ResumeLinks)) => void;
  // Returns the new slug (which may equal the old slug if the
  // generated value didn't change). Caller should navigate to
  // /resumes/<newSlug> if it differs from the URL.
  rename: (name: string) => Promise<string | null>;
  // Saves every pending edit now (ROUNDS-00A-L04). Waits for a save
  // already in flight, rejects when a save fails, and resolves with the
  // resume's saved `updated`, which server PDF sends as
  // `expected_updated`. A failed save keeps its edits pending, so the
  // next save carries them.
  flush: () => Promise<string>;
};

// PocketBase column names are snake_case; the patch we send to
// updateResume must match its column names exactly. A stray
// `templateId` (camelCase) was being silently dropped by PB, which
// is why template selection didn't survive a refresh.
type Pending = {
  data?: ResumeData;
  links?: ResumeLinks;
  template_id?: string;
  design?: TemplateConfig;
  name?: string;
  slug?: string;
};

export function useResume(slug: string | undefined): UseResumeResult {
  const [resume, setResume] = useState<Resume | null>(null);
  const [data, setLocalData] = useState<ResumeData>(emptyData());
  const [templateId, setLocalTemplateId] = useState<string>('modern');
  const [design, setLocalDesign] = useState<TemplateConfig>({});
  const [loading, setLoading] = useState(true);
  // A failed load and the slug it was for, so a later slug in the same
  // Studio shows its own outcome and never an earlier one's.
  const [loadError, setLoadError] = useState<{ slug: string; message: string } | null>(null);
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);
  const [links, setLocalLinks] = useState<ResumeLinks>(emptyLinks());

  // Pending patch coalesces calls between debounce ticks. It belongs to
  // the resume it was typed in (pendingForRef) and only ever saves to it.
  const pendingRef = useRef<Pending>({});
  const pendingForRef = useRef<string | null>(null);
  // The id of the resume on screen; null while the next one loads.
  const shownIdRef = useRef<string | null>(null);
  // Unsaved edits of resumes the Studio has moved on from, by id. Each
  // saves to its own resume, stays here if that fails, and comes back when
  // that resume loads again in this Studio.
  const keptRef = useRef<Map<string, Pending>>(new Map());
  // Those saves, chained; a load waits for them, so it reads what they wrote.
  const leavingRef = useRef<Promise<void>>(Promise.resolve());
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // The save in flight; saves run one at a time, each after the last.
  const savingRef = useRef<Promise<void> | null>(null);
  // The resume's `updated` as the server last answered it.
  const savedAtRef = useRef<string | null>(null);
  // After a failed save, the timer that tries again, and how many tries
  // have failed in a row (the wait doubles each time, up to a cap).
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const failuresRef = useRef(0);
  // The latest save, for the retry timer and the unmount save, which
  // outlive the render that set them up.
  const saveRef = useRef<(() => Promise<void>) | null>(null);
  // Cleared on unmount: the save made then is the last, with no retry.
  const mountedRef = useRef(true);
  const lastVersionAtRef = useRef<number>(0);
  const dataRef = useRef<ResumeData>(emptyData());
  const linksRef = useRef<ResumeLinks>(emptyLinks());
  // Tracks the slug we've already fetched. After a rename navigates
  // to the new slug, the loader effect would otherwise re-fetch the
  // same resume and flash a loading state — this short-circuits it.
  const loadedSlugRef = useRef<string | null>(null);
  // Stable ref to schedule so the initial-load effect can call it
  // without being listed as a dependency (schedule is defined below).
  const scheduleRef = useRef<((patch: Pending) => void) | null>(null);

  // Edits for a resume no longer on screen, merged under any kept since.
  const keep = (id: string, patch: Pending) => {
    if (Object.keys(patch).length === 0) return;
    keptRef.current.set(id, { ...patch, ...(keptRef.current.get(id) ?? {}) });
  };
  // One save of a resume's kept edits, to that resume. If it fails they
  // stay kept for it.
  const saveKept = async (id: string): Promise<void> => {
    const patch = keptRef.current.get(id);
    if (!patch) return;
    keptRef.current.delete(id);
    try {
      await updateResume(id, patch);
    } catch {
      keep(id, patch);
    }
  };

  // --- Initial load ----------------------------------------------------
  useEffect(() => {
    if (!slug) return;
    if (loadedSlugRef.current === slug) return; // already loaded
    // Moving to another resume in the same Studio: what's unsaved here is
    // the shown resume's, so it's kept for it and saved to it, after the
    // save in flight for it, and nothing of it is left for the next one.
    const leaving = shownIdRef.current ?? pendingForRef.current;
    if (timerRef.current) clearTimeout(timerRef.current);
    if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    timerRef.current = null;
    retryTimerRef.current = null;
    const inFlight = savingRef.current;
    savingRef.current = null;
    if (leaving) {
      keep(leaving, pendingRef.current);
      const saved = (inFlight ?? Promise.resolve()).catch(() => undefined).then(() => saveKept(leaving));
      leavingRef.current = Promise.all([leavingRef.current, saved]).then(() => undefined);
    }
    pendingRef.current = {};
    pendingForRef.current = null;
    shownIdRef.current = null;
    loadedSlugRef.current = null;
    savedAtRef.current = null;
    failuresRef.current = 0;
    lastVersionAtRef.current = 0;
    setResume(null);
    setSaveState('idle');
    setLastSavedAt(null);
    setLoadError(null);

    let cancelled = false;
    setLoading(true);
    const emptySnapshot: LibrarySnapshot = { jobs: {}, projects: {}, bullets: {} };
    leavingRef.current
      .then(() => Promise.all([getResumeBySlug(slug), loadLibrarySnapshot().catch(() => emptySnapshot)]))
      .then(([r, lib]) => {
        if (cancelled) return;
        const resolved = resolveAndSync(r.data, r.links, lib);
        // Edits kept from an earlier visit that never saved come back.
        const kept = keptRef.current.get(r.id);
        keptRef.current.delete(r.id);
        const shownData = kept?.data ?? resolved.data;
        const shownLinks = kept?.links ?? resolved.links;
        shownIdRef.current = r.id;
        setResume(r);
        setLocalData(shownData); dataRef.current = shownData;
        setLocalLinks(shownLinks); linksRef.current = shownLinks;
        setLocalTemplateId(kept?.template_id ?? (r.template_id || 'modern'));
        setLocalDesign(kept?.design ?? (r.design || {}));
        setLastSavedAt(r.updated_at);
        savedAtRef.current = r.updated_at;
        loadedSlugRef.current = r.slug;
        const patch: Pending = { ...(resolved.changed ? { data: resolved.data, links: resolved.links } : {}), ...kept };
        if (Object.keys(patch).length > 0) scheduleRef.current?.(patch);
      })
      .catch((err: Error) => { if (!cancelled) setLoadError({ slug, message: err.message }); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  // --- Save mechanics --------------------------------------------------
  // Saves the pending patch to the resume it belongs to. Rejects when the
  // save fails, with its patch put back under anything typed since; if the
  // Studio moved on from that resume meanwhile, the patch is kept for it.
  const performSave = useCallback(async () => {
    const id = pendingForRef.current;
    const patch = pendingRef.current;
    if (!id || Object.keys(patch).length === 0) return;
    pendingRef.current = {};
    // Only the resume on screen shows how its save went.
    const shown = () => shownIdRef.current === id;

    if (shown()) setSaveState('saving');
    try {
      const updated = await updateResume(id, patch);
      if (!shown()) return;
      setResume(updated);
      setLastSavedAt(updated.updated_at);
      savedAtRef.current = updated.updated_at;
      failuresRef.current = 0;
      setSaveState('saved');

      // Stamp an auto version, but coalesce so we don't write one per
      // tick. The version captures the canonical resume data only —
      // template/design tweaks aren't versioned (they're cheap to redo).
      const now = Date.now();
      if (patch.data && now - lastVersionAtRef.current > VERSION_COALESCE_MS) {
        lastVersionAtRef.current = now;
        // Best-effort; failure here doesn't affect the save.
        createVersion({
          resumeId: id,
          data: patch.data,
          links: patch.links ?? linksRef.current,
          isAuto: true,
        }).catch(() => {
          /* ignore */
        });
      }

      // Drop the "saved" badge after a beat.
      window.setTimeout(() => {
        setSaveState((s) => (s === 'saved' ? 'idle' : s));
      }, 1200);
    } catch (err) {
      if (!shown()) {
        keep(id, patch);
        throw err;
      }
      pendingRef.current = { ...patch, ...pendingRef.current };
      pendingForRef.current = id;
      // Try again on its own, waiting longer after each failure in a row,
      // so the edits never sit unsaved until the next keystroke; unless
      // another try can't succeed (PERMANENT_STATUSES).
      const refused = !retriable(err);
      setSaveState(refused ? 'refused' : 'error');
      failuresRef.current += 1;
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
      if (!mountedRef.current || refused) throw err;
      const wait = Math.min(RETRY_MAX_MS, RETRY_FIRST_MS * 2 ** (failuresRef.current - 1));
      retryTimerRef.current = setTimeout(() => {
        retryTimerRef.current = null;
        saveRef.current?.().catch(() => undefined);
      }, wait);
      throw err;
    }
    // Reads only refs, so one instance serves every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Starts a save once the one in flight ends, and returns it. A save
  // started for any reason replaces a retry still waiting.
  const save = useCallback((): Promise<void> => {
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
    const before = savingRef.current;
    const next = (before ? before.catch(() => undefined) : Promise.resolve()).then(performSave);
    savingRef.current = next;
    const clear = () => {
      if (savingRef.current === next) savingRef.current = null;
    };
    next.then(clear, clear);
    return next;
  }, [performSave]);
  saveRef.current = save;

  // A save nothing waits on: its failure already shows as the save state.
  const saveInBackground = useCallback(() => {
    save().catch(() => undefined);
  }, [save]);

  const schedule = useCallback(
    (patch: Pending) => {
      // Edits belong to the resume on screen; anything still pending for
      // another one is kept for that one.
      const id = shownIdRef.current;
      if (pendingForRef.current && pendingForRef.current !== id) {
        keep(pendingForRef.current, pendingRef.current);
        pendingRef.current = {};
      }
      pendingForRef.current = id;
      pendingRef.current = { ...pendingRef.current, ...patch };
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        saveInBackground();
      }, DEBOUNCE_MS);
    },
    [saveInBackground],
  );
  // Keep the ref current so the initial-load effect can reach schedule
  // without a dependency cycle.
  scheduleRef.current = schedule;

  // --- Public setters --------------------------------------------------
  const setData: UseResumeResult['setData'] = useCallback(
    (next) => {
      setLocalData((prev) => {
        const value = typeof next === 'function' ? (next as (p: ResumeData) => ResumeData)(prev) : next;
        dataRef.current = value;
        schedule({ data: value });
        return value;
      });
    },
    [schedule],
  );

  const setTemplateId = useCallback(
    (id: string) => {
      setLocalTemplateId(id);
      schedule({ template_id: id });
    },
    [schedule],
  );

  const setDesign: UseResumeResult['setDesign'] = useCallback(
    (next) => {
      setLocalDesign((prev) => {
        const value = typeof next === 'function' ? (next as (p: TemplateConfig) => TemplateConfig)(prev) : next;
        schedule({ design: value });
        return value;
      });
    },
    [schedule],
  );

  const setLinks: UseResumeResult['setLinks'] = useCallback((next) => {
    setLocalLinks((prev) => {
      const value = typeof next === 'function' ? (next as (p: ResumeLinks) => ResumeLinks)(prev) : next;
      linksRef.current = value;
      schedule({ links: value });
      return value;
    });
  }, [schedule]);

  const rename = useCallback(
    async (name: string): Promise<string | null> => {
      const current = resume;
      if (!current) return null;
      const trimmed = name.trim();
      if (!trimmed || trimmed === current.name) return current.slug;

      // Flush any in-flight edits before we re-slug. Otherwise a
      // pending PATCH from a recent keystroke could land after our
      // rename and clobber the new slug. A failed save keeps its edits
      // pending and the rename still goes ahead.
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      await save().catch(() => undefined);

      let newSlug = current.slug;
      try {
        newSlug = await ensureUniqueSlug(trimmed, current.id);
      } catch {
        // Slug lookup failed — keep the old slug and at least update
        // the name; the URL just won't follow.
        newSlug = current.slug;
      }

      // Mirror locally first so the studio UI reflects the change
      // immediately; the patch lands in the background.
      setResume((r) =>
        r ? { ...r, name: trimmed, slug: newSlug } : r,
      );

      try {
        const saved = await updateResume(current.id, {
          name: trimmed,
          ...(newSlug !== current.slug ? { slug: newSlug } : {}),
        });
        setResume(saved);
        setSaveState('saved');
        setLastSavedAt(saved.updated_at);
        savedAtRef.current = saved.updated_at;
        // Mark the saved slug as already loaded so the slug-keyed
        // loader effect short-circuits when ResumeStudio navigates.
        loadedSlugRef.current = saved.slug;
        return saved.slug;
      } catch {
        setSaveState('error');
        return current.slug;
      }
    },
    [resume, save],
  );

  const flush = useCallback(async (): Promise<string> => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    // Queued behind the save in flight, so a failure of either rejects.
    if (savingRef.current) await savingRef.current;
    await save();
    if (savedAtRef.current === null) throw new Error('This resume has not loaded yet.');
    return savedAtRef.current;
  }, [save]);

  // --- Lifecycle: flush on unmount/blur to avoid losing edits ----------
  // Set up once: it reads the latest save through saveRef, so a new
  // `resume` (every save makes one) doesn't tear it down mid-edit.
  useEffect(() => {
    // Starts a save of anything not yet saved, waiting or not. A save in
    // flight has already taken its edits, so one is queued behind it too:
    // it finds nothing to do once that save lands, and tries those edits
    // once more if it fails.
    const saveWhatIsLeft = () => {
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
      }
      if (Object.keys(pendingRef.current).length > 0 || savingRef.current) {
        saveRef.current?.().catch(() => undefined);
      }
      // And the edits kept for resumes the Studio moved on from, each to
      // its own resume.
      for (const id of [...keptRef.current.keys()]) {
        leavingRef.current = leavingRef.current.then(() => saveKept(id));
      }
    };
    // Best-effort; modern browsers don't wait for async work during
    // unload, so this only dispatches the save.
    const onBeforeUnload = () => saveWhatIsLeft();
    mountedRef.current = true;
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => {
      mountedRef.current = false;
      window.removeEventListener('beforeunload', onBeforeUnload);
      // Leaving the Studio (in-app navigation) saves pending edits,
      // a failed save's included, instead of dropping them.
      saveWhatIsLeft();
      if (retryTimerRef.current) {
        clearTimeout(retryTimerRef.current);
        retryTimerRef.current = null;
      }
    };
  }, []);

  return {
    resume,
    data,
    templateId,
    design,
    links,
    loading,
    error: loadError && loadError.slug === slug ? loadError.message : null,
    saveState,
    lastSavedAt,
    setData,
    setTemplateId,
    setDesign,
    setLinks,
    rename,
    flush,
  };
}

function emptyData(): ResumeData {
  return {
    personalInfo: { fullName: '' },
    experience: [],
    education: [],
    skills: [],
    projects: [],
    publications: [],
    profiles: [],
  };
}
