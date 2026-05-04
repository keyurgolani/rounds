import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Trash2 } from 'lucide-react';
import DatePicker from '../components/shell/DatePicker';
import Select from '../components/shell/Select';
import {
  buildMentionIndex,
  filterIndex,
  type MentionEntry,
} from '../lib/mentionIndex';
import {
  mentionLabelWithPrefix,
  mentionToken,
  splitBody,
  type Mention,
} from '../lib/mentions';
import { usePlatform } from '../hooks/usePlatform';

export type Priority = 'low' | 'normal' | 'high';

export interface TodoFormValue {
  body: string;
  due_date: string;
  priority: Priority;
  mentions: Mention[];
}

interface TodoFormProps {
  initial?: Partial<TodoFormValue>;
  onSubmit: (value: TodoFormValue) => Promise<void>;
  onDelete?: () => Promise<void>;
  onCancel: () => void;
  campaignName?: string;
  campaignMissing?: boolean;
  submitLabel?: string;
}

// Shared editor for create + edit. A single body field stands in for
// what used to be split title/body — the codebase treats a todo as a
// single piece of text now. Mentions ([[type:slug|label]] tokens) are
// authored inline via @-autocomplete.
export default function TodoForm({
  initial,
  onSubmit,
  onDelete,
  onCancel,
  campaignName,
  campaignMissing,
  submitLabel = 'Save',
}: TodoFormProps) {
  const { modifierSymbol } = usePlatform();
  const [body, setBody] = useState(initial?.body ?? '');
  const [dueDate, setDueDate] = useState(initial?.due_date ?? '');
  const [priority, setPriority] = useState<Priority>(initial?.priority ?? 'normal');
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [indexReady, setIndexReady] = useState(false);
  const indexRef = useRef<MentionEntry[]>([]);

  const bodyRef = useRef<HTMLTextAreaElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const [autocomplete, setAutocomplete] = useState<{
    query: string;
    start: number;
    caret: number;
    results: MentionEntry[];
    selected: number;
  } | null>(null);

  useEffect(() => {
    if (indexReady) return;
    let cancelled = false;
    (async () => {
      try {
        const index = await buildMentionIndex();
        if (cancelled) return;
        indexRef.current = index;
        setIndexReady(true);
      } catch {
        /* ignore — typing still works, @-autocomplete just won't show results */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [indexReady]);

  function syncScroll() {
    const ta = bodyRef.current;
    const ov = overlayRef.current;
    if (!ta || !ov) return;
    ov.scrollTop = ta.scrollTop;
    ov.scrollLeft = ta.scrollLeft;
  }

  function handleBodyChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    const next = e.target.value;
    setBody(next);
    const caret = e.target.selectionStart ?? next.length;
    const triggerIndex = lastUnescapedAt(next, caret);
    if (triggerIndex === -1) {
      setAutocomplete(null);
      return;
    }
    const query = next.slice(triggerIndex + 1, caret);
    if (query.includes(' ') || query.includes('\n')) {
      setAutocomplete(null);
      return;
    }
    const results = filterIndex(indexRef.current, query);
    setAutocomplete({ query, start: triggerIndex, caret, results, selected: 0 });
  }

  function insertMention(entry: MentionEntry) {
    if (!autocomplete) return;
    const { start, caret } = autocomplete;
    const m: Mention = { type: entry.type, slug: entry.slug, label: entry.label };
    const token = mentionToken(m);
    const next = body.slice(0, start) + token + ' ' + body.slice(caret);
    setBody(next);
    setAutocomplete(null);
    requestAnimationFrame(() => {
      const el = bodyRef.current;
      if (!el) return;
      const pos = start + token.length + 1;
      el.focus();
      el.setSelectionRange(pos, pos);
    });
  }

  const submit = useCallback(async () => {
    if (saving) return;
    const trimmed = body.trim();
    if (!trimmed) {
      setError('Add some text for the todo.');
      return;
    }
    if (campaignMissing) {
      setError('Pick an active campaign first.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await onSubmit({
        body,
        due_date: dueDate,
        priority,
        mentions: extractMentions(body),
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save todo.');
    } finally {
      setSaving(false);
    }
  }, [body, campaignMissing, dueDate, onSubmit, priority, saving]);

  function handleBodyKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      void submit();
      return;
    }
    if (e.key === 'Escape' && !autocomplete) {
      e.preventDefault();
      onCancel();
      return;
    }
    if (!autocomplete || autocomplete.results.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setAutocomplete({
        ...autocomplete,
        selected: (autocomplete.selected + 1) % autocomplete.results.length,
      });
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setAutocomplete({
        ...autocomplete,
        selected:
          (autocomplete.selected - 1 + autocomplete.results.length) %
          autocomplete.results.length,
      });
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      insertMention(autocomplete.results[autocomplete.selected]);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      setAutocomplete(null);
    }
  }

  const activeItem = useMemo(() => {
    if (!autocomplete) return null;
    return autocomplete.results[autocomplete.selected] ?? null;
  }, [autocomplete]);

  const chunks = useMemo(() => splitBody(body), [body]);

  async function handleDelete() {
    if (!onDelete || deleting) return;
    setDeleting(true);
    setError(null);
    try {
      await onDelete();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not delete todo.');
      setDeleting(false);
    }
  }

  return (
    <>
      <div style={{ position: 'relative' }}>
        <div
          ref={overlayRef}
          aria-hidden="true"
          style={{
            ...overlayStyle,
            minHeight: 96,
          }}
        >
          {chunks.length === 0 ? (
            <span style={{ color: 'var(--text-4)' }} />
          ) : (
            chunks.map((c, i) =>
              c.kind === 'text' ? (
                <span key={i}>{c.text}</span>
              ) : (
                <span key={i} style={chipStyle}>
                  {mentionLabelWithPrefix(c.mention)}
                </span>
              ),
            )
          )}
          <span>{'​'}</span>
        </div>
        <textarea
          ref={bodyRef}
          value={body}
          onChange={handleBodyChange}
          onKeyDown={handleBodyKeyDown}
          onScroll={syncScroll}
          rows={4}
          spellCheck={false}
          autoCorrect="off"
          autoComplete="off"
          autoFocus
          placeholder="What's next? Type @ to mention a question, anecdote, application, round, or campaign."
          style={{
            ...inputStyle,
            ...editorTextareaStyle,
            resize: 'vertical',
          }}
        />
        {autocomplete && autocomplete.results.length > 0 && (
          <div
            className="card"
            style={{
              position: 'absolute',
              left: 0,
              top: 'calc(100% + 4px)',
              width: '100%',
              maxHeight: 220,
              overflowY: 'auto',
              boxShadow: 'var(--shadow-elev)',
              padding: 4,
              zIndex: 95,
            }}
          >
            {autocomplete.results.map((r) => (
              <button
                key={`${r.type}:${r.slug}`}
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault();
                  insertMention(r);
                }}
                className="flex items-center justify-between w-full"
                style={{
                  padding: '6px 8px',
                  border: 0,
                  background:
                    activeItem?.slug === r.slug && activeItem.type === r.type
                      ? 'var(--bg-sunken)'
                      : 'transparent',
                  color: 'var(--text)',
                  cursor: 'pointer',
                  borderRadius: 'var(--radius)',
                  textAlign: 'left',
                  fontSize: 12.5,
                }}
              >
                <span
                  style={{
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {r.label}
                </span>
                <span
                  className="mono"
                  style={{ fontSize: 10, color: 'var(--text-4)', marginLeft: 8 }}
                >
                  {r.type}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
      <div
        className="grid gap-2 mt-2"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))' }}
      >
        <label className="flex flex-col gap-1">
          <span className="eyebrow">Due</span>
          <DatePicker value={dueDate} onChange={setDueDate} placeholder="Pick a date" />
        </label>
        <label className="flex flex-col gap-1">
          <span className="eyebrow">Priority</span>
          <Select<Priority>
            value={priority}
            onChange={setPriority}
            options={[
              { value: 'low', label: 'Low' },
              { value: 'normal', label: 'Normal' },
              { value: 'high', label: 'High' },
            ]}
            ariaLabel="Priority"
          />
        </label>
      </div>
      {campaignName && (
        <div className="mono mt-2" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
          Saving to campaign ·{' '}
          <span style={{ color: 'var(--accent)' }}>{campaignName}</span>
        </div>
      )}
      {error && (
        <div style={{ color: 'var(--plum)', fontSize: 12, marginTop: 8 }}>{error}</div>
      )}
      <div className="flex items-center justify-between mt-3">
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
          {modifierSymbol === '⌘' ? '⌘↵' : 'Ctrl+↵'} to save
        </span>
        <div className="flex items-center gap-2">
          {onDelete && (
            <button
              type="button"
              onClick={() => void handleDelete()}
              disabled={deleting || saving}
              aria-label="Delete todo"
              title="Delete todo"
              style={{
                ...secondaryBtn,
                color: 'var(--plum)',
                cursor: deleting ? 'wait' : 'pointer',
                opacity: deleting ? 0.7 : 1,
              }}
            >
              <Trash2 size={13} strokeWidth={1.8} />
              {deleting ? 'Deleting…' : 'Delete'}
            </button>
          )}
          <button
            type="button"
            onClick={() => void submit()}
            disabled={saving || deleting}
            style={{
              ...primaryBtn,
              cursor: saving ? 'wait' : 'pointer',
              opacity: saving ? 0.7 : 1,
            }}
          >
            {saving ? 'Saving…' : submitLabel}
          </button>
        </div>
      </div>
    </>
  );
}

function lastUnescapedAt(text: string, caret: number): number {
  for (let i = caret - 1; i >= 0; i -= 1) {
    const ch = text[i];
    if (ch === '@') {
      const prev = i === 0 ? ' ' : text[i - 1];
      if (/\s/.test(prev) || i === 0) return i;
      return -1;
    }
    if (/\s/.test(ch)) return -1;
  }
  return -1;
}

function extractMentions(body: string): Mention[] {
  const results: Mention[] = [];
  const seen = new Set<string>();
  const re = /\[\[([a-z-]+):([^\]|]+?)(?:\|([^\]]+?))?\]\]/g;
  for (const match of body.matchAll(re)) {
    const [, type, slug, label] = match;
    const key = `${type}:${slug}`;
    if (seen.has(key)) continue;
    seen.add(key);
    results.push({
      type: type as Mention['type'],
      slug,
      label: (label ?? slug).trim(),
    });
  }
  return results;
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  padding: '7px 10px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--border)',
  background: 'var(--bg-elev)',
  color: 'var(--text)',
  fontSize: 13,
};

const EDITOR_FONT = 'inherit';
const EDITOR_LINE_HEIGHT = 1.5;
const EDITOR_FONT_SIZE = 13;
const EDITOR_PADDING = '7px 10px';

const editorTextareaStyle: React.CSSProperties = {
  fontFamily: EDITOR_FONT,
  fontSize: EDITOR_FONT_SIZE,
  lineHeight: EDITOR_LINE_HEIGHT,
  padding: EDITOR_PADDING,
  color: 'transparent',
  caretColor: 'var(--text)',
  position: 'relative',
  zIndex: 2,
  background: 'transparent',
};

const overlayStyle: React.CSSProperties = {
  position: 'absolute',
  inset: 0,
  pointerEvents: 'none',
  padding: EDITOR_PADDING,
  fontFamily: EDITOR_FONT,
  fontSize: EDITOR_FONT_SIZE,
  lineHeight: EDITOR_LINE_HEIGHT,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  color: 'var(--text)',
  overflow: 'hidden',
  borderRadius: 'var(--radius)',
  border: '1px solid transparent',
  zIndex: 1,
  background: 'var(--bg-elev)',
};

const chipStyle: React.CSSProperties = {
  display: 'inline',
  padding: '1px 6px',
  margin: '0 1px',
  borderRadius: 6,
  background: 'var(--accent-soft)',
  color: 'var(--accent)',
  fontSize: 11.5,
  fontWeight: 500,
  lineHeight: 1.4,
  whiteSpace: 'nowrap',
};

const primaryBtn: React.CSSProperties = {
  padding: '7px 13px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'var(--accent)',
  color: 'var(--bg-elev)',
  fontSize: 12,
  fontWeight: 500,
};

const secondaryBtn: React.CSSProperties = {
  padding: '7px 11px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--border)',
  background: 'transparent',
  color: 'var(--text-3)',
  fontSize: 12,
  fontWeight: 500,
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
};
