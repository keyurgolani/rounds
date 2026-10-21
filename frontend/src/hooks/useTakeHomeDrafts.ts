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
  // What the server last confirmed for each path, updated as each save
  // lands, so saveNow knows what's unsaved even mid-autosave.
  const confirmedRef = useRef<Files>({});
  // The autosave pass in flight, if any.
  const autosaveRef = useRef<Promise<boolean> | null>(null);

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
      confirmedRef.current = merged;
      setFiles(merged);
      setSavedFiles(merged);
      setHydrated(true);
    })();
    return () => {
      cancelled = true;
    };
  }, [assignment?.id, campaignId]);

  // Mirror latest files into a ref so the autosave interval can read
  // current values without restarting on every keystroke.
  const filesRef = useRef<Files>({});
  useEffect(() => {
    filesRef.current = files;
  }, [files]);

  // Saves each path's current contents, one after another or all at
  // once. A save that fails goes back on the dirty list for the next
  // autosave. True when every save landed.
  async function savePaths(assignmentId: string, paths: string[], oneAtATime: boolean): Promise<boolean> {
    async function saveOne(path: string): Promise<boolean> {
      const contents = filesRef.current[path] ?? '';
      try {
        await upsertDraft({ assignmentId, campaignId, filePath: path, contents });
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
    if (!assignment || !hydrated) return;
    const assignmentId = assignment.id;
    const t = setInterval(() => {
      if (autosaveRef.current) return;
      const dirty = Array.from(dirtyRef.current);
      if (!dirty.length) return;
      dirtyRef.current.clear();
      const pass = savePaths(assignmentId, dirty, true);
      autosaveRef.current = pass;
      void pass.finally(() => {
        if (autosaveRef.current === pass) autosaveRef.current = null;
      });
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

  /**
   * Saves every file that differs from what the server last confirmed,
   * once any autosave in flight has finished, so a reload keeps it. The
   * autosave takes its paths off the dirty list before it saves them one
   * at a time, so a file it hadn't reached yet still counts. True when
   * every save landed.
   */
  async function saveNow(): Promise<boolean> {
    if (!assignment) return true;
    if (autosaveRef.current) await autosaveRef.current;
    const current = filesRef.current;
    const unsaved = new Set(dirtyRef.current);
    for (const [path, contents] of Object.entries(current)) {
      if (confirmedRef.current[path] !== contents) unsaved.add(path);
    }
    for (const path of unsaved) dirtyRef.current.delete(path);
    if (unsaved.size === 0) return true;
    return savePaths(assignment.id, [...unsaved], false);
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
    confirmedRef.current = starter;
    setFiles(starter);
    setSavedFiles(starter);
  }

  return { files, savedFiles, setFile, hydrated, resetToStarter, saveNow };
}
