import {
  forwardRef,
  useCallback,
  useEffect,
  useImperativeHandle,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import ModelSwitcher, { type ModelOverride } from '../ai/ModelSwitcher';
import {
  listAICodingModels,
  type AICodingModel,
} from '../../pages/ai-coding/aiCodingApi';
import ChatBubble from './ChatBubble';
import ChatComposer from './ChatComposer';
import type {
  ChatMessage,
  ChatPanelHandle,
  ChatSendArgs,
  ChatStreamCallbacks,
  ModelFilter,
} from './chatTypes';

export type ChatPanelProps<E = unknown> = {
  /** Caller-side streaming. Invoked when the user hits Send (or ⌘
   *  Enter). The handler is responsible for the wire protocol; it
   *  signals the panel via the supplied callbacks. */
  onSend: (args: ChatSendArgs<E>) => Promise<void>;

  /** Optional initial messages (rehydration). Consumed on first render
   *  only — subsequent changes are ignored so local edits stick. */
  initialMessages?: ChatMessage<E>[];
  /** Fires when a user or assistant message is committed. Use for
   *  persistence. */
  onMessageRecorded?: (msg: ChatMessage<E>) => void;

  /** Render the per-message extras slot (patches, tool chips, …)
   *  inside the bubble below the prose. */
  renderExtras?: (
    msg: ChatMessage<E>,
    ctx: { index: number; isStreaming: boolean },
  ) => ReactNode;

  /** When true, the body for this message renders as plain pre-wrap
   *  (skips Markdown). */
  shouldRenderRaw?: (msg: ChatMessage<E>) => boolean;

  // ── Header ─────────────────────────────────────────────
  /** Title rendered above the model picker (e.g. "AI sparring partner"). */
  title?: ReactNode;
  /** Right-aligned slot in the header row (status pill, etc.). */
  titleRight?: ReactNode;
  /** Right-aligned slot BELOW the title row, next to the model picker
   *  (mode toggle, etc.). */
  headerRight?: ReactNode;
  /** When true, the model picker is hidden entirely. */
  hideModelPicker?: boolean;
  /** Filter applied to the model list. Returning false hides the model. */
  modelFilter?: ModelFilter;
  /** Callout rendered under the model picker when no models match
   *  the filter (e.g. "Tool-use requires an Anthropic-compatible
   *  provider."). */
  modelPickerEmptyCallout?: ReactNode;

  // ── Empty state ─────────────────────────────────────────
  /** Replaces the default empty-state callout. */
  emptyState?: ReactNode;

  // ── Composer ───────────────────────────────────────────
  composerPlaceholder?: string;
  composerSendLabel?: string;
  /** When true, the composer is disabled and Send shows a muted state. */
  disabled?: boolean;
  /** Custom shortcut hint pill inside the Send button. */
  composerShortcutLabel?: ReactNode;

  // ── Streaming UX ───────────────────────────────────────
  /** Custom placeholder text shown in the streaming bubble before the
   *  first text token arrives. (Default: "Responding…") */
  streamingPlaceholder?: ReactNode;

  // ── Styling ─────────────────────────────────────────────
  rootStyle?: React.CSSProperties;
};

let _idCounter = 0;
function nextId(): string {
  _idCounter += 1;
  return `m-${Date.now().toString(36)}-${_idCounter}`;
}

/**
 * Generic chat panel shared by every AI-driven chat surface in the
 * app (AI Coding, SD Practice, Take-Home).
 *
 * Owns: message list state, scrolling, abort/Stop, model picker,
 * bubble-width tiering, composer, and the streaming placeholder. The
 * caller owns the wire protocol via `onSend` and the per-message
 * extras shape via the generic parameter `E` and `renderExtras`.
 */
function ChatPanelInner<E>(
  props: ChatPanelProps<E>,
  ref: React.ForwardedRef<ChatPanelHandle<E>>,
): React.ReactElement {
  const {
    onSend,
    initialMessages,
    onMessageRecorded,
    renderExtras,
    shouldRenderRaw,
    title,
    titleRight,
    headerRight,
    hideModelPicker,
    modelFilter,
    modelPickerEmptyCallout,
    emptyState,
    composerPlaceholder,
    composerSendLabel,
    disabled,
    composerShortcutLabel,
    streamingPlaceholder,
    rootStyle,
  } = props;

  const [messages, setMessages] = useState<ChatMessage<E>[]>(
    () => initialMessages ?? [],
  );
  const messagesRef = useRef(messages);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const [draft, setDraft] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [override, setOverride] = useState<ModelOverride>(null);
  const [models, setModels] = useState<AICodingModel[]>([]);
  const abortRef = useRef<AbortController | null>(null);
  const streamingTurnIdRef = useRef<string | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const [bubbleWidthPct, setBubbleWidthPct] = useState(90);

  useEffect(() => {
    listAICodingModels()
      .then(setModels)
      .catch((err) => {
        console.warn('[chat] failed to load model list:', err);
        setModels([]);
      });
  }, []);

  // Auto-scroll on new messages / streaming progress.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, streaming]);

  // Tiered bubble width: tighter container → bubble takes more room.
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

  const filteredModels = useMemo(() => {
    return modelFilter ? models.filter(modelFilter) : models;
  }, [models, modelFilter]);

  useImperativeHandle(
    ref,
    () => ({
      getMessages: () => messagesRef.current,
      reset: () => setMessages([]),
      updateMessage: (id, patch) => {
        setMessages((prev) =>
          prev.map((m) => (m.id === id ? patch(m) : m)),
        );
      },
    }),
    [],
  );

  /** Apply a partial update to the in-flight assistant bubble. */
  const updateStreamingTurn = useCallback(
    (patch: (m: ChatMessage<E>) => ChatMessage<E>) => {
      const id = streamingTurnIdRef.current;
      if (!id) return;
      setMessages((prev) =>
        prev.map((m) => (m.id === id && m.role === 'assistant' ? patch(m) : m)),
      );
    },
    [],
  );

  const send = useCallback(async () => {
    const text = draft.trim();
    if (!text || streaming || disabled) return;
    const userMsg: ChatMessage<E> = {
      id: nextId(),
      role: 'user',
      content: text,
    };
    const assistantId = nextId();
    const placeholder: ChatMessage<E> = {
      id: assistantId,
      role: 'assistant',
      content: '',
      streaming: true,
    };
    streamingTurnIdRef.current = assistantId;
    setMessages((prev) => [...prev, userMsg, placeholder]);
    onMessageRecorded?.(userMsg);
    setDraft('');
    setStreaming(true);

    const ac = new AbortController();
    abortRef.current = ac;

    const callbacks: ChatStreamCallbacks<E> = {
      appendText: (chunk) => {
        if (!chunk) return;
        updateStreamingTurn((m) => ({ ...m, content: m.content + chunk }));
      },
      replaceText: (next) => {
        updateStreamingTurn((m) => ({ ...m, content: next }));
      },
      setExtras: (updater) => {
        updateStreamingTurn((m) => ({ ...m, extras: updater(m.extras) }));
      },
      error: (err) => {
        const message =
          typeof err === 'string' ? err : err.message || String(err);
        setMessages((prev) => {
          const last = prev[prev.length - 1];
          const errMsg: ChatMessage<E> = {
            id: last?.id ?? nextId(),
            role: 'assistant',
            content: `Error: ${message}`,
            isError: true,
          };
          if (
            last?.role === 'assistant' &&
            !last.content &&
            !last.extras
          ) {
            return [...prev.slice(0, -1), errMsg];
          }
          return [...prev, errMsg];
        });
      },
    };

    try {
      // History snapshot includes the user message we just appended PLUS
      // the streaming placeholder. Callers usually want to slice off the
      // placeholder before sending to a backend, but having both makes
      // the contract obvious.
      const history = [...messagesRef.current];
      await onSend({
        text,
        history,
        override,
        signal: ac.signal,
        callbacks,
      });
    } catch (err) {
      if ((err as { name?: string }).name === 'AbortError') {
        // User-initiated stop — drop the still-empty placeholder so the
        // spinner doesn't linger.
      } else {
        callbacks.error(err as Error);
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
      streamingTurnIdRef.current = null;
      // Clear the streaming flag on the placeholder, and prune it if it
      // never got content or extras (model returned nothing / user
      // stopped before first token).
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (!last || last.role !== 'assistant') return prev;
        if (!last.content && !last.extras) {
          return prev.slice(0, -1);
        }
        if (last.streaming) {
          return [...prev.slice(0, -1), { ...last, streaming: false }];
        }
        return prev;
      });
      // Record the final assistant turn for persistence.
      const finalLast = messagesRef.current[messagesRef.current.length - 1];
      if (
        finalLast &&
        finalLast.role === 'assistant' &&
        (finalLast.content || finalLast.extras)
      ) {
        onMessageRecorded?.(finalLast);
      }
    }
  }, [
    draft,
    streaming,
    disabled,
    onSend,
    onMessageRecorded,
    override,
    updateStreamingTurn,
  ]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return (
    <div
      className="flex flex-col"
      style={{
        height: '100%',
        background: 'var(--bg)',
        minHeight: 0,
        ...rootStyle,
      }}
    >
      {(title ||
        titleRight ||
        headerRight ||
        !hideModelPicker ||
        modelPickerEmptyCallout) && (
        <div
          style={{
            padding: '8px 10px',
            borderBottom: '1px solid var(--border)',
            background: 'var(--bg-elev)',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            flexShrink: 0,
          }}
        >
          {(title || titleRight) && (
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
              {title}
              {titleRight && (
                <span style={{ marginLeft: 'auto' }}>{titleRight}</span>
              )}
            </div>
          )}
          <div
            className="flex items-center"
            style={{ gap: 8, minWidth: 0 }}
          >
            {!hideModelPicker && (
              <ModelSwitcher
                models={filteredModels}
                value={override}
                onChange={setOverride}
                disabled={disabled || streaming}
                fullWidth
              />
            )}
            {headerRight && (
              <div style={{ marginLeft: hideModelPicker ? 0 : 'auto' }}>
                {headerRight}
              </div>
            )}
          </div>
          {modelPickerEmptyCallout &&
            models.length > 0 &&
            filteredModels.length === 0 && (
              <div
                style={{
                  fontSize: 11,
                  color: 'var(--plum)',
                  lineHeight: 1.4,
                }}
              >
                {modelPickerEmptyCallout}
              </div>
            )}
        </div>
      )}

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
        {messages.length === 0 && !streaming && (emptyState ?? <DefaultEmpty />)}
        {messages.map((m, i) => {
          const isLast = i === messages.length - 1;
          const isStreamingNow = !!streaming && isLast && !!m.streaming;
          const extras = renderExtras
            ? renderExtras(m, { index: i, isStreaming: isStreamingNow })
            : undefined;
          return (
            <ChatBubble
              key={m.id}
              role={m.role}
              content={m.content}
              streaming={isStreamingNow}
              streamingPlaceholder={streamingPlaceholder}
              isError={m.isError}
              widthPct={bubbleWidthPct}
              extras={extras}
              rawText={shouldRenderRaw?.(m)}
            />
          );
        })}
      </div>

      <div
        style={{
          padding: 8,
          borderTop: '1px solid var(--border)',
          background: 'var(--bg-elev)',
          flexShrink: 0,
        }}
      >
        <ChatComposer
          value={draft}
          onChange={setDraft}
          onSend={send}
          onStop={stop}
          streaming={streaming}
          disabled={disabled}
          placeholder={composerPlaceholder}
          sendLabel={composerSendLabel}
          shortcutLabel={composerShortcutLabel}
        />
      </div>
    </div>
  );
}

function DefaultEmpty() {
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
        textAlign: 'center',
      }}
    >
      Ask the assistant a question.
    </div>
  );
}

// forwardRef preserves the generic parameter via an explicit cast on
// the wrapper. Without this the consumer would lose the `E` type when
// invoking the component with a typed ref.
const ChatPanel = forwardRef(ChatPanelInner) as <E = unknown>(
  props: ChatPanelProps<E> & { ref?: React.Ref<ChatPanelHandle<E>> },
) => React.ReactElement;

export default ChatPanel;
export type { ChatMessage, ChatSendArgs, ChatStreamCallbacks } from './chatTypes';
