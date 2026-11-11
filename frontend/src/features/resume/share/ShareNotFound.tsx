// The one page every unavailable share gets, on both share pages
// (pages/PublicResume and pages/SharedArtifact, ROUNDS-00B-L03). The server
// answers one not-found for every reason, and nothing from a response is
// shown. Focus lands on the heading so a screen reader announces it right
// away. The share capability page puts its password field under the
// message, and a throttled resolve gets the same page with its own words
// (ROUNDS-00B-L04).

import { useEffect, useRef, type ReactNode } from 'react';

export const SHARE_NOT_FOUND_HEADING = 'This link isn’t available';
export const SHARE_NOT_FOUND_MESSAGE =
  'It may have been turned off, or the address may be incomplete. Ask the person who shared it for a new link.';
export const SHARE_THROTTLED_HEADING = 'Too many attempts';

/** "Too many attempts. Try again in N minutes." */
export function throttledText(minutes: number): string {
  return `Too many attempts. Try again in ${minutes} ${minutes === 1 ? 'minute' : 'minutes'}.`;
}

export function ShareNotFound({ children }: { children?: ReactNode }) {
  return (
    <ShareMessage heading={SHARE_NOT_FOUND_HEADING} message={SHARE_NOT_FOUND_MESSAGE}>
      {children}
    </ShareMessage>
  );
}

export function ShareThrottled({ minutes }: { minutes: number }) {
  return <ShareMessage heading={SHARE_THROTTLED_HEADING} message={throttledText(minutes)} />;
}

function ShareMessage({ heading: text, message, children }: { heading: string; message: string; children?: ReactNode }) {
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
          {text}
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
          {message}
        </p>
        {children}
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
