import { useEffect, useMemo, useRef, useState } from 'react';
import { ArrowLeft, X, Search } from 'lucide-react';
import { useCommandCenter } from './CommandCenterProvider';
import { registry, type CommandView } from './registry';

export function CommandCenter() {
  const cc = useCommandCenter();
  const [query, setQuery] = useState('');

  useEffect(() => {
    if (!cc.isOpen) setQuery('');
  }, [cc.isOpen, cc.viewId]);

  useEffect(() => {
    if (!cc.isOpen) return;
    function onKey(e: KeyboardEvent) {
      // Skip if a child handler already handled Escape (e.g. closing a
      // popover, dismissing autocomplete, or the form's own cancel).
      // Without this guard the global handler stacks on top of the
      // child handler and ends up calling cc.back() one step too far.
      if (e.key === 'Escape' && !e.defaultPrevented) {
        e.preventDefault();
        cc.back();
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [cc.isOpen, cc]);

  useEffect(() => {
    if (!cc.isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [cc.isOpen]);

  if (!cc.isOpen) return null;

  const view: CommandView | undefined = cc.viewId
    ? registry.find((v) => v.id === cc.viewId)
    : undefined;
  const inView = !!cc.viewId;

  return (
    <div
      data-testid="cc-backdrop"
      onClick={cc.close}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.35)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: 80,
        paddingBottom: 80,
        zIndex: 100,
      }}
    >
      <div
        role="dialog"
        aria-label="Command Center"
        onClick={(e) => e.stopPropagation()}
        className="card"
        style={{
          width: 'min(640px, calc(100vw - 32px))',
          // Leave the same 80px breathing room at the bottom as the
          // backdrop's paddingTop above.
          maxHeight: 'calc(100vh - 160px)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
          boxShadow: 'var(--shadow-elev)',
        }}
      >
        <ModalHeader inView={inView} viewLabel={view?.label} />
        {inView ? (
          <ViewBody view={view} />
        ) : (
          <Hub query={query} onQueryChange={setQuery} />
        )}
      </div>
    </div>
  );
}

function ModalHeader({ inView, viewLabel }: { inView: boolean; viewLabel?: string }) {
  const cc = useCommandCenter();
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '12px 14px',
        borderBottom: '1px solid var(--border)',
      }}
    >
      {inView && (
        <button
          type="button"
          onClick={cc.back}
          aria-label="Back to Command Center"
          className="inline-flex items-center justify-center"
          style={{
            width: 28, height: 28, borderRadius: 6,
            border: 0, background: 'transparent', color: 'var(--text-2)',
            cursor: 'pointer',
          }}
        >
          <ArrowLeft size={16} strokeWidth={1.7} />
        </button>
      )}
      <div className="display-italic" style={{ fontSize: 16, color: 'var(--text)' }}>
        {inView ? viewLabel : 'Command Center'}
      </div>
      <div style={{ flex: 1 }} />
      <button
        type="button"
        onClick={cc.close}
        aria-label="Close Command Center"
        className="inline-flex items-center justify-center"
        style={{
          width: 28, height: 28, borderRadius: 6,
          border: 0, background: 'transparent', color: 'var(--text-3)',
          cursor: 'pointer',
        }}
      >
        <X size={16} strokeWidth={1.7} />
      </button>
    </div>
  );
}

function Hub({ query, onQueryChange }: { query: string; onQueryChange: (q: string) => void }) {
  const cc = useCommandCenter();
  const q = query.trim().toLowerCase();
  const filtered = useMemo(
    () =>
      q
        ? registry.filter(
            (v) =>
              v.label.toLowerCase().includes(q) ||
              (v.description ?? '').toLowerCase().includes(q),
          )
        : registry,
    [q],
  );

  const [selected, setSelected] = useState(0);
  const itemRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    setSelected(0);
  }, [q]);

  useEffect(() => {
    if (filtered.length === 0) return;
    if (selected >= filtered.length) setSelected(filtered.length - 1);
  }, [filtered.length, selected]);

  function handleInputKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (filtered.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelected((i) => (i + 1) % filtered.length);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelected((i) => (i - 1 + filtered.length) % filtered.length);
    } else if (e.key === 'Enter' || (e.key === ' ' && q === '')) {
      // Enter activates selection. Space activates only when the input
      // is empty (so users can still type spaces in their search).
      e.preventDefault();
      const view = filtered[selected];
      if (view) cc.openView(view.id);
    } else if (e.key === 'Home') {
      e.preventDefault();
      setSelected(0);
    } else if (e.key === 'End') {
      e.preventDefault();
      setSelected(filtered.length - 1);
    }
  }

  useEffect(() => {
    const node = itemRefs.current[selected];
    // jsdom doesn't implement scrollIntoView — skip when missing.
    if (typeof node?.scrollIntoView === 'function') {
      node.scrollIntoView({ block: 'nearest' });
    }
  }, [selected]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: 0 }}>
      <div
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 14px', borderBottom: '1px solid var(--border)',
        }}
      >
        <Search size={14} strokeWidth={1.7} style={{ color: 'var(--text-4)' }} />
        <input
          autoFocus
          placeholder="Search the Command Center"
          value={query}
          onChange={(e) => onQueryChange(e.target.value)}
          onKeyDown={handleInputKey}
          aria-activedescendant={
            filtered[selected] ? `cc-item-${filtered[selected].id}` : undefined
          }
          style={{
            flex: 1, border: 0, outline: 'none',
            background: 'transparent', color: 'var(--text)', fontSize: 13.5,
          }}
        />
      </div>
      <div role="listbox" style={{ overflowY: 'auto', padding: 8 }}>
        {filtered.length === 0 ? (
          <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-4)', fontSize: 12.5 }}>
            No actions {q ? 'match this search' : 'available yet'}.
          </div>
        ) : (
          filtered.map((v, i) => (
            <HubButton
              key={v.id}
              view={v}
              selected={i === selected}
              onHover={() => setSelected(i)}
              onClick={() => cc.openView(v.id)}
              buttonRef={(el) => {
                itemRefs.current[i] = el;
              }}
            />
          ))
        )}
      </div>
    </div>
  );
}

function HubButton({
  view,
  onClick,
  onHover,
  selected,
  buttonRef,
}: {
  view: CommandView;
  onClick: () => void;
  onHover: () => void;
  selected: boolean;
  buttonRef: (el: HTMLButtonElement | null) => void;
}) {
  return (
    <button
      type="button"
      ref={buttonRef}
      id={`cc-item-${view.id}`}
      role="option"
      aria-selected={selected}
      onClick={onClick}
      onMouseEnter={onHover}
      tabIndex={-1}
      className="card card-hover w-full text-left"
      style={{
        display: 'flex', alignItems: 'center', gap: 12,
        padding: '10px 12px', marginBottom: 6,
        border: 0, cursor: 'pointer',
        background: selected ? 'var(--bg-sunken)' : undefined,
        boxShadow: selected ? 'inset 0 0 0 1px var(--accent)' : undefined,
      }}
    >
      {view.icon && (
        <span
          className="inline-flex items-center justify-center flex-shrink-0"
          style={{
            width: 28, height: 28, borderRadius: 6,
            background: selected ? 'var(--accent-soft)' : 'var(--bg-sunken)',
            color: selected ? 'var(--accent)' : 'var(--text-2)',
          }}
        >
          {view.icon}
        </span>
      )}
      <span style={{ minWidth: 0, flex: 1 }}>
        <span style={{ display: 'block', fontSize: 13, fontWeight: 500 }}>{view.label}</span>
        {view.description && (
          <span style={{ display: 'block', fontSize: 11.5, color: 'var(--text-4)' }}>
            {view.description}
          </span>
        )}
      </span>
    </button>
  );
}

function ViewBody({ view }: { view?: CommandView }) {
  const cc = useCommandCenter();
  if (!view) {
    return (
      <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-4)', fontSize: 12.5 }}>
        View not found.
      </div>
    );
  }
  const Body = view.Component;
  return (
    <div style={{ overflowY: 'auto', padding: 14 }}>
      <Body onComplete={cc.close} />
    </div>
  );
}
