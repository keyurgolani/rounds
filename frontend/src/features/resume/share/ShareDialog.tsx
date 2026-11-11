// The share dialog for the active resume: the share links dialog
// (ROUNDS-00B-L04), with the resume's older links under its own links
// (ROUNDS-00B-L06). With share capability resolution off, it says sharing
// is turned off and offers no create.

import ShareLinksDialog from './ShareLinksDialog';

type Props = {
  open: boolean;
  onClose: () => void;
  resumeId: string;
};

export default function ShareDialog(props: Props) {
  return <ShareLinksDialog {...props} />;
}
