import { Clock, Pause, Play } from 'lucide-react';
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

export default function HeaderTimer({ kind, id }: Props) {
  const { displayMs, running, ready, toggle, reset } = useQuestionTimer(kind, id);
  if (!ready) {
    // Render a placeholder same width as the live state so the chip
    // doesn't reflow when the row loads.
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
  const label = running
    ? `Question timer: ${formatTimer(displayMs)} running. Click to pause; shift-click to reset.`
    : `Question timer: ${formatTimer(displayMs)} paused. Click to start; shift-click to reset.`;
  const Icon = running ? Pause : Play;
  return (
    <button
      type="button"
      onClick={(e) => {
        if (e.shiftKey) {
          reset();
        } else {
          toggle();
        }
      }}
      onContextMenu={(e) => {
        e.preventDefault();
        reset();
      }}
      aria-label={label}
      title={
        running
          ? 'Pause • Shift-click or right-click to reset'
          : 'Start • Shift-click or right-click to reset'
      }
      className="app-header-chrome-btn inline-flex items-center"
      style={{
        height: 24,
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
  );
}
