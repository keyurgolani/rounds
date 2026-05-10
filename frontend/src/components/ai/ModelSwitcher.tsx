import { useEffect, useId, useMemo, useRef, useState } from 'react';
import { Check, ChevronDown, Cpu, Search } from 'lucide-react';
import type { AICodingModel } from '../../pages/ai-coding/aiCodingApi';

export type ModelOverride = { provider_id: string; model: string } | null;

type Props = {
  models: AICodingModel[];
  value: ModelOverride;
  onChange: (next: ModelOverride) => void;
  disabled?: boolean;
  /** When true, the trigger expands to fill its container instead of
   *  hugging its content. Used in the AI chat header so the picker
   *  takes over the full row width when the rail is wide. */
  fullWidth?: boolean;
};

const SEP = '::';

/**
 * Polished, theme-aware model picker. Replaces the previous native
 * `<select>` so the dropdown can be fully styled (provider grouping,
 * selected check, hover highlight, app fonts) and so it can grow to
 * full-width inside the chat-rail header. Keyboard: Enter/Space opens,
 * Esc closes, click-outside dismisses.
 */
export default function ModelSwitcher({
  models,
  value,
  onChange,
  disabled,
  fullWidth = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const wrapRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const listId = useId();

  // De-dupe, filter by query, then group by provider for the menu.
  const grouped = useMemo(() => {
    const q = query.trim().toLowerCase();
    const seen = new Set<string>();
    const ordered: AICodingModel[] = [];
    for (const m of models) {
      const key = `${m.provider_id}${SEP}${m.model}`;
      if (seen.has(key)) continue;
      seen.add(key);
      if (q) {
        const hay = `${m.provider_label} ${m.model} ${m.kind ?? ''}`.toLowerCase();
        if (!hay.includes(q)) continue;
      }
      ordered.push(m);
    }
    const byProvider = new Map<string, { label: string; items: AICodingModel[] }>();
    for (const m of ordered) {
      const cur = byProvider.get(m.provider_id);
      if (cur) cur.items.push(m);
      else byProvider.set(m.provider_id, { label: m.provider_label, items: [m] });
    }
    return byProvider;
  }, [models, query]);

  const currentKey = value ? `${value.provider_id}${SEP}${value.model}` : '';
  const currentLabel = useMemo(() => {
    if (!value) return 'Default model';
    const m = models.find(
      (x) => x.provider_id === value.provider_id && x.model === value.model,
    );
    return m ? `${m.provider_label} · ${m.model}` : value.model;
  }, [models, value]);

  // Click-outside to dismiss.
  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (!wrapRef.current) return;
      if (!wrapRef.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false);
    }
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  // Reset the filter and focus the search box on each open so users can
  // start typing immediately instead of clicking the input first.
  useEffect(() => {
    if (!open) {
      setQuery('');
      return;
    }
    const t = window.setTimeout(() => searchRef.current?.focus(), 30);
    return () => window.clearTimeout(t);
  }, [open]);

  function pick(m: AICodingModel | null) {
    if (m === null) onChange(null);
    else onChange({ provider_id: m.provider_id, model: m.model });
    setOpen(false);
  }

  return (
    <div
      ref={wrapRef}
      style={{ position: 'relative', minWidth: 0, flex: fullWidth ? 1 : 'initial' }}
    >
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-label="AI model"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        className="inline-flex items-center"
        style={{
          width: fullWidth ? '100%' : 'auto',
          maxWidth: fullWidth ? undefined : 240,
          gap: 6,
          height: 28,
          padding: '0 6px 0 10px',
          background: open ? 'var(--bg-sunken)' : 'var(--bg)',
          color: 'var(--text-2)',
          border: 0,
          borderRadius: 8,
          boxShadow: open
            ? 'inset 0 0 0 1px var(--accent)'
            : 'inset 0 0 0 1px var(--border-strong)',
          cursor: disabled ? 'default' : 'pointer',
          fontSize: 12,
          fontWeight: 500,
          opacity: disabled ? 0.5 : 1,
          minWidth: 0,
        }}
      >
        <Cpu size={12} strokeWidth={1.8} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
        <span
          style={{
            flex: 1,
            minWidth: 0,
            textAlign: 'left',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {currentLabel}
        </span>
        <ChevronDown
          size={12}
          strokeWidth={1.8}
          style={{
            color: 'var(--text-3)',
            flexShrink: 0,
            transform: open ? 'rotate(180deg)' : 'none',
            transition: 'transform 140ms',
          }}
        />
      </button>

      {open && (
        <div
          id={listId}
          role="listbox"
          aria-label="AI model"
          style={{
            position: 'absolute',
            top: 'calc(100% + 4px)',
            left: 0,
            right: 0,
            minWidth: 240,
            zIndex: 50,
            background: 'var(--bg-elev)',
            borderRadius: 10,
            boxShadow:
              'inset 0 0 0 1px var(--border), 0 12px 28px -12px rgba(0,0,0,0.32)',
            padding: 4,
            maxHeight: 320,
            overflow: 'auto',
          }}
        >
          <div
            style={{
              position: 'sticky',
              top: 0,
              padding: 4,
              background: 'var(--bg-elev)',
              borderBottom: '1px solid var(--border)',
              marginBottom: 4,
              zIndex: 1,
            }}
          >
            <div
              className="flex items-center"
              style={{
                gap: 6,
                padding: '4px 8px',
                background: 'var(--bg)',
                borderRadius: 6,
                boxShadow: 'inset 0 0 0 1px var(--border)',
              }}
            >
              <Search size={11} strokeWidth={1.8} style={{ color: 'var(--text-4)' }} />
              <input
                ref={searchRef}
                aria-label="Filter models"
                placeholder="Search models…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                style={{
                  flex: 1,
                  background: 'transparent',
                  border: 0,
                  outline: 'none',
                  color: 'var(--text)',
                  fontSize: 12,
                  fontFamily: 'var(--font-sans)',
                  padding: 0,
                }}
              />
            </div>
          </div>
          {!query && (
            <Item
              label="Default model"
              sub="Use the application default"
              selected={!currentKey}
              onClick={() => pick(null)}
            />
          )}
          {grouped.size === 0 && (
            <div
              style={{
                padding: '10px 8px',
                fontSize: 12,
                color: 'var(--text-4)',
                textAlign: 'center',
              }}
            >
              No models match "{query}"
            </div>
          )}
          {[...grouped.entries()].map(([providerId, { label, items }]) => (
            <div key={providerId} style={{ marginTop: 4 }}>
              <div
                className="eyebrow"
                style={{
                  padding: '6px 8px 2px',
                  color: 'var(--text-4)',
                  letterSpacing: '0.1em',
                  fontSize: 9.5,
                }}
              >
                {label}
              </div>
              {items.map((m) => {
                const key = `${m.provider_id}${SEP}${m.model}`;
                return (
                  <Item
                    key={key}
                    label={m.model}
                    sub={m.kind ? m.kind.toUpperCase() : undefined}
                    selected={currentKey === key}
                    onClick={() => pick(m)}
                  />
                );
              })}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Item({
  label,
  sub,
  selected,
  onClick,
}: {
  label: string;
  sub?: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      role="option"
      aria-selected={selected}
      onClick={onClick}
      className="flex items-center"
      style={{
        gap: 8,
        width: '100%',
        textAlign: 'left',
        padding: '6px 8px',
        background: selected ? 'var(--accent-soft)' : 'transparent',
        color: selected ? 'var(--accent)' : 'var(--text-2)',
        border: 0,
        borderRadius: 6,
        cursor: 'pointer',
        fontSize: 12,
        fontWeight: selected ? 600 : 500,
      }}
      onMouseEnter={(e) => {
        if (selected) return;
        (e.currentTarget as HTMLButtonElement).style.background = 'var(--bg-sunken)';
      }}
      onMouseLeave={(e) => {
        if (selected) return;
        (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
      }}
    >
      <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {label}
      </span>
      {sub && (
        <span
          className="mono"
          style={{
            fontSize: 9.5,
            color: 'var(--text-4)',
            letterSpacing: '0.06em',
          }}
        >
          {sub}
        </span>
      )}
      {selected && <Check size={12} strokeWidth={2} />}
    </button>
  );
}
