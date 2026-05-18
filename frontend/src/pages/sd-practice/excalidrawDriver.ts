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

const COMPONENT_W = 200;
const COMPONENT_H = 84;
// Wide enough that arrows routed between adjacent boxes don't run
// through unrelated components, and the box labels have breathing room.
// (Earlier 60px gutter caused visible overlap; user feedback.)
const GUTTER_X = 160;
const GUTTER_Y = 110;
const GRID_COLS = 3;
const NOTE_W = 220;
const NOTE_H = 60;

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

/** Auto-layout: place a new component on a 3-column grid with a
 *  generous gutter so connecting arrows don't cross unrelated boxes.
 *  Counter advances per call (not per current size) so deletions
 *  don't cause later inserts to land on top of survivors. */
function autoPosition(state: DriverState): { x: number; y: number } {
  const n = state.counters.component;
  const col = n % GRID_COLS;
  const row = Math.floor(n / GRID_COLS);
  return {
    x: 80 + col * (COMPONENT_W + GUTTER_X),
    y: 80 + row * (COMPONENT_H + GUTTER_Y),
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
    // Connections (arrows with bindings). We supply an explicit
    // `points` polyline from box-centre to box-centre — without it
    // Excalidraw renders a zero-length stub at the start until the
    // first scene mutation triggers a rebinding pass, which is why
    // users saw arrows "appear" only after dragging a box. The
    // start/end bindings still clip the visible endpoints to the
    // rectangle edges, so the arrows look like clean side-to-side
    // links despite the polyline going centre-to-centre.
    const connections: ExcalidrawElementSkeleton[] = [];
    for (const [id, conn] of state.connections.entries()) {
      const from = state.components.get(conn.fromId);
      const to = state.components.get(conn.toId);
      if (!from || !to) continue;
      const fromCx = from.x + COMPONENT_W / 2;
      const fromCy = from.y + COMPONENT_H / 2;
      const toCx = to.x + COMPONENT_W / 2;
      const toCy = to.y + COMPONENT_H / 2;
      connections.push({
        id,
        type: 'arrow',
        x: fromCx,
        y: fromCy,
        points: [
          [0, 0],
          [toCx - fromCx, toCy - fromCy],
        ],
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
      if (call.name === 'draw_diagram') {
        const { components, connections = [], notes = [] } = call.input;
        // Map the AI-chosen ids (e.g. "lb", "gateway") to the
        // driver-issued ids that connections will bind to. Existing
        // canvas ids pass through so the AI can also draw additions
        // that link into prior turns.
        const idMap = new Map<string, string>();
        for (const c of components) {
          const id = `comp-${++state.counters.component}`;
          idMap.set(c.id, id);
          state.components.set(id, {
            kind: c.kind,
            label: c.label,
            x: c.position.x,
            y: c.position.y,
          });
        }
        const addedConnections: Array<{ id: string; from: string; to: string }> = [];
        for (const conn of connections) {
          const fromId = idMap.get(conn.from_id) ?? conn.from_id;
          const toId = idMap.get(conn.to_id) ?? conn.to_id;
          if (!state.components.has(fromId) || !state.components.has(toId)) {
            // Skip connections that reference unknown ids. The AI can
            // read the result and retry with the correct binding.
            continue;
          }
          const id = `conn-${++state.counters.connection}`;
          state.connections.set(id, { fromId, toId, label: conn.label });
          addedConnections.push({ id, from: fromId, to: toId });
        }
        const addedNotes: string[] = [];
        for (const n of notes) {
          const id = `note-${++state.counters.note}`;
          state.notes.set(id, { text: n.text, x: n.position.x, y: n.position.y });
          addedNotes.push(id);
        }
        rebuildScene();
        return {
          ok: true,
          result: {
            components: Array.from(idMap.entries()).map(([aiId, id]) => ({
              ai_id: aiId,
              id,
            })),
            connections: addedConnections,
            notes: addedNotes,
          },
        };
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
