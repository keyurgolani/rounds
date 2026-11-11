// The Share Capability page, /r#<token> (ROUNDS-00B-L03 stage 2).
//
// The token is read from the address's fragment, which the browser never
// sends to a server. Without one there's no request at all. With one, the
// page makes one POST to the resolver with the token in its body, and
// shows the snapshot it answers in SharedArtifactFrame, or the one fixed
// not-found page for any other answer, with nothing from the response.
//
// ROUNDS-00B-L04: a link with a password answers that same not-found until
// the password comes with it, so the not-found page carries a password
// field (SharePasswordForm). A throttled resolve says only how long to
// wait: "Too many attempts. Try again in N minutes."

import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { resolveSharedArtifact, ShareThrottled } from '../features/resume/share/client';
import SharedArtifactFrame from '../features/resume/share/SharedArtifactFrame';
import SharePasswordForm from '../features/resume/share/SharePasswordForm';
import { ShareLoading, ShareNotFound, ShareThrottled as ShareThrottledPage } from '../features/resume/share/ShareNotFound';

type State =
  | { kind: 'loading' }
  | { kind: 'missing' }
  | { kind: 'throttled'; minutes: number }
  | { kind: 'found'; markup: string };

export default function SharedArtifact() {
  const { hash } = useLocation();
  const token = hash.startsWith('#') ? hash.slice(1) : '';
  const [state, setState] = useState<State>(token ? { kind: 'loading' } : { kind: 'missing' });

  useEffect(() => {
    if (!token) {
      setState({ kind: 'missing' });
      return;
    }
    let live = true;
    setState({ kind: 'loading' });
    resolveSharedArtifact(token)
      .then((artifact) => live && setState({ kind: 'found', markup: artifact.markup }))
      .catch((err) => {
        if (!live) return;
        setState(err instanceof ShareThrottled ? { kind: 'throttled', minutes: err.minutes } : { kind: 'missing' });
      });
    return () => {
      live = false;
    };
  }, [token]);

  if (state.kind === 'loading') return <ShareLoading />;
  if (state.kind === 'throttled') return <ShareThrottledPage minutes={state.minutes} />;
  if (state.kind === 'missing') {
    return (
      <ShareNotFound>
        {token && <SharePasswordForm token={token} onOpen={(markup) => setState({ kind: 'found', markup })} />}
      </ShareNotFound>
    );
  }
  return (
    <main
      style={{
        position: 'fixed',
        inset: 0,
        display: 'flex',
        flexDirection: 'column',
        background: 'var(--bg)',
      }}
    >
      <SharedArtifactFrame markup={state.markup} />
    </main>
  );
}
