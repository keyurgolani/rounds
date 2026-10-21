// Denial states for the runner surfaces (ROUNDS-00A-L01): sign in
// again, limit reached with the wait, turned off, unavailable with the
// draft kept, too large, and not available for this account. The
// definition states (ROUNDS-00A-L02) add reload for an out-of-date page,
// with a Reload button that saves the draft first when the page passes
// `onReload` (a page whose save failed stays and says so, keeping the
// button), and retired, not here, unsupported, and file not allowed.
//
// The live region is always in the DOM, so screen readers announce a
// denial when it appears. The notice never takes focus. If the action
// dropped focus (its button was disabled while it ran) and nothing else
// took it, focus goes back to the control that started the action.
// Every state has an icon and a written title, so color is never the
// only signal.

import { useEffect, type CSSProperties } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Archive,
  CloudOff,
  FileX,
  Hourglass,
  Languages,
  Lock,
  LogIn,
  PowerOff,
  Printer,
  RotateCw,
  Scaling,
  SearchX,
  type LucideIcon,
} from 'lucide-react';
import { formatWait, type RunnerDenial, type RunnerDenialKind } from '../../lib/runnerDenial';
import { reloadPage } from '../../lib/definitions';

export type RunnerAction = 'run' | 'tests' | 'grade' | 'pdf';

interface ActionText {
  /** What the user tried, as in "Running code is turned off". */
  subject: string;
  /** What didn't happen. */
  none: string;
  /** What survives a failed attempt. */
  kept: string;
  /** Why a too-large request stopped. */
  tooLarge: string;
}

const ACTION_TEXT: Record<RunnerAction, ActionText> = {
  run: {
    subject: 'Running code',
    none: 'Nothing ran.',
    kept: 'Your code is still here.',
    tooLarge: 'Your code or input is over the size limit, so nothing ran. Shorten it and try again.',
  },
  tests: {
    subject: 'Running tests',
    none: 'No tests ran.',
    kept: 'Your code is still here.',
    tooLarge: 'Your code is over the size limit, so no tests ran. Shorten it and try again.',
  },
  grade: {
    subject: 'Grading',
    none: 'Nothing was graded.',
    kept: 'Your files and notes are still here.',
    tooLarge: 'Your files are over the size limit, so nothing was graded. Trim them and try again.',
  },
  pdf: {
    subject: 'Server PDF export',
    none: 'No PDF was made.',
    kept: 'Your resume is unchanged.',
    tooLarge: 'This resume is over the size limit, so no PDF was made. Shorten it and try again.',
  },
};

const ICONS: Record<RunnerDenialKind, LucideIcon> = {
  sign_in: LogIn,
  limit: Hourglass,
  turned_off: PowerOff,
  unavailable: CloudOff,
  too_large: Scaling,
  not_permitted: Lock,
  reload: RotateCw,
  retired: Archive,
  not_found: SearchX,
  unsupported: Languages,
  path_not_allowed: FileX,
};

function copyFor(denial: RunnerDenial, action: RunnerAction): { title: string; body: string } {
  const text = ACTION_TEXT[action];
  switch (denial.kind) {
    case 'sign_in':
      return {
        title: 'Sign in again',
        body: `Your session has ended. ${text.none} ${text.kept}`,
      };
    case 'limit':
      return {
        title: 'Limit reached',
        body: `You've reached the limit for now. Try again ${formatWait(denial.retryAfterSeconds)}. ${text.kept}`,
      };
    case 'turned_off':
      return {
        title: 'Turned off',
        body: `${text.subject} is turned off on this server. ${text.kept}`,
      };
    case 'unavailable':
      return {
        title: 'Unavailable right now',
        body: `${text.none} ${text.kept} Try again in a moment.`,
      };
    case 'too_large':
      return {
        title: 'Too large',
        body: text.tooLarge,
      };
    case 'not_permitted':
      return {
        title: 'Not available',
        body: `${text.subject} isn't available for this account.`,
      };
    case 'reload':
      if (denial.saveFailed) {
        return {
          title: 'Draft not saved',
          body: `Your draft couldn't be saved, so the page didn't reload. ${text.kept} Try Reload again.`,
        };
      }
      return {
        title: 'Reload to continue',
        body: `This page is out of date. ${text.none} ${text.kept}`,
      };
    case 'retired':
      return {
        title: 'Retired',
        body: `This practice item was retired, so it no longer runs. ${text.kept}`,
      };
    case 'not_found':
      return {
        title: 'Not on this server',
        body: `This server doesn't have this practice item in this language. ${text.none} ${text.kept}`,
      };
    case 'unsupported':
      return {
        title: 'Language not supported',
        body: `${denial.detail ?? "This language isn't supported here."} ${text.none} ${text.kept}`,
      };
    case 'path_not_allowed':
      return {
        title: 'File not allowed',
        body: `${denial.detail ?? "A file in this submission can't be sent."} ${text.none} ${text.kept}`,
      };
  }
}

interface RunnerDenialNoticeProps {
  denial: RunnerDenial | null;
  action: RunnerAction;
  /** PDF export offers browser printing when the server can't render. */
  onPrint?: () => void;
  /** What Reload does for an out-of-date page; pages save the draft
   *  first. Defaults to reloading the page. */
  onReload?: () => void | Promise<void>;
  signInHref?: string;
  /** Classes for the live region, which is always in the DOM. */
  className?: string;
  /** Extra style for the notice itself, such as its top margin. */
  contentStyle?: CSSProperties;
}

export function RunnerDenialNotice({
  denial,
  action,
  onPrint,
  onReload,
  signInHref = '/login',
  className,
  contentStyle,
}: RunnerDenialNoticeProps) {
  const location = useLocation();
  useEffect(() => {
    const trigger = denial?.trigger;
    if (!trigger || !trigger.isConnected) return;
    const active = document.activeElement;
    if (active && active !== document.body && active !== trigger) return;
    if ((trigger as HTMLButtonElement).disabled) return;
    trigger.focus({ preventScroll: true });
  }, [denial]);

  const content = denial ? copyFor(denial, action) : null;
  const Icon = denial ? ICONS[denial.kind] : null;
  const offerPrint =
    action === 'pdf' &&
    Boolean(onPrint) &&
    denial !== null &&
    (denial.kind === 'turned_off' || denial.kind === 'unavailable');

  return (
    <div
      role="status"
      aria-live="polite"
      aria-atomic="true"
      data-testid="runner-denial"
      className={className}
    >
      {denial && content && Icon && (
        <div
          data-denial={denial.kind}
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
            ...contentStyle,
          }}
        >
          <Icon aria-hidden="true" size={16} strokeWidth={1.8} style={{ flexShrink: 0, marginTop: 1 }} />
          <div style={{ minWidth: 0, flex: 1 }}>
            <strong style={{ display: 'block', color: 'var(--text)', fontWeight: 600 }}>
              {content.title}
              {/* Ends the title when a screen reader reads the region in one pass. */}
              <span className="sr-only">. </span>
            </strong>
            <span>{content.body}</span>
            {denial.correlationId && (
              <span
                className="mono"
                style={{ display: 'block', marginTop: 2, fontSize: 10.5, color: 'var(--text-4)' }}
              >
                Reference {denial.correlationId.slice(0, 8)}
              </span>
            )}
            {(denial.kind === 'sign_in' || denial.kind === 'reload' || offerPrint) && (
              <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                {denial.kind === 'reload' && (
                  <button
                    type="button"
                    onClick={() => void (onReload ? onReload() : reloadPage())}
                    style={actionStyle}
                  >
                    <RotateCw aria-hidden="true" size={12} strokeWidth={1.8} />
                    Reload
                  </button>
                )}
                {denial.kind === 'sign_in' && (
                  <Link
                    to={signInHref}
                    state={{ from: location.pathname }}
                    style={actionStyle}
                  >
                    <LogIn aria-hidden="true" size={12} strokeWidth={1.8} />
                    Sign in
                  </Link>
                )}
                {offerPrint && (
                  <button type="button" onClick={onPrint} style={actionStyle}>
                    <Printer aria-hidden="true" size={12} strokeWidth={1.8} />
                    Print to PDF instead
                  </button>
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
