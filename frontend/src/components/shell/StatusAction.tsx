import { usePracticeStatus, type PracticeKind } from '../../hooks/usePracticeStatus';
import PracticeStatusControl from './PracticeStatusControl';

// Shared wrapper used by every detail page's AppHeader action slots so
// per-track local versions don't drift in behavior. The detail pages
// share one contract: "render the status control for this track +
// numeric question id, defaulting to todo". `compact` swaps the 3-pill
// expanded control for a single glyph that fits the 44px focus-mode
// header.
export default function StatusAction({
  kind,
  id,
  compact = false,
}: {
  kind: PracticeKind;
  id: number | string;
  compact?: boolean;
}) {
  const [status, setStatus] = usePracticeStatus(kind, id, 'todo');
  return <PracticeStatusControl status={status} onChange={setStatus} compact={compact} />;
}
