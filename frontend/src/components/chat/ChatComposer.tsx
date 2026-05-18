import { useEffect, useLayoutEffect, useRef, type ReactNode } from 'react';
import { Square } from 'lucide-react';

type Props = {
  value: string;
  onChange: (v: string) => void;
  onSend: () => void;
  onStop: () => void;
  streaming: boolean;
  disabled?: boolean;
  placeholder?: string;
  /** Optional label override on the Send button (e.g. "Edit"). */
  sendLabel?: string;
  /** Optional hint rendered inside the Send button. Defaults to "⌘ ↵". */
  shortcutLabel?: ReactNode;
  /** Max height for the auto-grow textarea in px. Defaults to 160. */
  maxHeight?: number;
};

/**
 * Auto-growing chat composer. Single-line by default, expands as the
 * user types up to `maxHeight`, then scrolls. Submit on ⌘/Ctrl-Enter.
 *
 * The Send button morphs into a Stop button while `streaming` is true
 * so the user always has a clear way to interrupt a long response.
 *
 * The frame applies an ambient glow (CSS attr `data-ai-processing-glow`)
 * while streaming — caller styles the keyframes globally.
 */
export default function ChatComposer({
  value,
  onChange,
  onSend,
  onStop,
  streaming,
  disabled,
  placeholder,
  sendLabel = 'Send',
  shortcutLabel,
  maxHeight = 160,
}: Props) {
  const ref = useRef<HTMLTextAreaElement>(null);
  const wasStreamingRef = useRef(streaming);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, maxHeight) + 'px';
  }, [value, maxHeight]);

  // Return focus to the composer when the AI finishes responding so
  // the user can keep typing without reaching for the mouse. We track
  // the previous `streaming` value in a ref so we only refocus on the
  // true→false transition, not on every re-render.
  useEffect(() => {
    const justFinished = wasStreamingRef.current && !streaming;
    wasStreamingRef.current = streaming;
    if (!justFinished || disabled) return;
    // Wait a tick so the disabled→enabled transition completes before
    // we try to focus; some browsers (Safari) ignore .focus() on an
    // element that was disabled the same tick.
    const t = window.setTimeout(() => ref.current?.focus(), 0);
    return () => window.clearTimeout(t);
  }, [streaming, disabled]);

  function onKey(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      onSend();
    }
  }

  const sendDisabled = !!disabled || !value.trim();

  return (
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
        ref={ref}
        aria-label="Message to AI assistant"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKey}
        disabled={disabled || streaming}
        placeholder={placeholder}
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
          maxHeight,
        }}
      />
      {streaming ? (
        <StopButton onClick={onStop} />
      ) : (
        <SendButton
          onClick={onSend}
          disabled={sendDisabled}
          label={sendLabel}
          shortcut={shortcutLabel ?? <>&#8984; &#x21B5;</>}
        />
      )}
    </div>
  );
}

function SendButton({
  onClick,
  disabled,
  label,
  shortcut,
}: {
  onClick: () => void;
  disabled: boolean;
  label: string;
  shortcut: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={`${label} message`}
      title={`${label} (⌘ Enter)`}
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
      <span>{label}</span>
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
        {shortcut}
      </span>
    </button>
  );
}

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
