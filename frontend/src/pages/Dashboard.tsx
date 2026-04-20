import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { api } from '../api/client';
import { RoundsMark } from '../components/Logo';
import DifficultyPill from '../components/shell/DifficultyPill';
import { effectiveStatus, useStatusMapVersion } from '../hooks/usePracticeStatus';
import type { PracticeStatus } from '../components/shell/StatusDot';
import { useAuth } from '../auth/AuthProvider';
import StreakCard from '../components/shell/StreakCard';

type SQ = { id: number; title: string; difficulty: string };
type CQ = { id: number; title: string; difficulty: string };
type BQ = { id: number; title: string };
type App = { id: number; company: string; role: string; status: string };
type Anecdote = {
  id: number;
  title: string;
  situation: string;
  category_ids: number[];
  linked_question_ids: number[];
  updated_at?: string | null;
};
type Cat = { id: number; name: string; color: string };

const practiceStatuses: PracticeStatus[] = ['todo', 'in-progress', 'mastered'];

function countBy(items: { _s: PracticeStatus }[], s: PracticeStatus) {
  return items.filter((i) => i._s === s).length;
}

function formatDate(d: Date) {
  return d.toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
}

function greeting(hour: number) {
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  if (hour < 21) return 'Good evening';
  return 'Working late';
}

function firstName(full: string) {
  return full.split(/\s+/)[0] ?? full;
}

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  useStatusMapVersion();
  const [sys, setSys] = useState<SQ[]>([]);
  const [cod, setCod] = useState<CQ[]>([]);
  const [beh, setBeh] = useState<BQ[]>([]);
  const [apps, setApps] = useState<App[]>([]);
  const [anecdotes, setAnecdotes] = useState<Anecdote[]>([]);
  const [cats, setCats] = useState<Cat[]>([]);

  useEffect(() => {
    Promise.all([
      api.get<SQ[]>('/api/system-design'),
      api.get<CQ[]>('/api/coding'),
      api.get<BQ[]>('/api/behavioral'),
      api.get<App[]>('/api/applications'),
      api.get<Anecdote[]>('/api/anecdotes'),
      api.get<Cat[]>('/api/behavioral-categories'),
    ]).then(([s, c, b, a, an, ca]) => {
      setSys(s);
      setCod(c);
      setBeh(b);
      setApps(a);
      setAnecdotes(an);
      setCats(ca);
    });
  }, []);

  const sysStat = useMemo(
    () => sys.map((q) => ({ ...q, _s: effectiveStatus('system', q.id) })),
    [sys]
  );
  const codStat = useMemo(
    () => cod.map((q) => ({ ...q, _s: effectiveStatus('coding', q.id) })),
    [cod]
  );
  const behStat = useMemo(
    () => beh.map((q) => ({ ...q, _s: effectiveStatus('behavioral', q.id) })),
    [beh]
  );
  const all = [...sysStat, ...codStat, ...behStat];

  const totalQs = all.length;
  const mastered = countBy(all, 'mastered');
  const inProgress = countBy(all, 'in-progress');
  void practiceStatuses;

  const activeApps = apps.filter((a) =>
    ['Applied', 'Interviewing'].includes(a.status)
  ).length;

  const nextUp = useMemo(() => {
    const pick = <T extends { id: number; title: string; _s: PracticeStatus }>(
      arr: T[],
      kind: string,
      to: (id: number) => string,
      difficulty?: string
    ) => {
      const inp = arr.find((q) => q._s === 'in-progress') ?? arr.find((q) => q._s === 'todo');
      if (!inp) return null;
      return {
        kind,
        title: inp.title,
        hint: inp._s === 'in-progress' ? 'Pick up where you left off' : "You haven't started this one",
        difficulty,
        to: to(inp.id),
      };
    };
    return [
      pick(codStat, 'Coding', (id) => `/coding/question/${id}`),
      pick(sysStat, 'System Design', (id) => `/system-design/question/${id}`),
      pick(behStat, 'Behavioral', (id) => `/behavioral/question/${id}`),
    ].filter(Boolean) as { kind: string; title: string; hint: string; difficulty?: string; to: string }[];
  }, [sysStat, codStat, behStat]);

  const hour = new Date().getHours();
  const g = greeting(hour);
  const name = user ? firstName(user.name) : 'there';
  const roundsPhrase =
    inProgress > 0
      ? `${inProgress} ${inProgress === 1 ? 'round' : 'rounds'} today.`
      : totalQs > 0
        ? 'Pick a round.'
        : 'Open a track.';

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto px-12 pt-10 pb-10" style={{ maxWidth: 1280 }}>
        <div className="fade-up flex justify-between items-end gap-8 flex-wrap">
          <div className="min-w-0">
            <div className="eyebrow mb-2.5">{formatDate(new Date())}</div>
            <h1 style={{ margin: 0, lineHeight: 1.02, maxWidth: 820 }}>
              <span className="display" style={{ fontSize: 56, fontWeight: 400 }}>
                {g}, {name}.{' '}
              </span>
              <span
                className="display-italic"
                style={{ fontSize: 56, color: 'var(--accent)', fontWeight: 400 }}
              >
                {roundsPhrase}
              </span>
            </h1>
            <p
              style={{
                margin: '14px 0 0',
                fontSize: 15,
                color: 'var(--text-3)',
                maxWidth: 620,
                lineHeight: 1.55,
              }}
            >
              Small, consistent reps beat long cram sessions. Pick one, show up for the full round,
              then take the afternoon off.
            </p>
          </div>
          <StreakCard />
        </div>

        <div
          className="grid gap-3 mt-9"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}
        >
          <Stat label="In progress" value={inProgress} hint={`${totalQs} questions total`} accent />
          <Stat label="Mastered" value={mastered} hint="across all tracks" />
          <Stat label="Questions" value={totalQs} hint="covered in this app" />
          <Stat
            label="Active applications"
            value={activeApps}
            hint={apps.length ? `${apps.length} total` : 'none yet'}
            muted={activeApps === 0}
            onClick={() => navigate('/applications')}
          />
        </div>

        <section className="fade-up" style={{ marginTop: 44 }}>
          <SectionTitle kicker="Pick up where you left off">Next up</SectionTitle>
          {nextUp.length ? (
            <div
              className="grid gap-3.5"
              style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}
            >
              {nextUp.map((n, i) => (
                <NextUpCard key={i} item={n} featured={i === 0} />
              ))}
            </div>
          ) : (
            <InlineEmpty
              title="Everything's in the todo bucket"
              body="Open any track to start working through the list."
            />
          )}
        </section>

        <section
          className="fade-up grid gap-5"
          style={{ marginTop: 44, gridTemplateColumns: '1.1fr 1fr' }}
        >
          <div>
            <SectionTitle kicker="Where you stand" compact>
              Progress by track
            </SectionTitle>
            <div className="card p-6">
              <TrackBar
                name="System Design"
                total={sysStat.length}
                mastered={countBy(sysStat, 'mastered')}
                inProgress={countBy(sysStat, 'in-progress')}
                color="var(--terracotta)"
              />
              <TrackBar
                name="Coding"
                total={codStat.length}
                mastered={countBy(codStat, 'mastered')}
                inProgress={countBy(codStat, 'in-progress')}
                color="var(--forest)"
              />
              <TrackBar
                name="Behavioral"
                total={behStat.length}
                mastered={countBy(behStat, 'mastered')}
                inProgress={countBy(behStat, 'in-progress')}
                color="var(--plum)"
                last
              />
            </div>
          </div>

          <div>
            <SectionTitle
              kicker="Pipeline"
              compact
              action={
                <Link
                  to="/applications"
                  className="inline-flex items-center gap-1"
                  style={{ color: 'var(--accent)', fontSize: 12, fontWeight: 500, textDecoration: 'none' }}
                >
                  All applications <ArrowRight size={12} strokeWidth={1.8} />
                </Link>
              }
            >
              Applications
            </SectionTitle>
            {apps.length ? (
              <div className="card overflow-hidden">
                {apps.slice(0, 5).map((a, i) => (
                  <div
                    key={a.id}
                    className="flex items-center justify-between px-4 py-3"
                    style={{ borderBottom: i < 4 ? '1px solid var(--border)' : 'none' }}
                  >
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 500 }}>{a.company}</div>
                      <div style={{ fontSize: 11.5, color: 'var(--text-3)' }}>{a.role}</div>
                    </div>
                    <span className="pill" style={statusPill(a.status)}>
                      {a.status.toLowerCase()}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <InlineEmpty
                title="No applications yet"
                body="Track the companies you're pursuing from wishlist to offer."
                cta={
                  <button
                    type="button"
                    onClick={() => navigate('/applications')}
                    style={primaryBtnSm}
                  >
                    + Add a company
                  </button>
                }
              />
            )}
          </div>
        </section>

        {anecdotes.length > 0 && (
          <section className="fade-up" style={{ marginTop: 44 }}>
            <SectionTitle kicker="From your notebook" compact>
              Recent anecdotes
            </SectionTitle>
            <div
              className="grid gap-3"
              style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))' }}
            >
              {anecdotes.slice(0, 6).map((a) => (
                <div key={a.id} className="card card-hover p-4" style={{ cursor: 'pointer' }}>
                  <div className="flex justify-between items-baseline gap-3">
                    <div className="display-italic" style={{ fontSize: 20, fontWeight: 400 }}>
                      {a.title}
                    </div>
                  </div>
                  <p
                    style={{
                      margin: '6px 0 0',
                      fontSize: 12.5,
                      color: 'var(--text-3)',
                      lineHeight: 1.5,
                    }}
                  >
                    {a.situation.slice(0, 110)}
                    {a.situation.length > 110 ? '…' : ''}
                  </p>
                  <div className="flex gap-1.5 mt-2.5 flex-wrap">
                    {a.category_ids.map((cid) => {
                      const c = cats.find((x) => x.id === cid);
                      if (!c) return null;
                      return (
                        <span
                          key={cid}
                          className="pill"
                          style={{
                            background: 'transparent',
                            color: c.color,
                            boxShadow: `inset 0 0 0 1px ${c.color}`,
                          }}
                        >
                          {c.name}
                        </span>
                      );
                    })}
                    <span
                      className="mono"
                      style={{ fontSize: 10.5, color: 'var(--text-4)', marginLeft: 'auto' }}
                    >
                      {a.linked_question_ids.length} linked
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        <div style={{ height: 48 }} />
      </div>
    </div>
  );
}

function SectionTitle({
  kicker,
  children,
  action,
  compact,
}: {
  kicker?: string;
  children: React.ReactNode;
  action?: React.ReactNode;
  compact?: boolean;
}) {
  return (
    <div
      className="flex items-end justify-between gap-3"
      style={{ marginBottom: compact ? 14 : 16 }}
    >
      <div>
        {kicker && <div className="eyebrow mb-1">{kicker}</div>}
        <h2
          className="display"
          style={{ margin: 0, fontSize: compact ? 24 : 28, fontWeight: 400 }}
        >
          {children}
        </h2>
      </div>
      {action}
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
  accent,
  muted,
  onClick,
}: {
  label: string;
  value: number;
  hint?: string;
  accent?: boolean;
  muted?: boolean;
  onClick?: () => void;
}) {
  const body = (
    <>
      <div className="eyebrow mb-2.5">{label}</div>
      <div
        className="display"
        style={{
          fontSize: 40,
          lineHeight: 1,
          fontWeight: 400,
          color: muted ? 'var(--text-4)' : accent ? 'var(--accent)' : 'var(--text)',
        }}
      >
        {value}
      </div>
      {hint && <div style={{ marginTop: 8, fontSize: 11.5, color: 'var(--text-3)' }}>{hint}</div>}
    </>
  );
  if (onClick) {
    return (
      <button
        type="button"
        onClick={onClick}
        className="card card-hover text-left p-4"
        style={{ border: 0, background: 'var(--bg-elev)' }}
      >
        {body}
      </button>
    );
  }
  return <div className="card p-4">{body}</div>;
}

function NextUpCard({
  item,
  featured,
}: {
  item: { kind: string; title: string; hint: string; difficulty?: string; to: string };
  featured: boolean;
}) {
  return (
    <Link
      to={item.to}
      className="card card-hover relative overflow-hidden"
      style={{
        padding: featured ? 24 : 18,
        textDecoration: 'none',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        minHeight: featured ? 180 : 140,
        background: 'var(--bg-elev)',
        color: 'var(--text)',
      }}
    >
      {featured && (
        <div style={{ position: 'absolute', top: -40, right: -30, opacity: 0.08 }}>
          <RoundsMark size={160} accent="var(--accent)" />
        </div>
      )}
      <div className="flex items-center gap-2">
        <span className="eyebrow">{item.kind}</span>
        {item.difficulty && <DifficultyPill level={item.difficulty} />}
      </div>
      <div
        className="display-italic"
        style={{
          fontSize: featured ? 28 : 20,
          lineHeight: 1.1,
          fontWeight: 400,
          marginTop: featured ? 8 : 4,
        }}
      >
        {item.title}
      </div>
      <div style={{ fontSize: 12.5, color: 'var(--text-3)', lineHeight: 1.5, marginTop: 'auto' }}>
        {item.hint}
      </div>
      <div
        className="flex items-center gap-1.5"
        style={{ color: 'var(--accent)', fontSize: 12, fontWeight: 500, marginTop: 6 }}
      >
        Start round <ArrowRight size={13} strokeWidth={1.8} />
      </div>
    </Link>
  );
}

function TrackBar({
  name,
  total,
  mastered,
  inProgress,
  color,
  last,
}: {
  name: string;
  total: number;
  mastered: number;
  inProgress: number;
  color: string;
  last?: boolean;
}) {
  const pct = (v: number) => (total ? `${(v / total) * 100}%` : '0%');
  return (
    <div
      style={{
        padding: last ? '14px 0 0' : '14px 0',
        borderBottom: last ? 'none' : '1px solid var(--border)',
      }}
    >
      <div className="flex justify-between items-baseline mb-2.5">
        <div className="flex items-center gap-2.5">
          <span style={{ width: 6, height: 6, borderRadius: 999, background: color }} />
          <span style={{ fontSize: 13.5, fontWeight: 500 }}>{name}</span>
        </div>
        <div className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>
          {mastered}/{total} mastered · {inProgress} practicing
        </div>
      </div>
      <div
        style={{
          position: 'relative',
          height: 6,
          background: 'var(--paper-3)',
          borderRadius: 3,
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            inset: 0,
            width: pct(mastered),
            background: color,
            borderRadius: 3,
          }}
        />
        <div
          style={{
            position: 'absolute',
            top: 0,
            bottom: 0,
            left: pct(mastered),
            width: pct(inProgress),
            background: color,
            opacity: 0.35,
            borderRadius: 3,
          }}
        />
      </div>
    </div>
  );
}

function InlineEmpty({
  title,
  body,
  cta,
}: {
  title: string;
  body?: string;
  cta?: React.ReactNode;
}) {
  return (
    <div
      className="card flex items-center gap-5 flex-wrap"
      style={{ padding: '24px 22px', background: 'var(--bg-elev)' }}
    >
      <div className="flex-1" style={{ minWidth: 220 }}>
        <div
          className="display-italic"
          style={{ fontSize: 20, fontWeight: 400, marginBottom: 3 }}
        >
          {title}
        </div>
        {body && (
          <div style={{ fontSize: 12.5, color: 'var(--text-3)', lineHeight: 1.5 }}>{body}</div>
        )}
      </div>
      {cta}
    </div>
  );
}

const primaryBtnSm: React.CSSProperties = {
  padding: '7px 13px',
  borderRadius: 6,
  border: 0,
  background: 'var(--accent)',
  color: 'var(--bg-elev)',
  fontSize: 12,
  fontWeight: 500,
  whiteSpace: 'nowrap',
  flexShrink: 0,
  cursor: 'pointer',
};

function statusPill(status: string): React.CSSProperties {
  const m: Record<string, { bg: string; fg: string }> = {
    Wishlist: { bg: 'var(--paper-3)', fg: 'var(--text-3)' },
    Applied: { bg: 'var(--ochre-soft)', fg: 'var(--ochre)' },
    Interviewing: { bg: 'var(--accent-soft)', fg: 'var(--accent)' },
    Offer: { bg: 'var(--forest-soft)', fg: 'var(--forest)' },
    Rejected: { bg: 'var(--plum-soft)', fg: 'var(--plum)' },
    Closed: { bg: 'var(--plum-soft)', fg: 'var(--plum)' },
  };
  const s = m[status] ?? { bg: 'var(--paper-3)', fg: 'var(--text-3)' };
  return { background: s.bg, color: s.fg };
}
