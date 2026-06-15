// src/components/dashboard/ResumeCoverage.tsx
import { Link } from 'react-router-dom';
import type { ResumeCoverageResult } from './derive';

function ago(iso: string | null): string {
  if (!iso) return 'never';
  const t = Date.parse(iso);
  if (Number.isNaN(t)) return 'never';
  const days = Math.floor((Date.now() - t) / 86_400_000);
  return days <= 0 ? 'today' : days === 1 ? '1d ago' : `${days}d ago`;
}

export default function ResumeCoverage({ coverage }: { coverage: ResumeCoverageResult }) {
  return (
    <section className="card card-pad-lg fade-up">
      <div className="flex items-center justify-between" style={{ marginBottom: 8 }}>
        <h2 className="display" style={{ margin: 0, fontSize: 18, fontWeight: 400 }}>Resume coverage</h2>
        <Link to="/resumes" className="mono uppercase" style={{ fontSize: 10, color: 'var(--text-3)', letterSpacing: '0.1em', textDecoration: 'none' }}>Resumes →</Link>
      </div>
      {coverage.resumeCount === 0 ? (
        <div style={{ fontSize: 12.5, color: 'var(--text-3)' }}>
          No resumes yet. <Link to="/resumes" style={{ color: 'var(--accent)' }}>Create your first resume →</Link>
        </div>
      ) : (
        <>
          <div style={{ fontSize: 12.5, color: 'var(--text-2)' }}>
            <b>{coverage.resumeCount}</b> {coverage.resumeCount === 1 ? 'resume' : 'resumes'} · last edited {ago(coverage.lastEditedAt)} · <b>{coverage.covered} / {coverage.relevant}</b> active apps have a tailored variant
          </div>
          {coverage.missing.length > 0 && (
            <div style={{ marginTop: 9 }}>
              <div className="eyebrow mb-1">Missing a tailored resume</div>
              <div className="flex flex-wrap gap-1.5">
                {coverage.missing.map((m) => (
                  <Link key={m.id} to={`/applications/${m.id}`} className="pill" style={{ background: 'var(--accent-soft)', color: 'var(--accent)', textDecoration: 'none' }}>{m.company}</Link>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </section>
  );
}
