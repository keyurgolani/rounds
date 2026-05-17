/**
 * Canvas-driver interface + tool-call types shared by the Excalidraw
 * and tldraw prototype implementations. The backend (Anthropic) emits
 * tool_use events with these names; each driver implements them
 * against its native scene API.
 */

export type ComponentKind =
  | 'service'
  | 'db'
  | 'queue'
  | 'cache'
  | 'cdn'
  | 'client'
  | 'lb'
  | 'external';

export type CanvasElementSummary =
  | {
      id: string;
      kind: 'component';
      label: string;
      componentKind: ComponentKind;
      position?: { x: number; y: number };
    }
  | {
      id: string;
      kind: 'connection';
      label?: string;
      fromId: string;
      toId: string;
    }
  | {
      id: string;
      kind: 'note';
      label: string;
      position?: { x: number; y: number };
    };

/** A discriminated union of every tool call the AI can issue. */
export type CanvasToolCall =
  | {
      name: 'add_component';
      input: { label: string; kind: ComponentKind; position?: { x: number; y: number } };
    }
  | {
      name: 'add_connection';
      input: { from_id: string; to_id: string; label?: string; direction?: 'one-way' | 'two-way' };
    }
  | {
      name: 'update_component';
      input: { id: string; label?: string; kind?: ComponentKind };
    }
  | {
      name: 'delete_element';
      input: { id: string };
    }
  | {
      name: 'add_note';
      input: { text: string; position: { x: number; y: number } };
    }
  | {
      name: 'read_canvas';
      input: Record<string, never>;
    };

/**
 * What a canvas driver must implement. Both Excalidraw and tldraw
 * drivers conform to this shape; the chat panel speaks only to the
 * interface, not to either underlying library.
 */
export interface CanvasDriver {
  /** Read the current scene as a structured list. */
  readCanvas(): CanvasElementSummary[];
  /** Apply a tool call. Returns the structured tool_result the chat
   * layer should send back to the AI on the next turn. */
  applyTool(call: CanvasToolCall): { ok: true; result: unknown } | { ok: false; error: string };
}

/** A label palette per component kind. Drivers use this for coloring
 * so the Excalidraw and tldraw prototypes look comparable. */
export const COMPONENT_PALETTE: Record<
  ComponentKind,
  { bg: string; stroke: string; label: string }
> = {
  service: { bg: '#e8f1ff', stroke: '#2563eb', label: 'Service' },
  db: { bg: '#fef3c7', stroke: '#d97706', label: 'Database' },
  queue: { bg: '#ede9fe', stroke: '#7c3aed', label: 'Queue' },
  cache: { bg: '#fee2e2', stroke: '#dc2626', label: 'Cache' },
  cdn: { bg: '#dcfce7', stroke: '#16a34a', label: 'CDN / Edge' },
  client: { bg: '#f1f5f9', stroke: '#475569', label: 'Client' },
  lb: { bg: '#fce7f3', stroke: '#db2777', label: 'Load Balancer' },
  external: { bg: '#f5f5f4', stroke: '#78716c', label: 'External' },
};
