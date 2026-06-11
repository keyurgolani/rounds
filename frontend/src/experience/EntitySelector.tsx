import { useRef, useEffect, useState } from 'react';
import type { LucideProps } from 'lucide-react';
import { Briefcase, FolderKanban, MessageSquareQuote, ListChecks } from 'lucide-react';
import type { EntityKind } from './experienceApi';

const OPTIONS: Array<{
  kind: EntityKind;
  label: string;
  description: string;
  icon: React.ComponentType<LucideProps>;
  color: string;
}> = [
  {
    kind: 'job',
    label: 'Job',
    description: 'Where you worked and what role',
    icon: Briefcase,
    color: 'var(--ink)',
  },
  {
    kind: 'project',
    label: 'Project',
    description: 'What you built and the impact',
    icon: FolderKanban,
    color: 'var(--ochre)',
  },
  {
    kind: 'anecdote',
    label: 'Anecdote',
    description: 'A STAR story from your career',
    icon: MessageSquareQuote,
    color: 'var(--accent)',
  },
  {
    kind: 'bullet',
    label: 'Bullet',
    description: 'A quantified achievement',
    icon: ListChecks,
    color: 'var(--forest)',
  },
];

interface Props {
  onSelect: (kind: EntityKind) => void;
  onClose: () => void;
}

export default function EntitySelector({ onSelect, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) onClose();
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [onClose]);

  return (
    <div
      ref={ref}
      className="card"
      style={{
        position: 'absolute',
        top: 'calc(100% + 8px)',
        right: 0,
        zIndex: 50,
        width: 280,
        boxShadow: 'var(--shadow-elev)',
        padding: 8,
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
      }}
    >
      <div className="mono px-2 py-1" style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}>
        ADD ENTITY
      </div>
      {OPTIONS.map((opt) => {
        const Icon = opt.icon;
        return (
          <button
            key={opt.kind}
            type="button"
            onClick={() => onSelect(opt.kind)}
            className="flex items-center gap-3 text-left w-full"
            style={{
              padding: '10px 12px',
              border: 0,
              borderRadius: 'var(--radius)',
              background: 'transparent',
              cursor: 'pointer',
              transition: 'background 120ms',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--bg-sunken)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'transparent';
            }}
          >
            <span
              className="inline-flex items-center justify-center flex-shrink-0"
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: opt.color + '18',
                color: opt.color,
              }}
            >
              <Icon size={16} />
            </span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text)' }}>{opt.label}</div>
              <div style={{ fontSize: 11.5, color: 'var(--text-3)' }}>{opt.description}</div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
