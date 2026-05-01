import { Sparkles } from 'lucide-react';
import AppHeader from '../components/shell/AppHeader';
import PageShell from '../components/shell/PageShell';

export default function AICoding() {
  return (
    <PageShell
      header={
        <AppHeader
          eyebrow="Track 04 · AI Assisted Coding"
          title="AI Assisted Coding"
          description="Pair-programming style problems where you reason out loud with an AI partner and the bar is judgment, not raw recall."
        />
      }
    >
      <div className="px-5 sm:px-8 py-10 flex justify-center">
        <div
          className="card text-center"
          style={{
            padding: '56px 32px',
            maxWidth: 560,
            background: 'var(--bg-elev)',
          }}
        >
          <div className="flex justify-center mb-4">
            <span
              className="inline-flex items-center justify-center"
              style={{
                width: 56,
                height: 56,
                borderRadius: 999,
                background: 'var(--accent-soft)',
                color: 'var(--accent)',
              }}
            >
              <Sparkles size={24} strokeWidth={1.6} />
            </span>
          </div>
          <span
            className="pill"
            style={{
              background: 'var(--accent-soft)',
              color: 'var(--accent)',
              fontSize: 10.5,
              letterSpacing: '0.12em',
            }}
          >
            COMING SOON
          </span>
          <div
            className="display-italic"
            style={{
              fontSize: 30,
              fontWeight: 400,
              margin: '14px 0 8px',
              lineHeight: 1.1,
            }}
          >
            A new track is on the way.
          </div>
          <p
            style={{
              margin: '0 auto',
              fontSize: 13.5,
              color: 'var(--text-3)',
              maxWidth: 440,
              lineHeight: 1.6,
            }}
          >
            AI Assisted Coding rounds are becoming the new normal — interviewers want to see how
            you collaborate with a model, prompt for tradeoffs, and catch the things it gets
            wrong. We're building a focused track for exactly that. Stay tuned.
          </p>
        </div>
      </div>
    </PageShell>
  );
}
