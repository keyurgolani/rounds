import { useEffect, useRef, useState } from 'react';
import {
  deleteAllDrafts,
  draftPathFilter,
  listDrafts,
  upsertDraft,
  type AICodingRound,
  type AICodingRoundRaw,
  type DraftRow,
} from '../pages/ai-coding/aiCodingApi';

const AUTOSAVE_MS = 10_000;

type Files = Record<string, string>;

export function useAICodingDrafts(
  round: AICodingRound | null,
  campaignId?: string,
  rawRound?: AICodingRoundRaw | null,
) {
  const [files, setFiles] = useState<Files>({});
  const [savedFiles, setSavedFiles] = useState<Files>({});
  const [hydrated, setHydrated] = useState(false);
  const dirtyRef = useRef<Set<string>>(new Set());
  // What the server last confirmed for each path, updated as each save
  // lands, so saveNow knows what's unsaved even mid-autosave.
  const confirmedRef = useRef<Files>({});
  // The autosave pass in flight, if any.
  const autosaveRef = useRef<Promise<boolean> | null>(null);

  // Hydrate: starter overlaid by draft rows. A multi-language round
  // keeps every round's drafts under one round id, so a draft comes back
  // only when it's this language's: a starter file here, or a file the
  // candidate created that isn't another language's (draftPathFilter).
  useEffect(() => {
    if (!round) return;
    if (!Array.isArray(round.starter_files)) {
      // Should never happen — AICodingDetail resolves the round to a
      // single-language shape before passing it in. Bail rather than
      // attempting to iterate a map.
      return;
    }
    let cancelled = false;
    setHydrated(false);
    (async () => {
      const starter: Files = {};
      for (const f of round.starter_files as Array<{ path: string; contents: string }>) {
        starter[f.path] = f.contents;
      }
      const starterPaths = new Set(Object.keys(starter));
      const keep = rawRound ? draftPathFilter(rawRound, round.language) : (path: string) => starterPaths.has(path);
      let drafts: DraftRow[] = [];
      try {
        drafts = await listDrafts(round.id, campaignId);
      } catch {
        /* fallthrough — starter only */
      }
      const merged: Files = { ...starter };
      for (const d of drafts) {
        if (keep(d.file_path)) merged[d.file_path] = d.contents;
      }
      if (cancelled) return;
      confirmedRef.current = merged;
      setFiles(merged);
      setSavedFiles(merged);
      setHydrated(true);
    })();
    return () => {
      cancelled = true;
    };
    // `round?.language` is included so switching languages on a multi-
    // language round (which AICodingDetail signals by resolving to a
    // new effective round) triggers a re-hydrate against the new
    // language's starter files.
  }, [round?.id, round?.language, campaignId, rawRound]);

  // Mirror latest files into a ref so the autosave interval can read
  // current values without restarting on every keystroke.
  const filesRef = useRef<Files>({});
  useEffect(() => {
    filesRef.current = files;
  }, [files]);

  // Saves each path's current contents, one after another or all at
  // once. A save that fails goes back on the dirty list for the next
  // autosave. True when every save landed.
  async function savePaths(roundId: string, paths: string[], oneAtATime: boolean): Promise<boolean> {
    async function saveOne(path: string): Promise<boolean> {
      const contents = filesRef.current[path] ?? '';
      try {
        await upsertDraft({ roundId, campaignId, filePath: path, contents });
        confirmedRef.current = { ...confirmedRef.current, [path]: contents };
        return true;
      } catch {
        dirtyRef.current.add(path);
        return false;
      }
    }
    let saved = true;
    if (oneAtATime) {
      for (const path of paths) saved = (await saveOne(path)) && saved;
    } else {
      saved = (await Promise.all(paths.map(saveOne))).every(Boolean);
    }
    setSavedFiles({ ...confirmedRef.current });
    return saved;
  }

  // Autosave dirty files at most every AUTOSAVE_MS, one pass at a time.
  useEffect(() => {
    if (!round || !hydrated) return;
    const roundId = round.id;
    const t = setInterval(() => {
      if (autosaveRef.current) return;
      const dirty = Array.from(dirtyRef.current);
      if (!dirty.length) return;
      dirtyRef.current.clear();
      const pass = savePaths(roundId, dirty, true);
      autosaveRef.current = pass;
      void pass.finally(() => {
        if (autosaveRef.current === pass) autosaveRef.current = null;
      });
    }, AUTOSAVE_MS);
    return () => clearInterval(t);
  }, [round?.id, hydrated, campaignId]);

  function setFile(path: string, contents: string) {
    setFiles((prev) => {
      if (prev[path] === contents) return prev;
      dirtyRef.current.add(path);
      return { ...prev, [path]: contents };
    });
  }

  /**
   * Persist a set of file changes to the server RIGHT NOW (no waiting
   * for the autosave tick). Used when the user accepts an AI patch:
   * if they refresh within the autosave window, the post-apply
   * contents would otherwise be lost — the rehydrated chat would show
   * "Applied" but the workspace would still hold the pre-apply code.
   *
   * Updates the local files map AND savedFiles so the editor reflects
   * the new contents immediately, and clears those paths from the
   * dirty set so the timer doesn't double-write them.
   */
  async function persistImmediately(updates: Record<string, string>) {
    if (!round) return;
    const paths = Object.keys(updates);
    if (paths.length === 0) return;
    setFiles((prev) => ({ ...prev, ...updates }));
    for (const p of paths) dirtyRef.current.delete(p);
    await Promise.all(
      paths.map((path) =>
        upsertDraft({
          roundId: round.id,
          campaignId,
          filePath: path,
          contents: updates[path],
        })
          .then(() => {
            confirmedRef.current = { ...confirmedRef.current, [path]: updates[path] };
          })
          .catch(() => {
            // Re-mark for retry on the next autosave tick — at least the
            // local state is correct, and the user gets a second chance
            // at persistence. Don't surface the error to the caller; the
            // accept flow already proceeded.
            dirtyRef.current.add(path);
          }),
      ),
    );
    setSavedFiles((prev) => {
      const next = { ...prev };
      for (const p of paths) {
        if (!dirtyRef.current.has(p)) next[p] = updates[p];
      }
      return next;
    });
  }

  /**
   * Saves every file that differs from what the server last confirmed,
   * once any autosave in flight has finished, so a reload keeps it. The
   * autosave takes its paths off the dirty list before it saves them one
   * at a time, so a file it hadn't reached yet still counts. True when
   * every save landed.
   */
  async function saveNow(): Promise<boolean> {
    if (!round) return true;
    if (autosaveRef.current) await autosaveRef.current;
    const current = filesRef.current;
    const unsaved = new Set(dirtyRef.current);
    for (const [path, contents] of Object.entries(current)) {
      if (confirmedRef.current[path] !== contents) unsaved.add(path);
    }
    for (const path of unsaved) dirtyRef.current.delete(path);
    if (unsaved.size === 0) return true;
    return savePaths(round.id, [...unsaved], false);
  }

  /** Discard every saved draft on the server and rehydrate local
   *  state from the round's starter files. The caller is expected
   *  to confirm the destructive intent first. */
  async function resetToStarter() {
    if (!round) return;
    if (!Array.isArray(round.starter_files)) return;
    dirtyRef.current.clear();
    try {
      await deleteAllDrafts(round.id, campaignId);
    } catch {
      /* best-effort — local state still resets */
    }
    const starter: Files = {};
    for (const f of round.starter_files as Array<{ path: string; contents: string }>) {
      starter[f.path] = f.contents;
    }
    confirmedRef.current = starter;
    setFiles(starter);
    setSavedFiles(starter);
  }

  return {
    files,
    savedFiles,
    setFile,
    hydrated,
    resetToStarter,
    persistImmediately,
    saveNow,
  };
}
