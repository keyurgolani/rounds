import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import DifficultyPill from '../shell/DifficultyPill';
import type { DashApp, DashRound, NextRep, computeAtRisk } from './derive';

type AtRisk = ReturnType<typeof computeAtRisk>;

function shortDate(value: string) {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? 'No date' : d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
}

export default function TodayZone({
  nextInterview, nextInterviewApp, nextReps, atRisk,
}: {
  nextInterview: DashRound | null;
  nextInterviewApp: DashApp | null;
  nextReps: NextRep[];
  atRisk: AtRisk;
}) {
  const riskCount = atRisk.overdueTodos.length + atRisk.staleApps.length + atRisk.pendingOffers.length;
  return (
    <section className="card card-pad-lg fade-up" style={{ background: 'linear-gradient(135deg, var(--bg-elev), var(--bg))' }}>
      <div className="eyebrow" style={{ color: 'var(--accent)', marginBottom: 'var(--gap-sm)' }}>Today — what deserves attention first</div>
      <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
        {/* Next interview */}
        <div>
          <div className="eyebrow mb-1" style={{ color: 'var(--text-3)' }}>Next interview</div>
          {nextInterview ? (
            <Link to={nextInterviewApp ? `/applications/${nextInterviewApp.id}` : '/applications'} style={{ color: 'inherit', textDecoration: 'none' }}>
              <div className="display-italic" style={{ fontSize: 22, lineHeight: 1, fontWeight: 400 }}>{shortDate(nextInterview.date)}</div>
              <div style={{ marginTop: 6, fontWeight: 600 }}>{nextInterview.round_type}</div>
              <div style={{ marginTop: 3, color: 'var(--text-3)', fontSize: 12 }}>{nextInterviewApp ? `${nextInterviewApp.company} / ${nextInterviewApp.role}` : 'Application'}</div>
              {nextInterview.interviewer && <div style={{ marginTop: 6, color: 'var(--text-4)', fontSize: 11.5 }}>{nextInterview.interviewer}</div>}
            </Link>
          ) : (
            <div>
              <div className="display-italic" style={{ fontSize: 20, fontWeight: 400 }}>No round scheduled</div>
              <p style={{ margin: '6px 0 0', color: 'var(--text-3)', fontSize: 12 }}>Add the next interview so prep can anchor to a date.</p>
            </div>
          )}
        </div>

        {/* Next reps */}
        <div>
          <div className="eyebrow mb-1" style={{ color: 'var(--text-3)' }}>Pick up where you left off</div>
          {nextReps.length ? (
            <div className="grid gap-1.5">
              {nextReps.map((rep) => (
                <Link key={rep.to} to={rep.to} className="card card-hover p-3 flex items-center justify-between gap-2" style={{ textDecoration: 'none', color: 'inherit', background: 'var(--bg)', boxShadow: 'inset 0 0 0 1px var(--border)' }}>
                  <div style={{ minWidth: 0 }}>
                    <div className="flex items-center gap-2 mb-0.5"><span className="eyebrow">{rep.kind}</span>{rep.difficulty && <DifficultyPill level={rep.difficulty} />}</div>
                    <div style={{ fontSize: 13, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{rep.title}</div>
                    <div style={{ marginTop: 2, color: 'var(--text-3)', fontSize: 11.5 }}>{rep.status === 'in-progress' ? 'Continue current rep' : 'Start this rep'}</div>
                  </div>
                  <ArrowRight size={15} aria-hidden="true" style={{ color: 'var(--accent)', flexShrink: 0 }} />
                </Link>
              ))}
            </div>
          ) : (
            <p style={{ margin: 0, color: 'var(--text-3)', fontSize: 12 }}>No practice queued. Open a guide to start a track.</p>
          )}
        </div>

        {/* Needs attention */}
        <div>
          <div className="eyebrow mb-1" style={{ color: 'var(--plum)' }}>Needs attention {riskCount > 0 && <span className="mono" style={{ color: 'var(--text-4)' }}>· {riskCount}</span>}</div>
          {riskCount === 0 ? (
            <p style={{ margin: 0, color: 'var(--text-3)', fontSize: 12 }}>You're all caught up. Nice.</p>
          ) : (
            <div className="grid gap-1.5" style={{ fontSize: 12 }}>
              {atRisk.overdueTodos.length > 0 && (
                <Link to="/todos" style={riskRow}><span>🔴 {atRisk.overdueTodos.length} {atRisk.overdueTodos.length === 1 ? 'todo' : 'todos'} overdue</span></Link>
              )}
              {atRisk.staleApps.slice(0, 2).map((s) => (
                <Link key={s.app.id} to={`/applications/${s.app.id}`} style={riskRow}><span>🟡 {s.app.company} — stale</span></Link>
              ))}
              {atRisk.pendingOffers.slice(0, 2).map((p) => (
                <Link key={p.offer.id} to={`/applications/${p.offer.application_id}`} style={riskRow}><span>🟠 {p.appLabel} — {p.reason.toLowerCase()}</span></Link>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

const riskRow: React.CSSProperties = {
  padding: '7px 9px', border: '1px solid var(--border)', borderRadius: 'var(--radius)',
  textDecoration: 'none', color: 'inherit',
};
