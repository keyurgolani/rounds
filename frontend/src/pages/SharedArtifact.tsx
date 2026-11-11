// The Share Capability page, /r#<token> (ROUNDS-00B-L03 stage 2).
//
// The token is read from the address's fragment, which the browser never
// sends to a server. Without one there's no request at all. With one, the
// page makes one POST to the resolver with the token in its body, and
// shows the snapshot it answers in SharedArtifactFrame, or the one fixed
// not-found page for any other answer, with nothing from the response.

import { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { resolveSharedArtifact } from '../features/resume/share/client';
import SharedArtifactFrame from '../features/resume/share/SharedArtifactFrame';
import { ShareLoading, ShareNotFound } from '../features/resume/share/ShareNotFound';

type State = { kind: 'loading' } | { kind: 'missing' } | { kind: 'found'; markup: string };

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
      .catch(() => live && setState({ kind: 'missing' }));
    return () => {
      live = false;
    };
  }, [token]);

  if (state.kind === 'loading') return <ShareLoading />;
  if (state.kind === 'missing') return <ShareNotFound />;
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
