import { useEffect, useRef, useState } from 'react';
import {
  deleteAllDrafts,
  listDrafts,
  upsertDraft,
  type AICodingRound,
  type DraftRow,
} from '../pages/ai-coding/aiCodingApi';

const AUTOSAVE_MS = 10_000;

type Files = Record<string, string>;

export function useAICodingDrafts(round: AICodingRound | null, campaignId?: string) {
  const [files, setFiles] = useState<Files>({});
  const [savedFiles, setSavedFiles] = useState<Files>({});
  const [hydrated, setHydrated] = useState(false);
  const dirtyRef = useRef<Set<string>>(new Set());

  // Hydrate: starter overlaid by draft rows.
  useEffect(() => {
    if (!round) return;
    let cancelled = false;
    setHydrated(false);
    (async () => {
      const starter: Files = {};
      for (const f of round.starter_files) starter[f.path] = f.contents;
      let drafts: DraftRow[] = [];
      try {
        drafts = await listDrafts(round.id, campaignId);
      } catch {
        /* fallthrough — starter only */
      }
      const merged: Files = { ...starter };
      for (const d of drafts) merged[d.file_path] = d.contents;
      if (cancelled) return;
      setFiles(merged);
      setSavedFiles(merged);
      setHydrated(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [round?.id, campaignId]);

  // Mirror latest files/savedFiles into refs so the autosave interval can read
  // current values without restarting on every keystroke.
  const filesRef = useRef<Files>({});
  const savedRef = useRef<Files>({});
  useEffect(() => {
    filesRef.current = files;
  }, [files]);
  useEffect(() => {
    savedRef.current = savedFiles;
  }, [savedFiles]);

  // Autosave dirty files at most every AUTOSAVE_MS.
  useEffect(() => {
    if (!round || !hydrated) return;
    const t = setInterval(async () => {
      const dirty = Array.from(dirtyRef.current);
      if (!dirty.length) return;
      dirtyRef.current.clear();
      const next: Files = { ...savedRef.current };
      for (const path of dirty) {
        try {
          await upsertDraft({
            roundId: round.id,
            campaignId,
            filePath: path,
            contents: filesRef.current[path] ?? '',
          });
          next[path] = filesRef.current[path] ?? '';
        } catch {
          // Re-mark for retry next tick.
          dirtyRef.current.add(path);
        }
      }
      setSavedFiles(next);
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
        }).catch(() => {
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

  /** Discard every saved draft on the server and rehydrate local
   *  state from the round's starter files. The caller is expected
   *  to confirm the destructive intent first. */
  async function resetToStarter() {
    if (!round) return;
    dirtyRef.current.clear();
    try {
      await deleteAllDrafts(round.id, campaignId);
    } catch {
      /* best-effort — local state still resets */
    }
    const starter: Files = {};
    for (const f of round.starter_files) starter[f.path] = f.contents;
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
  };
}
