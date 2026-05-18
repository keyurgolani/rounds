import { memo, type ReactNode } from 'react';
import { Sparkles, User, AlertTriangle } from 'lucide-react';
import BlockMarkdown from '../shell/BlockMarkdown';
import type { ChatRole } from './chatTypes';

type Props = {
  role: ChatRole;
  content: string;
  /** When true, swap the body for a pulsing "Responding…" indicator
   *  (or `streamingPlaceholder`, when the caller customises it).
   *  Only meaningful on assistant rows. */
  streaming?: boolean;
  /** Custom text to show inside the streaming pulse (defaults to
   *  "Responding…"). Letting the caller customise this lets AI Coding
   *  show "Preparing edits…" during /edit mode. */
  streamingPlaceholder?: ReactNode;
  /** When true, render this bubble as an error (plum border + icon). */
  isError?: boolean;
  /** Width of the bubble, as % of the chat scroll container — set by
   *  ChatPanel's ResizeObserver so prose stays readable when the rail
   *  is narrow. */
  widthPct: number;
  /** Extras rendered inside the bubble below the body — patches,
   *  tool-call chips, etc. */
  extras?: ReactNode;
  /** When true, render `content` as plain pre-wrap (avoids running the
   *  prose through Markdown). User messages always do this. */
  rawText?: boolean;
};

/**
 * One chat bubble. Owns the avatar + the speech-bubble shell + the
 * streaming pulse indicator. Markdown rendering is applied to
 * assistant content by default; the caller can opt out with `rawText`.
 *
 * Extras (patches, tool chips, …) render INSIDE the bubble below the
 * prose so they share the bubble's framing.
 */
function ChatBubbleImpl({
  role,
  content,
  streaming,
  streamingPlaceholder,
  isError,
  widthPct,
  extras,
  rawText,
}: Props) {
  const isUser = role === 'user';
  const showStreamingPulse = !isUser && streaming && !content && !extras;
  return (
    <div
      className="flex"
      style={{ gap: 8, flexDirection: isUser ? 'row-reverse' : 'row' }}
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
          background: isUser
            ? 'var(--bg-sunken)'
            : isError
              ? 'rgba(214, 60, 60, 0.16)'
              : 'var(--accent-soft)',
          color: isUser
            ? 'var(--text-3)'
            : isError
              ? 'var(--plum)'
              : 'var(--accent)',
          marginTop: 2,
        }}
      >
        {isUser ? (
          <User size={11} strokeWidth={2} />
        ) : isError ? (
          <AlertTriangle size={11} strokeWidth={2} />
        ) : (
          <Sparkles size={11} strokeWidth={2} />
        )}
      </span>
      <div
        style={{
          maxWidth: `${widthPct}%`,
          flex: '1 1 auto',
          minWidth: 0,
          padding: '8px 10px',
          background: isUser ? 'var(--bg-sunken)' : 'var(--bg-elev)',
          borderRadius: 'var(--radius)',
          fontSize: 13,
          color: isError ? 'var(--plum)' : 'var(--text)',
          lineHeight: 1.5,
          wordWrap: 'break-word',
          boxShadow: isUser
            ? 'none'
            : isError
              ? 'inset 0 0 0 1px var(--plum)'
              : 'inset 0 0 0 1px var(--border)',
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}
      >
        {content && (
          <div style={{ minWidth: 0 }}>
            {isUser || rawText ? (
              <span style={{ whiteSpace: 'pre-wrap' }}>{content}</span>
            ) : (
              <BlockMarkdown text={content} />
            )}
          </div>
        )}
        {showStreamingPulse && (
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
            <span className="rounds-ai-shimmer">
              {streamingPlaceholder ?? 'Responding…'}
            </span>
          </span>
        )}
        {extras}
      </div>
    </div>
  );
}

export const ChatBubble = memo(ChatBubbleImpl);
export default ChatBubble;
