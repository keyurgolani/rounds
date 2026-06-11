import type { TimelineEntity } from './experienceApi';

const TYPE_COLORS: Record<TimelineEntity['kind'], { bg: string; text: string }> = {
  anecdote: { bg: 'var(--accent-soft)', text: 'var(--accent)' },
  bullet: { bg: 'var(--forest-soft)', text: 'var(--forest)' },
  project: { bg: 'var(--ochre-soft)', text: 'var(--ochre)' },
  job: { bg: 'var(--ink-soft)', text: 'var(--ink)' },
};

const TYPE_LABELS: Record<TimelineEntity['kind'], string> = {
  anecdote: 'Anecdote',
  bullet: 'Bullet',
  project: 'Project',
  job: 'Job',
};

function formatDate(entity: TimelineEntity): string {
  if (entity.kind === 'job' || entity.kind === 'project') {
    const s = new Date(entity.start_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    if (!entity.end_date) return `${s} – Present`;
    const e = new Date(entity.end_date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    return `${s} – ${e}`;
  }
  return new Date(entity.date).toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
}

type Size = 'small' | 'medium' | 'large';

function cardSize(kind: TimelineEntity['kind']): Size {
  if (kind === 'bullet') return 'small';
  if (kind === 'anecdote') return 'medium';
  return 'large';
}

interface Props {
  item: TimelineEntity;
  onClick: () => void;
}

export default function TimelineCard({ item, onClick }: Props) {
  const size = cardSize(item.kind);
  const colors = TYPE_COLORS[item.kind];

  const title = item.kind === 'job' ? item.company : item.title;
  const subtitle = item.kind === 'job' ? item.role : undefined;

  return (
    <button
      type="button"
      onClick={onClick}
      className="card card-hover text-left w-full"
      style={{
        padding: size === 'small' ? '10px 14px' : size === 'medium' ? '14px 18px' : '18px 22px',
        borderLeft: `3px solid ${colors.text}`,
        cursor: 'pointer',
        background: 'var(--bg-elev)',
      }}
    >
      <div className="flex items-center gap-2 flex-wrap" style={{ marginBottom: size === 'small' ? 2 : 6 }}>
        <span
          className="pill mono"
          style={{
            fontSize: 9,
            letterSpacing: '0.08em',
            background: colors.bg,
            color: colors.text,
            padding: '2px 8px',
          }}
        >
          {TYPE_LABELS[item.kind].toUpperCase()}
        </span>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
          {formatDate(item)}
        </span>
      </div>

      <div
        style={{
          fontSize: size === 'small' ? 13 : size === 'medium' ? 15 : 17,
          fontWeight: size === 'small' ? 500 : 600,
          color: 'var(--text)',
          lineHeight: 1.3,
          marginBottom: size === 'small' ? 0 : 4,
        }}
      >
        {title}
      </div>

      {subtitle && (
        <div style={{ fontSize: 12.5, color: 'var(--text-2)', marginTop: 2 }}>
          {subtitle}
        </div>
      )}

      {size !== 'small' && item.kind !== 'job' && 'description' in item && item.description && (
        <p
          className="line-clamp-2"
          style={{
            fontSize: 13,
            color: 'var(--text-3)',
            lineHeight: 1.5,
            margin: 0,
          }}
        >
          {item.description}
        </p>
      )}

      {size !== 'small' && item.kind === 'project' && item.company && (
        <div style={{ fontSize: 12.5, color: 'var(--text-2)', marginTop: 4 }}>
          {item.company}
          {item.role && ` · ${item.role}`}
        </div>
      )}

      {item.tags.length > 0 && size !== 'small' && (
        <div className="flex flex-wrap gap-1" style={{ marginTop: 8 }}>
          {item.tags.slice(0, 4).map((tag) => (
            <span
              key={tag}
              className="pill"
              style={{
                fontSize: 10,
                background: 'transparent',
                color: 'var(--text-4)',
                boxShadow: 'inset 0 0 0 1px var(--border)',
                padding: '1px 7px',
              }}
            >
              {tag}
            </span>
          ))}
        </div>
      )}
    </button>
  );
}
