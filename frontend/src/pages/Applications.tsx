import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, CalendarPlus, ChevronRight, Plus } from 'lucide-react';
import {
  listApplications,
  listRounds,
  type Application,
  type InterviewRound,
} from '../applications/api';
import { slugify } from '../lib/slug';
import AppHeader from '../components/shell/AppHeader';
import PageShell from '../components/shell/PageShell';
import Select from '../components/shell/Select';
import { usePersistedState } from '../hooks/usePersistedState';
import RoundsList from '../applications/RoundsList';
import InlineAddRound from '../applications/InlineAddRound';

/** Statuses where the round list should default to expanded — these
 *  are "ongoing" applications the user is actively working on. The
 *  other statuses (Offer, Rejected) are terminal and collapse by
 *  default to keep the list scannable. Either way the user can
 *  toggle and we persist their choice. */
const ONGOING_STATUSES = new Set(['Wishlist', 'Applied', 'Interviewing']);

type App = Application;

const statuses = [
  { key: 'Wishlist', color: 'var(--text-3)' },
  { key: 'Applied', color: 'var(--ochre)' },
  { key: 'Interviewing', color: 'var(--accent)' },
  { key: 'Offer', color: 'var(--forest)' },
  { key: 'Rejected', color: 'var(--plum)' },
];

type SortKey =
  | 'recent-desc'
  | 'recent-asc'
  | 'applied-desc'
  | 'applied-asc'
  | 'company-asc'
  | 'company-desc';

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'recent-desc', label: 'Recently updated' },
  { value: 'recent-asc', label: 'Least recent first' },
  { value: 'applied-desc', label: 'Applied (newest)' },
  { value: 'applied-asc', label: 'Applied (oldest)' },
  { value: 'company-asc', label: 'Company (A–Z)' },
  { value: 'company-desc', label: 'Company (Z–A)' },
];

export default function Applications() {
  const navigate = useNavigate();
  const [apps, setApps] = useState<App[]>([]);
  /** rounds keyed by application_id. We fetch them in parallel after
   *  the apps list resolves; missing entries mean "not loaded yet"
   *  (the row renders a small skeleton instead of "0 rounds"). */
  const [roundsByApp, setRoundsByApp] = useState<Record<string, InterviewRound[]>>({});
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = usePersistedState<string | null>('rounds.apps.statusFilter', null);
  const [sort, setSort] = usePersistedState<SortKey>('rounds.apps.sort', 'recent-desc');
  /** Per-application expansion override. Status drives the default;
   *  this map records intentional user toggles so the choice sticks
   *  across reloads and beyond a status change. */
  const [expandedOverride, setExpandedOverride] = usePersistedState<
    Record<string, boolean>
  >('rounds.apps.expanded', {});
  useEffect(() => {
    listApplications()
      .then(async (xs) => {
        setApps(xs);
        // Fan-out rounds load. Per-app cost is one PB filter query; with
        // ~20 apps in flight in parallel this is plenty fast and keeps
        // the code simple. We don't await before showing apps — they
        // render immediately, rounds fill in as they arrive.
        const entries = await Promise.all(
          xs.map(async (a) => {
            try {
              const rs = await listRounds(a.id);
              return [a.id, rs] as const;
            } catch {
              return [a.id, [] as InterviewRound[]] as const;
            }
          }),
        );
        setRoundsByApp(Object.fromEntries(entries));
      })
      .finally(() => setLoading(false));
  }, []);

  const isExpanded = useCallback(
    (app: App): boolean => {
      const override = expandedOverride[app.id];
      if (typeof override === 'boolean') return override;
      return ONGOING_STATUSES.has(app.status);
    },
    [expandedOverride],
  );

  const toggleExpanded = useCallback(
    (app: App) => {
      setExpandedOverride((prev) => ({
        ...prev,
        [app.id]: !isExpanded(app),
      }));
    },
    [isExpanded, setExpandedOverride],
  );

  const handleScheduled = useCallback(
    (appId: string, created: InterviewRound[]) => {
      setRoundsByApp((prev) => ({
        ...prev,
        [appId]: [...(prev[appId] ?? []), ...created],
      }));
      // Force-expand the row whose round was just scheduled so the
      // user sees the new entry land where they expect.
      setExpandedOverride((prev) => ({ ...prev, [appId]: true }));
    },
    [setExpandedOverride],
  );

  const hasData = apps.length > 0;

  const filtered = useMemo(() => {
    const matches = apps.filter((a) => {
      if (statusFilter && a.status !== statusFilter) return false;
      if (query.trim()) {
        const s = query.trim().toLowerCase();
        const blob = `${a.company} ${a.role} ${a.notes ?? ''}`.toLowerCase();
        if (!blob.includes(s)) return false;
      }
      return true;
    });
    const sorted = [...matches];
    const updatedKey = (a: App) => a.last_activity_at ?? a.updated_at ?? '';
    sorted.sort((a, b) => {
      switch (sort) {
        case 'recent-asc':
          return updatedKey(a).localeCompare(updatedKey(b)) || a.company.localeCompare(b.company);
        case 'applied-desc':
          return (b.applied_date || '').localeCompare(a.applied_date || '') ||
            a.company.localeCompare(b.company);
        case 'applied-asc':
          return (a.applied_date || '').localeCompare(b.applied_date || '') ||
            a.company.localeCompare(b.company);
        case 'company-asc':
          return a.company.localeCompare(b.company);
        case 'company-desc':
          return b.company.localeCompare(a.company);
        case 'recent-desc':
        default:
          return updatedKey(b).localeCompare(updatedKey(a)) || a.company.localeCompare(b.company);
      }
    });
    return sorted;
  }, [apps, query, statusFilter, sort]);

  return (
    <PageShell
      header={
        <>
          <AppHeader
            eyebrow="Track · Pipeline"
            title="Applications"
            description="Every company you're pursuing, from wishlist to offer. Track rounds, interviewers, and outcomes in one place."
            chromeActions={
              <Link to="/applications/new" className="inline-flex items-center gap-1.5" style={{ ...primaryBtn, padding: '6px 14px', borderRadius: 8 }}>
                <Plus size={13} strokeWidth={1.8} />
                New application
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
                  placeholder="Search company, role, notes…"
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
                  {([null, ...statuses.map((s) => s.key)] as (string | null)[]).map((k) => (
                    <button
                      key={String(k)}
                      type="button"
                      onClick={() => setStatusFilter(k)}
                      style={{
                        padding: '7px 12px',
                        border: 0,
                        borderRadius: 999,
                        background: statusFilter === k ? 'var(--ink)' : 'transparent',
                        color: statusFilter === k ? 'var(--paper)' : 'var(--text-3)',
                        boxShadow:
                          statusFilter === k
                            ? 'none'
                            : 'inset 0 0 0 1px var(--border-strong)',
                        fontSize: 11.5,
                        fontWeight: 500,
                        cursor: 'pointer',
                      }}
                    >
                      {k ?? 'All'}
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
                  {filtered.length} OF {apps.length} APPS
                </span>
              </div>
            </div>
          )}
        </>
      }
    >
      <div className="px-5 sm:px-8 py-5">
        <div
          className="grid gap-2.5 mb-5"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))' }}
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
          filtered.length === 0 ? (
            <div
              className="card p-8 text-center"
              style={{ color: 'var(--text-4)', fontSize: 13 }}
            >
              No applications match that filter.
            </div>
          ) : (
            <div className="card overflow-hidden">
              {filtered.map((a, i) => (
                <ApplicationRow
                  key={a.id}
                  app={a}
                  last={i === filtered.length - 1}
                  rounds={roundsByApp[a.id]}
                  expanded={isExpanded(a)}
                  onToggleExpanded={() => toggleExpanded(a)}
                  onRoundCreated={(round) => handleScheduled(a.id, [round])}
                  onRoundUpdated={(next) =>
                    setRoundsByApp((prev) => ({
                      ...prev,
                      [next.application_id]: (prev[next.application_id] ?? []).map(
                        (r) => (r.id === next.id ? next : r),
                      ),
                    }))
                  }
                  onRoundDeleted={(id) =>
                    setRoundsByApp((prev) => ({
                      ...prev,
                      [a.id]: (prev[a.id] ?? []).filter((r) => r.id !== id),
                    }))
                  }
                />
              ))}
            </div>
          )
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
    </PageShell>
  );
}

/**
 * One application + its embedded rounds list. The header row stays a
 * clickable Link to the detail page (so muscle memory still works);
 * the chevron button is the explicit toggle for the rounds drawer
 * underneath, and it stops propagation so the click doesn't navigate.
 */
function ApplicationRow({
  app,
  last,
  rounds,
  expanded,
  onToggleExpanded,
  onRoundCreated,
  onRoundUpdated,
  onRoundDeleted,
}: {
  app: App;
  last: boolean;
  /** undefined = "not loaded yet" (skeleton), [] = "loaded but none". */
  rounds: InterviewRound[] | undefined;
  expanded: boolean;
  onToggleExpanded: () => void;
  onRoundCreated: (round: InterviewRound) => void;
  onRoundUpdated: (next: InterviewRound) => void;
  onRoundDeleted: (id: string) => void;
}) {
  const existingLoopLabels = Array.from(
    new Set((rounds ?? []).map((r) => r.loop_label).filter(Boolean)),
  ).sort();
  const slug = slugify(`${app.company} ${app.role}`) || app.id;
  const hasRounds = !!rounds && rounds.length > 0;
  return (
    <div
      style={{
        borderBottom: last ? 'none' : '1px solid var(--border)',
      }}
    >
      <div
        className="flex md:grid items-start md:items-center gap-2 md:gap-3 transition-colors flex-col md:flex-row"
        style={{
          gridTemplateColumns: '24px 1fr 150px 120px auto',
          padding: '14px 16px',
        }}
      >
        <button
          type="button"
          onClick={onToggleExpanded}
          aria-expanded={expanded}
          aria-label={
            expanded
              ? `Collapse rounds for ${app.company}`
              : `Expand rounds for ${app.company}`
          }
          title={
            rounds === undefined
              ? 'Loading rounds…'
              : hasRounds
                ? `${rounds.length} round${rounds.length === 1 ? '' : 's'}`
                : 'No rounds scheduled yet'
          }
          style={{
            width: 24,
            height: 24,
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            background: 'transparent',
            border: 0,
            cursor: 'pointer',
            color: 'var(--text-3)',
            padding: 0,
            borderRadius: 4,
          }}
        >
          <ChevronRight
            size={14}
            strokeWidth={2}
            style={{
              transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
              transition: 'transform 120ms',
            }}
          />
        </button>
        <Link
          to={`/applications/${slug}`}
          className="min-w-0 flex-1"
          style={{
            textDecoration: 'none',
            color: 'var(--text)',
          }}
        >
          <div style={{ fontSize: 14, fontWeight: 500 }}>{app.company}</div>
          <div style={{ fontSize: 12, color: 'var(--text-3)' }}>{app.role}</div>
        </Link>
        <StatusPill status={app.status} />
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>
          {app.applied_date || '—'}
        </span>
        <div className="flex items-center gap-1">
          {rounds !== undefined && (
            <span
              className="mono"
              style={{
                fontSize: 10.5,
                color: 'var(--text-4)',
                letterSpacing: '0.08em',
                marginRight: 6,
              }}
              aria-hidden="true"
            >
              {rounds.length} {rounds.length === 1 ? 'ROUND' : 'ROUNDS'}
            </span>
          )}
          <Link
            to={`/applications/${slug}`}
            aria-label={`Open ${app.company} application`}
            style={{
              color: 'var(--text-4)',
              display: 'inline-flex',
              padding: '4px',
              marginLeft: 4,
              textDecoration: 'none',
              borderRadius: 4,
            }}
          >
            <ArrowRight size={13} strokeWidth={1.7} />
          </Link>
        </div>
      </div>
      {expanded && (
        <div
          style={{
            padding: '0 16px 14px 50px',
            background: 'var(--bg-elev)',
            borderTop: '1px solid var(--border)',
          }}
        >
          {rounds === undefined ? (
            <div
              style={{
                padding: '12px 0',
                fontSize: 12,
                color: 'var(--text-4)',
                fontStyle: 'italic',
              }}
            >
              Loading rounds…
            </div>
          ) : (
            <div
              style={{
                padding: '12px 0 4px',
                display: 'flex',
                flexDirection: 'column',
                gap: 10,
              }}
            >
              {rounds.length > 0 && (
                <RoundsList
                  rounds={rounds}
                  onUpdated={onRoundUpdated}
                  onDeleted={onRoundDeleted}
                />
              )}
              <InlineAddRound
                applicationId={app.id}
                existingLoopLabels={existingLoopLabels}
                onCreated={onRoundCreated}
              />
            </div>
          )}
        </div>
      )}
    </div>
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
