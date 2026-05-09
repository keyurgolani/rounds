import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, BriefcaseBusiness, CalendarClock, CheckCircle2, ClipboardList, Command, FolderKanban, ListTodo, Plus, Target } from 'lucide-react';
import { listApplications, listRounds } from '../applications/api';
import {
  listBehavioralCategories,
  listBehavioralQuestions,
  listCodingQuestions,
  listSystemDesignQuestions,
} from '../content/api';
import { listAnecdotes } from './behavioral/anecdotesApi';
import { useAuth } from '../auth/AuthProvider';
import { useCampaign } from '../campaign/CampaignContext';
import { useCommandCenter } from '../command-center/CommandCenterProvider';
import AppHeader from '../components/shell/AppHeader';
import DifficultyPill from '../components/shell/DifficultyPill';
import StreakCard from '../components/shell/StreakCard';
import AtRiskSection from '../components/dashboard/AtRiskSection';
import TodosWidget from '../components/dashboard/TodosWidget';
import { effectiveStatus, useStatusMapVersion } from '../hooks/usePracticeStatus';
import type { PracticeStatus } from '../components/shell/StatusDot';

type SQ = { id: string; title: string; difficulty: string };
type CQ = { id: string; title: string; difficulty: string };
type BQ = { id: string; title: string };
type App = { id: string; company: string; role: string; status: string; applied_date?: string; updated_at?: string; last_activity_at?: string };
type Round = { id: string; application_id: string; round_type: string; date: string; interviewer: string; notes: string; result: string };
type Anecdote = { id: string; title: string; situation: string; category_ids: string[]; linked_question_ids: string[]; updated_at?: string | null };
type Cat = { id: string; name: string; color: string };

function countBy(items: { _s: PracticeStatus }[], status: PracticeStatus) {
  return items.filter((item) => item._s === status).length;
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

function parseRoundDate(value: string): Date | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatShortDate(value?: string) {
  const date = value ? parseRoundDate(value) : null;
  if (!date) return 'No date';
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function statusPill(status: string): React.CSSProperties {
  const map: Record<string, { bg: string; fg: string }> = {
    Wishlist: { bg: 'var(--paper-3)', fg: 'var(--text-3)' },
    Applied: { bg: 'var(--ochre-soft)', fg: 'var(--ochre)' },
    Interviewing: { bg: 'var(--accent-soft)', fg: 'var(--accent)' },
    Offer: { bg: 'var(--forest-soft)', fg: 'var(--forest)' },
    Rejected: { bg: 'var(--plum-soft)', fg: 'var(--plum)' },
    Closed: { bg: 'var(--plum-soft)', fg: 'var(--plum)' },
  };
  const style = map[status] ?? { bg: 'var(--paper-3)', fg: 'var(--text-3)' };
  return { background: style.bg, color: style.fg };
}

export default function Dashboard() {
  const { user } = useAuth();
  const { currentId, currentCampaign, campaigns } = useCampaign();
  const cc = useCommandCenter();
  useStatusMapVersion();

  const [sys, setSys] = useState<SQ[]>([]);
  const [cod, setCod] = useState<CQ[]>([]);
  const [beh, setBeh] = useState<BQ[]>([]);
  const [apps, setApps] = useState<App[]>([]);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [anecdotes, setAnecdotes] = useState<Anecdote[]>([]);
  const [cats, setCats] = useState<Cat[]>([]);

  const load = useCallback(async () => {
    const [s, c, b, a, an, ca] = await Promise.all([
      listSystemDesignQuestions<SQ>(),
      listCodingQuestions<CQ>(),
      listBehavioralQuestions<BQ>(),
      listApplications(currentId ?? undefined),
      listAnecdotes(),
      listBehavioralCategories<Cat>(),
    ]);
    const roundLists = await Promise.all(a.map((app) => listRounds(app.id).catch(() => [] as Round[])));
    setSys(s);
    setCod(c);
    setBeh(b);
    setApps(a);
    setRounds(roundLists.flat());
    setAnecdotes(an);
    setCats(ca);
  }, [currentId]);

  useEffect(() => {
    void load();
    const refresh = () => void load();
    window.addEventListener('rounds:applications-changed', refresh);
    window.addEventListener('rounds:interviews-changed', refresh);
    window.addEventListener('rounds:campaigns-changed', refresh);
    return () => {
      window.removeEventListener('rounds:applications-changed', refresh);
      window.removeEventListener('rounds:interviews-changed', refresh);
      window.removeEventListener('rounds:campaigns-changed', refresh);
    };
  }, [load]);

  const sysStat = useMemo(() => sys.map((q) => ({ ...q, _s: effectiveStatus('system', q.id) })), [sys]);
  const codStat = useMemo(() => cod.map((q) => ({ ...q, _s: effectiveStatus('coding', q.id) })), [cod]);
  const behStat = useMemo(() => beh.map((q) => ({ ...q, _s: effectiveStatus('behavioral', q.id) })), [beh]);
  const all = [...sysStat, ...codStat, ...behStat];
  const totalQs = all.length;
  const mastered = countBy(all, 'mastered');
  const inProgress = countBy(all, 'in-progress');
  const activeApps = apps.filter((app) => ['Wishlist', 'Applied', 'Interviewing', 'Offer'].includes(app.status));
  const interviewingApps = apps.filter((app) => app.status === 'Interviewing');

  const upcomingRounds = useMemo(() => {
    const now = Date.now() - 12 * 60 * 60 * 1000;
    return rounds
      .map((round) => ({ round, date: parseRoundDate(round.date) }))
      .filter((item): item is { round: Round; date: Date } => !!item.date && item.date.getTime() >= now)
      .sort((a, b) => a.date.getTime() - b.date.getTime())
      .map((item) => item.round);
  }, [rounds]);

  const nextPractice = useMemo(() => {
    const pick = <T extends { id: string; title: string; _s: PracticeStatus; difficulty?: string }>(
      arr: T[],
      kind: string,
      to: (id: string) => string,
    ) => {
      const item = arr.find((q) => q._s === 'in-progress') ?? arr.find((q) => q._s === 'todo');
      if (!item) return null;
      return { kind, title: item.title, status: item._s, difficulty: item.difficulty, to: to(item.id) };
    };
    return [
      pick(codStat, 'Coding', (id) => `/coding/question/${id}`),
      pick(sysStat, 'System Design', (id) => `/system-design/question/${id}`),
      pick(behStat, 'Behavioral', (id) => `/behavioral/question/${id}`),
    ].filter(Boolean) as { kind: string; title: string; status: PracticeStatus; difficulty?: string; to: string }[];
  }, [sysStat, codStat, behStat]);

  const campaignLabel = currentCampaign?.name ?? (campaigns.length > 1 ? 'All active campaigns' : campaigns[0]?.name ?? 'Default');
  const hour = new Date().getHours();
  const name = user ? firstName(user.name) : 'there';
  const nextRound = upcomingRounds[0];
  const nextRoundApp = nextRound ? apps.find((app) => app.id === nextRound.application_id) : null;
  const headerDescription = `${activeApps.length} active ${activeApps.length === 1 ? 'application' : 'applications'} / ${upcomingRounds.length} upcoming ${upcomingRounds.length === 1 ? 'round' : 'rounds'} / ${inProgress} practice ${inProgress === 1 ? 'item' : 'items'} in motion`;

  return (
    <div className="h-full flex flex-col">
      <AppHeader
        title={`${greeting(hour)}, ${name}.`}
        eyebrow={<span className="eyebrow">{formatDate(new Date())} / {campaignLabel}</span>}
        description={headerDescription}
        actions={<StreakCard compact="header" />}
        compactActions={<StreakCard compact />}
      />
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="px-5 sm:px-8 lg:px-12 pt-6 pb-10 grid gap-8">
          <CampaignStrip
            label={campaignLabel}
            activeApps={activeApps.length}
            upcomingRounds={upcomingRounds.length}
            mastered={mastered}
            total={totalQs}
            onAddApplication={() => cc.openView('add-application')}
            onScheduleInterview={() => cc.openView('schedule-interview')}
            onCampaigns={() => cc.openView('campaigns')}
          />

          <section className="grid gap-5 xl:grid-cols-[minmax(0,1.25fr)_minmax(340px,0.75fr)] items-stretch">
            <TodayQueue nextRound={nextRound} nextRoundApp={nextRoundApp} practices={nextPractice} onScheduleInterview={() => cc.openView('schedule-interview')} />
            <PipelinePulse apps={apps} activeApps={activeApps} interviewingApps={interviewingApps} upcomingRounds={upcomingRounds} onAddApplication={() => cc.openView('add-application')} />
          </section>

          <AtRiskSection />

          <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px] items-start">
            <div className="grid gap-5">
              <TrackReadiness
                tracks={[
                  { name: 'Coding', to: '/coding/guide', total: codStat.length, mastered: countBy(codStat, 'mastered'), inProgress: countBy(codStat, 'in-progress'), color: 'var(--forest)' },
                  { name: 'System Design', to: '/system-design/guide', total: sysStat.length, mastered: countBy(sysStat, 'mastered'), inProgress: countBy(sysStat, 'in-progress'), color: 'var(--terracotta)' },
                  { name: 'Behavioral', to: '/behavioral/guide', total: behStat.length, mastered: countBy(behStat, 'mastered'), inProgress: countBy(behStat, 'in-progress'), color: 'var(--plum)' },
                ]}
              />
              <RecentApplications apps={apps.slice(0, 6)} onAddApplication={() => cc.openView('add-application')} />
              <RecentAnecdotes anecdotes={anecdotes.slice(0, 4)} cats={cats} />
            </div>
            <div className="grid gap-5">
              <TodosWidget />
              <UpcomingInterviews rounds={upcomingRounds.slice(0, 5)} apps={apps} onScheduleInterview={() => cc.openView('schedule-interview')} />
            </div>
          </section>

          <div style={{ height: 36 }} />
        </div>
      </div>
    </div>
  );
}

function CampaignStrip({ label, activeApps, upcomingRounds, mastered, total, onAddApplication, onScheduleInterview, onCampaigns }: { label: string; activeApps: number; upcomingRounds: number; mastered: number; total: number; onAddApplication: () => void; onScheduleInterview: () => void; onCampaigns: () => void }) {
  return (
    <section className="card p-4 sm:p-5 fade-up" style={{ background: 'linear-gradient(135deg, var(--bg-elev), var(--bg))' }}>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
        <div>
          <div className="eyebrow mb-2">Campaign command</div>
          <div className="display-italic" style={{ fontSize: 'clamp(28px, 5vw, 42px)', lineHeight: 0.95, fontWeight: 400 }}>{label}</div>
          <div className="flex flex-wrap gap-2 mt-3">
            <MetricPill label="Active apps" value={activeApps} />
            <MetricPill label="Upcoming rounds" value={upcomingRounds} />
            <MetricPill label="Mastered" value={`${mastered}/${total}`} />
          </div>
        </div>
        <div className="flex flex-wrap gap-2 lg:justify-end">
          <ActionButton onClick={onAddApplication} icon={<BriefcaseBusiness size={14} />}>Add application <KbdHint /></ActionButton>
          <ActionButton onClick={onScheduleInterview} icon={<CalendarClock size={14} />}>Schedule <KbdHint /></ActionButton>
          <ActionButton onClick={onCampaigns} icon={<FolderKanban size={14} />} subtle>Campaigns <KbdHint /></ActionButton>
        </div>
      </div>
    </section>
  );
}

function TodayQueue({ nextRound, nextRoundApp, practices, onScheduleInterview }: { nextRound?: Round; nextRoundApp?: App | null; practices: { kind: string; title: string; status: PracticeStatus; difficulty?: string; to: string }[]; onScheduleInterview: () => void }) {
  return (
    <section className="card p-5 fade-up h-full flex flex-col">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <div className="eyebrow mb-1">Today's prep queue</div>
          <h2 className="display" style={{ margin: 0, fontSize: 28, fontWeight: 400 }}>What deserves attention first</h2>
        </div>
        <button type="button" onClick={onScheduleInterview} className="pill mono" style={ghostPill}><Command size={12} /> Schedule <KbdHint /></button>
      </div>
      <div className="grid gap-4 lg:grid-cols-[minmax(260px,0.8fr)_minmax(0,1.2fr)]">
        <div className="card p-4" style={{ background: 'var(--bg-sunken)', boxShadow: 'none' }}>
          <div className="flex items-center gap-2 mb-3" style={{ color: 'var(--accent)' }}><CalendarClock size={15} /><span className="eyebrow">Next interview</span></div>
          {nextRound ? (
            <Link to={`/interviews/${nextRound.id}`} style={{ color: 'inherit', textDecoration: 'none' }}>
              <div className="display-italic" style={{ fontSize: 26, lineHeight: 1, fontWeight: 400 }}>{formatShortDate(nextRound.date)}</div>
              <div style={{ marginTop: 10, fontWeight: 600 }}>{nextRound.round_type}</div>
              <div style={{ marginTop: 4, color: 'var(--text-3)', fontSize: 12.5 }}>{nextRoundApp ? `${nextRoundApp.company} / ${nextRoundApp.role}` : 'Application'}</div>
              {nextRound.interviewer && <div style={{ marginTop: 8, color: 'var(--text-4)', fontSize: 12 }}>{nextRound.interviewer}</div>}
            </Link>
          ) : (
            <div>
              <div className="display-italic" style={{ fontSize: 24, fontWeight: 400 }}>No round scheduled</div>
              <p style={mutedText}>Add the next interview so prep can anchor to a real date.</p>
            </div>
          )}
        </div>
        <div className="grid gap-2">
          {practices.length ? practices.map((practice) => <PracticeRow key={practice.kind} practice={practice} />) : <EmptyCard title="No practice queue yet" body="Open a guide or question list to start a track." />}
        </div>
      </div>
    </section>
  );
}

function PipelinePulse({ apps, activeApps, interviewingApps, upcomingRounds, onAddApplication }: { apps: App[]; activeApps: App[]; interviewingApps: App[]; upcomingRounds: Round[]; onAddApplication: () => void }) {
  const counts = ['Wishlist', 'Applied', 'Interviewing', 'Offer'].map((status) => ({ status, count: apps.filter((app) => app.status === status).length }));
  return (
    <section className="card p-5 fade-up h-full flex flex-col">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <div className="eyebrow mb-1">Pipeline pulse</div>
          <h2 className="display" style={{ margin: 0, fontSize: 28, fontWeight: 400 }}>{activeApps.length} active targets</h2>
        </div>
        <button type="button" onClick={onAddApplication} className="pill mono" style={ghostPill}><Plus size={12} /> Add <KbdHint /></button>
      </div>
      <div className="grid gap-2">
        {counts.map(({ status, count }) => <PipelineCount key={status} status={status} count={count} total={Math.max(activeApps.length, 1)} />)}
      </div>
      <div className="grid gap-2 mt-4 pt-4" style={{ borderTop: '1px solid var(--border)' }}>
        <MiniSignal icon={<BriefcaseBusiness size={14} />} label="Interviewing" value={interviewingApps.length} />
        <MiniSignal icon={<CalendarClock size={14} />} label="Scheduled rounds" value={upcomingRounds.length} />
      </div>
    </section>
  );
}

function TrackReadiness({ tracks }: { tracks: { name: string; to: string; total: number; mastered: number; inProgress: number; color: string }[] }) {
  return (
    <section className="card p-5 fade-up">
      <div className="flex items-end justify-between gap-3 mb-4">
        <div>
          <div className="eyebrow mb-1">Track readiness</div>
          <h2 className="display" style={{ margin: 0, fontSize: 26, fontWeight: 400 }}>Prep coverage</h2>
        </div>
      </div>
      <div className="grid gap-3">
        {tracks.map((track) => <TrackBar key={track.name} {...track} />)}
      </div>
    </section>
  );
}

function RecentApplications({ apps, onAddApplication }: { apps: App[]; onAddApplication: () => void }) {
  return (
    <section className="card p-5 fade-up">
      <div className="flex items-center justify-between gap-3 mb-4">
        <div>
          <div className="eyebrow mb-1">Applications</div>
          <h2 className="display" style={{ margin: 0, fontSize: 24, fontWeight: 400 }}>Latest targets</h2>
        </div>
        <button type="button" onClick={onAddApplication} style={textAction}>Add <KbdHint inline /></button>
      </div>
      {apps.length ? (
        <div className="grid gap-2 sm:grid-cols-2">
          {apps.map((app) => (
            <Link key={app.id} to={`/applications/${app.id}`} className="card card-hover p-3" style={{ textDecoration: 'none', color: 'inherit', background: 'var(--bg)', boxShadow: 'inset 0 0 0 1px var(--border)' }}>
              <div className="flex items-start justify-between gap-2">
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 13.5, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{app.company}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{app.role}</div>
                </div>
                <span className="pill" style={statusPill(app.status)}>{app.status.toLowerCase()}</span>
              </div>
            </Link>
          ))}
        </div>
      ) : <EmptyCard title="No applications yet" body="Capture your first target from Command Center." />}
    </section>
  );
}

function UpcomingInterviews({ rounds, apps, onScheduleInterview }: { rounds: Round[]; apps: App[]; onScheduleInterview: () => void }) {
  return (
    <section className="card p-5 fade-up">
      <div className="flex items-center justify-between gap-3 mb-3">
        <span className="flex items-center gap-1.5" style={{ fontSize: 13, fontWeight: 600 }}><CalendarClock size={14} /> Upcoming interviews</span>
        <button type="button" onClick={onScheduleInterview} style={textAction}>Schedule <KbdHint inline /></button>
      </div>
      {rounds.length ? (
        <div className="grid gap-2">
          {rounds.map((round) => {
            const app = apps.find((item) => item.id === round.application_id);
            return (
              <Link key={round.id} to={`/interviews/${round.id}`} className="flex items-center justify-between gap-3" style={rowLink}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600 }}>{round.round_type}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{app ? `${app.company} / ${app.role}` : 'Application'}</div>
                </div>
                <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)', whiteSpace: 'nowrap' }}>{formatShortDate(round.date)}</span>
              </Link>
            );
          })}
        </div>
      ) : <div style={{ ...mutedText, margin: 0 }}>No scheduled rounds.</div>}
    </section>
  );
}

function RecentAnecdotes({ anecdotes, cats }: { anecdotes: Anecdote[]; cats: Cat[] }) {
  if (anecdotes.length === 0) return null;
  return (
    <section className="card p-5 fade-up">
      <div className="eyebrow mb-1">Behavioral notebook</div>
      <h2 className="display" style={{ margin: '0 0 14px', fontSize: 24, fontWeight: 400 }}>Recent stories</h2>
      <div className="grid gap-2 sm:grid-cols-2">
        {anecdotes.map((anecdote) => (
          <div key={anecdote.id} className="card p-3" style={{ background: 'var(--bg)', boxShadow: 'inset 0 0 0 1px var(--border)' }}>
            <div className="display-italic" style={{ fontSize: 19, lineHeight: 1.1, fontWeight: 400 }}>{anecdote.title}</div>
            <p style={{ margin: '6px 0 0', color: 'var(--text-3)', fontSize: 12, lineHeight: 1.45 }}>{anecdote.situation.slice(0, 100)}{anecdote.situation.length > 100 ? '...' : ''}</p>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {anecdote.category_ids.slice(0, 3).map((id) => {
                const cat = cats.find((item) => item.id === id);
                if (!cat) return null;
                return <span key={id} className="pill" style={{ background: 'transparent', color: cat.color, boxShadow: `inset 0 0 0 1px ${cat.color}` }}>{cat.name}</span>;
              })}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function PracticeRow({ practice }: { practice: { kind: string; title: string; status: PracticeStatus; difficulty?: string; to: string } }) {
  return (
    <Link to={practice.to} className="card card-hover p-3 flex items-center justify-between gap-3" style={{ textDecoration: 'none', color: 'inherit', background: 'var(--bg)', boxShadow: 'inset 0 0 0 1px var(--border)' }}>
      <div style={{ minWidth: 0 }}>
        <div className="flex items-center gap-2 mb-1"><span className="eyebrow">{practice.kind}</span>{practice.difficulty && <DifficultyPill level={practice.difficulty} />}</div>
        <div style={{ fontSize: 14, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{practice.title}</div>
        <div style={{ marginTop: 4, color: 'var(--text-3)', fontSize: 12 }}>{practice.status === 'in-progress' ? 'Continue current rep' : 'Start this rep'}</div>
      </div>
      <ArrowRight size={15} style={{ color: 'var(--accent)', flexShrink: 0 }} />
    </Link>
  );
}

function TrackBar({ name, to, total, mastered, inProgress, color }: { name: string; to: string; total: number; mastered: number; inProgress: number; color: string }) {
  const masteredPct = total ? (mastered / total) * 100 : 0;
  const progressPct = total ? (inProgress / total) * 100 : 0;
  return (
    <Link to={to} style={{ color: 'inherit', textDecoration: 'none' }}>
      <div className="card card-hover p-3" style={{ background: 'var(--bg)', boxShadow: 'inset 0 0 0 1px var(--border)' }}>
        <div className="flex items-center justify-between gap-3 mb-2">
          <span className="flex items-center gap-2" style={{ fontSize: 13.5, fontWeight: 600 }}><span style={{ width: 7, height: 7, borderRadius: 999, background: color }} />{name}</span>
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>{mastered}/{total}</span>
        </div>
        <div style={{ height: 7, borderRadius: 999, background: 'var(--bg-sunken)', overflow: 'hidden', position: 'relative' }}>
          <div style={{ position: 'absolute', inset: 0, width: `${masteredPct}%`, background: color }} />
          <div style={{ position: 'absolute', top: 0, bottom: 0, left: `${masteredPct}%`, width: `${progressPct}%`, background: color, opacity: 0.35 }} />
        </div>
      </div>
    </Link>
  );
}

function PipelineCount({ status, count, total }: { status: string; count: number; total: number }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span style={{ fontSize: 12.5, color: 'var(--text-2)' }}>{status}</span>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>{count}</span>
      </div>
      <div style={{ height: 6, borderRadius: 999, background: 'var(--bg-sunken)', overflow: 'hidden' }}>
        <div style={{ width: `${(count / total) * 100}%`, height: '100%', background: statusPill(status).color, opacity: 0.85 }} />
      </div>
    </div>
  );
}

function MiniSignal({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="flex items-center justify-between gap-3" style={{ fontSize: 12.5, color: 'var(--text-2)' }}>
      <span className="flex items-center gap-2">{icon}{label}</span>
      <span className="display-italic" style={{ fontSize: 22, color: 'var(--text)' }}>{value}</span>
    </div>
  );
}

function MetricPill({ label, value }: { label: string; value: React.ReactNode }) {
  return <span className="pill" style={{ background: 'var(--bg)', color: 'var(--text-2)', boxShadow: 'inset 0 0 0 1px var(--border)' }}><span className="mono" style={{ color: 'var(--accent)', marginRight: 6 }}>{value}</span>{label}</span>;
}

function ActionButton({ children, icon, onClick, subtle }: { children: React.ReactNode; icon: React.ReactNode; onClick: () => void; subtle?: boolean }) {
  return <button type="button" onClick={onClick} className="inline-flex items-center gap-2" style={{ border: 0, borderRadius: 'var(--radius)', padding: '9px 13px', background: subtle ? 'var(--bg)' : 'var(--accent)', color: subtle ? 'var(--text-2)' : 'var(--bg-elev)', boxShadow: subtle ? 'inset 0 0 0 1px var(--border)' : 'none', fontSize: 12.5, fontWeight: 600, cursor: 'pointer' }}>{icon}{children}</button>;
}

function EmptyCard({ title, body }: { title: string; body: string }) {
  return <div className="card p-4" style={{ background: 'var(--bg)', boxShadow: 'inset 0 0 0 1px var(--border)' }}><div className="display-italic" style={{ fontSize: 20, fontWeight: 400 }}>{title}</div><p style={mutedText}>{body}</p></div>;
}

function KbdHint({ inline }: { inline?: boolean } = {}) {
  const mod = typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.userAgent) ? '\u2318' : 'Ctrl';
  return (
    <span
      className="mono"
      style={{
        fontSize: 9.5,
        lineHeight: 1,
        padding: '2px 5px',
        borderRadius: 4,
        background: 'var(--bg-sunken)',
        color: 'var(--text-3)',
        marginLeft: 6,
        border: '1px solid var(--border)',
        whiteSpace: 'nowrap',
        pointerEvents: 'none',
      }}
    >
      {mod}K
    </span>
  );
}

const mutedText: React.CSSProperties = { margin: '8px 0 0', color: 'var(--text-3)', fontSize: 12.5, lineHeight: 1.5 };
const ghostPill: React.CSSProperties = { border: 0, color: 'var(--accent)', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: 5 };
const textAction: React.CSSProperties = { border: 0, background: 'transparent', color: 'var(--accent)', fontSize: 12, fontWeight: 600, display: 'inline-flex', alignItems: 'center', gap: 4, cursor: 'pointer' };
const rowLink: React.CSSProperties = { padding: '8px 10px', borderRadius: 'var(--radius)', border: '1px solid var(--border)', textDecoration: 'none', color: 'inherit' };
