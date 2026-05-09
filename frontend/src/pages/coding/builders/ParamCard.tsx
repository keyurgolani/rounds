// ParamCard — visual shell wrapping a single parameter editor in the
// Run tab's custom-input section. Header carries the param name + a type
// chip + per-param Reset / Raw toggles; body is the type-appropriate
// editor; optional footer surfaces inline validation or a structural
// preview (e.g. "Tree: 5 nodes, depth 3").
//
// All visual chrome lives here so the underlying editors stay focused on
// data and don't each reinvent labelling.

import type { ReactNode } from 'react';
import type { TypeName } from '../types';

interface ParamCardProps {
  name: string;
  type: TypeName | string;
  edited: boolean;
  rawMode: boolean;
  onToggleRaw: () => void;
  onReset: () => void;
  /** Optional small line under the type chip — e.g. "5 nodes, depth 3" or
      a validation message. */
  footer?: ReactNode;
  footerTone?: 'muted' | 'warn' | 'error';
  highlight?: boolean;
  cardId?: string;
  children: ReactNode;
}

export function ParamCard({
  name,
  type,
  edited,
  rawMode,
  onToggleRaw,
  onReset,
  footer,
  footerTone = 'muted',
  highlight,
  cardId,
  children,
}: ParamCardProps) {
  const footerColor =
    footerTone === 'error'
      ? 'var(--plum)'
      : footerTone === 'warn'
        ? 'var(--ochre)'
        : 'var(--text-4)';

  return (
    <section
      id={cardId}
      style={{
        background: 'var(--bg)',
        border: highlight
          ? '1px solid var(--accent)'
          : '1px solid var(--border)',
        borderRadius: 8,
        boxShadow: highlight
          ? '0 0 0 3px var(--accent-soft)'
          : 'none',
        transition: 'box-shadow 160ms, border-color 160ms',
      }}
    >
      <header
        className="flex items-center gap-2 flex-wrap"
        style={{
          padding: '8px 10px',
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-elev)',
          borderRadius: '8px 8px 0 0',
        }}
      >
        <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text)' }}>
          {name}
        </span>
        <TypeChip type={type} />
        {edited && (
          <span
            className="mono"
            style={{ fontSize: 10, color: 'var(--accent)' }}
          >
            ●
          </span>
        )}
        <span style={{ flex: 1 }} />
        {edited && (
          <button
            type="button"
            onClick={onReset}
            className="mono"
            style={{
              fontSize: 10.5,
              padding: '2px 6px',
              border: 0,
              background: 'transparent',
              color: 'var(--text-4)',
              cursor: 'pointer',
              textDecoration: 'underline',
              textDecorationColor: 'var(--border-strong)',
            }}
            title="Reset this param to its sample value"
          >
            Reset
          </button>
        )}
        <button
          type="button"
          onClick={onToggleRaw}
          aria-pressed={rawMode}
          className="mono"
          style={{
            fontSize: 10.5,
            padding: '2px 8px',
            border: '1px solid var(--border)',
            borderRadius: 999,
            background: rawMode ? 'var(--accent-soft)' : 'transparent',
            color: rawMode ? 'var(--accent)' : 'var(--text-3)',
            cursor: 'pointer',
          }}
          title={rawMode ? 'Switch to visual editor' : 'Edit as raw JSON'}
        >
          {rawMode ? 'Visual' : 'Raw'}
        </button>
      </header>
      <div style={{ padding: 10 }}>{children}</div>
      {footer && (
        <footer
          className="mono"
          style={{
            padding: '6px 10px',
            fontSize: 10.5,
            color: footerColor,
            borderTop: '1px solid var(--border)',
            background: 'var(--bg-sunken)',
            borderRadius: '0 0 8px 8px',
          }}
        >
          {footer}
        </footer>
      )}
    </section>
  );
}

function TypeChip({ type }: { type: TypeName | string }) {
  return (
    <span
      className="mono"
      style={{
        padding: '1px 7px',
        fontSize: 10,
        background: 'var(--bg-sunken)',
        color: 'var(--text-3)',
        border: '1px solid var(--border)',
        borderRadius: 999,
        whiteSpace: 'nowrap',
      }}
    >
      {type}
    </span>
  );
}
