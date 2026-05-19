import { useEffect, useState } from 'react';
import {
  Award,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  History,
  Layers,
  Trash2,
  X,
  XCircle,
} from 'lucide-react';
import {
  createOffer,
  deleteOffer,
  listOffers,
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

/** Statuses that lock the offer from term edits — accepted/declined/expired
 *  are terminal outcomes for the round. `superseded` is also frozen (it's
 *  history), but it never appears as the active row, so the active-card
 *  code paths don't see it. */
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
  superseded: { bg: 'var(--paper-3)', fg: 'var(--text-3)', icon: Layers },
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
  /** Fires when the *active* offer changes (null ↔ non-null transitions
   *  drive ApplicationDetail's auto-status flip). Mid-state edits and
   *  history changes don't trigger a parent-visible change. */
  onOfferChange?: (o: Offer | null) => void;
}

export default function OfferPanel({ applicationId, onOfferChange }: Props) {
  /** Full chain, newest first. The head (offers[0]) is either the
   *  active offer or — when the only rows are superseded — empty/none.
   *  We store the full list so history rendering is cheap. */
  const [offers, setOffers] = useState<Offer[]>([]);
  /** In-memory draft for "Record an offer" or "Record new round". No
   *  PB row exists yet — Cancel walks away cleanly. */
  const [draft, setDraft] = useState<Offer | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [confirmingDiscard, setConfirmingDiscard] = useState(false);
  const [discarding, setDiscarding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  /** Set of history offer ids the user has expanded. History entries
   *  collapse by default — the chain can grow long. */
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const active = offers.find((o) => o.status !== 'superseded') ?? null;
  const history = offers.filter((o) => o.status === 'superseded');

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    listOffers(applicationId)
      .then((list) => {
        if (cancel) return;
        setOffers(list);
        // Initial load does NOT fire onOfferChange. The parent already
        // reflects the persisted state; firing here would re-trigger the
        // null → Offer auto-flip on every page mount and clobber any
        // user-driven status changes.
      })
      .catch(() => {
        if (!cancel) setOffers([]);
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [applicationId]);

  function beginRecording(preFill: OfferTerms = EMPTY_TERMS) {
    setDraft({
      id: '',
      application_id: applicationId,
      ...preFill,
      status: 'pending',
      notes: '',
      trail: [],
      previous_offer_id: '',
    });
    setError(null);
  }

  async function saveDraft(next: Offer) {
    setSaving(true);
    setError(null);
    try {
      const created = await createOffer(applicationId, { ...next, trail: [] });
      // Reload the chain — createOffer flipped the prior active to
      // superseded, so the local list is stale.
      const list = await listOffers(applicationId);
      setOffers(list);
      setDraft(null);
      onOfferChange?.(list.find((o) => o.status !== 'superseded') ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save offer.');
    } finally {
      setSaving(false);
    }
  }

  /** Apply a single-field change to the active offer. Appends a
   *  negotiation-trail snapshot when a term changed and the round
   *  isn't frozen. Mirrors the prior per-field commit behavior; now
   *  scoped to the active row only. */
  async function commitField<K extends keyof Offer>(key: K, value: Offer[K]) {
    if (!active) return;
    if (normalize(active[key]) === normalize(value)) return;
    const merged: Offer = { ...active, [key]: value };
    const isTermChange = (TERM_KEYS as readonly string[]).includes(key as string);
    if (isTermChange && !FROZEN.includes(active.status)) {
      merged.trail = [
        ...active.trail,
        {
          timestamp: new Date().toISOString(),
          author_note: '',
          snapshot: pickTerms(active),
        },
      ];
    }
    const saved = await updateOffer(active.id, applicationId, merged);
    setOffers((prev) => prev.map((o) => (o.id === saved.id ? saved : o)));
    onOfferChange?.(saved);
  }

  async function setStatus(status: OfferStatus) {
    await commitField('status', status);
  }

  /** Walk back one step in the chain — delete the active round and
   *  revive the previous one to pending. With no prior round, the
   *  application becomes offer-less (parent flips status back to
   *  Interviewing via onOfferChange(null)). */
  async function discardActive() {
    if (!active) return;
    setDiscarding(true);
    setError(null);
    try {
      const revived = await deleteOffer(active.id);
      const list = await listOffers(applicationId);
      setOffers(list);
      setConfirmingDiscard(false);
      const nextActive = list.find((o) => o.status !== 'superseded') ?? null;
      onOfferChange?.(nextActive);
      // `revived` is returned by the API for documentation/future use
      // (which row was un-superseded); we re-derive nextActive from
      // the freshly-loaded list to avoid drift.
      void revived;
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not discard round.');
    } finally {
      setDiscarding(false);
    }
  }

  function toggleExpanded(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  if (loading) {
    return (
      <div className="card p-6">
        <div className="eyebrow mb-2">Offer</div>
        <div style={{ fontSize: 13, color: 'var(--text-4)' }}>Loading…</div>
      </div>
    );
  }

  // --- Empty state: no offers yet, no draft -------------------------
  if (!active && offers.length === 0 && !draft) {
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
          onClick={() => beginRecording()}
          className="inline-flex items-center gap-1.5"
          style={primaryBtn}
        >
          <Award size={13} strokeWidth={1.7} />
          Record an offer
        </button>
        {error && <div style={errorStyle}>{error}</div>}
      </div>
    );
  }

  // --- Draft state: recording a brand-new offer or a new round -----
  if (draft) {
    const isFirstRound = offers.length === 0;
    return (
      <div className="card p-6">
        <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
          <div className="eyebrow">
            {isFirstRound ? 'Offer · draft' : 'New round · draft'}
          </div>
        </div>
        {!isFirstRound && (
          <p
            style={{
              margin: 0,
              fontSize: 12.5,
              color: 'var(--text-3)',
              lineHeight: 1.55,
              marginBottom: 14,
            }}
          >
            Tweak the terms for this new round. Saving will mark the
            previous round as superseded and keep it in the history below.
          </p>
        )}
        <OfferDraftEditor
          initial={draft}
          saving={saving}
          onCancel={() => {
            setDraft(null);
            setError(null);
          }}
          onSave={(next) => saveDraft(next)}
        />
        {error && <div style={errorStyle}>{error}</div>}
      </div>
    );
  }

  if (!active) {
    // Edge case: every round is superseded (shouldn't normally happen,
    // but render history defensively rather than blank).
    return (
      <div className="card p-6">
        <div className="flex items-center justify-between mb-3">
          <div className="eyebrow">Offer · history only</div>
          <button
            type="button"
            onClick={() => beginRecording()}
            className="inline-flex items-center"
            style={primaryBtn}
          >
            <Award size={13} strokeWidth={1.7} />
            Record new round
          </button>
        </div>
        <ChainHistory
          history={history}
          expanded={expanded}
          onToggle={toggleExpanded}
        />
      </div>
    );
  }

  const frozen = FROZEN.includes(active.status);
  const status = STATUS_COLORS[active.status];
  const StatusIcon = status.icon;
  // Accepted = terminal. Declined/expired still allow a counter round.
  const allowNewRound = active.status !== 'accepted';
  const discardLabel = history.length > 0 ? 'Discard this round' : 'Clear offer';
  const discardTitle =
    history.length > 0
      ? 'Remove this round and restore the previous round as active'
      : 'Remove the offer and return to Interviewing';
  const roundIndex = offers.findIndex((o) => o.id === active.id);
  // Total rounds = active + history; round number counts from oldest.
  const roundNumber = offers.length - roundIndex;

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-3 gap-2 flex-wrap">
        <div className="flex items-center gap-2">
          <span className="eyebrow">
            Offer{offers.length > 1 ? ` · round ${roundNumber}` : ''}
          </span>
          <span
            className="pill inline-flex items-center gap-1"
            style={{ background: status.bg, color: status.fg }}
          >
            <StatusIcon size={11} strokeWidth={1.9} />
            {active.status}
          </span>
        </div>
        <div className="flex items-center" style={{ gap: 4 }}>
          {allowNewRound && (
            <button
              type="button"
              onClick={() => beginRecording(pickTerms(active))}
              className="inline-flex items-center"
              style={{
                gap: 5,
                padding: '4px 10px',
                background: 'var(--accent-soft)',
                color: 'var(--accent)',
                border: 0,
                borderRadius: 999,
                fontSize: 11,
                fontWeight: 600,
                cursor: 'pointer',
              }}
              title="Record a new offer round — supersedes this one and starts a fresh editable round pre-filled with these terms"
            >
              <Layers size={11} strokeWidth={1.8} /> Record new round
            </button>
          )}
          {confirmingDiscard ? (
            <>
              <button
                type="button"
                onClick={() => void discardActive()}
                disabled={discarding}
                aria-label="Confirm discard"
                title="Confirm"
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
                  cursor: discarding ? 'wait' : 'pointer',
                  opacity: discarding ? 0.6 : 1,
                }}
              >
                {discarding ? 'Discarding…' : `${discardLabel}?`}
              </button>
              <button
                type="button"
                onClick={() => setConfirmingDiscard(false)}
                disabled={discarding}
                aria-label="Cancel"
                title="Cancel"
                style={iconBtnStyle}
              >
                <X size={12} strokeWidth={2} />
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={() => setConfirmingDiscard(true)}
              aria-label={discardLabel}
              title={discardTitle}
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
              <Trash2 size={11} strokeWidth={1.8} /> {discardLabel}
            </button>
          )}
        </div>
      </div>

      {frozen ? (
        <OfferReadOnly offer={active} />
      ) : (
        <OfferInlineEditor
          offer={active}
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

      <OfferTrailView trail={active.trail ?? []} />

      <ChainHistory
        history={history}
        expanded={expanded}
        onToggle={toggleExpanded}
      />

      {error && <div style={errorStyle}>{error}</div>}
    </div>
  );
}

/** Collapsed list of superseded offer rounds. Each entry shows status
 *  pill, round label, key terms in one line; click to expand into the
 *  full read-only term grid. */
function ChainHistory({
  history,
  expanded,
  onToggle,
}: {
  history: Offer[];
  expanded: Set<string>;
  onToggle: (id: string) => void;
}) {
  if (history.length === 0) return null;
  return (
    <div className="mt-6">
      <div className="flex items-center gap-2 mb-3">
        <Layers size={13} strokeWidth={1.7} style={{ color: 'var(--text-3)' }} />
        <span className="eyebrow">Previous rounds · {history.length}</span>
      </div>
      <ol
        className="flex flex-col"
        style={{ listStyle: 'none', padding: 0, margin: 0, gap: 8 }}
      >
        {history.map((h, i) => {
          const isOpen = expanded.has(h.id);
          // Oldest round = #1; most recent superseded round = highest #.
          const roundNumber = history.length - i;
          return (
            <li
              key={h.id}
              style={{
                borderRadius: 'var(--radius)',
                background: 'var(--bg-sunken)',
                boxShadow: 'inset 0 0 0 1px var(--border)',
              }}
            >
              <button
                type="button"
                onClick={() => onToggle(h.id)}
                className="flex items-center w-full text-left"
                style={{
                  gap: 10,
                  padding: '10px 14px',
                  background: 'transparent',
                  border: 0,
                  cursor: 'pointer',
                  color: 'inherit',
                }}
              >
                {isOpen ? (
                  <ChevronDown size={13} strokeWidth={1.9} style={{ color: 'var(--text-4)' }} />
                ) : (
                  <ChevronRight size={13} strokeWidth={1.9} style={{ color: 'var(--text-4)' }} />
                )}
                <span
                  className="pill inline-flex items-center gap-1"
                  style={{
                    background: STATUS_COLORS.superseded.bg,
                    color: STATUS_COLORS.superseded.fg,
                  }}
                >
                  <Layers size={11} strokeWidth={1.9} />
                  Round {roundNumber}
                </span>
                <span
                  className="mono truncate"
                  style={{ fontSize: 12, color: 'var(--text-3)', flex: 1, minWidth: 0 }}
                >
                  {summarizeTerms(h)}
                </span>
                <span
                  className="mono"
                  style={{
                    fontSize: 10.5,
                    color: 'var(--text-4)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {h.updated_at
                    ? new Date(h.updated_at).toLocaleDateString(undefined, {
                        month: 'short',
                        day: 'numeric',
                      })
                    : ''}
                </span>
              </button>
              {isOpen && (
                <div style={{ padding: '0 14px 14px 14px' }}>
                  <OfferReadOnly offer={h} />
                </div>
              )}
            </li>
          );
        })}
      </ol>
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

/** Read-only view used for frozen states (accepted/declined/expired)
 *  and for expanded history rounds. Same field layout as the inline
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

/** Bulk editor used when the user is recording a new offer round
 *  (first round or a counter to an existing round). Cancel walks
 *  away with no DB write. */
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
        <span className="eyebrow">Negotiation trail (this round)</span>
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

/** Single-line summary for collapsed history rows — leads with the
 *  base salary and equity amount, the two terms most callers want at
 *  a glance. Falls back to "—" when neither is set. */
function summarizeTerms(o: Offer): string {
  const parts: string[] = [];
  if (o.base_salary != null) parts.push(`$${o.base_salary.toLocaleString()} base`);
  if (o.equity_amount) parts.push(o.equity_amount);
  if (o.sign_on != null) parts.push(`$${o.sign_on.toLocaleString()} sign-on`);
  return parts.length > 0 ? parts.join(' · ') : '—';
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

const errorStyle: React.CSSProperties = {
  marginTop: 10,
  color: 'var(--plum)',
  fontSize: 12,
};
