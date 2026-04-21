import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Briefcase, Calendar, CalendarPlus, ExternalLink, FileText } from 'lucide-react';
import { api } from '../api/client';
import PageHeader from '../components/shell/PageHeader';
import BackLink from '../components/shell/BackLink';
import InlineMarkdown from '../components/shell/InlineMarkdown';

type Application = {
  id: number;
  company: string;
  role: string;
  status: string;
  applied_date: string;
  notes: string;
  resume_variant: string;
  url: string;
  job_description: string;
  created_at?: string;
  updated_at?: string;
};

type Round = {
  id: number;
  application_id: number;
  round_type: string;
  date: string;
  interviewer: string;
  notes: string;
  result: string;
};

const STATUS_OPTIONS = ['Wishlist', 'Applied', 'Interviewing', 'Offer', 'Rejected'];

const STATUS_COLORS: Record<string, { bg: string; fg: string }> = {
  Wishlist: { bg: 'var(--paper-3)', fg: 'var(--text-3)' },
  Applied: { bg: 'var(--ochre-soft)', fg: 'var(--ochre)' },
  Interviewing: { bg: 'var(--accent-soft)', fg: 'var(--accent)' },
  Offer: { bg: 'var(--forest-soft)', fg: 'var(--forest)' },
  Rejected: { bg: 'var(--plum-soft)', fg: 'var(--plum)' },
};

export default function ApplicationDetail() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [app, setApp] = useState<Application | null>(null);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState('');

  useEffect(() => {
    if (!slug) return;
    Promise.all([
      api.get<Application>(`/api/applications/${slug}`),
      api.get<Round[]>(`/api/applications/${slug}/rounds`).catch(() => []),
    ])
      .then(([a, rs]) => {
        setApp(a);
        setStatus(a.status);
        setRounds(rs);
      })
      .finally(() => setLoading(false));
  }, [slug]);

  if (loading) {
    return (
      <div
        className="h-full flex items-center justify-center"
        style={{ color: 'var(--text-4)', fontSize: 13 }}
      >
        Loading…
      </div>
    );
  }

  if (!app) {
    return (
      <div className="h-full overflow-y-auto">
        <div className="px-8 pt-5">
          <BackLink to="/applications" label="All applications" />
        </div>
        <div
          className="flex items-center justify-center h-full"
          style={{ color: 'var(--text-3)', fontSize: 13 }}
        >
          Application not found.
        </div>
      </div>
    );
  }

  async function updateStatus(next: string) {
    if (!app || next === app.status) return;
    setSaving(true);
    setStatus(next);
    try {
      const saved = await api.put<Application>(`/api/applications/${app.id}`, {
        company: app.company,
        role: app.role,
        status: next,
        applied_date: app.applied_date,
        notes: app.notes,
        resume_variant: app.resume_variant,
        url: app.url,
        job_description: app.job_description,
      });
      setApp(saved);
    } catch {
      setStatus(app.status);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="px-8 pt-5">
        <BackLink to="/applications" label="All applications" />
      </div>

      <PageHeader
        eyebrow={`Track · Application · ${app.company}`}
        title={app.role}
        subtitle={`Everything you've captured about ${app.company} — status, role detail, prepped rounds, and the notes you want near you before the next conversation.`}
      >
        <button
          type="button"
          onClick={() => navigate(`/interviews/new?applicationId=${app.id}`)}
          className="inline-flex items-center gap-1.5"
          style={primaryBtn}
        >
          <CalendarPlus size={14} strokeWidth={1.7} />
          Schedule a round
        </button>
      </PageHeader>

      <div
        className="px-8 py-6 grid gap-5"
        style={{ gridTemplateColumns: 'minmax(0, 1fr) 320px' }}
      >
        <div className="flex flex-col gap-5">
          <div className="card p-6">
            <div className="eyebrow mb-3">Company</div>
            <div className="flex items-baseline gap-3 flex-wrap">
              <span
                className="display-italic"
                style={{ fontSize: 36, fontWeight: 400, lineHeight: 1.05 }}
              >
                {app.company}
              </span>
              {(() => {
                const c = STATUS_COLORS[app.status] ?? STATUS_COLORS.Applied;
                return (
                  <span
                    className="pill"
                    style={{ background: c.bg, color: c.fg }}
                  >
                    {app.status.toLowerCase()}
                  </span>
                );
              })()}
            </div>

            <div
              className="grid gap-6 mt-5"
              style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}
            >
              <Meta label="Role" value={app.role} Icon={Briefcase} />
              <Meta
                label="Applied"
                value={app.applied_date || '—'}
                Icon={Calendar}
                mono
              />
              <Meta
                label="Resume"
                value={app.resume_variant || '—'}
                Icon={FileText}
                mono
              />
              {app.url ? (
                <a
                  href={app.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex flex-col gap-1.5"
                  style={{ textDecoration: 'none' }}
                >
                  <span className="eyebrow inline-flex items-center gap-1.5">
                    <ExternalLink size={11} strokeWidth={1.7} />
                    Posting
                  </span>
                  <span
                    className="mono truncate"
                    style={{ color: 'var(--accent)', fontSize: 12 }}
                  >
                    {prettyUrl(app.url)}
                  </span>
                </a>
              ) : (
                <Meta label="Posting" value="—" Icon={ExternalLink} mono />
              )}
            </div>
          </div>

          <div className="card p-6">
            <div className="eyebrow mb-3">Job description</div>
            {app.job_description.trim() ? (
              <InlineMarkdown
                as="div"
                text={app.job_description}
                style={{
                  fontSize: 14,
                  color: 'var(--text-2)',
                  lineHeight: 1.7,
                  whiteSpace: 'pre-wrap',
                }}
              />
            ) : (
              <p
                style={{
                  margin: 0,
                  fontSize: 13,
                  color: 'var(--text-4)',
                  lineHeight: 1.6,
                  fontStyle: 'italic',
                }}
              >
                No job description on file. Paste the role description when you edit this
                application — it'll anchor prep to the actual asks.
              </p>
            )}
          </div>

          {app.notes.trim() && (
            <div className="card p-6">
              <div className="eyebrow mb-3">Notes</div>
              <InlineMarkdown
                as="div"
                text={app.notes}
                style={{
                  fontSize: 13.5,
                  color: 'var(--text-2)',
                  lineHeight: 1.65,
                  whiteSpace: 'pre-wrap',
                }}
              />
            </div>
          )}

          <div className="card p-6">
            <div className="flex items-center justify-between mb-3">
              <div className="eyebrow">Rounds</div>
              <button
                type="button"
                onClick={() => navigate(`/interviews/new?applicationId=${app.id}`)}
                className="mono uppercase inline-flex items-center gap-1"
                style={{
                  background: 'transparent',
                  border: 0,
                  color: 'var(--accent)',
                  fontSize: 10.5,
                  letterSpacing: '0.12em',
                  cursor: 'pointer',
                  padding: 0,
                }}
              >
                <CalendarPlus size={12} strokeWidth={1.7} />
                Schedule
              </button>
            </div>
            {rounds.length === 0 ? (
              <div
                style={{
                  fontSize: 13,
                  color: 'var(--text-4)',
                  lineHeight: 1.55,
                  fontStyle: 'italic',
                }}
              >
                No rounds scheduled yet. When you put one on the calendar, the dashboard will
                surface prep tailored to the round type.
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {rounds.map((r, i) => (
                  <div
                    key={r.id}
                    className="flex justify-between items-center"
                    style={{
                      padding: '12px 14px',
                      borderRadius: 'var(--radius)',
                      background: 'var(--bg-sunken)',
                      boxShadow: 'inset 0 0 0 1px var(--border)',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 500 }}>
                        <span
                          className="mono"
                          style={{
                            color: 'var(--text-4)',
                            marginRight: 8,
                            fontSize: 10.5,
                          }}
                        >
                          {String(i + 1).padStart(2, '0')}
                        </span>
                        {r.round_type}
                      </div>
                      <div
                        style={{ fontSize: 11.5, color: 'var(--text-3)', marginTop: 2 }}
                      >
                        {r.interviewer || 'Interviewer TBD'}
                      </div>
                    </div>
                    <span
                      className="mono"
                      style={{ fontSize: 11, color: 'var(--text-3)' }}
                    >
                      {r.date || '—'}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <aside className="flex flex-col gap-4">
          <div className="card p-5">
            <div className="eyebrow mb-3">Status</div>
            <div className="flex flex-col gap-1.5">
              {STATUS_OPTIONS.map((opt) => {
                const active = status === opt;
                const c = STATUS_COLORS[opt] ?? STATUS_COLORS.Applied;
                return (
                  <button
                    key={opt}
                    type="button"
                    onClick={() => updateStatus(opt)}
                    disabled={saving}
                    className="flex items-center justify-between"
                    style={{
                      padding: '8px 12px',
                      border: 0,
                      borderRadius: 'var(--radius)',
                      background: active ? c.bg : 'transparent',
                      boxShadow: active ? 'none' : 'inset 0 0 0 1px var(--border)',
                      color: active ? c.fg : 'var(--text-2)',
                      fontSize: 12.5,
                      fontWeight: active ? 500 : 400,
                      cursor: saving ? 'wait' : 'pointer',
                      textAlign: 'left' as const,
                    }}
                  >
                    <span>{opt}</span>
                    {active && (
                      <span
                        style={{
                          width: 6,
                          height: 6,
                          borderRadius: 999,
                          background: c.fg,
                        }}
                      />
                    )}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="card p-5">
            <div className="eyebrow mb-2.5">Activity</div>
            <Row
              label="Rounds scheduled"
              value={String(rounds.length)}
            />
            <Row
              label="Last updated"
              value={
                app.updated_at
                  ? new Date(app.updated_at).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                    })
                  : '—'
              }
            />
            <Row
              label="Created"
              value={
                app.created_at
                  ? new Date(app.created_at).toLocaleDateString(undefined, {
                      month: 'short',
                      day: 'numeric',
                    })
                  : '—'
              }
              last
            />
          </div>

          <Link
            to={`/interviews/new?applicationId=${app.id}`}
            className="card card-hover inline-flex items-center justify-between"
            style={{
              padding: '14px 18px',
              textDecoration: 'none',
              color: 'var(--accent)',
              fontSize: 13,
              fontWeight: 500,
            }}
          >
            <span>Schedule a round</span>
            <CalendarPlus size={14} strokeWidth={1.7} />
          </Link>
        </aside>
      </div>
    </div>
  );
}

function Meta({
  label,
  value,
  Icon,
  mono,
}: {
  label: string;
  value: string;
  Icon: (p: { size?: number; strokeWidth?: number }) => React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1.5 min-w-0">
      <span className="eyebrow inline-flex items-center gap-1.5">
        <Icon size={11} strokeWidth={1.7} />
        {label}
      </span>
      <span
        className={mono ? 'mono truncate' : 'truncate'}
        style={{ fontSize: 13, color: 'var(--text)' }}
      >
        {value}
      </span>
    </div>
  );
}

function Row({ label, value, last }: { label: string; value: string; last?: boolean }) {
  return (
    <div
      className="flex justify-between py-2.5 gap-3"
      style={{ borderBottom: last ? 'none' : '1px solid var(--border)' }}
    >
      <span style={{ fontSize: 12, color: 'var(--text-3)' }}>{label}</span>
      <span className="mono" style={{ fontSize: 12, color: 'var(--text)' }}>
        {value}
      </span>
    </div>
  );
}

function prettyUrl(url: string) {
  try {
    const u = new URL(url);
    return u.host + u.pathname.replace(/\/$/, '');
  } catch {
    return url;
  }
}

const primaryBtn: React.CSSProperties = {
  padding: '8px 14px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'var(--accent)',
  color: 'var(--bg-elev)',
  fontSize: 12.5,
  fontWeight: 500,
  cursor: 'pointer',
};
