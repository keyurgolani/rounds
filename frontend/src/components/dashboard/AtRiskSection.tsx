import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Award, Calendar, ChevronRight, Clock } from 'lucide-react';
import {
  getOffer,
  listApplications,
  listRounds,
  type Offer,
} from '../../applications/api';
import { useCampaign } from '../../campaign/CampaignContext';
import { listTodos, type Todo } from '../../todos/api';
import { splitBody } from '../../lib/mentions';

function todoSummary(t: Todo): string {
  return splitBody(t.body)
    .map((c) => (c.kind === 'text' ? c.text : c.mention.label))
    .join('')
    .trim();
}

interface RawApp {
  id: string;
  company: string;
  role: string;
  status: string;
  last_activity_at?: string;
  updated_at?: string;
}

interface RawRound {
  id: string;
  application_id: string;
  date: string;
  scheduled_status?: string;
}

type RawOffer = Pick<Offer, 'id' | 'application_id' | 'status' | 'decision_deadline'>;

// Thresholds live on the client — cheap to compute, easy to tweak.
const STALE_APP_DAYS = 10;
const STALE_ROUND_HORIZON_DAYS = 14;
const OFFER_DEADLINE_HORIZON_DAYS = 3;

export default function AtRiskSection() {
  const { currentId } = useCampaign();
  const [todos, setTodos] = useState<Todo[]>([]);
  const [apps, setApps] = useState<RawApp[]>([]);
  const [rounds, setRounds] = useState<RawRound[]>([]);
  const [offers, setOffers] = useState<RawOffer[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [todosResp, appsResp] = await Promise.all([
        listTodos(currentId ?? undefined).catch(() => [] as Todo[]),
        listApplications(currentId ?? undefined).catch(() => [] as RawApp[]),
      ]);

      setTodos(todosResp);
      setApps(appsResp);

      // Rounds and offers are per-application; fetch them in parallel
      // so the dashboard lands quickly even with a dozen apps in flight.
      const [roundsLists, offersPerApp] = await Promise.all([
        Promise.all(appsResp.map((a) => listRounds(a.id).catch(() => [] as RawRound[]))),
        Promise.all(appsResp.map((a) => getOffer(a.id).catch(() => null))),
      ]);
      setRounds(roundsLists.flat());
      setOffers(offersPerApp.filter((o): o is Offer => !!o));
    } finally {
      setLoading(false);
    }
  }, [currentId]);

  useEffect(() => {
    void load();
    function onChange() {
      void load();
    }
    window.addEventListener('rounds:todos-changed', onChange);
    return () => window.removeEventListener('rounds:todos-changed', onChange);
  }, [load]);

  const { overdueTodos, staleApps, pendingOffers } = useMemo(
    () => compute(todos, apps, rounds, offers),
    [todos, apps, rounds, offers],
  );

  const total = overdueTodos.length + staleApps.length + pendingOffers.length;
  if (loading && total === 0) return null;
  if (!loading && total === 0) return null;

  return (
    <section className="fade-up" style={{ marginTop: 44 }}>
      <div
        className="flex items-center gap-2 mb-3"
        style={{ color: 'var(--plum)' }}
      >
        <AlertTriangle size={14} strokeWidth={1.8} />
        <span
          className="eyebrow"
          style={{ color: 'var(--plum)', fontSize: 11, letterSpacing: '0.12em' }}
        >
          Needs attention
        </span>
        <span
          className="mono"
          style={{ fontSize: 10.5, color: 'var(--text-4)', marginLeft: 4 }}
        >
          {total}
        </span>
      </div>
      <div
        className="grid gap-3"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}
      >
        {overdueTodos.length > 0 && (
          <RiskCard
            title="Overdue todos"
            Icon={Clock}
            seeMore={{ to: '/todos', label: 'Open todos' }}
          >
            {overdueTodos.slice(0, 5).map((t) => (
              <RiskRow
                key={t.id}
                to="/todos"
                primary={todoSummary(t)}
                secondary={t.due_date || 'no date'}
                reason={`Due ${t.due_date}`}
              />
            ))}
            {overdueTodos.length > 5 && (
              <MoreLink to="/todos" label={`+${overdueTodos.length - 5} more`} />
            )}
          </RiskCard>
        )}

        {staleApps.length > 0 && (
          <RiskCard
            title="Stale applications"
            Icon={Calendar}
            seeMore={{ to: '/applications', label: 'Open applications' }}
          >
            {staleApps.slice(0, 5).map((s) => (
              <RiskRow
                key={s.app.id}
                to={`/applications/${s.app.id}`}
                primary={`${s.app.company} · ${s.app.role}`}
                secondary={s.app.status}
                reason={s.reason}
              />
            ))}
            {staleApps.length > 5 && (
              <MoreLink
                to="/applications"
                label={`+${staleApps.length - 5} more`}
              />
            )}
          </RiskCard>
        )}

        {pendingOffers.length > 0 && (
          <RiskCard
            title="Pending offers"
            Icon={Award}
            seeMore={{ to: '/applications', label: 'Open applications' }}
          >
            {pendingOffers.map((p) => (
              <RiskRow
                key={p.offer.id}
                to={`/applications/${p.offer.application_id}`}
                primary={p.appLabel}
                secondary={p.offer.decision_deadline || 'no deadline set'}
                reason={p.reason}
              />
            ))}
          </RiskCard>
        )}
      </div>
    </section>
  );
}

function RiskCard({
  title,
  Icon,
  seeMore,
  children,
}: {
  title: string;
  Icon: (p: { size?: number; strokeWidth?: number }) => React.ReactNode;
  seeMore: { to: string; label: string };
  children: React.ReactNode;
}) {
  return (
    <div className="card p-5 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span
          className="flex items-center gap-1.5"
          style={{ fontSize: 13, fontWeight: 500 }}
        >
          <Icon size={13} strokeWidth={1.8} />
          {title}
        </span>
        <Link
          to={seeMore.to}
          className="mono uppercase inline-flex items-center gap-0.5"
          style={{
            fontSize: 10,
            color: 'var(--text-3)',
            letterSpacing: '0.1em',
            textDecoration: 'none',
          }}
        >
          {seeMore.label}
          <ChevronRight size={11} strokeWidth={1.7} />
        </Link>
      </div>
      <div className="flex flex-col gap-1.5">{children}</div>
    </div>
  );
}

function RiskRow({
  to,
  primary,
  secondary,
  reason,
}: {
  to: string;
  primary: string;
  secondary: string;
  reason: string;
}) {
  return (
    <Link
      to={to}
      title={reason}
      className="flex items-center justify-between gap-2"
      style={{
        padding: '8px 10px',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        textDecoration: 'none',
        color: 'inherit',
      }}
    >
      <span
        style={{
          fontSize: 12.5,
          color: 'var(--text)',
          fontWeight: 500,
          minWidth: 0,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}
      >
        {primary}
      </span>
      <span
        className="mono"
        style={{
          fontSize: 10.5,
          color: 'var(--text-3)',
          whiteSpace: 'nowrap',
        }}
      >
        {secondary}
      </span>
    </Link>
  );
}

function MoreLink({ to, label }: { to: string; label: string }) {
  return (
    <Link
      to={to}
      className="mono"
      style={{
        fontSize: 11,
        color: 'var(--text-3)',
        textDecoration: 'none',
        padding: '6px 0 0',
      }}
    >
      {label}
    </Link>
  );
}

export function compute(
  todos: Todo[],
  apps: RawApp[],
  rounds: RawRound[],
  offers: RawOffer[],
) {
  const now = Date.now();
  const staleCutoff = now - STALE_APP_DAYS * 86_400_000;
  const roundHorizon = now + STALE_ROUND_HORIZON_DAYS * 86_400_000;
  const offerCutoff = now + OFFER_DEADLINE_HORIZON_DAYS * 86_400_000;

  // Overdue todos
  const overdueTodos = todos
    .filter((t) => {
      if (t.completed_at) return false;
      if (!t.due_date) return false;
      const d = Date.parse(t.due_date);
      if (Number.isNaN(d)) return false;
      return d < now;
    })
    .sort((a, b) => (a.due_date || '').localeCompare(b.due_date || ''));

  // Stale applications
  const staleApps: { app: RawApp; reason: string }[] = [];
  for (const app of apps) {
    if (app.status !== 'Applied' && app.status !== 'Interviewing') continue;
    const lastTs = Date.parse(app.last_activity_at ?? app.updated_at ?? '');
    const effectiveTs = Number.isNaN(lastTs) ? 0 : lastTs;
    if (effectiveTs > staleCutoff) continue;
    const hasUpcomingRound = rounds.some((r) => {
      if (r.application_id !== app.id) return false;
      if (r.scheduled_status === 'completed' || r.scheduled_status === 'canceled') return false;
      if (!r.date) return false;
      const ts = Date.parse(r.date);
      if (Number.isNaN(ts)) return false;
      return ts >= now && ts <= roundHorizon;
    });
    if (hasUpcomingRound) continue;
    staleApps.push({
      app,
      reason: `No activity for ${daysAgo(effectiveTs)} and no upcoming round`,
    });
  }
  staleApps.sort(
    (a, b) =>
      (Date.parse(a.app.last_activity_at ?? a.app.updated_at ?? '0') || 0) -
      (Date.parse(b.app.last_activity_at ?? b.app.updated_at ?? '0') || 0),
  );

  // Pending offers
  const pendingOffers: { offer: RawOffer; appLabel: string; reason: string }[] = [];
  for (const offer of offers) {
    if (offer.status !== 'pending') continue;
    const deadlineTs = Date.parse(offer.decision_deadline ?? '');
    const hasDeadline = !Number.isNaN(deadlineTs);
    if (hasDeadline && deadlineTs > offerCutoff) continue;
    // No deadline set → still surface: the offer is in limbo.
    const app = apps.find((a) => a.id === offer.application_id);
    const label = app ? `${app.company} · ${app.role}` : offer.application_id;
    const reason = !hasDeadline
      ? 'No decision deadline set'
      : deadlineTs < now
        ? 'Deadline has passed'
        : 'Deadline within 3 days';
    pendingOffers.push({ offer, appLabel: label, reason });
  }
  pendingOffers.sort(
    (a, b) =>
      (Date.parse(a.offer.decision_deadline ?? '9999') || 0) -
      (Date.parse(b.offer.decision_deadline ?? '9999') || 0),
  );

  return { overdueTodos, staleApps, pendingOffers };
}

function daysAgo(ts: number): string {
  if (!ts) return 'a while';
  const days = Math.floor((Date.now() - ts) / 86_400_000);
  if (days <= 0) return 'today';
  if (days === 1) return '1 day';
  return `${days} days`;
}
