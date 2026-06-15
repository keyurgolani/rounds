// src/components/dashboard/ExperienceLibraryOverview.tsx
import { Link } from 'react-router-dom';
import type { ExperienceOverviewResult } from './derive';

function Stat({ n, label }: { n: number; label: string }) {
  return (
    <span><b className="display" style={{ fontSize: 18 }}>{n}</b> <span style={{ fontSize: 11, color: 'var(--text-3)' }}>{label}</span></span>
  );
}

export default function ExperienceLibraryOverview({ overview }: { overview: ExperienceOverviewResult }) {
  return (
    <section className="card card-pad-lg fade-up">
      <div className="flex items-center justify-between" style={{ marginBottom: 9 }}>
        <h2 className="display" style={{ margin: 0, fontSize: 18, fontWeight: 400 }}>Experience library</h2>
        <Link to="/experience" className="mono uppercase" style={{ fontSize: 10, color: 'var(--text-3)', letterSpacing: '0.1em', textDecoration: 'none' }}>Open →</Link>
      </div>
      <div className="flex flex-wrap" style={{ gap: 14, marginBottom: 9 }}>
        <Stat n={overview.jobs} label="jobs" />
        <Stat n={overview.projects} label="projects" />
        <Stat n={overview.anecdotes} label="anecdotes" />
        <Stat n={overview.bullets} label="bullets" />
      </div>
      <div style={{ fontSize: 11.5, color: 'var(--text-2)' }}>
        {overview.addedThisWeek > 0 && <>{overview.addedThisWeek} added this week · </>}
        <span style={{ color: 'var(--text-3)' }}>{overview.unusedBullets} bullets not yet linked in the library</span>
      </div>
    </section>
  );
}
