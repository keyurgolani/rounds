import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { Sparkles, Square, User } from 'lucide-react';
import { runnerSSE } from '../../lib/runnerFetch';
import ModelSwitcher, { type ModelOverride } from '../ai/ModelSwitcher';
import { listAICodingModels, type AICodingModel } from '../../pages/ai-coding/aiCodingApi';

type Msg = { role: 'user' | 'assistant'; content: string };

type Props = {
  assignmentSlug: string;
  files: Record<string, string>;
  disabled?: boolean;
  /** Optional rehydration source — see AIChatPanel for semantics. */
  initialMessages?: Msg[];
  onMessageRecorded?: (m: Msg) => void;
};

export default function TakeHomeChatPanel({
  assignmentSlug,
  files,
  disabled,
  initialMessages,
  onMessageRecorded,
}: Props) {
  const [messages, setMessages] = useState<Msg[]>(() => initialMessages ?? []);
  const [draft, setDraft] = useState('');
  const [streaming, setStreaming] = useState(false);
  const streamingRef = useRef<string>('');
  const abortRef = useRef<AbortController | null>(null);
  const [models, setModels] = useState<AICodingModel[]>([]);
  const [override, setOverride] = useState<ModelOverride>(null);
  const composerRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [bubbleWidthPct, setBubbleWidthPct] = useState<number>(90);

  useEffect(() => {
    listAICodingModels()
      .then(setModels)
      .catch((err) => {
        console.warn('[take-home] failed to load model list:', err);
        setModels([]);
      });
  }, []);

  useLayoutEffect(() => {
    const el = composerRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const max = 160;
    el.style.height = Math.min(el.scrollHeight, max) + 'px';
  }, [draft]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, streaming]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect.width ?? 0;
      const next = w >= 480 ? 90 : w >= 360 ? 95 : 100;
      setBubbleWidthPct((prev) => (prev === next ? prev : next));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  async function send() {
    if (!draft.trim() || streaming) return;
    const userMsg: Msg = { role: 'user', content: draft };
    // Eager assistant placeholder so the avatar + "Responding…" shimmer
    // appears the instant the user hits send (otherwise users stare at
    // their own bubble for the whole round-trip).
    setMessages((m) => [...m, userMsg, { role: 'assistant', content: '' }]);
    onMessageRecorded?.(userMsg);
    setDraft('');
    setStreaming(true);
    streamingRef.current = '';
    const ac = new AbortController();
    abortRef.current = ac;
    try {
      await runnerSSE('/api/take-home/chat', {
        method: 'POST',
        auth: 'optional',
        signal: ac.signal,
        body: {
          assignment_slug: assignmentSlug,
          provider_id: override?.provider_id,
          model: override?.model,
          messages: [...messages, userMsg],
          files,
        },
        onDelta: (t) => {
          streamingRef.current += t;
          setMessages((m) => {
            const last = m[m.length - 1];
            if (
              last?.role === 'assistant' &&
              last.content === streamingRef.current.slice(0, last.content.length)
            ) {
              return [
                ...m.slice(0, -1),
                { role: 'assistant', content: streamingRef.current },
              ];
            }
            return [...m, { role: 'assistant', content: streamingRef.current }];
          });
        },
        onDone: () => {
          if (streamingRef.current) {
            onMessageRecorded?.({ role: 'assistant', content: streamingRef.current });
          }
        },
        onError: (e) => {
          setMessages((m) => {
            const last = m[m.length - 1];
            const errMsg: Msg = {
              role: 'assistant',
              content: `Error: ${e.message}`,
            };
            if (last?.role === 'assistant' && !last.content) {
              return [...m.slice(0, -1), errMsg];
            }
            return [...m, errMsg];
          });
        },
      });
    } finally {
      setStreaming(false);
      abortRef.current = null;
      // Drop a stranded empty assistant bubble if the SSE closed with
      // no delta + no error, or the user hit Stop before any token.
      setMessages((m) => {
        const last = m[m.length - 1];
        if (last?.role === 'assistant' && !last.content) {
          return m.slice(0, -1);
        }
        return m;
      });
    }
  }

  function stop() {
    abortRef.current?.abort();
  }

  function onComposerKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div
      className="flex flex-col"
      style={{ height: '100%', background: 'var(--bg)', minHeight: 0 }}
    >
      <div
        className="flex items-center"
        style={{
          padding: '8px 10px',
          gap: 8,
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-elev)',
          flexShrink: 0,
        }}
      >
        <ModelSwitcher
          models={models}
          value={override}
          onChange={setOverride}
          disabled={disabled || streaming}
          fullWidth
        />
      </div>

      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflow: 'auto',
          padding: 12,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}
      >
        {messages.length === 0 && !streaming && (
          <div
            style={{
              margin: 'auto 0',
              padding: 14,
              background: 'var(--bg-sunken)',
              borderRadius: 'var(--radius)',
              fontSize: 12.5,
              color: 'var(--text-3)',
              lineHeight: 1.55,
              textAlign: 'center',
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
              <Sparkles size={11} strokeWidth={2} /> AI PAIR
            </div>
            <div>Ask about the prompt or your code.</div>
          </div>
        )}
        {messages.map((m, i) => (
          <Bubble
            key={i}
            role={m.role}
            content={m.content}
            widthPct={bubbleWidthPct}
          />
        ))}
      </div>

      <div
        style={{
          padding: 8,
          borderTop: '1px solid var(--border)',
          background: 'var(--bg-elev)',
          flexShrink: 0,
        }}
      >
        <div
          data-ai-processing-glow={streaming ? 'true' : undefined}
          className="flex items-end"
          style={{
            gap: 6,
            background: 'var(--bg)',
            borderRadius: 'var(--radius)',
            boxShadow: 'inset 0 0 0 1px var(--border-strong)',
            padding: '6px 6px 6px 10px',
          }}
        >
          <textarea
            ref={composerRef}
            aria-label="Message to AI assistant"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onComposerKey}
            disabled={disabled || streaming}
            placeholder={disabled ? 'AI disabled' : 'Ask the model…'}
            rows={1}
            style={{
              flex: 1,
              resize: 'none',
              background: 'transparent',
              border: 0,
              outline: 'none',
              color: 'var(--text)',
              fontSize: 13,
              fontFamily: 'var(--font-sans)',
              lineHeight: 1.45,
              padding: '4px 0',
              minHeight: 22,
              maxHeight: 160,
            }}
          />
          {streaming ? (
            <StopButton onClick={stop} />
          ) : (
            <SendButton
              onClick={send}
              disabled={!!disabled || !draft.trim()}
            />
          )}
        </div>
      </div>
    </div>
  );
}

/** Send pill that surfaces ⌘ Enter inline so the composer doesn't
 *  need a separate helper-text row beneath it. */
function SendButton({
  onClick,
  disabled,
}: {
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label="Send message"
      title="Send (⌘ Enter)"
      className="inline-flex items-center"
      style={{
        gap: 6,
        height: 28,
        padding: '0 4px 0 10px',
        border: 0,
        borderRadius: 999,
        background: disabled ? 'var(--bg-sunken)' : 'var(--accent)',
        color: disabled ? 'var(--text-4)' : 'var(--bg)',
        cursor: disabled ? 'default' : 'pointer',
        fontSize: 12,
        fontWeight: 600,
        flexShrink: 0,
      }}
    >
      <span>Send</span>
      <span
        className="mono inline-flex items-center"
        aria-hidden="true"
        style={{
          fontSize: 9.5,
          letterSpacing: '0.04em',
          padding: '2px 6px',
          marginRight: 2,
          borderRadius: 999,
          background: disabled ? 'transparent' : 'rgba(0,0,0,0.18)',
          color: disabled ? 'var(--text-4)' : 'var(--bg)',
          opacity: disabled ? 0.6 : 1,
        }}
      >
        ⌘ ↵
      </span>
    </button>
  );
}

/** Replaces SendButton while the AI is streaming so the user has a
 *  clear way to interrupt a long response. */
function StopButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Stop AI response"
      title="Stop AI response"
      className="inline-flex items-center"
      style={{
        gap: 6,
        height: 28,
        padding: '0 12px',
        border: 0,
        borderRadius: 999,
        background: 'var(--plum)',
        color: 'var(--bg)',
        cursor: 'pointer',
        fontSize: 12,
        fontWeight: 600,
        flexShrink: 0,
      }}
    >
      <Square size={10} strokeWidth={0} fill="currentColor" />
      <span>Stop</span>
    </button>
  );
}

function Bubble({
  role,
  content,
  widthPct,
}: {
  role: 'user' | 'assistant';
  content: string;
  widthPct?: number;
}) {
  const isUser = role === 'user';
  return (
    <div
      className="flex"
      style={{
        gap: 8,
        flexDirection: isUser ? 'row-reverse' : 'row',
      }}
    >
      <span
        aria-hidden="true"
        style={{
          flexShrink: 0,
          width: 22,
          height: 22,
          borderRadius: 999,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: isUser ? 'var(--bg-sunken)' : 'var(--accent-soft)',
          color: isUser ? 'var(--text-3)' : 'var(--accent)',
          marginTop: 2,
        }}
      >
        {isUser ? <User size={11} strokeWidth={2} /> : <Sparkles size={11} strokeWidth={2} />}
      </span>
      <div
        style={{
          maxWidth: `${widthPct ?? 90}%`,
          padding: '8px 10px',
          background: isUser ? 'var(--bg-sunken)' : 'var(--bg-elev)',
          borderRadius: 'var(--radius)',
          fontSize: 13,
          color: 'var(--text)',
          lineHeight: 1.5,
          whiteSpace: 'pre-wrap',
          wordWrap: 'break-word',
          boxShadow: isUser ? 'none' : 'inset 0 0 0 1px var(--border)',
        }}
      >
        {content || (
          <span
            className="inline-flex items-center"
            style={{ gap: 8, fontSize: 13, fontWeight: 600 }}
          >
            <span
              aria-hidden="true"
              style={{
                width: 7,
                height: 7,
                borderRadius: 999,
                background: 'var(--accent)',
                boxShadow: '0 0 8px var(--accent)',
                animation: 'rounds-ai-pulse 1.2s ease-in-out infinite',
              }}
            />
            <span className="rounds-ai-shimmer">Responding…</span>
          </span>
        )}
      </div>
    </div>
  );
}
