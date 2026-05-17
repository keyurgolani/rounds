/**
 * SSE client for the SD practice chat endpoint. Parses streamed
 * events into a typed callback shape so the chat UI doesn't have to
 * know about raw SSE.
 */
import { runnerFetch } from '../../lib/runnerFetch';
import type { CanvasElementSummary } from './canvasTools';

export type SDChatStreamEvent =
  | { type: 'text_delta'; text: string }
  | { type: 'tool_use_start'; id: string; name: string }
  | { type: 'tool_use_delta'; id: string; partial_json: string }
  | { type: 'tool_use_stop'; id: string }
  | { type: 'done' }
  | { type: 'end' }
  | { type: 'error'; message: string; error_kind?: string; request_id?: string };

export type SDChatMessage = {
  role: 'user' | 'assistant';
  content:
    | string
    | Array<
        | { type: 'text'; text: string }
        | { type: 'tool_use'; id: string; name: string; input: unknown }
        | { type: 'tool_result'; tool_use_id: string; content: string; is_error?: boolean }
      >;
};

export type SDChatRequest = {
  question_slug: string;
  question_prompt?: string;
  canvas_elements: Array<{
    id: string;
    kind: 'component' | 'connection' | 'note';
    label?: string;
    component_kind?: string;
    from_id?: string;
    to_id?: string;
    position?: { x: number; y: number };
  }>;
  messages: SDChatMessage[];
  provider_id?: string;
  model?: string;
};

export function canvasElementsToWire(els: CanvasElementSummary[]): SDChatRequest['canvas_elements'] {
  return els.map((el) => {
    if (el.kind === 'component') {
      return {
        id: el.id,
        kind: 'component',
        label: el.label,
        component_kind: el.componentKind,
        position: el.position,
      };
    }
    if (el.kind === 'connection') {
      return {
        id: el.id,
        kind: 'connection',
        label: el.label,
        from_id: el.fromId,
        to_id: el.toId,
      };
    }
    return {
      id: el.id,
      kind: 'note',
      label: el.label,
      position: el.position,
    };
  });
}

/**
 * Stream a chat completion. Calls `onEvent` for every parsed SSE event.
 * Resolves when the server emits `end` or an `error` event.
 */
export async function streamSDChat(
  body: SDChatRequest,
  onEvent: (e: SDChatStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await runnerFetch('/api/sd-practice/chat', {
    method: 'POST',
    body,
    signal,
    errorPrefix: 'SD practice chat',
  });
  if (!res.body) throw new Error('SD practice chat: empty response body');
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let nlIdx;
    while ((nlIdx = buffer.indexOf('\n\n')) !== -1) {
      const line = buffer.slice(0, nlIdx).trim();
      buffer = buffer.slice(nlIdx + 2);
      if (!line.startsWith('data:')) continue;
      const payload = line.slice(5).trim();
      if (!payload) continue;
      try {
        const evt = JSON.parse(payload) as SDChatStreamEvent;
        onEvent(evt);
        if (evt.type === 'end' || evt.type === 'error') return;
      } catch {
        // ignore malformed lines
      }
    }
  }
}
