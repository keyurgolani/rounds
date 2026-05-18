/**
 * Click-to-edit field with explicit ✓/✗ commit. Renders a read view
 * by default; clicking it swaps to an input flanked by a tick and a
 * cross. Tick (or Enter) applies the change; cross (or Escape) discards.
 *
 * The `onCommit` callback is async — while it runs the controls
 * disable and the field shows a faint saving state. On error, the
 * field stays in edit mode with the entered value preserved and the
 * error rendered underneath.
 *
 * Designed for the application / offer / round detail pattern where
 * the user scans values and only edits the one they want to change.
 */
import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react';
import { Check, X } from 'lucide-react';
import Select from './Select';
import DatePicker from './DatePicker';

type BaseProps = {
  /** Label rendered above the value (eyebrow style). */
  label: string;
  /** Current value of the field. */
  value: string;
  /** Async commit. Resolve to confirm save; throw to surface an
   *  error and keep the field in edit mode. */
  onCommit: (next: string) => Promise<void>;
  /** Placeholder shown when the value is empty. */
  placeholder?: string;
  /** Override the read-view rendering (e.g. show a formatted number
   *  instead of raw text). The "click target" affordance is added by
   *  this component regardless. */
  renderRead?: (value: string) => ReactNode;
};

type TextProps = BaseProps & { kind: 'text' };
type MultilineProps = BaseProps & { kind: 'multiline'; rows?: number };
type DateOnlyProps = BaseProps & { kind: 'date-only' };
type SelectProps = BaseProps & {
  kind: 'select';
  options: Array<{ value: string; label: string }>;
};
type UrlProps = BaseProps & { kind: 'url' };

type Props =
  | TextProps
  | MultilineProps
  | DateOnlyProps
  | SelectProps
  | UrlProps;

export default function InlineEditField(props: Props) {
  const { label, value, onCommit, placeholder, renderRead } = props;
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement | HTMLTextAreaElement | null>(null);

  // Reset the draft whenever the upstream value changes while we're
  // not editing — the parent might have refreshed the row.
  useEffect(() => {
    if (!editing) setDraft(value);
  }, [value, editing]);

  // Auto-focus the input as soon as we enter edit mode.
  useEffect(() => {
    if (editing) {
      const el = inputRef.current;
      if (el) {
        el.focus();
        if ('select' in el && typeof el.select === 'function') {
          el.select();
        }
      }
    }
  }, [editing]);

  function startEdit() {
    if (saving) return;
    setDraft(value);
    setError(null);
    setEditing(true);
  }

  function discard() {
    setEditing(false);
    setDraft(value);
    setError(null);
  }

  async function commit() {
    if (draft === value) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onCommit(draft);
      setEditing(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save');
    } finally {
      setSaving(false);
    }
  }

  function onKey(e: React.KeyboardEvent) {
    if (e.key === 'Escape') {
      e.preventDefault();
      discard();
    } else if (
      e.key === 'Enter' &&
      // Allow newlines in textareas — only commit on Cmd/Ctrl+Enter
      // or on plain Enter for single-line inputs.
      (props.kind !== 'multiline' || e.metaKey || e.ctrlKey)
    ) {
      e.preventDefault();
      void commit();
    }
  }

  return (
    <div className="flex flex-col" style={{ gap: 4 }}>
      <span className="eyebrow" style={{ color: 'var(--text-3)' }}>
        {label}
      </span>
      {editing ? (
        <div
          className="flex"
          style={{
            gap: 6,
            alignItems: props.kind === 'multiline' ? 'flex-start' : 'center',
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            {renderInput({ props, draft, setDraft, onKey, inputRef, placeholder })}
          </div>
          <div className="flex items-center" style={{ gap: 4, flexShrink: 0 }}>
            <button
              type="button"
              onClick={() => void commit()}
              disabled={saving}
              aria-label="Apply change"
              title="Apply (Enter)"
              style={commitBtnStyle('apply', saving)}
            >
              <Check size={13} strokeWidth={2.2} />
            </button>
            <button
              type="button"
              onClick={discard}
              disabled={saving}
              aria-label="Discard change"
              title="Discard (Esc)"
              style={commitBtnStyle('discard', saving)}
            >
              <X size={13} strokeWidth={2.2} />
            </button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={startEdit}
          className="text-left"
          style={readBtnStyle}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--bg-sunken)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
          }}
        >
          {renderRead ? (
            <span style={{ display: 'inline-block', width: '100%' }}>
              {renderRead(value)}
            </span>
          ) : value ? (
            <span style={{ color: 'var(--text)', fontSize: 13 }}>{value}</span>
          ) : (
            <span style={{ color: 'var(--text-4)', fontSize: 13, fontStyle: 'italic' }}>
              {placeholder ?? 'Click to add'}
            </span>
          )}
        </button>
      )}
      {error && (
        <div style={{ fontSize: 11.5, color: 'var(--plum)' }}>{error}</div>
      )}
    </div>
  );
}

function renderInput({
  props,
  draft,
  setDraft,
  onKey,
  inputRef,
  placeholder,
}: {
  props: Props;
  draft: string;
  setDraft: (v: string) => void;
  onKey: (e: React.KeyboardEvent) => void;
  inputRef: React.MutableRefObject<HTMLInputElement | HTMLTextAreaElement | null>;
  placeholder?: string;
}): ReactNode {
  switch (props.kind) {
    case 'multiline':
      return (
        <textarea
          ref={(el) => {
            inputRef.current = el;
          }}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKey}
          rows={props.rows ?? 4}
          placeholder={placeholder}
          style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit' }}
        />
      );
    case 'date-only':
      return (
        <DatePicker
          value={draft}
          onChange={setDraft}
          ariaLabel={placeholder ?? 'Date'}
        />
      );
    case 'select':
      return (
        <Select
          value={draft}
          options={props.options}
          onChange={setDraft}
          fullWidth
        />
      );
    case 'url':
      return (
        <input
          ref={(el) => {
            inputRef.current = el;
          }}
          type="url"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKey}
          placeholder={placeholder}
          style={{ ...inputStyle, fontFamily: 'var(--font-mono)' }}
        />
      );
    case 'text':
    default:
      return (
        <input
          ref={(el) => {
            inputRef.current = el;
          }}
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKey}
          placeholder={placeholder}
          style={inputStyle}
        />
      );
  }
}

const inputStyle: CSSProperties = {
  padding: '8px 10px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--accent)',
  background: 'var(--bg)',
  color: 'var(--text)',
  fontSize: 13,
  width: '100%',
};

const readBtnStyle: CSSProperties = {
  padding: '6px 10px',
  borderRadius: 'var(--radius)',
  border: '1px solid transparent',
  background: 'transparent',
  cursor: 'text',
  minHeight: 32,
  display: 'flex',
  alignItems: 'center',
  width: '100%',
  transition: 'background 120ms',
};

function commitBtnStyle(
  kind: 'apply' | 'discard',
  saving: boolean,
): CSSProperties {
  return {
    width: 28,
    height: 28,
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: kind === 'apply' ? 'var(--accent)' : 'var(--bg-sunken)',
    color: kind === 'apply' ? 'var(--bg)' : 'var(--text-2)',
    border: 0,
    borderRadius: 999,
    cursor: saving ? 'wait' : 'pointer',
    opacity: saving ? 0.6 : 1,
  };
}
