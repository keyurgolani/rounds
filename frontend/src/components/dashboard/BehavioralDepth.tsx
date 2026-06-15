// src/components/dashboard/BehavioralDepth.tsx
import { Link } from 'react-router-dom';
import type { BehavioralDepthResult } from './derive';

export default function BehavioralDepth({ depth }: { depth: BehavioralDepthResult }) {
  return (
    <section className="card card-pad-lg fade-up">
      <div className="flex items-center justify-between" style={{ marginBottom: 8 }}>
        <h2 className="display" style={{ margin: 0, fontSize: 18, fontWeight: 400 }}>Behavioral prep depth</h2>
        <Link to="/behavioral/questions" className="mono uppercase" style={{ fontSize: 10, color: 'var(--text-3)', letterSpacing: '0.1em', textDecoration: 'none' }}>Stories →</Link>
      </div>
      <div className="t2" style={{ fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.5 }}>
        <b>{depth.covered} / {depth.total}</b> questions have a linked story · <b>{depth.storyCount}</b> stories across {depth.categoryCount} categories
      </div>
      {depth.thinCategories.length > 0 && (
        <div style={{ marginTop: 9 }}>
          <div className="eyebrow mb-1">Thin categories</div>
          <div className="flex flex-wrap gap-1.5">
            {depth.thinCategories.map((c) => (
              <span key={c.id} className="pill" style={{ background: 'transparent', color: c.color ?? 'var(--text-3)', boxShadow: `inset 0 0 0 1px ${c.color ?? 'var(--border-strong)'}` }}>
                {c.name} · {c.count}
              </span>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
