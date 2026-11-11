// Public read-only renderer for /r/:token. Fetches the link's projection
// (only the resume data, template, and design) from the runner, then
// renders it inside the same `ZoomablePage` component the studio
// PreviewDialog uses, so what the recipient sees matches what the user
// designs, with a read-only header bar.
//
// Every failure shows the same fixed page: the server answers one
// not-found for every reason, and nothing from a response is shown.

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { Eye } from 'lucide-react';
import {
  fetchPublicResume,
  type PublicResumePayload,
} from '../features/resume/share/client';
import ZoomablePage from '../features/resume/ZoomablePage';

export const SHARE_NOT_FOUND_HEADING = 'This link isn’t available';
export const SHARE_NOT_FOUND_MESSAGE =
  'It may have been turned off, or the address may be incomplete. Ask the person who shared it for a new link.';
export const SHARE_TOOLBAR_LABEL = 'Shared resume, read-only';

export default function PublicResume() {
  const { token } = useParams<{ token: string }>();
  const [payload, setPayload] = useState<PublicResumePayload | null>(null);
  const [failed, setFailed] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!token) {
      setFailed(true);
      setLoading(false);
      return;
    }
    let live = true;
    setLoading(true);
    setFailed(false);
    fetchPublicResume(token)
      .then((p) => live && setPayload(p))
      .catch(() => live && setFailed(true))
      .finally(() => live && setLoading(false));
    return () => {
      live = false;
    };
  }, [token]);

  if (loading) {
    return (
      <Center>
        <div role="status" style={{ color: 'var(--text-3)', fontSize: 13 }}>
          Loading…
        </div>
      </Center>
    );
  }
  if (failed || !payload) {
    return <ShareNotFound />;
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
        toolbarLabel={SHARE_TOOLBAR_LABEL}
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
            <Eye size={12} strokeWidth={1.8} aria-hidden="true" />
            Read-only
          </span>
        }
      />
    </div>
  );
}

// The one page every unavailable link gets. Focus lands on the heading so
// a screen reader announces it right away.
export function ShareNotFound() {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
  }, []);
  return (
    <main
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--bg)',
        padding: '48px 24px',
        boxSizing: 'border-box',
      }}
    >
      <div style={{ width: '100%', maxWidth: 440 }}>
        <h1
          ref={heading}
          tabIndex={-1}
          style={{
            margin: 0,
            fontFamily: 'var(--font-display)',
            fontWeight: 400,
            fontSize: 'clamp(28px, 6vw, 36px)',
            lineHeight: 1.15,
            letterSpacing: '-0.01em',
            color: 'var(--text)',
            textWrap: 'balance',
            outline: 'none',
          }}
        >
          {SHARE_NOT_FOUND_HEADING}
        </h1>
        <p
          style={{
            margin: '14px 0 0',
            paddingTop: 14,
            borderTop: '1px solid var(--border)',
            fontSize: 14,
            lineHeight: 1.6,
            color: 'var(--text-2)',
            textWrap: 'pretty',
          }}
        >
          {SHARE_NOT_FOUND_MESSAGE}
        </p>
      </div>
    </main>
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
