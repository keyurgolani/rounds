import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, CalendarPlus, Plus } from 'lucide-react';
import { api } from '../api/client';
import { slugify } from '../lib/slug';
import PageHeader from '../components/shell/PageHeader';

type App = {
  id: number;
  company: string;
  role: string;
  status: string;
  applied_date: string;
  notes: string;
  url: string;
};

const statuses = [
  { key: 'Wishlist', color: 'var(--text-3)' },
  { key: 'Applied', color: 'var(--ochre)' },
  { key: 'Interviewing', color: 'var(--accent)' },
  { key: 'Offer', color: 'var(--forest)' },
  { key: 'Rejected', color: 'var(--plum)' },
];

export default function Applications() {
  const navigate = useNavigate();
  const [apps, setApps] = useState<App[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .get<App[]>('/api/applications')
      .then(setApps)
      .finally(() => setLoading(false));
  }, []);

  const hasData = apps.length > 0;

  return (
    <div className="h-full overflow-y-auto">
      <PageHeader
        eyebrow="Track · Pipeline"
        title="Applications"
        subtitle="Every company you're pursuing, from wishlist to offer. Track rounds, interviewers, and outcomes in one place."
      >
        <Link to="/applications/new" className="inline-flex items-center gap-1.5" style={primaryBtn}>
          <Plus size={13} strokeWidth={1.8} />
          New application
        </Link>
      </PageHeader>

      <div className="px-8 py-5">
        <div
          className="grid gap-2.5 mb-5"
          style={{ gridTemplateColumns: `repeat(${statuses.length}, 1fr)` }}
        >
          {statuses.map((s) => (
            <div key={s.key} className="card p-3.5">
              <div className="flex items-center gap-2 mb-2">
                <span
                  style={{ width: 8, height: 8, borderRadius: 999, background: s.color }}
                />
                <span className="eyebrow" style={{ fontSize: 9.5 }}>
                  {s.key}
                </span>
              </div>
              <div
                className="display"
                style={{
                  fontSize: 28,
                  fontWeight: 400,
                  color: hasData ? 'var(--text)' : 'var(--text-4)',
                }}
              >
                {apps.filter((a) => a.status === s.key).length}
              </div>
            </div>
          ))}
        </div>

        {loading ? (
          <div className="card p-8 text-center" style={{ color: 'var(--text-3)' }}>
            Loading…
          </div>
        ) : hasData ? (
          <div className="card overflow-hidden">
            {apps.map((a, i) => (
              <ApplicationRow
                key={a.id}
                app={a}
                last={i === apps.length - 1}
                onSchedule={() => navigate(`/interviews/new?applicationId=${a.id}`)}
              />
            ))}
          </div>
        ) : (
          <EmptyPanel
            illustration={<PaperStackIllustration />}
            title="No applications yet"
            body="Add your first company to start tracking rounds, interviewers, and outcomes. Questions you practice can be linked to each role."
            primary={{
              label: 'Add a company',
              onClick: () => navigate('/applications/new'),
            }}
            tip="Add a role before your first interview — Rounds will surface relevant questions on Today."
          />
        )}
      </div>
    </div>
  );
}

function ApplicationRow({
  app,
  last,
  onSchedule,
}: {
  app: App;
  last: boolean;
  onSchedule: () => void;
}) {
  return (
    <Link
      to={`/applications/${slugify(`${app.company} ${app.role}`) || app.id}`}
      className="grid items-center gap-3 transition-colors"
      style={{
        gridTemplateColumns: '1fr 150px 120px auto',
        padding: '14px 18px',
        borderBottom: last ? 'none' : '1px solid var(--border)',
        textDecoration: 'none',
        color: 'var(--text)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'var(--bg-sunken)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'transparent';
      }}
    >
      <div className="min-w-0">
        <div style={{ fontSize: 14, fontWeight: 500 }}>{app.company}</div>
        <div style={{ fontSize: 12, color: 'var(--text-3)' }}>{app.role}</div>
      </div>
      <StatusPill status={app.status} />
      <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>
        {app.applied_date || '—'}
      </span>
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onSchedule();
          }}
          className="inline-flex items-center gap-1.5"
          aria-label={`Schedule a round for ${app.company}`}
          style={{
            padding: '6px 10px',
            border: 0,
            borderRadius: 'var(--radius)',
            background: 'transparent',
            boxShadow: 'inset 0 0 0 1px var(--border-strong)',
            color: 'var(--text-2)',
            fontSize: 11.5,
            fontWeight: 500,
            cursor: 'pointer',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--bg-elev)';
            e.currentTarget.style.color = 'var(--accent)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'transparent';
            e.currentTarget.style.color = 'var(--text-2)';
          }}
        >
          <CalendarPlus size={12} strokeWidth={1.7} />
          Round
        </button>
        <span style={{ color: 'var(--text-4)', display: 'inline-flex', marginLeft: 4 }}>
          <ArrowRight size={13} strokeWidth={1.7} />
        </span>
      </div>
    </Link>
  );
}

function StatusPill({ status }: { status: string }) {
  const color = statuses.find((s) => s.key === status)?.color ?? 'var(--text-3)';
  return (
    <span
      className="pill"
      style={{
        background: 'transparent',
        color,
        boxShadow: `inset 0 0 0 1px ${color}`,
      }}
    >
      {status.toLowerCase()}
    </span>
  );
}

function EmptyPanel({
  illustration,
  title,
  body,
  primary,
  tip,
}: {
  illustration: React.ReactNode;
  title: string;
  body: string;
  primary: { label: string; onClick: () => void };
  tip?: string;
}) {
  return (
    <div
      className="card text-center"
      style={{ padding: '56px 32px', background: 'var(--bg-elev)' }}
    >
      <div className="flex justify-center mb-4 opacity-90">{illustration}</div>
      <div
        className="display-italic"
        style={{ fontSize: 30, fontWeight: 400, marginBottom: 8 }}
      >
        {title}
      </div>
      <p
        style={{
          margin: '0 auto',
          fontSize: 13.5,
          color: 'var(--text-3)',
          maxWidth: 440,
          lineHeight: 1.55,
        }}
      >
        {body}
      </p>
      <div className="flex justify-center gap-2.5 mt-5">
        <button type="button" onClick={primary.onClick} style={primaryBtn}>
          {primary.label}
        </button>
      </div>
      {tip && (
        <div
          className="mono mt-5"
          style={{ fontSize: 11.5, color: 'var(--text-4)', letterSpacing: '0.02em' }}
        >
          TIP · {tip}
        </div>
      )}
    </div>
  );
}

function PaperStackIllustration() {
  return (
    <svg viewBox="0 0 120 84" width="120" height="84" fill="none" aria-hidden="true">
      <rect
        x="18"
        y="20"
        width="74"
        height="54"
        rx="4"
        fill="var(--bg-sunken)"
        stroke="var(--border-strong)"
        strokeWidth="1"
        transform="rotate(-4 55 47)"
      />
      <rect
        x="24"
        y="14"
        width="74"
        height="54"
        rx="4"
        fill="var(--bg-elev)"
        stroke="var(--border-strong)"
        strokeWidth="1"
        transform="rotate(3 61 41)"
      />
      <rect
        x="22"
        y="18"
        width="74"
        height="54"
        rx="4"
        fill="var(--bg-elev)"
        stroke="var(--border-strong)"
        strokeWidth="1"
      />
      <line x1="30" y1="30" x2="70" y2="30" stroke="var(--text-4)" strokeWidth="1.4" strokeLinecap="round" />
      <line x1="30" y1="38" x2="82" y2="38" stroke="var(--text-4)" strokeWidth="1.4" strokeLinecap="round" opacity="0.6" />
      <line x1="30" y1="46" x2="66" y2="46" stroke="var(--text-4)" strokeWidth="1.4" strokeLinecap="round" opacity="0.4" />
      <circle cx="88" cy="60" r="6" fill="var(--accent)" opacity="0.15" />
      <path
        d="M85 60 L87.5 62.5 L91 58.5"
        stroke="var(--accent)"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

const primaryBtn: React.CSSProperties = {
  padding: '8px 14px',
  borderRadius: 6,
  border: 0,
  background: 'var(--accent)',
  color: 'var(--bg-elev)',
  fontSize: 12.5,
  fontWeight: 500,
  cursor: 'pointer',
};
