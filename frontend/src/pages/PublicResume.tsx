// Public read-only renderer for /r/:token. Fetches via the FastAPI
// share endpoint (which uses an admin-cached token to bypass PB
// owner rules), then renders the resume inside the same `ZoomablePage`
// component the studio PreviewDialog uses — so what the recipient
// sees matches what the user designs, with the same zoom + fit + page-
// break markers and a "read-only" header bar.

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Eye } from 'lucide-react';
import {
  fetchPublicResume,
  type PublicResumePayload,
} from '../features/resume/share/client';
import ZoomablePage from '../features/resume/ZoomablePage';

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
          <div
            style={{
              fontSize: 14,
              fontWeight: 500,
              marginBottom: 6,
              color: 'var(--plum)',
            }}
          >
            Couldn't load this share
          </div>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-3)', lineHeight: 1.55 }}>
            {error || 'This link may have been deleted or never existed.'}
          </p>
        </div>
      </Center>
    );
  }

  // Full-viewport column: the ZoomablePage owns its toolbar + scroll
  // area and fills the remaining height via flex.
  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg)',
      }}
    >
      <ZoomablePage
        data={payload.data}
        templateId={payload.template_id}
        design={payload.design}
        toolbarLabel={`Shared ${payload.kind === 'variant' ? 'variant' : 'resume'} · read-only`}
        toolbarActions={
          <span
            className="inline-flex items-center gap-1.5"
            title="This view is shared via a public link"
            style={{
              padding: '6px 10px',
              borderRadius: 8,
              background: 'var(--bg-sunken)',
              color: 'var(--text-3)',
              boxShadow: 'inset 0 0 0 1px var(--border)',
              fontSize: 11,
              fontWeight: 500,
            }}
          >
            <Eye size={12} strokeWidth={1.8} />
            Read-only
          </span>
        }
      />
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
