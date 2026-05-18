/**
 * One round, rendered as a collapsed summary that expands inline to
 * a read view of every field. Each field is click-to-edit with ✓/✗
 * commit (see InlineEditField). No autosave-on-blur — every change
 * is explicit, so accidental drags / blurs don't mutate the row.
 *
 * The summary header carries the chevron + type pill + interviewer +
 * status pill + date + a small trash-icon delete button. The delete
 * button two-step-confirms in place so accidental clicks don't blow
 * away a round.
 *
 * The expanded view holds the editor for every field plus an "Open
 * guide" deep link for types with a matching question-track guide
 * page (system design, coding, behavioral, etc).
 */
import { useState, type CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, ChevronRight, Layers, Trash2, X } from 'lucide-react';
import InterviewTypePill from './InterviewTypePill';
import InlineEditField from './InlineEditField';
import { interviewTypeGuidePath, interviewTypeLabel } from './interviewTypes';
import { deleteRound, updateRound, type InterviewRound } from './api';

type Props = {
  round: InterviewRound;
  ordinal?: number;
  nested?: boolean;
  onUpdated: (next: InterviewRound) => void;
  onDeleted: (id: string) => void;
};

const STATUS_COLORS: Record<
  InterviewRound['scheduled_status'],
  { fg: string; bg: string }
> = {
  scheduled: { fg: 'var(--accent)', bg: 'color-mix(in oklab, var(--accent) 14%, transparent)' },
  completed: { fg: 'var(--forest)', bg: 'color-mix(in oklab, #16a34a 14%, transparent)' },
  canceled: { fg: 'var(--text-4)', bg: 'var(--bg-sunken)' },
};

const SCHEDULED_STATUS_OPTIONS = [
  { value: 'scheduled', label: 'Scheduled' },
  { value: 'completed', label: 'Completed' },
  { value: 'canceled', label: 'Canceled' },
];

function formatDuration(min: number): string {
  if (!min || min <= 0) return '—';
  if (min < 60) return `${min} min`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

export default function RoundCard({
  round,
  ordinal,
  nested,
  onUpdated,
  onDeleted,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function commit<K extends keyof InterviewRound>(
    field: K,
    next: InterviewRound[K],
  ) {
    const saved = await updateRound(round.id, { [field]: next } as Partial<InterviewRound>);
    onUpdated(saved);
  }

  async function handleDelete() {
    setDeleting(true);
    try {
      await deleteRound(round.id);
      onDeleted(round.id);
    } finally {
      setDeleting(false);
    }
  }

  function toggleExpanded() {
    setExpanded((v) => !v);
    // Closing the card discards the delete confirm prompt too.
    setConfirmingDelete(false);
  }

  const statusColors = STATUS_COLORS[round.scheduled_status];
  const guidePath = interviewTypeGuidePath(round.round_type);

  return (
    <div
      style={{
        background: nested ? 'transparent' : 'var(--bg-sunken)',
        borderRadius: nested ? 0 : 'var(--radius)',
        boxShadow: nested ? 'none' : 'inset 0 0 0 1px var(--border)',
        borderBottom: nested ? '1px solid var(--border)' : undefined,
        overflow: 'hidden',
      }}
    >
      {/*
        Header row — a div (not a button) because we want a trash icon
        embedded inside it as its own button. Clicking the row toggles
        expansion; clicking the trash icon (or its confirm cluster)
        stops propagation so the row doesn't toggle behind it.
      */}
      <div
        role="button"
        tabIndex={0}
        onClick={toggleExpanded}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggleExpanded();
          }
        }}
        aria-expanded={expanded}
        className="flex items-center"
        style={{
          padding: nested ? '10px 12px' : '12px 14px',
          gap: 12,
          cursor: 'pointer',
        }}
      >
        <ChevronRight
          size={12}
          strokeWidth={2}
          style={{
            color: 'var(--text-4)',
            flexShrink: 0,
            transform: expanded ? 'rotate(90deg)' : 'rotate(0deg)',
            transition: 'transform 120ms',
          }}
        />
        {ordinal !== undefined && (
          <span
            className="mono"
            style={{
              color: 'var(--text-4)',
              fontSize: 10.5,
              width: 18,
              flexShrink: 0,
            }}
          >
            {String(ordinal).padStart(2, '0')}
          </span>
        )}
        <InterviewTypePill type={round.round_type} short />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div
            style={{
              fontSize: 12.5,
              color: 'var(--text-2)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {round.interviewer || (
              <span style={{ color: 'var(--text-4)', fontStyle: 'italic' }}>
                Interviewer TBD
              </span>
            )}
          </div>
        </div>
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            padding: '2px 8px',
            borderRadius: 999,
            fontSize: 10.5,
            fontWeight: 500,
            background: statusColors.bg,
            color: statusColors.fg,
            flexShrink: 0,
            textTransform: 'capitalize',
          }}
        >
          {round.scheduled_status}
        </span>
        <span
          className="mono"
          style={{
            fontSize: 11,
            color: 'var(--text-3)',
            flexShrink: 0,
            minWidth: 40,
            textAlign: 'right',
          }}
        >
          {formatDuration(round.duration_minutes)}
        </span>
        <span
          className="mono"
          style={{
            fontSize: 11,
            color: 'var(--text-3)',
            flexShrink: 0,
          }}
        >
          {round.date || '—'}
        </span>
        {/*
          Inline delete affordance. Two-step confirm sits adjacent to
          the icon — never under a footer the user has to scroll to.
        */}
        <div
          className="flex items-center"
          style={{ gap: 4, flexShrink: 0 }}
          onClick={(e) => e.stopPropagation()}
        >
          {confirmingDelete ? (
            <>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  void handleDelete();
                }}
                disabled={deleting}
                aria-label="Confirm delete"
                title="Confirm delete"
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
                  cursor: deleting ? 'wait' : 'pointer',
                  opacity: deleting ? 0.6 : 1,
                }}
              >
                Delete?
              </button>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setConfirmingDelete(false);
                }}
                disabled={deleting}
                aria-label="Cancel delete"
                title="Cancel delete"
                style={iconBtnStyle}
              >
                <X size={12} strokeWidth={2} />
              </button>
            </>
          ) : (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setConfirmingDelete(true);
              }}
              aria-label="Delete round"
              title="Delete round"
              style={iconBtnStyle}
            >
              <Trash2 size={12} strokeWidth={1.8} />
            </button>
          )}
        </div>
      </div>

      {expanded && (
        <div
          style={{
            padding: '12px 14px 14px 38px',
            background: 'var(--bg)',
            borderTop: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
            gap: 12,
          }}
        >
          {(round.loop_label || guidePath) && (
            <div
              className="flex items-center"
              style={{ gap: 8, flexWrap: 'wrap' }}
            >
              {round.loop_label && (
                <div
                  className="inline-flex items-center"
                  style={{
                    gap: 5,
                    padding: '3px 9px',
                    fontSize: 11,
                    fontWeight: 500,
                    background: 'var(--bg-sunken)',
                    color: 'var(--text-2)',
                    border: '1px solid var(--border)',
                    borderRadius: 999,
                  }}
                  title="Interview loop"
                >
                  <Layers size={11} strokeWidth={1.8} />
                  {round.loop_label}
                </div>
              )}
              {guidePath && (
                <Link
                  to={guidePath}
                  className="inline-flex items-center"
                  style={{
                    gap: 5,
                    padding: '3px 10px',
                    fontSize: 11,
                    fontWeight: 500,
                    background: 'var(--accent-soft)',
                    color: 'var(--accent)',
                    border: 0,
                    borderRadius: 999,
                    textDecoration: 'none',
                  }}
                >
                  <BookOpen size={11} strokeWidth={1.8} />
                  Open {interviewTypeLabel(round.round_type)} guide
                </Link>
              )}
            </div>
          )}

          <div
            className="grid gap-3"
            style={{
              gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            }}
          >
            <InlineEditField
              kind="interview-type"
              label="Type"
              value={round.round_type}
              onCommit={(next) => commit('round_type', next)}
              renderRead={() => (
                <InterviewTypePill type={round.round_type} />
              )}
            />
            <InlineEditField
              kind="date"
              label="Date"
              value={round.date}
              onCommit={(next) => commit('date', next)}
              placeholder="Set a date"
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
              kind="duration-minutes"
              label="Duration"
              value={String(round.duration_minutes || '')}
              onCommit={(next) => {
                const n = Number(next);
                return commit('duration_minutes', Number.isFinite(n) && n > 0 ? n : 0);
              }}
              placeholder="e.g. 60"
              renderRead={() => (
                <span
                  className="mono"
                  style={{
                    fontSize: 13,
                    color: round.duration_minutes ? 'var(--text)' : 'var(--text-4)',
                  }}
                >
                  {formatDuration(round.duration_minutes)}
                </span>
              )}
            />
            <InlineEditField
              kind="text"
              label="Interviewer"
              value={round.interviewer}
              onCommit={(next) => commit('interviewer', next)}
              placeholder="Name, role, timezone"
            />
            <InlineEditField
              kind="text"
              label="Loop label"
              value={round.loop_label}
              onCommit={(next) => commit('loop_label', next)}
              placeholder="Add to a loop (optional)"
            />
            <InlineEditField
              kind="select"
              label="Status"
              value={round.scheduled_status}
              options={SCHEDULED_STATUS_OPTIONS}
              onCommit={(next) =>
                commit(
                  'scheduled_status',
                  next as InterviewRound['scheduled_status'],
                )
              }
              renderRead={() => (
                <span
                  style={{
                    display: 'inline-flex',
                    alignItems: 'center',
                    padding: '2px 10px',
                    borderRadius: 999,
                    fontSize: 11.5,
                    fontWeight: 500,
                    background: statusColors.bg,
                    color: statusColors.fg,
                    textTransform: 'capitalize',
                  }}
                >
                  {round.scheduled_status}
                </span>
              )}
            />
            <InlineEditField
              kind="text"
              label="Result"
              value={round.result}
              onCommit={(next) => commit('result', next)}
              placeholder="Pending / Passed / Follow-up / …"
            />
          </div>

          <InlineEditField
            kind="multiline"
            label="Preparation notes"
            value={round.preparation_notes}
            onCommit={(next) => commit('preparation_notes', next)}
            placeholder="What do you want top-of-mind going in?"
          />

          <InlineEditField
            kind="multiline"
            label="Notes"
            value={round.notes}
            onCommit={(next) => commit('notes', next)}
            placeholder="Running notes during or after the round."
          />
        </div>
      )}
    </div>
  );
}

const iconBtnStyle: CSSProperties = {
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
