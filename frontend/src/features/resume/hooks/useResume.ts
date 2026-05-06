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

const DEBOUNCE_MS = 700;
// Keep a short-lived save in flight from kicking another version row
// per keystroke — coalesce auto-versions to one per minute of activity.
const VERSION_COALESCE_MS = 60_000;

export type SaveState = 'idle' | 'saving' | 'saved' | 'error';

export type UseResumeResult = {
  resume: Resume | null;
  data: ResumeData;
  templateId: string;
  design: TemplateConfig;
  loading: boolean;
  error: string | null;
  saveState: SaveState;
  lastSavedAt: string | null;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
  setTemplateId: (id: string) => void;
  setDesign: (next: TemplateConfig | ((prev: TemplateConfig) => TemplateConfig)) => void;
  // Returns the new slug (which may equal the old slug if the
  // generated value didn't change). Caller should navigate to
  // /resumes/<newSlug> if it differs from the URL.
  rename: (name: string) => Promise<string | null>;
  flush: () => Promise<void>;
};

// PocketBase column names are snake_case; the patch we send to
// updateResume must match its column names exactly. A stray
// `templateId` (camelCase) was being silently dropped by PB, which
// is why template selection didn't survive a refresh.
type Pending = {
  data?: ResumeData;
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
  const [error, setError] = useState<string | null>(null);
  const [saveState, setSaveState] = useState<SaveState>('idle');
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null);

  // Pending patch coalesces calls between debounce ticks.
  const pendingRef = useRef<Pending>({});
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastVersionAtRef = useRef<number>(0);
  const dataRef = useRef<ResumeData>(emptyData());
  // Tracks the slug we've already fetched. After a rename navigates
  // to the new slug, the loader effect would otherwise re-fetch the
  // same resume and flash a loading state — this short-circuits it.
  const loadedSlugRef = useRef<string | null>(null);

  // --- Initial load ----------------------------------------------------
  useEffect(() => {
    if (!slug) return;
    if (loadedSlugRef.current === slug) return; // already loaded
    let cancelled = false;
    setLoading(true);
    getResumeBySlug(slug)
      .then((r) => {
        if (cancelled) return;
        setResume(r);
        setLocalData(r.data);
        dataRef.current = r.data;
        setLocalTemplateId(r.template_id || 'modern');
        setLocalDesign(r.design || {});
        setLastSavedAt(r.updated_at);
        loadedSlugRef.current = r.slug;
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  // --- Save mechanics --------------------------------------------------
  const performSave = useCallback(async () => {
    const r = resume;
    const patch = pendingRef.current;
    if (!r || Object.keys(patch).length === 0) return;
    pendingRef.current = {};

    setSaveState('saving');
    try {
      const updated = await updateResume(r.id, patch);
      setResume(updated);
      setLastSavedAt(updated.updated_at);
      setSaveState('saved');

      // Stamp an auto version, but coalesce so we don't write one per
      // tick. The version captures the canonical resume data only —
      // template/design tweaks aren't versioned (they're cheap to redo).
      const now = Date.now();
      if (patch.data && now - lastVersionAtRef.current > VERSION_COALESCE_MS) {
        lastVersionAtRef.current = now;
        // Best-effort; failure here doesn't affect the save.
        createVersion({
          resumeId: r.id,
          data: patch.data,
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
      setSaveState('error');
      setError((err as Error).message);
    }
  }, [resume]);

  const schedule = useCallback(
    (patch: Pending) => {
      pendingRef.current = { ...pendingRef.current, ...patch };
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        timerRef.current = null;
        void performSave();
      }, DEBOUNCE_MS);
    },
    [performSave],
  );

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

  const rename = useCallback(
    async (name: string): Promise<string | null> => {
      const current = resume;
      if (!current) return null;
      const trimmed = name.trim();
      if (!trimmed || trimmed === current.name) return current.slug;

      // Flush any in-flight edits before we re-slug. Otherwise a
      // pending PATCH from a recent keystroke could land after our
      // rename and clobber the new slug.
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
        await performSave();
      }

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
        // Mark the saved slug as already loaded so the slug-keyed
        // loader effect short-circuits when ResumeStudio navigates.
        loadedSlugRef.current = saved.slug;
        return saved.slug;
      } catch {
        setSaveState('error');
        return current.slug;
      }
    },
    [resume, performSave],
  );

  const flush = useCallback(async () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
    await performSave();
  }, [performSave]);

  // --- Lifecycle: flush on unmount/blur to avoid losing edits ----------
  useEffect(() => {
    const onBeforeUnload = () => {
      // Best-effort sync flush; modern browsers ignore async during
      // unload, so we just clear the timer and rely on saves already
      // dispatched in the background.
      if (timerRef.current) {
        clearTimeout(timerRef.current);
        timerRef.current = null;
        void performSave();
      }
    };
    window.addEventListener('beforeunload', onBeforeUnload);
    return () => {
      window.removeEventListener('beforeunload', onBeforeUnload);
      if (timerRef.current) {
        clearTimeout(timerRef.current);
      }
    };
  }, [performSave]);

  return {
    resume,
    data,
    templateId,
    design,
    loading,
    error,
    saveState,
    lastSavedAt,
    setData,
    setTemplateId,
    setDesign,
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
