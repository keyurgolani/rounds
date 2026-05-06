// Public read-only renderer for /r/:token. Fetches via the FastAPI
// share endpoint (which uses an admin-cached token to bypass PB
// owner rules), then renders the resume with the same template
// registry the editor uses — so what the recipient sees matches what
// the user designs.

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchPublicResume, type PublicResumePayload } from '../features/resume/share/client';
import { ResumePageStyles } from '../features/resume/templates/parts';
import { templateById } from '../features/resume/templates/registry';

export default function PublicResume() {
  const { token } = useParams<{ token: string }>();
  const [payload, setPayload] = useState<PublicResumePayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) return;
    setLoading(true);
    fetchPublicResume(token)
      .then(setPayload)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  if (loading) {
    return (
      <Center>
        <div style={{ color: 'var(--text-3)', fontSize: 13 }}>Loading…</div>
      </Center>
    );
  }
  if (error || !payload) {
    return (
      <Center>
        <div className="card" style={{ padding: 24, maxWidth: 480, textAlign: 'center' }}>
          <div className="eyebrow" style={{ fontSize: 9.5, marginBottom: 8 }}>
            Public resume
          </div>
          <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 6, color: 'var(--plum)' }}>
            Couldn't load this share
          </div>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-3)', lineHeight: 1.55 }}>
            {error || 'This link may have been deleted or never existed.'}
          </p>
        </div>
      </Center>
    );
  }

  const Template = templateById(payload.template_id).component;

  return (
    <div
      style={{
        minHeight: '100vh',
        background: 'var(--bg-sunken)',
        padding: '24px 16px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 16,
      }}
    >
      <ResumePageStyles />
      <div
        className="mono"
        style={{
          fontSize: 10.5,
          color: 'var(--text-4)',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
        }}
      >
        Shared resume {payload.kind === 'variant' ? '(variant)' : ''} · read-only
      </div>
      <Template data={payload.data} design={payload.design} />
    </div>
  );
}

function Center({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg)',
        padding: 24,
      }}
    >
      {children}
    </div>
  );
}
