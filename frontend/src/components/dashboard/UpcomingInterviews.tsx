// src/components/dashboard/UpcomingInterviews.tsx
import { Link } from 'react-router-dom';
import { CalendarClock } from 'lucide-react';
import type { DashApp, DashRound } from './derive';

function shortDate(value: string) {
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? 'No date' : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

export default function UpcomingInterviews({ rounds, apps }: { rounds: DashRound[]; apps: DashApp[] }) {
  return (
    <section className="card card-pad-lg fade-up">
      <div className="flex items-center justify-between gap-3" style={{ marginBottom: 'var(--gap-sm)' }}>
        <span className="flex items-center gap-1.5" style={{ fontSize: 13, fontWeight: 600 }}><CalendarClock size={14} /> Upcoming interviews</span>
        <Link to="/applications" className="mono uppercase" style={{ fontSize: 10, color: 'var(--text-3)', letterSpacing: '0.1em', textDecoration: 'none' }}>All →</Link>
      </div>
      {rounds.length ? (
        <div className="grid gap-1.5">
          {rounds.map((round) => {
            const app = apps.find((a) => a.id === round.application_id);
            return (
              <Link key={round.id} to={app ? `/applications/${app.id}` : '/applications'} className="flex items-center justify-between gap-3"
                style={{ padding: '8px 10px', borderRadius: 'var(--radius)', border: '1px solid var(--border)', textDecoration: 'none', color: 'inherit' }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: 12.5, fontWeight: 600 }}>{round.round_type}</div>
                  <div style={{ fontSize: 11.5, color: 'var(--text-3)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{app ? `${app.company} / ${app.role}` : 'Application'}</div>
                </div>
                <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)', whiteSpace: 'nowrap' }}>{shortDate(round.date)}</span>
              </Link>
            );
          })}
        </div>
      ) : (
        <div style={{ margin: 0, color: 'var(--text-3)', fontSize: 12.5 }}>No scheduled rounds.</div>
      )}
    </section>
  );
}
