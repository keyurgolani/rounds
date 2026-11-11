// The share links dialog while share capability resolution is on
// (ROUNDS-00B-L04). A link's secret is shown once:
//
//   - Create link makes one with an optional expiry and password, under
//     one Idempotency-Key per form. A retry of the same form reuses the
//     key and answers already-issued, never the secret again; any edit
//     mints a new key.
//   - The secret appears only in the show-once panel, in this
//     component's state. Nothing copies it for you, and "I saved this
//     link" is the panel's only way out; closing it drops the secret.
//   - Each live row can be rotated (a new link, one key per click; the
//     old link stops working) or revoked. Expired, revoked, and source
//     deleted rows only show their state.
//
// The panel is the dialog: it traps focus, takes Escape and the backdrop
// only while no secret shows, and gives focus back to what opened it.

import { useCallback, useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from 'react';
import { Check, Copy, KeyRound, Link2, X } from 'lucide-react';
import { isRunnerError } from '../../../lib/runnerFetch';
import { mintIdempotencyKey } from '../../../lib/idempotency';
import {
  buildCapabilityUrl,
  capabilityState,
  createCapability,
  expiryDay,
  listCapabilities,
  parseShareDate,
  revokeCapability,
  rotateCapability,
  type CapabilityState,
  type IssuedFields,
  type ShareCapability,
} from './client';

type Props = {
  open: boolean;
  onClose: () => void;
  resumeId: string;
};

export const EXPIRY_CHOICES = [
  { days: 7, label: 'In 7 days' },
  { days: 30, label: 'In 30 days' },
  { days: 90, label: 'In 90 days' },
  { days: 365, label: 'In 1 year' },
] as const;
const DEFAULT_EXPIRY_DAYS = 90;
const PASSWORD_MIN = 8;
const PASSWORD_MAX = 128;

export const SHOW_ONCE_TEXT = 'This is the only time Rounds shows this link. Copy it now.';
export const SAVED_LABEL = 'I saved this link';
export const ALREADY_ISSUED_TEXT = 'You already made this link, and Rounds shows each link only once. Rotate it to get a new one.';
export const ROTATE_CONFIRM_TEXT = 'The current link stops working, and Rounds makes a new one.';
export const REVOKE_CONFIRM_TEXT = 'This link stops working for good. You can’t undo this.';
export const COPY_FAILED_TEXT = 'Couldn’t copy. Select the link and copy it.';

const INELIGIBLE: Record<string, string> = {
  demo_account: 'The demo account can’t share links.',
  data_too_large: 'This resume is too large to share. Shorten it, then try again.',
  data_malformed: 'This resume’s content can’t be read. Edit it, then try again.',
  design_out_of_domain: 'A design setting is outside what the templates show. Reset it in the Design tab, then try again.',
  parent_invalid: 'This variant’s resume isn’t available.',
};

type Reveal = { token: string; rotated: boolean; passwordSet: boolean };
type Notice =
  | { kind: 'already-issued'; fields: IssuedFields; passwordSet: boolean }
  | { kind: 'ineligible'; reason: string };
type Command = { key: string; body: { resume_id: string; expires_at: string | null; password: string | null } };
type RowAction = { id: string; kind: 'rotate' | 'revoke' };

function code(err: unknown): string | null {
  return isRunnerError(err) ? err.code : null;
}

// A failure that leaves the command as it was: the same key may try again.
function transient(err: unknown): boolean {
  if (!isRunnerError(err)) return true;
  return err.status === 0 || err.status >= 500 || err.code === 'already_in_flight';
}

function createErrorText(err: unknown): string {
  switch (code(err)) {
    case 'unauthenticated':
      return 'Sign in again to make a link.';
    case 'not_found':
      return 'This resume can’t be shared. Reload the page, then try again.';
    case 'invalid_request':
      // Also what a runner that reads the gate as closed answers this
      // dialog during a flip.
      return 'This link can’t be made as set. Reload the page, then try again.';
    case 'snapshot_conflict':
      return 'This resume changed while the link was being made. Create it again.';
    case 'already_in_flight':
      return 'This link is still being made. Try again in a moment.';
    case 'snapshot_quota_exceeded':
      return 'This account has reached its limit for saved snapshots.';
    case 'quota_exceeded':
    case 'demo_limit_reached':
      return 'You’ve reached the limit for now. Try again later.';
    default:
      return 'Links can’t be made right now. Try again shortly.';
  }
}

function rowErrorText(err: unknown, kind: 'rotate' | 'revoke'): string {
  switch (code(err)) {
    case 'capability_version_conflict':
      return 'This link changed since the list loaded. The list is up to date now.';
    case 'capability_revoked':
      return 'This link was revoked.';
    case 'capability_expired':
      return 'This link has expired.';
    case 'not_found':
      return 'This link isn’t available anymore.';
    case 'route_disabled':
      return 'Rotating links is turned off on this server.';
    default:
      return kind === 'rotate'
        ? 'The link can’t be rotated right now. Try again shortly.'
        : 'The link can’t be revoked right now. Try again shortly.';
  }
}

function formatDay(at: Date): string {
  return at.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}

export function stateLabel(state: CapabilityState): string {
  switch (state.kind) {
    case 'expires':
      return `Expires ${formatDay(state.at)}`;
    case 'expired':
      return 'Expired';
    case 'revoked':
      return state.at ? `Revoked ${formatDay(state.at)}` : 'Revoked';
    case 'source-deleted':
      return 'Source deleted';
  }
}

// A live link reads forest, one that ran out ochre, and one its owner
// revoked plum; one whose resume is gone stays neutral. The words carry
// the state; the tone only backs them up.
const BADGE_TONE: Record<CapabilityState['kind'], React.CSSProperties> = {
  expires: { background: 'var(--forest-soft)', color: 'var(--text)' },
  expired: { background: 'var(--ochre-soft)', color: 'var(--text)' },
  revoked: { background: 'var(--plum-soft)', color: 'var(--text)' },
  'source-deleted': { background: 'var(--bg-sunken)', color: 'var(--text-2)' },
};

const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex="0"]';

export default function ShareLinksDialog({ open, onClose, resumeId }: Props) {
  // Mounted only while open, so closing drops every secret the panel held.
  if (!open) return null;
  return <SharePanel onClose={onClose} resumeId={resumeId} />;
}

function SharePanel({ onClose, resumeId }: { onClose: () => void; resumeId: string }) {
  const titleId = useId();
  const expiryId = useId();
  const passwordId = useId();
  const passwordHintId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const firstFieldRef = useRef<HTMLSelectElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const urlRef = useRef<HTMLInputElement>(null);
  const opener = useRef<Element | null>(typeof document !== 'undefined' ? document.activeElement : null);

  const [rows, setRows] = useState<ShareCapability[] | null>(null);
  const [listFailed, setListFailed] = useState(false);
  const [expiryDays, setExpiryDays] = useState<number>(DEFAULT_EXPIRY_DAYS);
  const [wantsPassword, setWantsPassword] = useState(false);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [command, setCommand] = useState<Command | null>(null);
  const [creating, setCreating] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [reveal, setReveal] = useState<Reveal | null>(null);
  const [copy, setCopy] = useState<'idle' | 'copied' | 'failed'>('idle');
  const [rowAction, setRowAction] = useState<RowAction | null>(null);
  const [rowBusy, setRowBusy] = useState<string | null>(null);
  const [rowError, setRowError] = useState<{ id: string; text: string } | null>(null);

  const load = useCallback(async () => {
    setListFailed(false);
    try {
      setRows(await listCapabilities());
    } catch {
      setListFailed(true);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Focus the form when it opens, and give focus back when the dialog goes.
  useEffect(() => {
    firstFieldRef.current?.focus();
    const back = opener.current;
    return () => {
      if (back instanceof HTMLElement) back.focus();
    };
  }, []);

  // The show-once panel takes focus on its link, selected for the keyboard.
  useEffect(() => {
    if (!reveal) return;
    urlRef.current?.focus();
    urlRef.current?.select();
  }, [reveal]);

  const close = useCallback(() => {
    if (!reveal) onClose();
  }, [reveal, onClose]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !reveal) {
        e.stopPropagation();
        onClose();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [reveal, onClose]);

  const trapFocus = (e: React.KeyboardEvent) => {
    if (e.key !== 'Tab' || !panelRef.current) return;
    const items = [...panelRef.current.querySelectorAll<HTMLElement>(FOCUSABLE)];
    if (items.length === 0) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  // Any edit to the form is another request, so it gets another key.
  const edited = () => {
    setCommand(null);
    setFormError(null);
  };

  const showSecret = (token: string, rotated: boolean, passwordSet: boolean) => {
    setCopy('idle');
    setReveal({ token, rotated, passwordSet });
  };

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    if (creating) return;
    if (wantsPassword && (password.length < PASSWORD_MIN || password.length > PASSWORD_MAX)) {
      setFormError(`Use ${PASSWORD_MIN} to ${PASSWORD_MAX} characters for the password.`);
      passwordRef.current?.focus();
      return;
    }
    const next: Command = command ?? {
      key: mintIdempotencyKey(),
      body: { resume_id: resumeId, expires_at: expiryDay(expiryDays), password: wantsPassword ? password : null },
    };
    setCommand(next);
    setCreating(true);
    setFormError(null);
    setNotice(null);
    try {
      const outcome = await createCapability(next.body, next.key);
      setCommand(null);
      if (outcome.kind === 'issued') {
        showSecret(outcome.token, false, next.body.password !== null);
        setPassword('');
        setWantsPassword(false);
        setShowPassword(false);
      } else {
        setNotice(
          outcome.kind === 'already-issued'
            ? { kind: 'already-issued', fields: outcome.fields, passwordSet: next.body.password !== null }
            : outcome,
        );
        void load();
      }
    } catch (err) {
      if (!transient(err)) setCommand(null);
      setFormError(createErrorText(err));
    } finally {
      setCreating(false);
    }
  }

  async function onRotate(id: string, expectedVersion: number, passwordSet: boolean) {
    setRowBusy(id);
    setRowError(null);
    try {
      const outcome = await rotateCapability(id, expectedVersion, mintIdempotencyKey());
      setRowAction(null);
      setNotice(null);
      if (outcome.kind === 'issued') showSecret(outcome.token, true, passwordSet);
      else setRowError({ id, text: 'This link was already replaced, and its new one was shown once. Rotate it again.' });
    } catch (err) {
      setRowError({ id, text: rowErrorText(err, 'rotate') });
      if (!transient(err)) setRowAction(null);
    } finally {
      setRowBusy(null);
      void load();
    }
  }

  async function onRevoke(id: string) {
    setRowBusy(id);
    setRowError(null);
    try {
      await revokeCapability(id);
      setRowAction(null);
    } catch (err) {
      setRowError({ id, text: rowErrorText(err, 'revoke') });
    } finally {
      setRowBusy(null);
      void load();
    }
  }

  async function onCopy() {
    if (!reveal) return;
    try {
      await navigator.clipboard.writeText(buildCapabilityUrl(reveal.token));
      setCopy('copied');
    } catch {
      setCopy('failed');
      urlRef.current?.focus();
      urlRef.current?.select();
    }
  }

  function onSaved() {
    setReveal(null);
    setCopy('idle');
    void load();
  }

  const alreadyIssued = notice?.kind === 'already-issued' ? notice : null;

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 60,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
      }}
    >
      <div aria-hidden="true" onClick={close} style={{ position: 'absolute', inset: 0, background: 'rgba(0,0,0,0.45)' }} />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        onKeyDown={trapFocus}
        className="card"
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: 560,
          maxHeight: '88vh',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            padding: '8px 8px 8px 20px',
            minHeight: 60,
            borderBottom: '1px solid var(--border)',
          }}
        >
          <h2 id={titleId} style={{ margin: 0, fontSize: 15, fontWeight: 600, color: 'var(--text)' }}>
            {reveal ? (reveal.rotated ? 'Copy your new link' : 'Copy your link') : 'Share links'}
          </h2>
          {!reveal && (
            <button type="button" onClick={onClose} aria-label="Close" className="share-btn share-btn-icon">
              <X size={16} strokeWidth={1.8} />
            </button>
          )}
        </div>

        {reveal ? (
          <div className="share-reveal" style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: 'var(--text)' }}>{SHOW_ONCE_TEXT}</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <label htmlFor={`${titleId}-url`} style={labelStyle}>
                Share link
              </label>
              <input
                id={`${titleId}-url`}
                ref={urlRef}
                readOnly
                value={buildCapabilityUrl(reveal.token)}
                onFocus={(e) => e.currentTarget.select()}
                className="share-input mono"
                style={{ fontSize: 13, background: 'var(--bg-sunken)' }}
                spellCheck={false}
              />
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <button type="button" onClick={onCopy} className="share-btn share-btn-quiet">
                {copy === 'copied' ? <Check size={15} strokeWidth={1.9} /> : <Copy size={15} strokeWidth={1.7} />}
                Copy link
              </button>
              <span aria-live="polite" style={{ fontSize: 13, color: copy === 'failed' ? 'var(--plum)' : 'var(--text-2)' }}>
                {copy === 'copied' ? 'Copied.' : copy === 'failed' ? COPY_FAILED_TEXT : ''}
              </span>
            </div>
            {reveal.passwordSet && (
              <p style={{ margin: 0, fontSize: 13, lineHeight: 1.55, color: 'var(--text-2)' }}>
                {reveal.rotated
                  ? 'The password stays the same.'
                  : 'Send the password separately from the link.'}
              </p>
            )}
            <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: 6 }}>
              <button type="button" onClick={onSaved} className="share-btn share-btn-primary share-btn-wide">
                {SAVED_LABEL}
              </button>
            </div>
          </div>
        ) : (
          <div style={{ overflowY: 'auto', minHeight: 0 }}>
            <form onSubmit={onCreate} noValidate style={{ padding: 20, display: 'flex', flexDirection: 'column', gap: 14 }}>
              <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.55, color: 'var(--text-2)', maxWidth: '62ch' }}>
                Anyone with a link can view this resume, read-only. You see each link once, when you make it.
              </p>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label htmlFor={expiryId} style={labelStyle}>
                  Expires
                </label>
                <select
                  id={expiryId}
                  ref={firstFieldRef}
                  value={expiryDays}
                  onChange={(e) => {
                    setExpiryDays(Number(e.target.value));
                    edited();
                  }}
                  className="share-input"
                >
                  {EXPIRY_CHOICES.map((c) => (
                    <option key={c.days} value={c.days}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>
              <label style={{ display: 'flex', alignItems: 'center', gap: 10, minHeight: 44, fontSize: 14, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={wantsPassword}
                  onChange={(e) => {
                    setWantsPassword(e.target.checked);
                    edited();
                  }}
                  style={{ width: 18, height: 18, accentColor: 'var(--accent)' }}
                />
                Require a password
              </label>
              {wantsPassword && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  <label htmlFor={passwordId} style={labelStyle}>
                    Password
                  </label>
                  <div style={{ display: 'flex', gap: 8 }}>
                    <input
                      id={passwordId}
                      ref={passwordRef}
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        edited();
                      }}
                      autoComplete="new-password"
                      maxLength={PASSWORD_MAX}
                      aria-describedby={passwordHintId}
                      className="share-input"
                      style={{ flex: 1, minWidth: 0 }}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      aria-pressed={showPassword}
                      className="share-btn share-btn-quiet"
                    >
                      {showPassword ? 'Hide' : 'Show'}
                    </button>
                  </div>
                  <span id={passwordHintId} style={{ fontSize: 12.5, color: 'var(--text-2)' }}>
                    {PASSWORD_MIN} to {PASSWORD_MAX} characters. Send it separately from the link.
                  </span>
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <button type="submit" disabled={creating} className="share-btn share-btn-primary">
                  <Link2 size={15} strokeWidth={1.8} />
                  {creating ? 'Creating link…' : 'Create link'}
                </button>
              </div>
              {formError && (
                <p role="alert" style={{ margin: 0, fontSize: 13, color: 'var(--plum)' }}>
                  {formError}
                </p>
              )}
              {notice?.kind === 'ineligible' && (
                <p role="alert" style={{ margin: 0, fontSize: 13, color: 'var(--plum)' }}>
                  {INELIGIBLE[notice.reason] ?? 'This resume can’t be shared right now.'}
                </p>
              )}
              {alreadyIssued && (
                <div
                  role="status"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: 12,
                    flexWrap: 'wrap',
                    padding: '10px 12px',
                    borderRadius: 'var(--radius)',
                    background: 'var(--bg-sunken)',
                  }}
                >
                  <span style={{ fontSize: 13, lineHeight: 1.5, color: 'var(--text)' }}>{ALREADY_ISSUED_TEXT}</span>
                  <button
                    type="button"
                    disabled={rowBusy === alreadyIssued.fields.capability_id}
                    onClick={() =>
                      onRotate(
                        alreadyIssued.fields.capability_id,
                        alreadyIssued.fields.capability_version,
                        alreadyIssued.passwordSet,
                      )
                    }
                    className="share-btn share-btn-quiet"
                  >
                    Rotate
                  </button>
                </div>
              )}
            </form>

            <section aria-labelledby={`${titleId}-list`} style={{ borderTop: '1px solid var(--border)', padding: '16px 20px 20px' }}>
              <h3 id={`${titleId}-list`} style={{ margin: '0 0 6px', fontSize: 13, fontWeight: 600, color: 'var(--text-2)' }}>
                Your links
              </h3>
              <LinkList
                rows={rows}
                failed={listFailed}
                onRetry={load}
                action={rowAction}
                busy={rowBusy}
                error={rowError}
                onAction={(next) => {
                  setRowAction(next);
                  setRowError(null);
                }}
                onRotate={onRotate}
                onRevoke={onRevoke}
              />
            </section>
          </div>
        )}
      </div>
    </div>
  );
}

function LinkList({
  rows,
  failed,
  onRetry,
  action,
  busy,
  error,
  onAction,
  onRotate,
  onRevoke,
}: {
  rows: ShareCapability[] | null;
  failed: boolean;
  onRetry: () => void;
  action: RowAction | null;
  busy: string | null;
  error: { id: string; text: string } | null;
  onAction: (next: RowAction | null) => void;
  onRotate: (id: string, expectedVersion: number, passwordSet: boolean) => void;
  onRevoke: (id: string) => void;
}) {
  if (failed) {
    return (
      <div role="alert" style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap', fontSize: 13 }}>
        <span style={{ color: 'var(--text)' }}>Your links can’t be loaded right now.</span>
        <button type="button" onClick={onRetry} className="share-btn share-btn-quiet">
          Try again
        </button>
      </div>
    );
  }
  if (rows === null) {
    return (
      <div role="status" aria-label="Loading your links" style={{ display: 'flex', flexDirection: 'column', gap: 10, paddingTop: 6 }}>
        {[0, 1].map((i) => (
          <div key={i} style={{ height: 44, borderRadius: 'var(--radius)', background: 'var(--bg-sunken)' }} />
        ))}
      </div>
    );
  }
  if (rows.length === 0) {
    return (
      <p style={{ margin: 0, fontSize: 13, lineHeight: 1.55, color: 'var(--text-2)' }}>
        No links yet. Make one above and send it to anyone who should see this resume.
      </p>
    );
  }
  return (
    <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
      {rows.map((row) => {
        const state = capabilityState(row);
        const created = parseShareDate(row.created);
        const confirming = action?.id === row.id ? action.kind : null;
        const rowBusy = busy === row.id;
        return (
          <li key={row.id} style={{ padding: '12px 0', borderTop: '1px solid var(--border)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <span style={{ fontSize: 14, fontWeight: 500, color: 'var(--text)', minWidth: 0, overflowWrap: 'anywhere' }}>
                {row.purpose || 'Shared resume'}
              </span>
              <Badge style={BADGE_TONE[state.kind]}>{stateLabel(state)}</Badge>
              {row.password_set && (
                <Badge style={{ color: 'var(--text-2)', boxShadow: 'inset 0 0 0 1px var(--border-strong)' }}>
                  <KeyRound size={12} strokeWidth={1.8} aria-hidden="true" />
                  Password
                </Badge>
              )}
            </div>
            {created && (
              <div style={{ marginTop: 2, fontSize: 12.5, color: 'var(--text-2)' }}>Created {formatDay(created)}</div>
            )}
            {state.kind === 'expires' &&
              (confirming ? (
                <div role="group" aria-label={confirming === 'rotate' ? 'Rotate this link' : 'Revoke this link'} style={{ marginTop: 10 }}>
                  <p style={{ margin: '0 0 8px', fontSize: 13, lineHeight: 1.5, color: 'var(--text)' }}>
                    {confirming === 'rotate' ? ROTATE_CONFIRM_TEXT : REVOKE_CONFIRM_TEXT}
                  </p>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      disabled={rowBusy}
                      onClick={() =>
                        confirming === 'rotate'
                          ? onRotate(row.id, row.capability_version, row.password_set)
                          : onRevoke(row.id)
                      }
                      className={`share-btn ${confirming === 'rotate' ? 'share-btn-primary' : 'share-btn-danger'}`}
                    >
                      {confirming === 'rotate' ? 'Rotate link' : 'Revoke link'}
                    </button>
                    <button type="button" disabled={rowBusy} onClick={() => onAction(null)} className="share-btn share-btn-quiet">
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                  <button type="button" onClick={() => onAction({ id: row.id, kind: 'rotate' })} className="share-btn share-btn-quiet">
                    Rotate
                  </button>
                  <button type="button" onClick={() => onAction({ id: row.id, kind: 'revoke' })} className="share-btn share-btn-quiet">
                    Revoke
                  </button>
                </div>
              ))}
            {error?.id === row.id && (
              <p role="alert" style={{ margin: '8px 0 0', fontSize: 13, color: 'var(--plum)' }}>
                {error.text}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}

function Badge({ children, style }: { children: ReactNode; style: React.CSSProperties }) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        padding: '2px 8px',
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 500,
        lineHeight: 1.6,
        ...style,
      }}
    >
      {children}
    </span>
  );
}

const labelStyle: React.CSSProperties = { fontSize: 13, fontWeight: 500, color: 'var(--text)' };
