import { useCallback, useRef, useState } from 'react';
import { ChevronRight, Sparkles } from 'lucide-react';
import ChatPanel, {
  type ChatMessage,
  type ChatSendArgs,
} from '../../components/chat/ChatPanel';
import {
  canvasElementsToWire,
  streamSDChat,
  type SDChatMessage,
} from './sdPracticeApi';
import type { CanvasDriver, CanvasToolCall } from './canvasTools';

/** Extras attached to assistant turns in the SD chat — one entry per
 *  tool the AI invoked during that turn. The chip beneath the bubble
 *  surfaces success/failure to the candidate. */
type SDToolCall = {
  id: string;
  name: string;
  parsed?: CanvasToolCall;
  result?: { ok: true; value: unknown } | { ok: false; error: string };
};

type SDExtras = { toolCalls: SDToolCall[] };

type Props = {
  questionSlug: string;
  questionPrompt: string;
  driver: CanvasDriver | null;
};

/**
 * AI sparring partner for system-design practice. Streams text +
 * tool_use blocks; tool calls mutate the Excalidraw canvas via the
 * supplied driver. Tool-call chips render as per-message extras below
 * each assistant bubble.
 *
 * All chat shell concerns — composer, scrolling, model picker, Stop
 * button, Markdown rendering, bubble width tiering — live in the
 * shared ChatPanel.
 */
export default function SDPracticeChatPanel({
  questionSlug,
  questionPrompt,
  driver,
}: Props) {
  // In-flight tool-call buffers, kept OUTSIDE React state so the canvas
  // mutation can run exactly once. React 18 StrictMode invokes
  // setState updater functions twice in dev — anything inside one runs
  // twice. (See dedupe note in handleStreamEvent below.)
  const toolBufferRef = useRef<
    Map<string, { name: string; partialJson: string }>
  >(new Map());

  const handleSend = useCallback(
    async (args: ChatSendArgs<SDExtras>) => {
      if (!driver) return;
      const { text, history, override, signal, callbacks } = args;

      // Build the Anthropic-shaped wire history from prior messages.
      // `history` includes the just-appended user turn AND the empty
      // streaming placeholder. We slice off the placeholder, then add
      // the new user text explicitly so the wire ordering is obvious.
      const priorTurns = history.slice(0, -2);
      const backendMessages = priorTurnsToWire(priorTurns);
      backendMessages.push({ role: 'user', content: text });

      const canvasState = driver.readCanvas();
      try {
        await streamSDChat(
          {
            question_slug: questionSlug,
            question_prompt: questionPrompt,
            canvas_elements: canvasElementsToWire(canvasState),
            messages: backendMessages,
            provider_id: override?.provider_id,
            model: override?.model,
          },
          (evt) => {
            if (evt.type === 'text_delta') {
              callbacks.appendText(evt.text);
              return;
            }
            if (evt.type === 'tool_use_start') {
              toolBufferRef.current.set(evt.id, {
                name: evt.name,
                partialJson: '',
              });
              callbacks.setExtras((prev) => ({
                toolCalls: [
                  ...(prev?.toolCalls ?? []),
                  { id: evt.id, name: evt.name },
                ],
              }));
              return;
            }
            if (evt.type === 'tool_use_delta') {
              const buf = toolBufferRef.current.get(evt.id);
              if (buf) buf.partialJson += evt.partial_json;
              return;
            }
            if (evt.type === 'tool_use_stop') {
              // Side effect — apply against the canvas exactly once.
              const buf = toolBufferRef.current.get(evt.id);
              toolBufferRef.current.delete(evt.id);
              let parsed: CanvasToolCall | undefined;
              let resolved:
                | { ok: true; value: unknown }
                | { ok: false; error: string };
              if (!buf) {
                resolved = { ok: false, error: 'Missing tool call buffer.' };
              } else {
                try {
                  const input = buf.partialJson
                    ? (JSON.parse(buf.partialJson) as unknown)
                    : {};
                  parsed = { name: buf.name, input } as CanvasToolCall;
                } catch {
                  resolved = {
                    ok: false,
                    error: 'AI emitted malformed tool input JSON.',
                  };
                }
                if (parsed) {
                  const out = driver.applyTool(parsed);
                  resolved = out.ok
                    ? { ok: true, value: out.result }
                    : { ok: false, error: out.error };
                }
              }
              callbacks.setExtras((prev) => ({
                toolCalls: (prev?.toolCalls ?? []).map((tc) =>
                  tc.id === evt.id ? { ...tc, parsed, result: resolved } : tc,
                ),
              }));
              return;
            }
            if (evt.type === 'error') {
              callbacks.error(evt.message);
            }
          },
          signal,
        );
      } catch (err) {
        if ((err as { name?: string }).name === 'AbortError') return;
        throw err;
      }
    },
    [driver, questionSlug, questionPrompt],
  );

  return (
    <ChatPanel<SDExtras>
      onSend={handleSend}
      composerPlaceholder={
        driver ? 'Ask the AI…' : 'Canvas loading…'
      }
      disabled={!driver}
      emptyState={<SDEmpty />}
      renderExtras={(msg) =>
        msg.role === 'assistant' && msg.extras?.toolCalls?.length
          ? <ToolCallList calls={msg.extras.toolCalls} />
          : null
      }
      rootStyle={{
        background: 'var(--bg-elev)',
        borderLeft: '1px solid var(--border)',
      }}
    />
  );
}

/** Pack the prior conversation back into the Anthropic-shaped wire
 *  protocol the SD chat backend expects. */
function priorTurnsToWire(
  prior: ChatMessage<SDExtras>[],
): SDChatMessage[] {
  const out: SDChatMessage[] = [];
  for (const m of prior) {
    if (m.role === 'user') {
      if (!m.content) continue;
      out.push({ role: 'user', content: m.content });
      continue;
    }
    // assistant: text + tool_use blocks
    const blocks: Array<
      | { type: 'text'; text: string }
      | { type: 'tool_use'; id: string; name: string; input: unknown }
    > = [];
    if (m.content) blocks.push({ type: 'text', text: m.content });
    const toolCalls = m.extras?.toolCalls ?? [];
    for (const tc of toolCalls) {
      if (!tc.parsed) continue;
      blocks.push({
        type: 'tool_use',
        id: tc.id,
        name: tc.name,
        input: tc.parsed.input,
      });
    }
    if (blocks.length) out.push({ role: 'assistant', content: blocks });
    // Tool results — sent as a user turn with structured content.
    const results = toolCalls
      .filter((tc) => tc.parsed && tc.result)
      .map((tc) => ({
        type: 'tool_result' as const,
        tool_use_id: tc.id,
        content:
          tc.result && tc.result.ok
            ? JSON.stringify(tc.result.value)
            : tc.result && !tc.result.ok
              ? tc.result.error
              : '',
        is_error: tc.result && !tc.result.ok ? true : undefined,
      }));
    if (results.length) out.push({ role: 'user', content: results });
  }
  return out;
}

function SDEmpty() {
  return (
    <div
      style={{
        margin: 'auto 0',
        padding: 14,
        background: 'var(--bg-sunken)',
        borderRadius: 'var(--radius)',
        fontSize: 12.5,
        color: 'var(--text-3)',
        lineHeight: 1.55,
      }}
    >
      <div
        className="eyebrow"
        style={{
          marginBottom: 6,
          color: 'var(--accent)',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
        }}
      >
        <Sparkles size={11} strokeWidth={2} /> SPARRING PARTNER
      </div>
      <div>
        Ask the AI to spar on this design. It draws on the canvas but
        asks before mutating and challenges your assumptions.
      </div>
      <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>
        <li>"Start me off — what should I clarify first?"</li>
        <li>"Add an API gateway in front of the service."</li>
        <li>"What's the failure mode here at p99?"</li>
      </ul>
    </div>
  );
}

function ToolCallList({ calls }: { calls: SDToolCall[] }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {calls.map((tc) => (
        <ToolCallChip key={tc.id} call={tc} />
      ))}
    </div>
  );
}

function ToolCallChip({ call }: { call: SDToolCall }) {
  const [expanded, setExpanded] = useState(false);
  const status: 'pending' | 'ok' | 'error' = !call.result
    ? 'pending'
    : call.result.ok
      ? 'ok'
      : 'error';
  const color =
    status === 'error'
      ? 'var(--plum)'
      : status === 'ok'
        ? 'var(--forest)'
        : 'var(--text-3)';
  const glyph = status === 'pending' ? '…' : status === 'ok' ? '✓' : '✗';
  const summary = call.parsed
    ? summariseToolCall(call.name, call.parsed.input)
    : { verb: prettyToolName(call.name), detail: null as string | null };
  // Pending tool calls have no parsed input yet — not interactive.
  const canExpand = !!call.parsed;

  return (
    <div
      style={{
        background: 'var(--bg-sunken)',
        border: '1px solid var(--border)',
        borderRadius: 4,
        fontSize: 11.5,
        color,
        lineHeight: 1.5,
        overflow: 'hidden',
      }}
    >
      <button
        type="button"
        onClick={canExpand ? () => setExpanded((v) => !v) : undefined}
        disabled={!canExpand}
        aria-expanded={canExpand ? expanded : undefined}
        style={{
          width: '100%',
          padding: '4px 8px',
          background: 'transparent',
          border: 0,
          color: 'inherit',
          font: 'inherit',
          textAlign: 'left',
          cursor: canExpand ? 'pointer' : 'default',
          display: 'flex',
          alignItems: 'baseline',
          gap: 6,
        }}
      >
        {canExpand ? (
          <span
            aria-hidden="true"
            style={{
              width: 12,
              flexShrink: 0,
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
              transition: 'transform 120ms',
              color: 'var(--text-4)',
            }}
          >
            <ChevronRight size={11} strokeWidth={2.2} />
          </span>
        ) : (
          <span style={{ width: 12, flexShrink: 0 }} />
        )}
        <span
          aria-hidden="true"
          className="mono"
          style={{ fontWeight: 600, width: 12, flexShrink: 0 }}
        >
          {glyph}
        </span>
        <span style={{ fontWeight: 500 }}>{summary.verb}</span>
        {summary.detail && (
          <span style={{ color: 'var(--text-3)', flex: 1, minWidth: 0 }}>
            {summary.detail}
          </span>
        )}
        {status === 'error' && (
          <span style={{ color: 'var(--plum)', flex: 1, minWidth: 0 }}>
            — {(call.result as { ok: false; error: string }).error}
          </span>
        )}
      </button>
      {canExpand && expanded && call.parsed && (
        <ToolCallDetails name={call.name} input={call.parsed.input} />
      )}
    </div>
  );
}

/** Expanded panel: a structured breakdown of the tool's input so the
 *  user can audit exactly what the AI drew without scanning raw JSON. */
function ToolCallDetails({
  name,
  input,
}: {
  name: string;
  input: unknown;
}) {
  return (
    <div
      style={{
        padding: '8px 10px 10px 30px',
        borderTop: '1px solid var(--border)',
        background: 'var(--bg)',
        fontSize: 11.5,
        color: 'var(--text-2)',
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      {renderToolDetail(name, input)}
    </div>
  );
}

function renderToolDetail(name: string, input: unknown): React.ReactNode {
  if (!input || typeof input !== 'object') {
    return <em style={{ color: 'var(--text-4)' }}>No input.</em>;
  }
  const obj = input as Record<string, unknown>;

  if (name === 'draw_diagram') {
    const components = Array.isArray(obj.components)
      ? (obj.components as Array<Record<string, unknown>>)
      : [];
    const connections = Array.isArray(obj.connections)
      ? (obj.connections as Array<Record<string, unknown>>)
      : [];
    const notes = Array.isArray(obj.notes)
      ? (obj.notes as Array<Record<string, unknown>>)
      : [];
    return (
      <>
        {components.length > 0 && (
          <DetailSection title={`Components (${components.length})`}>
            {components.map((c, i) => (
              <DetailRow
                key={`comp-${i}`}
                label={String(c.label ?? `#${i + 1}`)}
                meta={[
                  c.kind ? `kind: ${String(c.kind)}` : null,
                  c.id ? `id: ${String(c.id)}` : null,
                  positionLabel(c.position),
                ]}
              />
            ))}
          </DetailSection>
        )}
        {connections.length > 0 && (
          <DetailSection title={`Connections (${connections.length})`}>
            {connections.map((c, i) => (
              <DetailRow
                key={`conn-${i}`}
                label={`${String(c.from_id ?? '?')} → ${String(c.to_id ?? '?')}`}
                meta={[c.label ? `“${String(c.label)}”` : null]}
              />
            ))}
          </DetailSection>
        )}
        {notes.length > 0 && (
          <DetailSection title={`Notes (${notes.length})`}>
            {notes.map((n, i) => (
              <DetailRow
                key={`note-${i}`}
                label={String(n.text ?? `Note #${i + 1}`)}
                meta={[positionLabel(n.position)]}
              />
            ))}
          </DetailSection>
        )}
      </>
    );
  }

  if (name === 'add_component') {
    return (
      <DetailSection title="Component">
        <DetailRow
          label={String(obj.label ?? '(unnamed)')}
          meta={[
            obj.kind ? `kind: ${String(obj.kind)}` : null,
            positionLabel(obj.position),
          ]}
        />
      </DetailSection>
    );
  }

  if (name === 'add_connection') {
    return (
      <DetailSection title="Connection">
        <DetailRow
          label={`${String(obj.from_id ?? '?')} → ${String(obj.to_id ?? '?')}`}
          meta={[
            obj.label ? `label: “${String(obj.label)}”` : null,
            obj.direction ? `direction: ${String(obj.direction)}` : null,
          ]}
        />
      </DetailSection>
    );
  }

  if (name === 'update_component') {
    return (
      <DetailSection title="Update">
        <DetailRow
          label={String(obj.id ?? '(no id)')}
          meta={[
            obj.label ? `label: “${String(obj.label)}”` : null,
            obj.kind ? `kind: ${String(obj.kind)}` : null,
          ]}
        />
      </DetailSection>
    );
  }

  if (name === 'delete_element') {
    return (
      <DetailSection title="Delete">
        <DetailRow label={String(obj.id ?? '(no id)')} meta={[]} />
      </DetailSection>
    );
  }

  if (name === 'add_note') {
    return (
      <DetailSection title="Note">
        <DetailRow
          label={String(obj.text ?? '')}
          meta={[positionLabel(obj.position)]}
        />
      </DetailSection>
    );
  }

  if (name === 'read_canvas') {
    return (
      <em style={{ color: 'var(--text-4)' }}>
        No input. (See assistant message for the AI&rsquo;s read-out.)
      </em>
    );
  }

  // Unknown tool — fall through to a labelled key/value list, avoiding
  // a raw JSON dump.
  return (
    <DetailSection title="Input">
      {Object.entries(obj).map(([k, v]) => (
        <DetailRow
          key={k}
          label={k}
          meta={[typeof v === 'string' ? v : JSON.stringify(v)]}
        />
      ))}
    </DetailSection>
  );
}

function DetailSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div
        className="eyebrow"
        style={{
          fontSize: 9.5,
          letterSpacing: '0.08em',
          color: 'var(--text-4)',
          marginBottom: 4,
        }}
      >
        {title}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {children}
      </div>
    </div>
  );
}

function DetailRow({
  label,
  meta,
}: {
  label: string;
  meta: Array<string | null>;
}) {
  const visibleMeta = meta.filter((m): m is string => !!m);
  return (
    <div
      style={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'baseline',
        gap: 6,
        minWidth: 0,
      }}
    >
      <span style={{ color: 'var(--text)', fontWeight: 500 }}>{label}</span>
      {visibleMeta.length > 0 && (
        <span
          className="mono"
          style={{ color: 'var(--text-4)', fontSize: 10.5 }}
        >
          {visibleMeta.join(' · ')}
        </span>
      )}
    </div>
  );
}

function positionLabel(pos: unknown): string | null {
  if (!pos || typeof pos !== 'object') return null;
  const p = pos as Record<string, unknown>;
  if (typeof p.x !== 'number' || typeof p.y !== 'number') return null;
  return `(${Math.round(p.x)}, ${Math.round(p.y)})`;
}

function prettyToolName(name: string): string {
  switch (name) {
    case 'add_component':
      return 'Added component';
    case 'add_connection':
      return 'Linked';
    case 'update_component':
      return 'Updated component';
    case 'delete_element':
      return 'Deleted element';
    case 'add_note':
      return 'Added note';
    case 'draw_diagram':
      return 'Drew diagram';
    case 'read_canvas':
      return 'Read canvas';
    default:
      return name;
  }
}

/** Produce a human-friendly verb + detail pair from a tool call's
 *  input. Distinct from raw JSON dumps — keeps the chat clean even
 *  when the AI emits a batch draw_diagram with dozens of items. */
function summariseToolCall(
  name: string,
  input: unknown,
): { verb: string; detail: string | null } {
  const verb = prettyToolName(name);
  if (!input || typeof input !== 'object') return { verb, detail: null };
  const obj = input as Record<string, unknown>;

  if (name === 'draw_diagram') {
    const components = Array.isArray(obj.components)
      ? (obj.components as Array<{ label?: string }>)
      : [];
    const connections = Array.isArray(obj.connections)
      ? (obj.connections as unknown[])
      : [];
    const notes = Array.isArray(obj.notes) ? (obj.notes as unknown[]) : [];
    const parts: string[] = [];
    parts.push(plural(components.length, 'component', 'components'));
    if (connections.length) {
      parts.push(plural(connections.length, 'connection', 'connections'));
    }
    if (notes.length) {
      parts.push(plural(notes.length, 'note', 'notes'));
    }
    return { verb, detail: parts.join(' · ') };
  }

  if (name === 'add_component') {
    const label = typeof obj.label === 'string' ? obj.label : '';
    const kind = typeof obj.kind === 'string' ? obj.kind : '';
    const detail = label
      ? kind
        ? `${label} (${kind})`
        : label
      : kind || null;
    return { verb, detail };
  }

  if (name === 'add_connection') {
    const from = typeof obj.from_id === 'string' ? obj.from_id : '';
    const to = typeof obj.to_id === 'string' ? obj.to_id : '';
    const label = typeof obj.label === 'string' ? obj.label : '';
    if (from && to) {
      return {
        verb,
        detail: label ? `${from} → ${to} (${label})` : `${from} → ${to}`,
      };
    }
    return { verb, detail: null };
  }

  if (name === 'update_component') {
    const id = typeof obj.id === 'string' ? obj.id : '';
    const label = typeof obj.label === 'string' ? obj.label : '';
    return {
      verb,
      detail: id ? (label ? `${id} → "${label}"` : id) : null,
    };
  }

  if (name === 'delete_element') {
    const id = typeof obj.id === 'string' ? obj.id : '';
    return { verb, detail: id || null };
  }

  if (name === 'add_note') {
    const text = typeof obj.text === 'string' ? obj.text : '';
    const trimmed = text.length > 60 ? text.slice(0, 57) + '…' : text;
    return { verb, detail: trimmed || null };
  }

  if (name === 'read_canvas') {
    return { verb, detail: null };
  }

  // Unknown tool — fall back to first string-valued key, never dump JSON.
  for (const [k, v] of Object.entries(obj)) {
    if (typeof v === 'string') return { verb, detail: `${k}: ${v}` };
  }
  return { verb, detail: null };
}

function plural(n: number, one: string, many: string): string {
  return `${n} ${n === 1 ? one : many}`;
}
