// The password field under the share page's not-found message
// (ROUNDS-00B-L04). A protected link answers the same not-found as an
// unknown one until its password comes with it, so the page always offers
// the field and never says which it was. The password goes only in the
// resolve's body. What the page shows for a failure is fixed text: never
// anything from the server.

import { useId, useState, type FormEvent } from 'react';
import { resolveSharedArtifact, ShareThrottled } from './client';
import { throttledText } from './ShareNotFound';

export const SHARE_PASSWORD_HINT = 'If the person who shared this link gave you a password, enter it.';
export const SHARE_PASSWORD_RETRY = 'That didn’t open it. Check the password, or ask for a new link.';

export default function SharePasswordForm({ token, onOpen }: { token: string; onOpen: (markup: string) => void }) {
  const inputId = useId();
  const hintId = useId();
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!password || busy) return;
    setBusy(true);
    setMessage(null);
    try {
      const artifact = await resolveSharedArtifact(token, password);
      onOpen(artifact.markup);
    } catch (err) {
      setMessage(err instanceof ShareThrottled ? throttledText(err.minutes) : SHARE_PASSWORD_RETRY);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} style={{ marginTop: 22, display: 'flex', flexDirection: 'column', gap: 8 }}>
      <label htmlFor={inputId} style={{ fontSize: 14, fontWeight: 500, color: 'var(--text)' }}>
        Password
      </label>
      <span id={hintId} style={{ fontSize: 13.5, lineHeight: 1.55, color: 'var(--text-2)' }}>
        {SHARE_PASSWORD_HINT}
      </span>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          id={inputId}
          type="password"
          value={password}
          onChange={(e) => {
            setPassword(e.target.value);
            setMessage(null);
          }}
          autoComplete="off"
          aria-describedby={hintId}
          className="share-input"
          style={{ flex: 1, minWidth: 0 }}
        />
        <button type="submit" disabled={busy || !password} className="share-btn share-btn-primary">
          {busy ? 'Opening…' : 'Open'}
        </button>
      </div>
      {message && (
        <p role="alert" style={{ margin: 0, fontSize: 13.5, lineHeight: 1.5, color: 'var(--plum)' }}>
          {message}
        </p>
      )}
    </form>
  );
}
