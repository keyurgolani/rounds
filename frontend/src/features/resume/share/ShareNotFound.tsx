// The one page every unavailable share gets on the share page
// (pages/SharedArtifact, ROUNDS-00B-L03). The server answers one not-found
// for every reason, and nothing from a response is shown. Focus lands on
// the heading so a screen reader announces it right away. The share page
// puts its password field under the message, and a throttled resolve gets
// the same page with its own words (ROUNDS-00B-L04). An older link's
// address gets ShareGone, in the same layout (ROUNDS-00B-L06).

import { useEffect, useRef, type ReactNode } from 'react';

export const SHARE_NOT_FOUND_HEADING = 'This link isn’t available';
export const SHARE_NOT_FOUND_MESSAGE =
  'It may have been turned off, or the address may be incomplete. Ask the person who shared it for a new link.';
export const SHARE_THROTTLED_HEADING = 'Too many attempts';
export const SHARE_GONE_HEADING = 'This link no longer works';
export const SHARE_GONE_MESSAGE = 'Ask the person who shared it for a new one.';

/** "Wait N minutes, then try again.", under the throttled page's heading. */
export function throttledWait(minutes: number): string {
  return `Wait ${minutes} ${minutes === 1 ? 'minute' : 'minutes'}, then try again.`;
}

/** "Too many attempts. Wait N minutes, then try again.", where no heading
 *  says it first. */
export function throttledText(minutes: number): string {
  return `${SHARE_THROTTLED_HEADING}. ${throttledWait(minutes)}`;
}

export function ShareNotFound({ children }: { children?: ReactNode }) {
  return (
    <ShareMessage heading={SHARE_NOT_FOUND_HEADING} message={SHARE_NOT_FOUND_MESSAGE}>
      {children}
    </ShareMessage>
  );
}

export function ShareThrottled({ minutes }: { minutes: number }) {
  return <ShareMessage heading={SHARE_THROTTLED_HEADING} message={throttledWait(minutes)} />;
}

/** What an older link's address opens: the same page for every one. */
export function ShareGone() {
  return <ShareMessage heading={SHARE_GONE_HEADING} message={SHARE_GONE_MESSAGE} />;
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

// What the share page shows while its one request is out.
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
