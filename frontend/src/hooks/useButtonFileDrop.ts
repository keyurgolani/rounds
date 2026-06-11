// frontend/src/hooks/useButtonFileDrop.ts
//
// Makes a button-sized element a file drop target. Returns drag handlers to
// spread on the element plus an `isOver` flag for highlighting. Only reacts to
// real file drags (dataTransfer carries 'Files'), so internal element drags
// (e.g. the Arrange board's drag-to-connect) are never intercepted.
import { useCallback, useState } from 'react';
import type { DragEvent } from 'react';

interface UseButtonFileDropOptions {
  /** Called with the first dropped file. */
  onFile: (file: File) => void;
  /** When true, the target highlights nothing and drops are swallowed (no onFile). */
  disabled?: boolean;
}

interface ButtonFileDrop {
  dropProps: {
    onDragEnter: (e: DragEvent) => void;
    onDragOver: (e: DragEvent) => void;
    onDragLeave: (e: DragEvent) => void;
    onDrop: (e: DragEvent) => void;
  };
  isOver: boolean;
}

/** True when the drag carries files (vs. text, an element, etc.). */
function dragHasFiles(e: DragEvent): boolean {
  return Array.from(e.dataTransfer?.types ?? []).includes('Files');
}

export function useButtonFileDrop({ onFile, disabled = false }: UseButtonFileDropOptions): ButtonFileDrop {
  const [isOver, setIsOver] = useState(false);

  const onDragEnter = useCallback((e: DragEvent) => {
    if (disabled || !dragHasFiles(e)) return;
    e.preventDefault();
    setIsOver(true);
  }, [disabled]);

  const onDragOver = useCallback((e: DragEvent) => {
    if (disabled || !dragHasFiles(e)) return;
    e.preventDefault(); // required so the element becomes a valid drop target
    if (e.dataTransfer) e.dataTransfer.dropEffect = 'copy';
    setIsOver(true);
  }, [disabled]);

  const onDragLeave = useCallback((e: DragEvent) => {
    if (!dragHasFiles(e)) return;
    // dragleave also fires when crossing between child nodes (icon/text); only
    // clear when the pointer actually leaves the button.
    if (e.currentTarget.contains(e.relatedTarget as Node | null)) return;
    setIsOver(false);
  }, []);

  const onDrop = useCallback((e: DragEvent) => {
    if (!dragHasFiles(e)) return;
    e.preventDefault(); // stop the browser from navigating to the dropped file
    setIsOver(false);
    if (disabled) return;
    const file = e.dataTransfer.files?.[0];
    if (file) onFile(file);
  }, [disabled, onFile]);

  return { dropProps: { onDragEnter, onDragOver, onDragLeave, onDrop }, isOver };
}
