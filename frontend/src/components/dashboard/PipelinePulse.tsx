// src/components/dashboard/PipelinePulse.tsx
import { Link } from 'react-router-dom';

const STATUSES = ['Wishlist', 'Applied', 'Interviewing', 'Offer'] as const;
const COLOR: Record<string, string> = {
  Wishlist: 'var(--text-4)', Applied: 'var(--ochre)', Interviewing: 'var(--accent)', Offer: 'var(--forest)',
};

export default function PipelinePulse({ counts }: { counts: Record<string, number> }) {
  const total = Math.max(STATUSES.reduce((n, s) => n + (counts[s] ?? 0), 0), 1);
  return (
    <section className="card card-pad-lg fade-up">
      <div className="flex items-center justify-between" style={{ marginBottom: 'var(--gap-sm)' }}>
        <h2 className="display" style={{ margin: 0, fontSize: 18, fontWeight: 400 }}>Pipeline pulse</h2>
        <Link to="/applications" className="mono uppercase" style={{ fontSize: 10, color: 'var(--text-3)', letterSpacing: '0.1em', textDecoration: 'none' }}>Applications →</Link>
      </div>
      <div className="grid gap-2">
        {STATUSES.map((s) => {
          const count = counts[s] ?? 0;
          return (
            <div key={s}>
              <div className="flex items-center justify-between mb-1.5">
                <span style={{ fontSize: 12.5, color: 'var(--text-2)' }}>{s}</span>
                <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>{count}</span>
              </div>
              <div style={{ height: 6, borderRadius: 999, background: 'var(--bg-sunken)', overflow: 'hidden' }}>
                <div style={{ width: `${(count / total) * 100}%`, height: '100%', background: COLOR[s], opacity: 0.85 }} />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
