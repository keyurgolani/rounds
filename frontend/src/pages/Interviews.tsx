import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import AppHeader from '../components/shell/AppHeader';
import PageShell from '../components/shell/PageShell';
import Select from '../components/shell/Select';

type App = { id: number; company: string; role: string; status: string };
type Round = {
  id: number;
  application_id: number;
  round_type: string;
  date: string;
  interviewer: string;
  notes: string;
  result: string;
};

const interviewTypes = [
  { key: 'phone', label: 'Phone / recruiter screen' },
  { key: 'coding', label: 'Coding round' },
  { key: 'system', label: 'System design' },
  { key: 'behavioral', label: 'Behavioral / leadership' },
  { key: 'onsite', label: 'On-site / panel' },
];

const TYPE_FILTERS = [
  { key: null as string | null, label: 'All' },
  { key: 'phone', label: 'Phone' },
  { key: 'coding', label: 'Coding' },
  { key: 'system', label: 'System' },
  { key: 'behavioral', label: 'Behavioral' },
  { key: 'onsite', label: 'Onsite' },
];

type SortKey = 'date-asc' | 'date-desc' | 'company-asc' | 'company-desc';

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'date-asc', label: 'Date (soonest first)' },
  { value: 'date-desc', label: 'Date (latest first)' },
  { value: 'company-asc', label: 'Company (A–Z)' },
  { value: 'company-desc', label: 'Company (Z–A)' },
];

function parseDate(s: string): Date | null {
  if (!s) return null;
  const d = new Date(s);
  return isNaN(d.getTime()) ? null : d;
}

export default function Interviews() {
  const [apps, setApps] = useState<App[]>([]);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [sort, setSort] = useState<SortKey>('date-asc');

  useEffect(() => {
    async function load() {
      try {
        const appList = await api.get<App[]>('/api/applications').catch(() => []);
        setApps(appList);
        const perApp = await Promise.all(
          appList.map((a) =>
            api.get<Round[]>(`/api/applications/${a.id}/rounds`).catch(() => []),
          ),
        );
        setRounds(perApp.flat());
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const now = new Date();
  const matchesQuery = (r: Round) => {
    if (typeFilter && !r.round_type.toLowerCase().includes(typeFilter)) return false;
    if (query.trim()) {
      const s = query.trim().toLowerCase();
      const app = apps.find((a) => a.id === r.application_id);
      const blob = `${app?.company ?? ''} ${app?.role ?? ''} ${r.round_type} ${r.interviewer ?? ''} ${r.notes ?? ''}`.toLowerCase();
      if (!blob.includes(s)) return false;
    }
    return true;
  };
  const sortRounds = (arr: Round[]) => {
    const out = [...arr];
    out.sort((a, b) => {
      switch (sort) {
        case 'date-desc':
          return (b.date || '').localeCompare(a.date || '');
        case 'company-asc': {
          const ac = apps.find((x) => x.id === a.application_id)?.company ?? '';
          const bc = apps.find((x) => x.id === b.application_id)?.company ?? '';
          return ac.localeCompare(bc);
        }
        case 'company-desc': {
          const ac = apps.find((x) => x.id === a.application_id)?.company ?? '';
          const bc = apps.find((x) => x.id === b.application_id)?.company ?? '';
          return bc.localeCompare(ac);
        }
        case 'date-asc':
        default:
          return (a.date || '').localeCompare(b.date || '');
      }
    });
    return out;
  };
  const upcomingRaw = rounds.filter((r) => {
    const d = parseDate(r.date);
    return d && d.getTime() >= now.getTime() - 12 * 60 * 60 * 1000;
  });
  const pastRaw = rounds.filter((r) => {
    const d = parseDate(r.date);
    return d && d.getTime() < now.getTime() - 12 * 60 * 60 * 1000;
  });
  const upcoming = useMemo(
    () => sortRounds(upcomingRaw.filter(matchesQuery)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [upcomingRaw, query, typeFilter, sort, apps],
  );
  const past = useMemo(
    () => sortRounds(pastRaw.filter(matchesQuery)),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [pastRaw, query, typeFilter, sort, apps],
  );
  const totalMatching = upcoming.length + past.length;
  const hasData = rounds.length > 0;

  return (
    <PageShell
      header={
        <>
          <AppHeader
            eyebrow="Track · Schedule"
            title="Interviews"
            description="Your upcoming rounds and past debriefs. Each round can link to the questions you expect, the anecdotes you'll use, and the notes you wrote afterward."
            actions={
              <Link
                to="/interviews/new"
                style={{
                  padding: '6px 14px',
                  borderRadius: 8,
                  border: 0,
                  background: 'var(--accent)',
                  color: 'var(--bg-elev)',
                  fontSize: 12.5,
                  fontWeight: 500,
                  textDecoration: 'none',
                }}
              >
                + Schedule round
              </Link>
            }
          />
          {hasData && (
            <div
              className="flex-shrink-0 px-5 sm:px-8 pt-4 pb-2"
              style={{ background: 'var(--bg)' }}
            >
              <div className="flex flex-wrap gap-2 items-center">
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search company, round type, interviewer…"
                  className="mono"
                  style={{
                    flex: '1 1 240px',
                    padding: '9px 12px',
                    background: 'var(--bg-elev)',
                    boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                    borderRadius: 'var(--radius)',
                    border: 0,
                    fontSize: 12.5,
                    color: 'var(--text)',
                    outline: 'none',
                  }}
                />
                <div className="flex gap-1.5 flex-wrap">
                  {TYPE_FILTERS.map((t) => (
                    <button
                      key={String(t.key)}
                      type="button"
                      onClick={() => setTypeFilter(t.key)}
                      style={{
                        padding: '7px 12px',
                        border: 0,
                        borderRadius: 999,
                        background: typeFilter === t.key ? 'var(--ink)' : 'transparent',
                        color: typeFilter === t.key ? 'var(--paper)' : 'var(--text-3)',
                        boxShadow:
                          typeFilter === t.key
                            ? 'none'
                            : 'inset 0 0 0 1px var(--border-strong)',
                        fontSize: 11.5,
                        fontWeight: 500,
                        cursor: 'pointer',
                      }}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
                <div style={{ minWidth: 200 }}>
                  <Select<SortKey>
                    value={sort}
                    onChange={setSort}
                    options={SORT_OPTIONS}
                    ariaLabel="Sort"
                    align="right"
                  />
                </div>
                <span
                  className="mono ml-auto"
                  style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}
                >
                  {totalMatching} OF {rounds.length} ROUNDS
                </span>
              </div>
            </div>
          )}
        </>
      }
    >
      <div className="px-5 sm:px-8 py-5">
        <div className="grid gap-5 grid-cols-1 lg:[grid-template-columns:2fr_1fr]">
          <section>
            <div className="eyebrow mb-3">Upcoming</div>
            {loading ? (
              <div className="card p-8 text-center" style={{ color: 'var(--text-3)' }}>
                Loading…
              </div>
            ) : upcoming.length ? (
              <RoundList rounds={upcoming} apps={apps} />
            ) : (
              <EmptyPanel
                illustration={<CalendarIllustration />}
                title="Nothing on the calendar"
                body="When you schedule a round, it'll appear here with prep materials tailored to the interview type — coding, system design, or behavioral."
                compact
              />
            )}

            {past.length > 0 && (
              <>
                <div className="eyebrow mt-8 mb-3">Past</div>
                <RoundList rounds={past} apps={apps} muted />
              </>
            )}
          </section>

          <aside>
            <div className="eyebrow mb-3">This cycle</div>
            <div className="card p-4">
              {[
                ['Rounds completed', String(past.length)],
                ['Total scheduled', String(rounds.length)],
                ['Upcoming this week', String(upcoming.length)],
              ].map(([k, v]) => (
                <div
                  key={k}
                  className="flex justify-between py-2.5"
                  style={{ borderBottom: '1px solid var(--border)' }}
                >
                  <span style={{ fontSize: 12.5, color: 'var(--text-3)' }}>{k}</span>
                  <span className="mono" style={{ fontSize: 12, color: 'var(--text)' }}>
                    {v}
                  </span>
                </div>
              ))}
            </div>

            <div className="eyebrow" style={{ margin: '24px 0 12px' }}>
              Interview types
            </div>
            <div className="flex flex-col gap-1.5">
              {interviewTypes.map((t) => {
                const count = rounds.filter((r) =>
                  r.round_type.toLowerCase().includes(t.key)
                ).length;
                return (
                  <div
                    key={t.key}
                    className="flex items-center gap-2.5"
                    style={{
                      padding: '10px 12px',
                      borderRadius: 6,
                      background: 'var(--bg-elev)',
                      boxShadow: '0 0 0 1px var(--border)',
                    }}
                  >
                    <span
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: 999,
                        background: 'var(--accent)',
                      }}
                    />
                    <span style={{ fontSize: 12.5 }}>{t.label}</span>
                    <span
                      className="mono"
                      style={{ marginLeft: 'auto', fontSize: 10.5, color: 'var(--text-4)' }}
                    >
                      {count}
                    </span>
                  </div>
                );
              })}
            </div>
          </aside>
        </div>
      </div>
    </PageShell>
  );
}

function RoundList({
  rounds,
  apps,
  muted,
}: {
  rounds: Round[];
  apps: App[];
  muted?: boolean;
}) {
  return (
    <div className="flex flex-col gap-2.5" style={{ opacity: muted ? 0.75 : 1 }}>
      {rounds.map((r) => {
        const app = apps.find((a) => a.id === r.application_id);
        return (
          <Link
            key={r.id}
            to={`/interviews/${r.id}`}
            className="card card-hover p-4"
            style={{ textDecoration: 'none', color: 'inherit' }}
          >
            <div className="flex justify-between items-center">
              <div>
                <div style={{ fontSize: 14, fontWeight: 500 }}>
                  {app?.company ?? 'Unknown'} · {r.round_type}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>
                  {r.interviewer || 'Interviewer TBD'}
                </div>
              </div>
              <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>
                {r.date || '—'}
              </span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}

function EmptyPanel({
  illustration,
  title,
  body,
  compact,
}: {
  illustration: React.ReactNode;
  title: string;
  body: string;
  compact?: boolean;
}) {
  return (
    <div
      className="card text-center"
      style={{ padding: compact ? '40px 28px' : '56px 32px', background: 'var(--bg-elev)' }}
    >
      <div className="flex justify-center mb-4 opacity-90">{illustration}</div>
      <div
        className="display-italic"
        style={{ fontSize: compact ? 24 : 30, fontWeight: 400, marginBottom: 8 }}
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
    </div>
  );
}

function CalendarIllustration() {
  return (
    <svg viewBox="0 0 120 84" width="120" height="84" fill="none" aria-hidden="true">
      <rect
        x="22"
        y="18"
        width="76"
        height="58"
        rx="4"
        fill="var(--bg-elev)"
        stroke="var(--border-strong)"
        strokeWidth="1"
      />
      <path d="M22 30 H98" stroke="var(--border-strong)" strokeWidth="1" />
      <line x1="38" y1="14" x2="38" y2="24" stroke="var(--text-3)" strokeWidth="2" strokeLinecap="round" />
      <line x1="82" y1="14" x2="82" y2="24" stroke="var(--text-3)" strokeWidth="2" strokeLinecap="round" />
      {[0, 1, 2, 3].map((r) =>
        [0, 1, 2, 3, 4].map((c) => (
          <circle
            key={`${r}-${c}`}
            cx={32 + c * 14}
            cy={40 + r * 10}
            r="1.6"
            fill="var(--text-4)"
            opacity={0.5 - r * 0.08}
          />
        ))
      )}
      <circle cx="74" cy="50" r="7" fill="var(--accent)" opacity="0.15" />
      <circle cx="74" cy="50" r="2.5" fill="var(--accent)" />
    </svg>
  );
}
