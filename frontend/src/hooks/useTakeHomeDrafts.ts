import { useEffect, useRef, useState } from 'react';
import {
  deleteAllDrafts,
  listDrafts,
  upsertDraft,
  type TakeHomeAssignment,
  type TakeHomeDraftRow,
} from '../pages/take-home/takeHomeApi';

const AUTOSAVE_MS = 10_000;

type Files = Record<string, string>;

/**
 * Take-home equivalent of {@link useAICodingDrafts}. Hydrates the editor
 * from the assignment's starter files overlaid by any rows in the
 * `take_home_drafts` collection, then autosaves dirty buffers every
 * AUTOSAVE_MS until the user submits.
 */
export function useTakeHomeDrafts(
  assignment: TakeHomeAssignment | null,
  campaignId?: string,
) {
  const [files, setFiles] = useState<Files>({});
  const [savedFiles, setSavedFiles] = useState<Files>({});
  const [hydrated, setHydrated] = useState(false);
  const dirtyRef = useRef<Set<string>>(new Set());

  // Hydrate: starter overlaid by draft rows.
  useEffect(() => {
    if (!assignment) return;
    let cancelled = false;
    setHydrated(false);
    (async () => {
      const starter: Files = {};
      for (const f of assignment.starter_files) starter[f.path] = f.contents;
      let drafts: TakeHomeDraftRow[] = [];
      try {
        drafts = await listDrafts(assignment.id, campaignId);
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
  }, [assignment?.id, campaignId]);

  // Mirror latest files/savedFiles into refs so the autosave interval can
  // read current values without restarting on every keystroke.
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
    if (!assignment || !hydrated) return;
    const t = setInterval(async () => {
      const dirty = Array.from(dirtyRef.current);
      if (!dirty.length) return;
      dirtyRef.current.clear();
      const next: Files = { ...savedRef.current };
      for (const path of dirty) {
        try {
          await upsertDraft({
            assignmentId: assignment.id,
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
  }, [assignment?.id, hydrated, campaignId]);

  function setFile(path: string, contents: string) {
    setFiles((prev) => {
      if (prev[path] === contents) return prev;
      dirtyRef.current.add(path);
      return { ...prev, [path]: contents };
    });
  }

  /** Discard every saved draft on the server and rehydrate local
   *  state from the assignment's starter files. Caller confirms first. */
  async function resetToStarter() {
    if (!assignment) return;
    dirtyRef.current.clear();
    try {
      await deleteAllDrafts(assignment.id, campaignId);
    } catch {
      /* best-effort — local state still resets */
    }
    const starter: Files = {};
    for (const f of assignment.starter_files) starter[f.path] = f.contents;
    setFiles(starter);
    setSavedFiles(starter);
  }

  return { files, savedFiles, setFile, hydrated, resetToStarter };
}
