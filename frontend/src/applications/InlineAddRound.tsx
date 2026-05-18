/**
 * Inline "Add round" affordance that lives at the bottom of an
 * application's rounds list. Replaces the modal-based scheduler.
 *
 * Initial state: a small "+ Add round" link. Clicking it expands a
 * draft card with type, date, interviewer, and loop label fields.
 * The user fills them in and clicks ✓ to commit (or ✗ to cancel).
 *
 * For loops: there's no separate "loop mode" any more — the user
 * just types a label in the Loop field. Adding a second round with
 * the same label clusters them visually. Less keyboard-friendly than
 * the old modal's "stack 6 drafts" mode, but matches the user's
 * inline-everything preference.
 */
import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { Check, Plus, X } from 'lucide-react';
import { createRound, type InterviewRound } from './api';
import { INTERVIEW_TYPES } from './interviewTypes';
import Select from '../components/shell/Select';
import DateTimePicker from '../components/shell/DateTimePicker';

type Props = {
  applicationId: string;
  /** Existing loop labels on this app, surfaced as a datalist so the
   *  user can pick one and attach the new round to it. */
  existingLoopLabels: string[];
  onCreated: (round: InterviewRound) => void;
};

const DEFAULT_TYPE = 'coding';
const DEFAULT_DURATION = 60;

export default function InlineAddRound({
  applicationId,
  existingLoopLabels,
  onCreated,
}: Props) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState({
    round_type: DEFAULT_TYPE,
    date: '',
    interviewer: '',
    loop_label: '',
    duration_minutes: DEFAULT_DURATION,
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const interviewerRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) interviewerRef.current?.focus();
  }, [open]);

  function cancel() {
    setOpen(false);
    setDraft({
      round_type: DEFAULT_TYPE,
      date: '',
      interviewer: '',
      loop_label: '',
      duration_minutes: DEFAULT_DURATION,
    });
    setError(null);
  }

  async function commit() {
    setError(null);
    if (!draft.round_type) {
      setError('Pick a round type.');
      return;
    }
    setSaving(true);
    try {
      const created = await createRound(applicationId, {
        round_type: draft.round_type,
        date: draft.date,
        interviewer: draft.interviewer,
        loop_label: draft.loop_label.trim(),
        duration_minutes: draft.duration_minutes || 0,
      });
      onCreated(created);
      cancel();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not add round');
    } finally {
      setSaving(false);
    }
  }

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="inline-flex items-center"
        style={{
          alignSelf: 'flex-start',
          padding: '8px 12px',
          gap: 6,
          background: 'transparent',
          border: '1px dashed var(--border-strong)',
          borderRadius: 'var(--radius)',
          color: 'var(--accent)',
          fontSize: 12.5,
          fontWeight: 500,
          cursor: 'pointer',
        }}
      >
        <Plus size={13} strokeWidth={2} /> Add round
      </button>
    );
  }

  return (
    <div
      style={{
        padding: 12,
        background: 'var(--bg)',
        border: '1px solid var(--accent)',
        borderRadius: 'var(--radius)',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      <div
        className="eyebrow"
        style={{ color: 'var(--accent)', letterSpacing: '0.08em' }}
      >
        New round
      </div>
      <div
        className="grid gap-3"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}
      >
        <Field label="Type">
          <Select
            value={draft.round_type}
            onChange={(v) => setDraft({ ...draft, round_type: v })}
            options={INTERVIEW_TYPES.map((t) => ({
              value: t.key,
              label: t.label,
            }))}
            fullWidth
          />
        </Field>
        <Field label="Date &amp; time">
          <DateTimePicker
            value={draft.date}
            onChange={(v) => setDraft({ ...draft, date: v })}
            ariaLabel="Round date and time"
          />
        </Field>
        <Field label="Duration (min)">
          <input
            type="number"
            min={0}
            max={1440}
            step={5}
            value={draft.duration_minutes || ''}
            onChange={(e) =>
              setDraft({
                ...draft,
                duration_minutes: Number(e.target.value) || 0,
              })
            }
            placeholder="e.g. 60"
            style={{ ...inputStyle, fontFamily: 'var(--font-mono)', colorScheme: 'light dark' }}
          />
        </Field>
        <Field label="Interviewer">
          <input
            ref={interviewerRef}
            type="text"
            value={draft.interviewer}
            onChange={(e) => setDraft({ ...draft, interviewer: e.target.value })}
            placeholder="Name, role, timezone"
            style={inputStyle}
          />
        </Field>
        <Field label="Loop label">
          <input
            type="text"
            list="inline-add-loop-labels"
            value={draft.loop_label}
            onChange={(e) => setDraft({ ...draft, loop_label: e.target.value })}
            placeholder="Group into a loop (optional)"
            style={inputStyle}
          />
          {existingLoopLabels.length > 0 && (
            <datalist id="inline-add-loop-labels">
              {existingLoopLabels.map((lbl) => (
                <option key={lbl} value={lbl} />
              ))}
            </datalist>
          )}
        </Field>
      </div>
      {error && (
        <div
          style={{
            fontSize: 11.5,
            color: 'var(--plum)',
          }}
        >
          {error}
        </div>
      )}
      <div className="flex items-center" style={{ gap: 6 }}>
        <button
          type="button"
          onClick={() => void commit()}
          disabled={saving}
          aria-label="Add round"
          title="Add round (Enter)"
          className="inline-flex items-center"
          style={{
            gap: 6,
            padding: '6px 12px',
            background: 'var(--accent)',
            color: 'var(--bg)',
            border: 0,
            borderRadius: 'var(--radius)',
            fontSize: 12.5,
            fontWeight: 600,
            cursor: saving ? 'wait' : 'pointer',
            opacity: saving ? 0.6 : 1,
          }}
        >
          <Check size={13} strokeWidth={2.2} /> {saving ? 'Adding…' : 'Add round'}
        </button>
        <button
          type="button"
          onClick={cancel}
          disabled={saving}
          aria-label="Discard new round"
          title="Discard (Esc)"
          className="inline-flex items-center"
          style={{
            gap: 6,
            padding: '6px 12px',
            background: 'var(--bg-sunken)',
            color: 'var(--text-2)',
            border: 0,
            borderRadius: 'var(--radius)',
            fontSize: 12.5,
            cursor: 'pointer',
          }}
        >
          <X size={13} strokeWidth={2.2} /> Cancel
        </button>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col" style={{ gap: 4 }}>
      <span className="eyebrow" style={{ color: 'var(--text-3)' }}>
        {label}
      </span>
      {children}
    </label>
  );
}

const inputStyle: CSSProperties = {
  padding: '8px 10px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--border)',
  background: 'var(--bg)',
  color: 'var(--text)',
  fontSize: 13,
  width: '100%',
};
