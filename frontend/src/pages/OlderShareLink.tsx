// What an older share link's address opens, /r/<anything> (ROUNDS-00B-L06).
//
// Every link made before then stopped working for good, so this page is
// fixed: it reads nothing from the address, makes no request, and is the
// same for every value. A link made since is /r#<token>, which the share
// page resolves (pages/SharedArtifact).

import { ShareGone } from '../features/resume/share/ShareNotFound';

export default function OlderShareLink() {
  return <ShareGone />;
}
