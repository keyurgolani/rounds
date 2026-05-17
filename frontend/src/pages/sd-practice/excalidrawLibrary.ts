/**
 * Pre-installed Excalidraw library for system-design practice.
 *
 * Each ComponentKind in our palette gets a library item — a small
 * pre-sized + pre-coloured rectangle the candidate can drag onto
 * the canvas from the Library sidebar. Matches what the AI's
 * `add_component` tool would produce.
 */
import { convertToExcalidrawElements } from '@excalidraw/excalidraw';
import type { LibraryItem } from '@excalidraw/excalidraw/types';
import { COMPONENT_PALETTE, type ComponentKind } from './canvasTools';

const ITEM_W = 180;
const ITEM_H = 70;

const KINDS_IN_ORDER: ComponentKind[] = [
  'client',
  'lb',
  'cdn',
  'service',
  'cache',
  'queue',
  'db',
  'external',
];

/**
 * Build the library items synchronously. Excalidraw accepts
 * `initialData.libraryItems` as a `LibraryItems | Promise<LibraryItems>`,
 * so we hand it back the resolved array.
 */
export function buildSystemDesignLibrary(): LibraryItem[] {
  const now = Date.now();
  return KINDS_IN_ORDER.map((kind, idx) => {
    const palette = COMPONENT_PALETTE[kind];
    const elements = convertToExcalidrawElements([
      {
        type: 'rectangle',
        x: 0,
        y: 0,
        width: ITEM_W,
        height: ITEM_H,
        backgroundColor: palette.bg,
        strokeColor: palette.stroke,
        strokeWidth: 2,
        fillStyle: 'solid',
        roundness: { type: 3 },
        label: {
          text: palette.label,
          fontSize: 16,
        },
      },
    ]);
    return {
      id: `sd-${kind}`,
      status: 'published' as const,
      name: palette.label,
      created: now + idx,
      elements,
    } as LibraryItem;
  });
}
