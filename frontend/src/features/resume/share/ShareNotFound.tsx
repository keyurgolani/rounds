// The one page every unavailable share gets, on both share pages
// (pages/PublicResume and pages/SharedArtifact, ROUNDS-00B-L03). The server
// answers one not-found for every reason, and nothing from a response is
// shown. Focus lands on the heading so a screen reader announces it right
// away.

import { useEffect, useRef } from 'react';

export const SHARE_NOT_FOUND_HEADING = 'This link isn’t available';
export const SHARE_NOT_FOUND_MESSAGE =
  'It may have been turned off, or the address may be incomplete. Ask the person who shared it for a new link.';

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

// What both share pages show while their one request is out.
export function ShareLoading() {
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
      <div role="status" style={{ color: 'var(--text-3)', fontSize: 13 }}>
        Loading…
      </div>
    </div>
  );
}
