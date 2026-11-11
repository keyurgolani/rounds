// Public read-only renderer for /r/:token. Fetches the link's projection
// (only the resume data, template, and design) from the runner, then
// renders it inside the same `ZoomablePage` component the studio
// PreviewDialog uses, so what the recipient sees matches what the user
// designs, with a read-only header bar.
//
// Every failure shows the same fixed page: the server answers one
// not-found for every reason, and nothing from a response is shown.

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  fetchPublicResume,
  type PublicResumePayload,
} from '../features/resume/share/client';
import { ReadOnlyBadge, SHARE_TOOLBAR_LABEL } from '../features/resume/share/ReadOnlyBadge';
import { ShareLoading, ShareNotFound } from '../features/resume/share/ShareNotFound';
import ZoomablePage from '../features/resume/ZoomablePage';

export { SHARE_TOOLBAR_LABEL } from '../features/resume/share/ReadOnlyBadge';
export {
  SHARE_NOT_FOUND_HEADING,
  SHARE_NOT_FOUND_MESSAGE,
  ShareNotFound,
} from '../features/resume/share/ShareNotFound';

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
    return <ShareLoading />;
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
        toolbarActions={<ReadOnlyBadge />}
      />
    </div>
  );
}
