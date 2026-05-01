import { useEffect, useRef, useState } from 'react';
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

// `compact` produces a slim horizontal strip suitable for an
// AppHeader actions slot — number + 7-day beads on a single line, no
// card chrome, no context line, fits inside the 124px expanded
// header.
export default function StreakCard({ compact = false }: { compact?: boolean } = {}) {
  const { current, longest, activeToday, last7, last30 } = useLoginStreak();
  const [expanded, setExpanded] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!expanded) return;
    function onDocClick(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setExpanded(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setExpanded(false);
    }
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [expanded]);

  // Index within last7 of today (last element).
  const todayIdx = 6;

  if (compact) {
    return (
      <div ref={ref} style={{ position: 'relative' }}>
        <button
          type="button"
          className="inline-flex items-center gap-3"
          aria-expanded={expanded}
          aria-label={`Open month streak view. Current streak: ${current} ${current === 1 ? 'day' : 'days'}, longest ${longest}`}
          title={`Streak: ${current} ${current === 1 ? 'day' : 'days'} · longest ${longest}`}
          onClick={() => setExpanded((v) => !v)}
          style={{
            padding: '6px 12px',
            border: 0,
            borderRadius: 999,
            background: 'var(--bg-sunken)',
            boxShadow: expanded ? 'inset 0 0 0 1px var(--accent)' : 'inset 0 0 0 1px var(--border)',
            cursor: 'pointer',
          }}
        >
          <span className="inline-flex items-baseline gap-1.5">
            <Flame
              size={14}
              strokeWidth={1.8}
              style={{ color: current > 0 ? 'var(--accent)' : 'var(--text-4)' }}
            />
            <span
              className="display-italic"
              style={{
                fontSize: 18,
                fontWeight: 400,
                lineHeight: 1,
                color: current > 0 ? 'var(--text)' : 'var(--text-4)',
              }}
            >
              {current}
            </span>
            <span
              className="mono uppercase"
              style={{
                fontSize: 9.5,
                color: 'var(--text-4)',
                letterSpacing: '0.12em',
              }}
            >
              {current === 1 ? 'day' : 'days'}
            </span>
          </span>
          <span
            aria-label={`Last 7 days: ${last7.map((b) => (b ? 'active' : 'idle')).join(', ')}`}
            className="inline-flex items-center gap-1"
            style={{ borderLeft: '1px solid var(--border)', paddingLeft: 10 }}
          >
            {last7.map((active, i) => {
              const isToday = i === todayIdx;
              return (
                <span
                  key={i}
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: 999,
                    background: active ? 'var(--accent)' : 'transparent',
                    boxShadow: active
                      ? isToday
                        ? '0 0 0 2px var(--accent-soft)'
                        : 'none'
                      : 'inset 0 0 0 1px var(--border-strong)',
                  }}
                />
              );
            })}
          </span>
        </button>
        {expanded && (
          <MonthView
            current={current}
            longest={longest}
            activeToday={activeToday}
            cells={last30}
          />
        )}
      </div>
    );
  }

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

function MonthView({
  current,
  longest,
  activeToday,
  cells,
}: {
  current: number;
  longest: number;
  activeToday: boolean;
  cells: { date: string; active: boolean }[];
}) {
  return (
    <div
      className="card fade-up"
      role="dialog"
      aria-label="30-day login streak"
      style={{
        position: 'absolute',
        top: 'calc(100% + 10px)',
        right: 0,
        zIndex: 80,
        width: 'min(340px, calc(100vw - 32px))',
        padding: 18,
        boxShadow: 'var(--shadow-elev)',
      }}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="eyebrow mb-1.5">30-day streak</div>
          <div className="display-italic" style={{ fontSize: 34, lineHeight: 1, fontWeight: 400 }}>
            {current} {current === 1 ? 'day' : 'days'}
          </div>
        </div>
        <div className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.08em' }}>
          LONGEST · {longest}
        </div>
      </div>
      <div
        className="grid gap-2 mt-4"
        style={{ gridTemplateColumns: 'repeat(7, minmax(0, 1fr))' }}
      >
        {DAY_LABELS.map((label, index) => (
          <div
            key={`${label}-${index}`}
            className="mono text-center"
            style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.08em' }}
          >
            {label}
          </div>
        ))}
        {cells.map((cell) => {
          const date = new Date(`${cell.date}T00:00:00`);
          return (
            <div
              key={cell.date}
              title={`${date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}: ${cell.active ? 'active' : 'idle'}`}
              className="flex items-center justify-center mono"
              style={{
                aspectRatio: '1',
                borderRadius: 12,
                background: cell.active ? 'var(--accent-soft)' : 'var(--bg-sunken)',
                color: cell.active ? 'var(--accent)' : 'var(--text-4)',
                boxShadow: cell.active ? 'inset 0 0 0 1px var(--accent)' : 'inset 0 0 0 1px var(--border)',
                fontSize: 11,
                fontWeight: cell.active ? 700 : 500,
              }}
            >
              {date.getDate()}
            </div>
          );
        })}
      </div>
      <div
        className="mt-4 pt-3 flex items-center justify-between gap-3"
        style={{ borderTop: '1px solid var(--border)' }}
      >
        <span style={{ fontSize: 12, color: 'var(--text-3)', lineHeight: 1.45 }}>
          {contextLine(current, longest, activeToday)}
        </span>
        <span className="inline-flex items-center gap-1.5 mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
          <span style={{ width: 7, height: 7, borderRadius: 999, background: 'var(--accent)' }} />
          ACTIVE
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
