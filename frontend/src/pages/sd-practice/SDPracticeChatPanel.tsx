import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Send, Sparkles, AlertTriangle, X } from 'lucide-react';
import {
  canvasElementsToWire,
  streamSDChat,
  type SDChatMessage,
  type SDChatStreamEvent,
} from './sdPracticeApi';
import type {
  CanvasDriver,
  CanvasToolCall,
} from './canvasTools';
import ModelSwitcher, { type ModelOverride } from '../../components/ai/ModelSwitcher';
import { listAICodingModels, type AICodingModel } from '../ai-coding/aiCodingApi';

type ChatTurn =
  | { id: string; role: 'user'; text: string }
  | {
      id: string;
      role: 'assistant';
      text: string;
      toolCalls: Array<{
        id: string;
        name: string;
        partialJson: string;
        parsed?: CanvasToolCall;
        result?: { ok: true; value: unknown } | { ok: false; error: string };
      }>;
      streaming: boolean;
    };

type Props = {
  questionSlug: string;
  questionPrompt: string;
  driver: CanvasDriver | null;
};

/** Accumulates streamed text + tool_use blocks per assistant turn,
 *  executes each tool against the canvas driver, and packages a
 *  follow-up tool_result message for the AI on the next turn. */
export default function SDPracticeChatPanel({
  questionSlug,
  questionPrompt,
  driver,
}: Props) {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [models, setModels] = useState<AICodingModel[]>([]);
  const [override, setOverride] = useState<ModelOverride>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Tool-use requires an Anthropic-compatible provider; filter the
  // model list down so the picker only surfaces options that will
  // actually work against /api/sd-practice/chat.
  const anthropicModels = useMemo(
    () => models.filter((m) => m.kind === 'anthropic' || m.kind === 'anthropic-compatible'),
    [models],
  );

  useEffect(() => {
    listAICodingModels()
      .then(setModels)
      .catch((err) => {
        console.warn('[sd-practice] failed to load model list:', err);
        setModels([]);
      });
  }, []);

  const scrollToBottom = useCallback(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [turns, scrollToBottom]);

  const buildBackendMessages = useCallback(
    (priorTurns: ChatTurn[], pendingUserText: string): SDChatMessage[] => {
      const out: SDChatMessage[] = [];
      for (const t of priorTurns) {
        if (t.role === 'user') {
          out.push({ role: 'user', content: t.text });
        } else {
          // Assistant turn: text + tool_use blocks
          const blocks: Array<
            | { type: 'text'; text: string }
            | { type: 'tool_use'; id: string; name: string; input: unknown }
          > = [];
          if (t.text) blocks.push({ type: 'text', text: t.text });
          for (const tc of t.toolCalls) {
            if (!tc.parsed) continue;
            blocks.push({
              type: 'tool_use',
              id: tc.id,
              name: tc.name,
              input: tc.parsed.input,
            });
          }
          if (blocks.length) out.push({ role: 'assistant', content: blocks });
          // Tool results from the canvas driver — sent as a user turn
          // containing only tool_result blocks, per Anthropic API shape.
          const results = t.toolCalls
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
          if (results.length) {
            out.push({ role: 'user', content: results });
          }
        }
      }
      out.push({ role: 'user', content: pendingUserText });
      return out;
    },
    [],
  );

  const send = useCallback(async () => {
    const text = draft.trim();
    if (!text || busy || !driver) return;
    setError(null);
    setBusy(true);

    const userTurn: ChatTurn = {
      id: `u-${Date.now()}`,
      role: 'user',
      text,
    };
    const aTurn: ChatTurn = {
      id: `a-${Date.now()}`,
      role: 'assistant',
      text: '',
      toolCalls: [],
      streaming: true,
    };

    // Capture priorTurns BEFORE we add the new user message so the
    // history we send to the backend is accurate.
    const priorTurns = turns;
    setTurns((prev) => [...prev, userTurn, aTurn]);
    setDraft('');

    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;

    try {
      const canvasState = driver.readCanvas();
      const backendMessages = buildBackendMessages(priorTurns, text);
      await streamSDChat(
        {
          question_slug: questionSlug,
          question_prompt: questionPrompt,
          canvas_elements: canvasElementsToWire(canvasState),
          messages: backendMessages,
          provider_id: override?.provider_id,
          model: override?.model,
        },
        (evt) => handleStreamEvent(evt, aTurn.id, driver),
        ac.signal,
      );
    } catch (err) {
      if ((err as { name?: string }).name === 'AbortError') return;
      setError((err as Error).message);
    } finally {
      setBusy(false);
      setTurns((prev) =>
        prev.map((t) => (t.id === aTurn.id && t.role === 'assistant' ? { ...t, streaming: false } : t)),
      );
    }
  }, [draft, busy, driver, turns, questionSlug, questionPrompt, buildBackendMessages, override]);

  const handleStreamEvent = useCallback(
    (evt: SDChatStreamEvent, turnId: string, drv: CanvasDriver) => {
      setTurns((prev) =>
        prev.map((t) => {
          if (t.id !== turnId || t.role !== 'assistant') return t;
          if (evt.type === 'text_delta') {
            return { ...t, text: t.text + evt.text };
          }
          if (evt.type === 'tool_use_start') {
            return {
              ...t,
              toolCalls: [
                ...t.toolCalls,
                { id: evt.id, name: evt.name, partialJson: '' },
              ],
            };
          }
          if (evt.type === 'tool_use_delta') {
            return {
              ...t,
              toolCalls: t.toolCalls.map((tc) =>
                tc.id === evt.id
                  ? { ...tc, partialJson: tc.partialJson + evt.partial_json }
                  : tc,
              ),
            };
          }
          if (evt.type === 'tool_use_stop') {
            return {
              ...t,
              toolCalls: t.toolCalls.map((tc) => {
                if (tc.id !== evt.id) return tc;
                let parsed: CanvasToolCall | undefined;
                try {
                  const input = tc.partialJson
                    ? (JSON.parse(tc.partialJson) as unknown)
                    : {};
                  parsed = { name: tc.name, input } as CanvasToolCall;
                } catch {
                  return {
                    ...tc,
                    result: { ok: false, error: 'AI emitted malformed tool input JSON.' },
                  };
                }
                const out = drv.applyTool(parsed);
                return {
                  ...tc,
                  parsed,
                  result: out.ok
                    ? { ok: true, value: out.result }
                    : { ok: false, error: out.error },
                };
              }),
            };
          }
          return t;
        }),
      );
      if (evt.type === 'error') {
        setError(evt.message);
      }
    },
    [],
  );

  const onKey = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        void send();
      }
    },
    [send],
  );

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: 'var(--bg-elev)',
        borderLeft: '1px solid var(--border)',
        minWidth: 0,
      }}
    >
      <div
        style={{
          padding: 'var(--pad-sm) var(--pad-md)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            fontSize: 13,
            fontWeight: 600,
            color: 'var(--text-2)',
          }}
        >
          <Sparkles size={14} strokeWidth={1.8} />
          AI sparring partner
          <span
            className="mono"
            style={{
              marginLeft: 'auto',
              fontSize: 10.5,
              color: 'var(--text-4)',
              letterSpacing: '0.1em',
            }}
          >
            CANVAS-AWARE
          </span>
        </div>
        <ModelSwitcher
          models={anthropicModels}
          value={override}
          onChange={setOverride}
          disabled={busy}
          fullWidth
        />
        {models.length > 0 && anthropicModels.length === 0 && (
          <div
            style={{
              fontSize: 11,
              color: 'var(--plum)',
              lineHeight: 1.4,
            }}
          >
            Tool-use requires an Anthropic-compatible provider. Add one in settings.
          </div>
        )}
      </div>

      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 'var(--pad-md)',
          display: 'flex',
          flexDirection: 'column',
          gap: 'var(--gap-sm)',
        }}
      >
        {turns.length === 0 && (
          <div style={{ color: 'var(--text-3)', fontSize: 13, lineHeight: 1.55 }}>
            Ask the AI to spar on this design. It can draw on the canvas, but it
            asks before mutating and challenges your assumptions. Try:
            <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>
              <li>"Start me off — what should I clarify first?"</li>
              <li>"Add an API gateway in front of the service."</li>
              <li>"What's the failure mode here at p99?"</li>
            </ul>
          </div>
        )}
        {turns.map((t) => (
          <Turn key={t.id} turn={t} />
        ))}
        {error && (
          <div
            style={{
              padding: 8,
              border: '1px solid var(--plum)',
              borderRadius: 'var(--radius)',
              color: 'var(--plum)',
              fontSize: 12,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <AlertTriangle size={13} /> {error}
            <button
              type="button"
              onClick={() => setError(null)}
              style={{
                marginLeft: 'auto',
                background: 'transparent',
                border: 0,
                color: 'inherit',
                cursor: 'pointer',
              }}
              aria-label="Dismiss error"
            >
              <X size={12} />
            </button>
          </div>
        )}
      </div>

      <div
        style={{
          padding: 'var(--pad-sm)',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
        }}
      >
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKey}
          placeholder={driver ? 'Ask the AI… (⌘/Ctrl+Enter to send)' : 'Canvas loading…'}
          disabled={!driver || busy}
          rows={3}
          style={{
            width: '100%',
            resize: 'vertical',
            padding: 8,
            fontSize: 13,
            lineHeight: 1.5,
            background: 'var(--bg)',
            color: 'var(--text)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            fontFamily: 'inherit',
          }}
        />
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 11, color: 'var(--text-4)' }}>
            ⌘/Ctrl+Enter to send
          </span>
          <button
            type="button"
            onClick={() => void send()}
            disabled={!draft.trim() || busy || !driver}
            style={{
              marginLeft: 'auto',
              padding: '6px 12px',
              background: !draft.trim() || busy ? 'var(--bg-sunken)' : 'var(--accent)',
              color: !draft.trim() || busy ? 'var(--text-4)' : 'var(--bg-elev)',
              border: 0,
              borderRadius: 'var(--radius)',
              fontSize: 12.5,
              fontWeight: 600,
              cursor: !draft.trim() || busy ? 'not-allowed' : 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <Send size={12} /> {busy ? 'Thinking…' : 'Send'}
          </button>
        </div>
      </div>
    </div>
  );
}

function Turn({ turn }: { turn: ChatTurn }) {
  if (turn.role === 'user') {
    return (
      <div
        style={{
          alignSelf: 'flex-end',
          maxWidth: '92%',
          padding: '8px 12px',
          background: 'var(--accent-soft)',
          color: 'var(--accent)',
          borderRadius: 'var(--radius)',
          fontSize: 13,
          lineHeight: 1.5,
          whiteSpace: 'pre-wrap',
        }}
      >
        {turn.text}
      </div>
    );
  }
  return (
    <div
      style={{
        alignSelf: 'flex-start',
        maxWidth: '92%',
        fontSize: 13,
        lineHeight: 1.55,
      }}
    >
      <div style={{ whiteSpace: 'pre-wrap', color: 'var(--text)' }}>
        {turn.text}
        {turn.streaming && (
          <span
            className="mono"
            style={{ marginLeft: 4, color: 'var(--text-4)', fontSize: 11 }}
          >
            ▍
          </span>
        )}
      </div>
      {turn.toolCalls.map((tc) => (
        <div
          key={tc.id}
          className="mono"
          style={{
            marginTop: 4,
            padding: '4px 8px',
            background: 'var(--bg-sunken)',
            border: '1px solid var(--border)',
            borderRadius: 4,
            fontSize: 11,
            color:
              tc.result && !tc.result.ok
                ? 'var(--plum)'
                : tc.result?.ok
                  ? 'var(--forest)'
                  : 'var(--text-3)',
          }}
        >
          <span style={{ fontWeight: 600 }}>
            {tc.result ? (tc.result.ok ? '✓' : '✗') : '…'}
          </span>{' '}
          {tc.name}
          {tc.parsed?.input ? ` (${summariseInput(tc.parsed.input)})` : ''}
          {tc.result && !tc.result.ok && (
            <span style={{ marginLeft: 6 }}>— {tc.result.error}</span>
          )}
        </div>
      ))}
    </div>
  );
}

function summariseInput(input: unknown): string {
  if (!input || typeof input !== 'object') return '';
  const obj = input as Record<string, unknown>;
  // Prefer label or id when present, else just the first 2 keys.
  if (typeof obj.label === 'string') return String(obj.label);
  if (typeof obj.id === 'string') return String(obj.id);
  const keys = Object.keys(obj).slice(0, 2);
  return keys
    .map((k) => {
      const v = obj[k];
      return `${k}=${typeof v === 'string' ? v : JSON.stringify(v)}`;
    })
    .join(', ');
}
