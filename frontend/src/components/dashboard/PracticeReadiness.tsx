// src/components/dashboard/PracticeReadiness.tsx
import { Link } from 'react-router-dom';
import type { TrackReadiness } from './derive';

export default function PracticeReadiness({ tracks }: { tracks: TrackReadiness[] }) {
  return (
    <section className="card card-pad-lg fade-up">
      <div className="eyebrow mb-1">Practice readiness</div>
      <h2 className="display" style={{ margin: '0 0 var(--gap-sm)', fontSize: 22, fontWeight: 400 }}>Prep coverage</h2>
      <div className="grid gap-2">
        {tracks.map((t) => {
          const masteredPct = t.total ? (t.mastered / t.total) * 100 : 0;
          const progressPct = t.total ? (t.inProgress / t.total) * 100 : 0;
          return (
            <Link key={t.key} to={t.to} style={{ color: 'inherit', textDecoration: 'none' }}>
              <div className="card card-hover p-3" style={{ background: 'var(--bg)', boxShadow: 'inset 0 0 0 1px var(--border)' }}>
                <div className="flex items-center justify-between gap-3 mb-2">
                  <span className="flex items-center gap-2" style={{ fontSize: 13.5, fontWeight: 600 }}>
                    <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: 999, background: t.color }} />{t.name}
                  </span>
                  <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>{t.mastered}/{t.total}</span>
                </div>
                <div style={{ height: 7, borderRadius: 999, background: 'var(--bg-sunken)', overflow: 'hidden', position: 'relative' }}>
                  <div style={{ position: 'absolute', inset: 0, width: `${masteredPct}%`, background: t.color }} />
                  <div style={{ position: 'absolute', top: 0, bottom: 0, left: `${masteredPct}%`, width: `${progressPct}%`, background: t.color, opacity: 0.35 }} />
                </div>
              </div>
            </Link>
          );
        })}
      </div>
    </section>
  );
}
