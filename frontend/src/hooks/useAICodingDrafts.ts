import { useEffect, useRef, useState } from 'react';
import {
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

  return { files, savedFiles, setFile, hydrated };
}
