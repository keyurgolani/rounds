import type {
  ExcalidrawElement,
  ExcalidrawArrowElement,
  ExcalidrawTextElement,
} from '@excalidraw/excalidraw/element/types';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';
import type { ExcalidrawElementSkeleton } from '@excalidraw/excalidraw/data/transform';
import { convertToExcalidrawElements } from '@excalidraw/excalidraw';
import {
  COMPONENT_PALETTE,
  type CanvasDriver,
  type CanvasElementSummary,
  type CanvasToolCall,
  type ComponentKind,
} from './canvasTools';

const COMPONENT_W = 180;
const COMPONENT_H = 70;
const GUTTER = 60;
const NOTE_W = 200;
const NOTE_H = 56;

type DriverState = {
  components: Map<string, { kind: ComponentKind; label: string; x: number; y: number }>;
  connections: Map<string, { fromId: string; toId: string; label?: string }>;
  notes: Map<string, { text: string; x: number; y: number }>;
  // Maps stable driver-issued IDs to the actual Excalidraw element IDs
  // that updateScene cares about. We control both, so they're 1:1.
  counters: { component: number; connection: number; note: number };
};

function emptyState(): DriverState {
  return {
    components: new Map(),
    connections: new Map(),
    notes: new Map(),
    counters: { component: 0, connection: 0, note: 0 },
  };
}

/** Auto-layout: place a new component on a 4-col grid using the
 *  current component count. */
function autoPosition(state: DriverState): { x: number; y: number } {
  const n = state.components.size;
  const col = n % 4;
  const row = Math.floor(n / 4);
  return {
    x: 80 + col * (COMPONENT_W + GUTTER),
    y: 80 + row * (COMPONENT_H + GUTTER),
  };
}

export function createExcalidrawDriver(api: ExcalidrawImperativeAPI): CanvasDriver {
  const state = emptyState();

  function rebuildScene(): void {
    // Components first (so arrows can bind to their IDs).
    const components: ExcalidrawElementSkeleton[] = [];
    for (const [id, c] of state.components.entries()) {
      const palette = COMPONENT_PALETTE[c.kind];
      components.push({
        id,
        type: 'rectangle',
        x: c.x,
        y: c.y,
        width: COMPONENT_W,
        height: COMPONENT_H,
        backgroundColor: palette.bg,
        strokeColor: palette.stroke,
        strokeWidth: 2,
        fillStyle: 'solid',
        roundness: { type: 3 },
        label: {
          text: `${c.label}\n${palette.label}`,
          fontSize: 16,
        },
      });
    }
    // Connections (arrows with bindings).
    const connections: ExcalidrawElementSkeleton[] = [];
    for (const [id, conn] of state.connections.entries()) {
      const from = state.components.get(conn.fromId);
      const to = state.components.get(conn.toId);
      if (!from || !to) continue;
      connections.push({
        id,
        type: 'arrow',
        x: from.x + COMPONENT_W / 2,
        y: from.y + COMPONENT_H / 2,
        start: { id: conn.fromId, type: 'rectangle' },
        end: { id: conn.toId, type: 'rectangle' },
        strokeColor: '#475569',
        strokeWidth: 2,
        ...(conn.label
          ? { label: { text: conn.label, fontSize: 14 } }
          : {}),
      });
    }
    // Notes (free-floating text).
    const notes: ExcalidrawElementSkeleton[] = [];
    for (const [id, n] of state.notes.entries()) {
      notes.push({
        id,
        type: 'text',
        x: n.x,
        y: n.y,
        text: n.text,
        fontSize: 14,
        strokeColor: '#7c3aed',
      });
    }
    const elements = convertToExcalidrawElements([
      ...components,
      ...connections,
      ...notes,
    ]) as ExcalidrawElement[];
    api.updateScene({ elements });
  }

  return {
    readCanvas(): CanvasElementSummary[] {
      const out: CanvasElementSummary[] = [];
      for (const [id, c] of state.components.entries()) {
        out.push({
          id,
          kind: 'component',
          label: c.label,
          componentKind: c.kind,
          position: { x: c.x, y: c.y },
        });
      }
      for (const [id, conn] of state.connections.entries()) {
        out.push({
          id,
          kind: 'connection',
          label: conn.label,
          fromId: conn.fromId,
          toId: conn.toId,
        });
      }
      for (const [id, n] of state.notes.entries()) {
        out.push({
          id,
          kind: 'note',
          label: n.text,
          position: { x: n.x, y: n.y },
        });
      }
      return out;
    },

    applyTool(call: CanvasToolCall): { ok: true; result: unknown } | { ok: false; error: string } {
      if (call.name === 'add_component') {
        const pos = call.input.position ?? autoPosition(state);
        const id = `comp-${++state.counters.component}`;
        state.components.set(id, {
          kind: call.input.kind,
          label: call.input.label,
          x: pos.x,
          y: pos.y,
        });
        rebuildScene();
        return { ok: true, result: { id, kind: 'component', label: call.input.label } };
      }
      if (call.name === 'add_connection') {
        const { from_id, to_id } = call.input;
        if (!state.components.has(from_id)) {
          return { ok: false, error: `Unknown from_id: ${from_id}` };
        }
        if (!state.components.has(to_id)) {
          return { ok: false, error: `Unknown to_id: ${to_id}` };
        }
        const id = `conn-${++state.counters.connection}`;
        state.connections.set(id, {
          fromId: from_id,
          toId: to_id,
          label: call.input.label,
        });
        rebuildScene();
        return { ok: true, result: { id, from_id, to_id } };
      }
      if (call.name === 'update_component') {
        const c = state.components.get(call.input.id);
        if (!c) return { ok: false, error: `Unknown component id: ${call.input.id}` };
        if (call.input.label !== undefined) c.label = call.input.label;
        if (call.input.kind !== undefined) c.kind = call.input.kind;
        rebuildScene();
        return { ok: true, result: { id: call.input.id } };
      }
      if (call.name === 'delete_element') {
        const id = call.input.id;
        if (state.components.delete(id)) {
          // Also drop any connections referencing this component.
          for (const [cid, conn] of state.connections.entries()) {
            if (conn.fromId === id || conn.toId === id) {
              state.connections.delete(cid);
            }
          }
          rebuildScene();
          return { ok: true, result: { id, kind: 'component' } };
        }
        if (state.connections.delete(id)) {
          rebuildScene();
          return { ok: true, result: { id, kind: 'connection' } };
        }
        if (state.notes.delete(id)) {
          rebuildScene();
          return { ok: true, result: { id, kind: 'note' } };
        }
        return { ok: false, error: `Unknown id: ${id}` };
      }
      if (call.name === 'add_note') {
        const id = `note-${++state.counters.note}`;
        state.notes.set(id, {
          text: call.input.text,
          x: call.input.position.x,
          y: call.input.position.y,
        });
        rebuildScene();
        return { ok: true, result: { id } };
      }
      if (call.name === 'read_canvas') {
        return { ok: true, result: { elements: this.readCanvas() } };
      }
      return { ok: false, error: `Unknown tool: ${(call as { name: string }).name}` };
    },
  };
}

// Re-export so consumers don't have to import from internal types.
export type { ExcalidrawImperativeAPI, ExcalidrawArrowElement, ExcalidrawTextElement };
