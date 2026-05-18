import { useEffect, useState } from 'react';
import { Award, CheckCircle2, Clock, History, Trash2, X, XCircle } from 'lucide-react';
import {
  createOffer,
  deleteOffer,
  getOffer,
  updateOffer,
  type Offer,
  type OfferStatus,
  type OfferTerms,
  type TrailEntry,
  type VisaOption,
} from '../../applications/api';
import DatePicker from './DatePicker';
import Select from './Select';
import InlineEditField from './InlineEditField';

export type { Offer, OfferStatus, OfferTerms, TrailEntry, VisaOption };

const FROZEN: OfferStatus[] = ['accepted', 'declined', 'expired'];

const TERM_KEYS: (keyof OfferTerms)[] = [
  'base_salary',
  'equity_type',
  'equity_amount',
  'equity_vest_schedule',
  'sign_on',
  'annual_bonus_target_pct',
  'relocation',
  'visa_sponsorship',
  'remote_policy',
  'pto',
  'decision_deadline',
  'letter_url',
];

const STATUS_COLORS: Record<OfferStatus, { bg: string; fg: string; icon: typeof Clock }> = {
  pending: { bg: 'var(--ochre-soft)', fg: 'var(--ochre)', icon: Clock },
  accepted: { bg: 'var(--forest-soft)', fg: 'var(--forest)', icon: CheckCircle2 },
  declined: { bg: 'var(--plum-soft)', fg: 'var(--plum)', icon: XCircle },
  expired: { bg: 'var(--paper-3)', fg: 'var(--text-3)', icon: XCircle },
};

const EMPTY_TERMS: OfferTerms = {
  base_salary: null,
  equity_type: '',
  equity_amount: '',
  equity_vest_schedule: '',
  sign_on: null,
  annual_bonus_target_pct: null,
  relocation: '',
  visa_sponsorship: 'n/a',
  remote_policy: '',
  pto: '',
  decision_deadline: '',
  letter_url: '',
};

const VISA_OPTIONS: { value: VisaOption; label: string }[] = [
  { value: 'n/a', label: 'N/A' },
  { value: 'yes', label: 'Yes' },
  { value: 'no', label: 'No' },
];

interface Props {
  applicationId: string;
  onOfferChange?: (o: Offer | null) => void;
}

export default function OfferPanel({ applicationId, onOfferChange }: Props) {
  const [offer, setOffer] = useState<Offer | null>(null);
  /** A locally-held offer in "draft" mode, BEFORE we've persisted any
   *  PB row. The user can Cancel and walk away without leaving an
   *  all-zeros row in the database — the previous version did that
   *  because it called createOffer() the instant the button was
   *  clicked. */
  const [draftOffer, setDraftOffer] = useState<Offer | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [confirmingClear, setConfirmingClear] = useState(false);
  const [clearing, setClearing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    getOffer(applicationId)
      .then((o) => {
        if (cancel) return;
        setOffer(o);
        // We deliberately do NOT fire onOfferChange on initial load.
        // The parent already knows about persisted offers if it cares;
        // firing here makes parents that auto-react to "an offer
        // exists" (e.g. ApplicationDetail's auto-flip to status =
        // Offer) clobber any subsequent user-driven status change
        // every time the page mounts.
      })
      .catch(() => {
        if (!cancel) setOffer(null);
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [applicationId]);

  /** "Record an offer" — opens the editor with an in-memory draft only.
   *  No PB row is created until the user clicks Save. */
  function beginRecordingOffer() {
    setDraftOffer({
      id: '',
      application_id: applicationId,
      ...EMPTY_TERMS,
      status: 'pending',
      notes: '',
      trail: [],
    });
    setError(null);
  }

  async function saveDraft(next: Offer) {
    setSaving(true);
    setError(null);
    try {
      const created = await createOffer(applicationId, {
        ...next,
        trail: [],
      });
      setOffer(created);
      setDraftOffer(null);
      onOfferChange?.(created);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save offer.');
    } finally {
      setSaving(false);
    }
  }

  /** Apply a single-field change to the persisted offer. Each commit
   *  appends a snapshot to the negotiation trail when a term changed
   *  and the offer isn't frozen — same semantics as the old bulk
   *  editor, just per-field instead of per-save. */
  async function commitField<K extends keyof Offer>(key: K, value: Offer[K]) {
    if (!offer) return;
    if (normalize(offer[key]) === normalize(value)) return;
    const merged: Offer = { ...offer, [key]: value };
    const isTermChange = (TERM_KEYS as readonly string[]).includes(key as string);
    if (isTermChange && !FROZEN.includes(offer.status)) {
      merged.trail = [
        ...offer.trail,
        {
          timestamp: new Date().toISOString(),
          author_note: '',
          snapshot: pickTerms(offer),
        },
      ];
    }
    const saved = await updateOffer(offer.id, applicationId, merged);
    setOffer(saved);
    onOfferChange?.(saved);
  }

  async function setStatus(status: OfferStatus) {
    await commitField('status', status);
  }

  async function clearOffer() {
    if (!offer) return;
    setClearing(true);
    setError(null);
    try {
      await deleteOffer(offer.id);
      setOffer(null);
      setConfirmingClear(false);
      onOfferChange?.(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not clear offer.');
    } finally {
      setClearing(false);
    }
  }

  if (loading) {
    return (
      <div className="card p-6">
        <div className="eyebrow mb-2">Offer</div>
        <div style={{ fontSize: 13, color: 'var(--text-4)' }}>Loading…</div>
      </div>
    );
  }

  if (!offer && !draftOffer) {
    return (
      <div className="card p-6">
        <div className="flex items-center justify-between mb-2">
          <div className="eyebrow">Offer</div>
        </div>
        <p
          style={{
            margin: 0,
            fontSize: 13,
            color: 'var(--text-4)',
            lineHeight: 1.6,
            fontStyle: 'italic',
            marginBottom: 12,
          }}
        >
          No offer recorded yet. When the company sends one, log it here so comp, benefits,
          and the decision deadline all live alongside the application.
        </p>
        <button
          type="button"
          onClick={beginRecordingOffer}
          className="inline-flex items-center gap-1.5"
          style={{
            padding: '8px 14px',
            borderRadius: 'var(--radius)',
            border: 0,
            background: 'var(--accent)',
            color: 'var(--bg-elev)',
            fontSize: 12.5,
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          <Award size={13} strokeWidth={1.7} />
          Record an offer
        </button>
        {error && (
          <div style={{ marginTop: 10, color: 'var(--plum)', fontSize: 12 }}>{error}</div>
        )}
      </div>
    );
  }

  // Draft mode: bulk editor. Cancel walks away cleanly — no PB row was
  // ever created.
  if (!offer && draftOffer) {
    return (
      <div className="card p-6">
        <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
          <div className="eyebrow">Offer · draft</div>
        </div>
        <OfferDraftEditor
          initial={draftOffer}
          saving={saving}
          onCancel={() => {
            setDraftOffer(null);
            setError(null);
          }}
          onSave={(next) => saveDraft(next)}
        />
        {error && (
          <div style={{ marginTop: 10, color: 'var(--plum)', fontSize: 12 }}>{error}</div>
        )}
      </div>
    );
  }

  if (!offer) return null; // Unreachable.

  const frozen = FROZEN.includes(offer.status);
  const status = STATUS_COLORS[offer.status];
  const StatusIcon = status.icon;

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="eyebrow">Offer</span>
          <span className="pill inline-flex items-center gap-1" style={{ background: status.bg, color: status.fg }}>
            <StatusIcon size={11} strokeWidth={1.9} />
            {offer.status}
          </span>
        </div>
        <div className="flex items-center" style={{ gap: 4 }}>
          {confirmingClear ? (
            <>
              <button
                type="button"
                onClick={() => void clearOffer()}
                disabled={clearing}
                aria-label="Confirm clear offer"
                title="Confirm — deletes the offer and flips status back to Interviewing"
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 4,
                  padding: '4px 10px',
                  border: 0,
                  borderRadius: 999,
                  background: 'var(--plum)',
                  color: 'var(--bg)',
                  fontSize: 11,
                  fontWeight: 600,
                  cursor: clearing ? 'wait' : 'pointer',
                  opacity: clearing ? 0.6 : 1,
                }}
              >
                {clearing ? 'Clearing…' : 'Clear offer?'}
              </button>
              <button
                type="button"
                onClick={() => setConfirmingClear(false)}
                disabled={clearing}
                aria-label="Cancel clear"
                title="Cancel"
                style={iconBtnStyle}
              >
                <X size={12} strokeWidth={2} />
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmingClear(true)}
              aria-label="Clear offer"
              title="Delete the offer and return to Interviewing"
              className="inline-flex items-center"
              style={{
                gap: 5,
                padding: '4px 10px',
                background: 'transparent',
                color: 'var(--text-3)',
                border: 0,
                borderRadius: 999,
                fontSize: 11,
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              <Trash2 size={11} strokeWidth={1.8} /> Clear offer
            </button>
          )}
        </div>
      </div>

      {frozen ? (
        // Frozen states show terms read-only so a closed-out offer
        // doesn't get accidentally rewritten. The user can still
        // Clear offer if they need to undo.
        <OfferReadOnly offer={offer} />
      ) : (
        <OfferInlineEditor
          offer={offer}
          onCommitText={(key, raw) => commitField(key, raw as Offer[typeof key])}
          onCommitNumber={(key, raw) => {
            const value =
              raw === '' ? null : (() => {
                const n = Number(raw);
                if (!Number.isFinite(n)) throw new Error('Must be a number');
                return n;
              })();
            return commitField(key, value as Offer[typeof key]);
          }}
          onCommitVisa={(v) => commitField('visa_sponsorship', v)}
        />
      )}

      {!frozen && (
        <div className="flex flex-wrap gap-2 mt-5">
          <StatusBtn label="Mark accepted" tone="forest" onClick={() => void setStatus('accepted')} />
          <StatusBtn label="Mark declined" tone="plum" onClick={() => void setStatus('declined')} />
          <StatusBtn label="Mark expired" tone="muted" onClick={() => void setStatus('expired')} />
        </div>
      )}

      <OfferTrailView trail={offer.trail ?? []} />

      {error && (
        <div style={{ marginTop: 10, color: 'var(--plum)', fontSize: 12 }}>{error}</div>
      )}
    </div>
  );
}

/** Grid of inline-edit rows over the offer's terms. Each row owns its
 *  own commit; the parent threads commits through into updateOffer +
 *  trail logging. */
function OfferInlineEditor({
  offer,
  onCommitText,
  onCommitNumber,
  onCommitVisa,
}: {
  offer: Offer;
  onCommitText: (key: keyof Offer, raw: string) => Promise<void>;
  onCommitNumber: (key: keyof OfferTerms, raw: string) => Promise<void>;
  onCommitVisa: (v: VisaOption) => Promise<void>;
}) {
  return (
    <>
      <div
        className="grid gap-3 mt-2"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}
      >
        <InlineEditField
          kind="text"
          label="Base salary (USD)"
          value={offer.base_salary != null ? String(offer.base_salary) : ''}
          placeholder="e.g. 195000"
          onCommit={(raw) => onCommitNumber('base_salary', raw)}
          renderRead={(v) => (
            <span
              className="mono"
              style={{ fontSize: 13, color: v ? 'var(--text)' : 'var(--text-4)' }}
            >
              {v ? `$${Number(v).toLocaleString()}` : '—'}
            </span>
          )}
        />
        <InlineEditField
          kind="text"
          label="Sign-on bonus (USD)"
          value={offer.sign_on != null ? String(offer.sign_on) : ''}
          placeholder="e.g. 25000"
          onCommit={(raw) => onCommitNumber('sign_on', raw)}
          renderRead={(v) => (
            <span
              className="mono"
              style={{ fontSize: 13, color: v ? 'var(--text)' : 'var(--text-4)' }}
            >
              {v ? `$${Number(v).toLocaleString()}` : '—'}
            </span>
          )}
        />
        <InlineEditField
          kind="text"
          label="Annual bonus target %"
          value={offer.annual_bonus_target_pct != null ? String(offer.annual_bonus_target_pct) : ''}
          placeholder="e.g. 15"
          onCommit={(raw) => onCommitNumber('annual_bonus_target_pct', raw)}
          renderRead={(v) => (
            <span
              className="mono"
              style={{ fontSize: 13, color: v ? 'var(--text)' : 'var(--text-4)' }}
            >
              {v ? `${v}%` : '—'}
            </span>
          )}
        />
        <InlineEditField
          kind="text"
          label="Equity type"
          value={offer.equity_type}
          placeholder="RSU / ISO / PIU"
          onCommit={(raw) => onCommitText('equity_type', raw)}
        />
        <InlineEditField
          kind="text"
          label="Equity amount"
          value={offer.equity_amount}
          placeholder="e.g. 120k over 4y"
          onCommit={(raw) => onCommitText('equity_amount', raw)}
        />
        <InlineEditField
          kind="text"
          label="Vest schedule"
          value={offer.equity_vest_schedule}
          placeholder="25/25/25/25 with 1y cliff"
          onCommit={(raw) => onCommitText('equity_vest_schedule', raw)}
        />
        <InlineEditField
          kind="date-only"
          label="Decision deadline"
          value={offer.decision_deadline}
          placeholder="Pick a date"
          onCommit={(raw) => onCommitText('decision_deadline', raw)}
          renderRead={(v) => (
            <span
              className="mono"
              style={{ fontSize: 13, color: v ? 'var(--text)' : 'var(--text-4)' }}
            >
              {v || '—'}
            </span>
          )}
        />
        <InlineEditField
          kind="select"
          label="Visa sponsorship"
          value={offer.visa_sponsorship}
          options={VISA_OPTIONS}
          onCommit={(raw) => onCommitVisa(raw as VisaOption)}
          renderRead={(v) => (
            <span
              style={{ fontSize: 13, color: v ? 'var(--text)' : 'var(--text-4)' }}
            >
              {v === 'n/a' ? '—' : v}
            </span>
          )}
        />
        <InlineEditField
          kind="text"
          label="Remote policy"
          value={offer.remote_policy}
          placeholder="Remote / hybrid / on-site"
          onCommit={(raw) => onCommitText('remote_policy', raw)}
        />
        <InlineEditField
          kind="text"
          label="Relocation"
          value={offer.relocation}
          placeholder="e.g. $25k lump sum"
          onCommit={(raw) => onCommitText('relocation', raw)}
        />
        <InlineEditField
          kind="text"
          label="PTO"
          value={offer.pto}
          placeholder="Unlimited / 20 days / …"
          onCommit={(raw) => onCommitText('pto', raw)}
        />
        <InlineEditField
          kind="url"
          label="Letter URL"
          value={offer.letter_url}
          placeholder="https://…"
          onCommit={(raw) => onCommitText('letter_url', raw)}
          renderRead={(v) =>
            v ? (
              <a
                href={v}
                target="_blank"
                rel="noreferrer"
                className="mono truncate"
                style={{
                  fontSize: 12,
                  color: 'var(--accent)',
                  textDecoration: 'none',
                }}
                onClick={(e) => e.stopPropagation()}
              >
                {shortUrl(v)}
              </a>
            ) : (
              <span
                className="mono"
                style={{ fontSize: 12, color: 'var(--text-4)', fontStyle: 'italic' }}
              >
                —
              </span>
            )
          }
        />
      </div>
      <div className="mt-5">
        <InlineEditField
          kind="multiline"
          label="Notes"
          value={offer.notes}
          placeholder="Anything you want to remember about this offer."
          onCommit={(raw) => onCommitText('notes', raw)}
        />
      </div>
    </>
  );
}

/** Read-only view used when the offer is in a frozen state
 *  (accepted/declined/expired). Same field layout as the inline
 *  editor so the UI doesn't jump when the user marks it. */
function OfferReadOnly({ offer }: { offer: Offer }) {
  const rows = termRows(offer);
  return (
    <>
      <div
        className="grid gap-4 mt-2"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}
      >
        {rows.map((r) => (
          <div key={r.label} className="flex flex-col gap-1">
            <span className="eyebrow">{r.label}</span>
            <span
              className={r.mono ? 'mono' : ''}
              style={{ fontSize: 13, color: r.value ? 'var(--text)' : 'var(--text-4)' }}
            >
              {r.value || '—'}
            </span>
          </div>
        ))}
      </div>
      {offer.notes?.trim() && (
        <div className="mt-5">
          <div className="eyebrow mb-1.5">Notes</div>
          <p style={{ margin: 0, fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
            {offer.notes}
          </p>
        </div>
      )}
    </>
  );
}

/** Bulk editor used only when the user is creating their first offer
 *  for an application. Cancel walks away with no DB row created. */
function OfferDraftEditor({
  initial,
  saving,
  onCancel,
  onSave,
}: {
  initial: Offer;
  saving: boolean;
  onCancel: () => void;
  onSave: (next: Offer) => void;
}) {
  const [form, setForm] = useState<Offer>(initial);

  function update<K extends keyof Offer>(key: K, value: Offer[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function numberFieldHandler(key: keyof OfferTerms) {
    return (e: React.ChangeEvent<HTMLInputElement>) => {
      const raw = e.target.value;
      if (raw === '') update(key as keyof Offer, null as Offer[keyof Offer]);
      else {
        const n = Number(raw);
        update(key as keyof Offer, (Number.isFinite(n) ? n : null) as Offer[keyof Offer]);
      }
    };
  }

  return (
    <div className="flex flex-col gap-3 mt-2">
      <div
        className="grid gap-3"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}
      >
        <Field label="Base salary (annual, USD)">
          <input
            type="number"
            value={form.base_salary ?? ''}
            onChange={numberFieldHandler('base_salary')}
            style={inputStyle}
          />
        </Field>
        <Field label="Sign-on bonus (USD)">
          <input
            type="number"
            value={form.sign_on ?? ''}
            onChange={numberFieldHandler('sign_on')}
            style={inputStyle}
          />
        </Field>
        <Field label="Annual bonus target %">
          <input
            type="number"
            value={form.annual_bonus_target_pct ?? ''}
            onChange={numberFieldHandler('annual_bonus_target_pct')}
            style={inputStyle}
          />
        </Field>
        <Field label="Equity type">
          <input
            type="text"
            placeholder="RSU / ISO / PIU"
            value={form.equity_type}
            onChange={(e) => update('equity_type', e.target.value)}
            style={inputStyle}
          />
        </Field>
        <Field label="Equity amount">
          <input
            type="text"
            placeholder="e.g. 120k over 4y"
            value={form.equity_amount}
            onChange={(e) => update('equity_amount', e.target.value)}
            style={inputStyle}
          />
        </Field>
        <Field label="Vest schedule">
          <input
            type="text"
            placeholder="25/25/25/25 with 1y cliff"
            value={form.equity_vest_schedule}
            onChange={(e) => update('equity_vest_schedule', e.target.value)}
            style={inputStyle}
          />
        </Field>
        <Field label="Decision deadline">
          <DatePicker
            value={form.decision_deadline}
            onChange={(v) => update('decision_deadline', v)}
            placeholder="Pick a date"
            ariaLabel="Decision deadline"
          />
        </Field>
        <Field label="Visa sponsorship">
          <Select<VisaOption>
            value={form.visa_sponsorship}
            onChange={(v) => update('visa_sponsorship', v)}
            options={VISA_OPTIONS}
            ariaLabel="Visa sponsorship"
          />
        </Field>
        <Field label="Remote policy">
          <input
            type="text"
            placeholder="Remote / hybrid / on-site"
            value={form.remote_policy}
            onChange={(e) => update('remote_policy', e.target.value)}
            style={inputStyle}
          />
        </Field>
        <Field label="Relocation">
          <input
            type="text"
            placeholder="e.g. $25k lump sum"
            value={form.relocation}
            onChange={(e) => update('relocation', e.target.value)}
            style={inputStyle}
          />
        </Field>
        <Field label="PTO">
          <input
            type="text"
            placeholder="Unlimited / 20 days / …"
            value={form.pto}
            onChange={(e) => update('pto', e.target.value)}
            style={inputStyle}
          />
        </Field>
        <Field label="Letter URL">
          <input
            type="url"
            value={form.letter_url}
            onChange={(e) => update('letter_url', e.target.value)}
            style={inputStyle}
          />
        </Field>
      </div>
      <Field label="Notes">
        <textarea
          rows={3}
          value={form.notes}
          onChange={(e) => update('notes', e.target.value)}
          style={{ ...inputStyle, fontFamily: 'inherit', resize: 'vertical' }}
        />
      </Field>
      <div className="flex gap-2 justify-end">
        <button type="button" onClick={onCancel} disabled={saving} style={secondaryBtn}>
          Cancel
        </button>
        <button
          type="button"
          onClick={() => onSave(form)}
          disabled={saving}
          style={primaryBtn}
        >
          {saving ? 'Saving…' : 'Save offer'}
        </button>
      </div>
    </div>
  );
}

function OfferTrailView({ trail }: { trail: TrailEntry[] }) {
  if (trail.length === 0) return null;
  return (
    <div className="mt-6">
      <div className="flex items-center gap-2 mb-3">
        <History size={13} strokeWidth={1.7} style={{ color: 'var(--text-3)' }} />
        <span className="eyebrow">Negotiation trail</span>
      </div>
      <ol className="flex flex-col gap-3" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {[...trail].reverse().map((e, i) => (
          <li
            key={`${e.timestamp}-${i}`}
            style={{
              padding: '12px 14px',
              borderRadius: 'var(--radius)',
              background: 'var(--bg-sunken)',
              boxShadow: 'inset 0 0 0 1px var(--border)',
            }}
          >
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <span
                className="mono"
                style={{ fontSize: 11, color: 'var(--text-3)' }}
              >
                {new Date(e.timestamp).toLocaleString(undefined, {
                  month: 'short',
                  day: 'numeric',
                  hour: 'numeric',
                  minute: '2-digit',
                })}
              </span>
              {e.author_note && (
                <span style={{ fontSize: 12, color: 'var(--text-2)' }}>{e.author_note}</span>
              )}
            </div>
            <div
              className="grid gap-1.5"
              style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))' }}
            >
              {termRows({ ...e.snapshot } as Offer)
                .filter((r) => r.value)
                .map((r) => (
                  <div key={r.label} className="flex items-baseline gap-1.5 min-w-0">
                    <span
                      style={{
                        fontSize: 10.5,
                        color: 'var(--text-4)',
                        letterSpacing: '0.08em',
                        textTransform: 'uppercase',
                      }}
                    >
                      {r.label}
                    </span>
                    <span
                      className={r.mono ? 'mono truncate' : 'truncate'}
                      style={{ fontSize: 12, color: 'var(--text-2)' }}
                    >
                      {r.value}
                    </span>
                  </div>
                ))}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}

function termRows(offer: Offer | OfferTerms) {
  const o = offer as Offer;
  const fmt = (n: number | null | undefined) =>
    n == null || Number.isNaN(n) ? '' : `$${n.toLocaleString()}`;
  return [
    { label: 'Base salary', value: fmt(o.base_salary), mono: true },
    { label: 'Sign-on', value: fmt(o.sign_on), mono: true },
    { label: 'Bonus %', value: o.annual_bonus_target_pct != null ? `${o.annual_bonus_target_pct}%` : '', mono: true },
    { label: 'Equity', value: [o.equity_type, o.equity_amount].filter(Boolean).join(' · ') },
    { label: 'Vest', value: o.equity_vest_schedule },
    { label: 'Remote', value: o.remote_policy },
    { label: 'Relocation', value: o.relocation },
    { label: 'Visa', value: o.visa_sponsorship === 'n/a' ? '' : o.visa_sponsorship },
    { label: 'PTO', value: o.pto },
    { label: 'Decision by', value: o.decision_deadline, mono: true },
    { label: 'Letter', value: o.letter_url ? shortUrl(o.letter_url) : '', mono: true },
  ];
}

function pickTerms(offer: Offer): OfferTerms {
  const t: OfferTerms = { ...EMPTY_TERMS };
  for (const k of TERM_KEYS) {
    const v = offer[k];
    // Runtime-safe: TERM_KEYS is the exact union of OfferTerms keys,
    // so `offer[k]` is assignable to `t[k]` at that same key — TS just
    // can't prove it through the index.
    (t as unknown as Record<string, unknown>)[k] = v;
  }
  return t;
}

function normalize(v: unknown): string {
  if (v == null) return '';
  return String(v).trim();
}

function shortUrl(url: string) {
  try {
    const u = new URL(url);
    return u.host + u.pathname;
  } catch {
    return url;
  }
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 min-w-0">
      <span className="eyebrow">{label}</span>
      {children}
    </label>
  );
}

function StatusBtn({
  label,
  tone,
  onClick,
}: {
  label: string;
  tone: 'forest' | 'plum' | 'muted';
  onClick: () => void;
}) {
  const colors =
    tone === 'forest'
      ? { bg: 'var(--forest-soft)', fg: 'var(--forest)' }
      : tone === 'plum'
      ? { bg: 'var(--plum-soft)', fg: 'var(--plum)' }
      : { bg: 'var(--paper-3)', fg: 'var(--text-3)' };
  return (
    <button
      type="button"
      onClick={onClick}
      style={{
        padding: '7px 12px',
        borderRadius: 'var(--radius)',
        border: 0,
        background: colors.bg,
        color: colors.fg,
        fontSize: 12,
        fontWeight: 500,
        cursor: 'pointer',
      }}
    >
      {label}
    </button>
  );
}

const inputStyle: React.CSSProperties = {
  padding: '8px 10px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--border)',
  background: 'var(--bg-elev)',
  color: 'var(--text)',
  fontSize: 13,
};

const primaryBtn: React.CSSProperties = {
  padding: '8px 14px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'var(--accent)',
  color: 'var(--bg-elev)',
  fontSize: 12.5,
  fontWeight: 500,
  cursor: 'pointer',
};

const secondaryBtn: React.CSSProperties = {
  padding: '8px 14px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--border)',
  background: 'transparent',
  color: 'var(--text-2)',
  fontSize: 12.5,
  fontWeight: 500,
  cursor: 'pointer',
};

const iconBtnStyle: React.CSSProperties = {
  width: 26,
  height: 26,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'transparent',
  border: 0,
  borderRadius: 999,
  color: 'var(--text-4)',
  cursor: 'pointer',
};
