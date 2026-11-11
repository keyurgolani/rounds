// Where a graded result's rubric review stands (ROUNDS-00A-L03 PR 3), in
// its report: reviewing, not asked for yet, no AI provider set up, files
// changed since the grade, a review that didn't finish or that this
// server can't give, a limit, or a review that couldn't start. Asking
// again is offered where it can help.
//
// The region is a polite live region that stays in the report, so a
// screen reader hears the review land; a finished review says so to
// screen readers only, since the report shows it. Every state has an
// icon and a written title, so color is never the only signal.

import type { CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import {
  CircleSlash,
  CloudOff,
  FileDiff,
  Hourglass,
  KeyRound,
  MessageSquareDashed,
  MessageSquareOff,
  RotateCcw,
  ScanText,
  type LucideIcon,
} from 'lucide-react';
import type { ReviewStatus } from '../../hooks/useRubricReview';
import { formatWait } from '../../lib/runnerDenial';

interface ReviewCopy {
  icon: LucideIcon;
  title: string;
  body: string;
  /** Offers to ask again. */
  again?: 'retry' | 'request';
  settings?: boolean;
}

/** What a review state shows; null for a review the report shows itself. */
export function reviewCopy(status: ReviewStatus, retryAfterSeconds: number | null = null): ReviewCopy | null {
  switch (status) {
    case 'reviewed':
      return null;
    case 'reviewing':
      return {
        icon: ScanText,
        title: 'Reviewing',
        body: 'Your AI provider is reviewing this submission against the rubric. It can take up to a minute.',
      };
    case 'not_requested':
      return {
        icon: MessageSquareDashed,
        title: 'Not reviewed yet',
        body: "This submission doesn't have its rubric review yet. Your files have to be the ones you submitted.",
        again: 'request',
      };
    case 'no_provider':
      return {
        icon: KeyRound,
        title: 'No AI provider set up',
        body: 'Add one in Settings to get a rubric review of your submissions.',
        settings: true,
      };
    case 'files_changed':
      return {
        icon: FileDiff,
        title: 'Files changed',
        body: "Your files changed after this submission, so it can't be reviewed. Submit again to review them.",
      };
    case 'lost':
      return {
        icon: MessageSquareOff,
        title: "Review didn't finish",
        body: "The review didn't finish, so this submission has no review.",
      };
    case 'not_reviewable':
      return {
        icon: CircleSlash,
        title: "Can't review here",
        body: "This submission can't be reviewed on this server.",
      };
    case 'limit':
      return {
        icon: Hourglass,
        title: 'Limit reached',
        body: `You've reached the review limit for now. Try again ${formatWait(retryAfterSeconds)}. Your submission is graded.`,
        again: 'retry',
      };
    case 'unavailable':
      return {
        icon: CloudOff,
        title: 'Review unavailable',
        body: "The review couldn't start right now. Your submission is graded.",
        again: 'retry',
      };
  }
}

interface ReviewStatusNoteProps {
  status: ReviewStatus | null;
  retryAfterSeconds?: number | null;
  onRetry?: () => void;
  onRequest?: () => void;
  style?: CSSProperties;
}

export function ReviewStatusNote({ status, retryAfterSeconds = null, onRetry, onRequest, style }: ReviewStatusNoteProps) {
  const copy = status === null ? null : reviewCopy(status, retryAfterSeconds);
  const action = copy?.again === 'request' ? onRequest : copy?.again === 'retry' ? onRetry : undefined;
  const Icon = copy?.icon;
  return (
    <div role="status" aria-live="polite" aria-atomic="true" data-testid="review-status" data-review={status ?? ''}>
      {status === 'reviewed' && <span className="sr-only">Reviewed. The rubric review is ready.</span>}
      {copy && Icon && (
        <div
          style={{
            display: 'flex',
            gap: 10,
            alignItems: 'flex-start',
            padding: '10px 12px',
            borderRadius: 'var(--radius)',
            background: 'var(--bg-elev)',
            boxShadow: 'inset 0 0 0 1px var(--border-strong)',
            fontSize: 12.5,
            lineHeight: 1.45,
            color: 'var(--text-2)',
            ...style,
          }}
        >
          <Icon
            aria-hidden="true"
            size={16}
            strokeWidth={1.8}
            style={{ flexShrink: 0, marginTop: 1, color: status === 'reviewing' ? 'var(--ochre)' : 'var(--text-3)' }}
          />
          <div style={{ minWidth: 0, flex: 1 }}>
            <strong style={{ display: 'block', color: 'var(--text)', fontWeight: 600 }}>
              {copy.title}
              <span className="sr-only">. </span>
            </strong>
            <span>{copy.body}</span>
            {(action || copy.settings) && (
              <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                {action && (
                  <button type="button" onClick={action} style={actionStyle}>
                    <RotateCcw aria-hidden="true" size={12} strokeWidth={1.8} />
                    {copy.again === 'request' ? 'Request review' : 'Try again'}
                  </button>
                )}
                {copy.settings && (
                  <Link to="/settings" style={actionStyle}>
                    <KeyRound aria-hidden="true" size={12} strokeWidth={1.8} />
                    Open settings
                  </Link>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const actionStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  minHeight: 32,
  padding: '6px 12px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'transparent',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
  color: 'var(--text)',
  fontSize: 12,
  fontWeight: 500,
  cursor: 'pointer',
  textDecoration: 'none',
} as const;
