import { Flame } from 'lucide-react';
import { useLoginStreak } from '../../hooks/useLoginStreak';

// Editorial streak card — big italic number on the left, 7-day bead strip on
// the right. Designed to earn its place in an otherwise calm dashboard.

const DAY_LABELS = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

function contextLine(current: number, longest: number, activeToday: boolean): string {
  if (current === 0 && longest === 0) {
    return 'Sign in tomorrow to extend your streak.';
  }
  if (current === 0) {
    return 'Gap day — a fresh sign-in restarts the run.';
  }
  if (current === 1 && activeToday) return 'First day on the board.';
  if (current === longest && current > 1) return 'Personal best — keep it going.';
  if (current >= 7) return 'Strong run. Show up again tomorrow.';
  return 'Show up once a day. That is the whole trick.';
}

export default function StreakCard() {
  const { current, longest, activeToday, last7 } = useLoginStreak();

  // Index within last7 of today (last element).
  const todayIdx = 6;

  return (
    <div
      className="relative overflow-hidden flex-shrink-0 fade-up"
      style={{
        padding: 20,
        minWidth: 300,
        borderRadius: 'var(--radius-lg)',
        background: 'var(--bg-elev)',
        boxShadow: 'var(--shadow-card)',
      }}
    >
      {/* Background mark — a large, low-opacity flame that hints at the
          streak metaphor without shouting. */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: -20,
          right: -10,
          color: 'var(--accent)',
          opacity: 0.08,
          pointerEvents: 'none',
        }}
      >
        <Flame size={120} strokeWidth={1.2} />
      </div>

      <div className="flex items-center gap-5" style={{ position: 'relative' }}>
        <div style={{ minWidth: 80 }}>
          <div className="eyebrow mb-2">Streak</div>
          <div className="flex items-baseline gap-2">
            <span
              className="display-italic"
              style={{
                fontSize: 52,
                fontWeight: 400,
                lineHeight: 1,
                color: current > 0 ? 'var(--text)' : 'var(--text-4)',
                letterSpacing: '-0.02em',
              }}
            >
              {current}
            </span>
            <span
              className="mono uppercase"
              style={{
                fontSize: 10,
                color: 'var(--text-4)',
                letterSpacing: '0.14em',
              }}
            >
              {current === 1 ? 'day' : 'days'}
            </span>
          </div>
        </div>

        <div
          aria-label={`Last 7 days: ${last7.map((b) => (b ? 'active' : 'idle')).join(', ')}`}
          className="flex gap-1.5 pl-5"
          style={{ borderLeft: '1px solid var(--border)' }}
        >
          {last7.map((active, i) => {
            const isToday = i === todayIdx;
            return (
              <div
                key={i}
                className="flex flex-col items-center gap-1.5"
                style={{ width: 18 }}
              >
                <div
                  style={{
                    width: 10,
                    height: 10,
                    borderRadius: 999,
                    background: active ? 'var(--accent)' : 'transparent',
                    boxShadow: active
                      ? isToday
                        ? '0 0 0 3px var(--accent-soft)'
                        : 'none'
                      : 'inset 0 0 0 1px var(--border-strong)',
                    transition: 'background 160ms, box-shadow 160ms',
                  }}
                />
                <span
                  className="mono"
                  style={{
                    fontSize: 9,
                    color: isToday ? 'var(--accent)' : 'var(--text-4)',
                    letterSpacing: '0.08em',
                    fontWeight: isToday ? 600 : 400,
                  }}
                >
                  {dayLetter(i, todayIdx)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div
        className="flex items-center justify-between mt-4 pt-3"
        style={{ borderTop: '1px solid var(--border)', gap: 12 }}
      >
        <span style={{ fontSize: 12, color: 'var(--text-3)', lineHeight: 1.5 }}>
          {contextLine(current, longest, activeToday)}
        </span>
        <span
          className="mono whitespace-nowrap"
          style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.08em' }}
        >
          LONGEST · {longest}
        </span>
      </div>
    </div>
  );
}

function dayLetter(idx: number, todayIdx: number): string {
  // Show the weekday letter for each of the last 7 days, today last.
  const d = new Date();
  d.setDate(d.getDate() - (todayIdx - idx));
  return DAY_LABELS[d.getDay()];
}
