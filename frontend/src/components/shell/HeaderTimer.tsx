import { Clock, Pause, Play, RotateCcw } from 'lucide-react';
import { useQuestionTimer } from '../../hooks/useQuestionTimer';
import type { PracticeKind } from '../../hooks/progressApi';

export function formatTimer(ms: number): string {
  const totalSeconds = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

type Props = {
  kind: PracticeKind;
  id: string | number;
};

// Two-button chip: a large primary play/pause that owns the readout, and
// a small reset that only appears once the timer has accumulated time so
// it doesn't add noise to a fresh round. Both buttons sit in one rounded
// well so they read as a single control unit.
export default function HeaderTimer({ kind, id }: Props) {
  const { displayMs, running, ready, toggle, reset } = useQuestionTimer(kind, id);
  if (!ready) {
    return (
      <span
        aria-hidden="true"
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          height: 24,
          padding: '0 8px',
          fontSize: 11.5,
          color: 'var(--text-3)',
          opacity: 0.5,
        }}
      >
        <Clock size={12} strokeWidth={1.7} />
        <span style={{ fontVariantNumeric: 'tabular-nums' }}>--:--</span>
      </span>
    );
  }
  const Icon = running ? Pause : Play;
  const elapsed = displayMs > 0;
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'stretch',
        height: 24,
      }}
    >
      <button
        type="button"
        onClick={toggle}
        aria-label={
          running
            ? `Pause question timer at ${formatTimer(displayMs)}`
            : elapsed
              ? `Resume question timer at ${formatTimer(displayMs)}`
              : 'Start question timer'
        }
        title={running ? 'Pause' : elapsed ? 'Resume' : 'Start'}
        className="app-header-chrome-btn inline-flex items-center"
        style={{
          height: '100%',
          padding: '0 8px',
          gap: 5,
          fontSize: 11.5,
          whiteSpace: 'nowrap',
          border: 0,
          borderRadius: 5,
          background: 'transparent',
          color: running ? 'var(--accent)' : 'var(--text-2)',
          cursor: 'pointer',
          fontVariantNumeric: 'tabular-nums',
        }}
      >
        <Icon size={12} strokeWidth={1.8} />
        <span>{formatTimer(displayMs)}</span>
      </button>
      {elapsed && (
        <button
          type="button"
          onClick={reset}
          aria-label="Reset question timer to 00:00"
          title="Reset timer"
          className="app-header-chrome-btn inline-flex items-center justify-center"
          style={{
            height: '100%',
            width: 22,
            marginLeft: 2,
            border: 0,
            borderRadius: 5,
            background: 'transparent',
            color: 'var(--text-3)',
            cursor: 'pointer',
          }}
        >
          <RotateCcw size={11} strokeWidth={1.8} />
        </button>
      )}
    </span>
  );
}
