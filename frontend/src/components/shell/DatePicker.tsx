import { useEffect, useMemo, useRef, useState } from 'react';
import { Calendar as CalIcon, ChevronLeft, ChevronRight, X } from 'lucide-react';

// Themed calendar picker. Matches the sans/paper look of the rest of
// the app, reads/writes ISO date strings (`YYYY-MM-DD`) to keep the
// existing PocketBase payloads and Dashboard filters unchanged.
//
// Single-component: one input-shaped trigger plus a popover calendar.
// No external deps. Outside clicks and Escape close.

interface Props {
  value: string;
  onChange: (next: string) => void;
  placeholder?: string;
  min?: string;
  max?: string;
  ariaLabel?: string;
  style?: React.CSSProperties;
  className?: string;
  disabled?: boolean;
  // Show a "Clear" action in the popover — useful for optional dates.
  clearable?: boolean;
}

export default function DatePicker({
  value,
  onChange,
  placeholder = 'Select date',
  min,
  max,
  ariaLabel,
  style,
  className,
  disabled,
  clearable = true,
}: Props) {
  const [open, setOpen] = useState(false);
  const [placement, setPlacement] = useState<'down' | 'up'>('down');
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  const parsed = useMemo(() => parseISO(value), [value]);
  const [viewMonth, setViewMonth] = useState<{ year: number; month: number }>(() => {
    const base = parsed ?? new Date();
    return { year: base.getFullYear(), month: base.getMonth() };
  });

  // Decide whether to drop down or pop up based on available viewport
  // space at trigger time. Popover is ~360px tall; if there's less than
  // that below but more above, flip it.
  useEffect(() => {
    if (!open) return;
    const trigger = triggerRef.current;
    if (!trigger) return;
    const rect = trigger.getBoundingClientRect();
    const POPOVER_H = 360;
    const below = window.innerHeight - rect.bottom;
    const above = rect.top;
    if (below < POPOVER_H && above > below) setPlacement('up');
    else setPlacement('down');
  }, [open]);

  // Keep the viewed month aligned with the current value when it
  // changes externally (e.g. form reset).
  useEffect(() => {
    if (!parsed) return;
    setViewMonth({ year: parsed.getFullYear(), month: parsed.getMonth() });
  }, [parsed]);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape' && open) {
        // preventDefault so the surrounding chrome (CommandCenter, modal)
        // doesn't ALSO interpret Escape and dismiss its own layer.
        e.preventDefault();
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onDocClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const minDate = useMemo(() => parseISO(min), [min]);
  const maxDate = useMemo(() => parseISO(max), [max]);

  function pickDay(day: Date) {
    onChange(formatISO(day));
    setOpen(false);
  }

  function gotoToday() {
    const now = new Date();
    setViewMonth({ year: now.getFullYear(), month: now.getMonth() });
  }

  function stepMonth(delta: number) {
    setViewMonth((v) => {
      const m = v.month + delta;
      const year = v.year + Math.floor(m / 12);
      const month = ((m % 12) + 12) % 12;
      return { year, month };
    });
  }

  const label = parsed ? formatDisplay(parsed) : placeholder;

  return (
    <div ref={ref} style={{ position: 'relative', ...style }} className={className}>
      <button
        ref={triggerRef}
        type="button"
        aria-label={ariaLabel ?? placeholder}
        aria-haspopup="dialog"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2 w-full"
        style={{
          width: '100%',
          padding: '7px 10px',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--border)',
          background: 'var(--bg-elev)',
          color: parsed ? 'var(--text)' : 'var(--text-4)',
          fontSize: 13,
          textAlign: 'left',
          cursor: disabled ? 'not-allowed' : 'pointer',
          fontFamily: 'inherit',
        }}
      >
        <CalIcon size={13} strokeWidth={1.8} style={{ color: 'var(--text-3)', flexShrink: 0 }} />
        <span
          style={{
            flex: 1,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {label}
        </span>
        {parsed && clearable && !disabled && (
          <span
            role="button"
            aria-label="Clear date"
            onClick={(e) => {
              e.stopPropagation();
              onChange('');
            }}
            style={{
              display: 'inline-flex',
              color: 'var(--text-4)',
              padding: 2,
              borderRadius: 4,
              cursor: 'pointer',
            }}
          >
            <X size={12} strokeWidth={1.8} />
          </span>
        )}
      </button>

      {open && !disabled && (
        <div
          role="dialog"
          className="card"
          style={{
            position: 'absolute',
            ...(placement === 'up'
              ? { bottom: 'calc(100% + 6px)' }
              : { top: 'calc(100% + 6px)' }),
            left: 0,
            zIndex: 100,
            padding: 10,
            boxShadow: 'var(--shadow-elev)',
            minWidth: 280,
            background: 'var(--bg-elev)',
          }}
        >
          <div className="flex items-center justify-between mb-2">
            <button
              type="button"
              aria-label="Previous month"
              onClick={() => stepMonth(-1)}
              style={navBtn}
            >
              <ChevronLeft size={14} strokeWidth={1.8} />
            </button>
            <button
              type="button"
              onClick={gotoToday}
              style={{
                padding: '4px 10px',
                border: 0,
                background: 'transparent',
                color: 'var(--text)',
                fontSize: 13,
                fontWeight: 500,
                cursor: 'pointer',
                fontFamily: 'inherit',
              }}
              title="Jump to current month"
            >
              {MONTH_NAMES[viewMonth.month]} {viewMonth.year}
            </button>
            <button
              type="button"
              aria-label="Next month"
              onClick={() => stepMonth(1)}
              style={navBtn}
            >
              <ChevronRight size={14} strokeWidth={1.8} />
            </button>
          </div>

          <div
            className="grid"
            style={{
              gridTemplateColumns: 'repeat(7, minmax(0, 1fr))',
              gap: 2,
              marginBottom: 4,
            }}
          >
            {DOW_LABELS.map((d) => (
              <div
                key={d}
                className="eyebrow"
                style={{
                  textAlign: 'center',
                  padding: '4px 0',
                  fontSize: 9.5,
                  color: 'var(--text-4)',
                }}
              >
                {d}
              </div>
            ))}
          </div>

          <div
            className="grid"
            style={{
              gridTemplateColumns: 'repeat(7, minmax(0, 1fr))',
              gap: 2,
            }}
          >
            {buildGrid(viewMonth.year, viewMonth.month).map((d, i) => {
              const inMonth = d.getMonth() === viewMonth.month;
              const isToday = sameDay(d, new Date());
              const selected = parsed && sameDay(d, parsed);
              const disabledDay =
                (minDate && d < stripTime(minDate)) ||
                (maxDate && d > stripTime(maxDate));
              return (
                <button
                  key={i}
                  type="button"
                  disabled={Boolean(disabledDay)}
                  onClick={() => pickDay(d)}
                  style={{
                    padding: '6px 0',
                    border: 0,
                    borderRadius: 6,
                    background: selected
                      ? 'var(--accent)'
                      : isToday
                        ? 'var(--bg-sunken)'
                        : 'transparent',
                    boxShadow:
                      !selected && isToday
                        ? 'inset 0 0 0 1px var(--border-strong)'
                        : 'none',
                    color: selected
                      ? 'var(--bg-elev)'
                      : inMonth
                        ? 'var(--text)'
                        : 'var(--text-4)',
                    fontSize: 12.5,
                    fontWeight: selected ? 600 : isToday ? 500 : 400,
                    cursor: disabledDay ? 'not-allowed' : 'pointer',
                    opacity: disabledDay ? 0.4 : 1,
                    fontFamily: 'inherit',
                  }}
                >
                  {d.getDate()}
                </button>
              );
            })}
          </div>

          <div
            className="flex items-center justify-between mt-3 pt-2"
            style={{ borderTop: '1px solid var(--border)' }}
          >
            <button
              type="button"
              onClick={() => {
                const now = new Date();
                onChange(formatISO(now));
                setOpen(false);
              }}
              style={footerBtn}
            >
              Today
            </button>
            {parsed && clearable && (
              <button
                type="button"
                onClick={() => {
                  onChange('');
                  setOpen(false);
                }}
                style={{ ...footerBtn, color: 'var(--plum)' }}
              >
                Clear
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

const MONTH_NAMES = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];

const DOW_LABELS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT'];

function stripTime(d: Date): Date {
  const copy = new Date(d);
  copy.setHours(0, 0, 0, 0);
  return copy;
}

function sameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

function parseISO(v: string | undefined): Date | null {
  if (!v) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(v);
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return Number.isNaN(d.getTime()) ? null : d;
}

function formatISO(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function formatDisplay(d: Date): string {
  return d.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function buildGrid(year: number, month: number): Date[] {
  const first = new Date(year, month, 1);
  const start = new Date(first);
  start.setDate(first.getDate() - first.getDay()); // back to Sunday
  const days: Date[] = [];
  for (let i = 0; i < 42; i += 1) {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    days.push(d);
  }
  return days;
}

const navBtn: React.CSSProperties = {
  padding: 6,
  border: 0,
  background: 'transparent',
  color: 'var(--text-3)',
  cursor: 'pointer',
  borderRadius: 6,
  display: 'inline-flex',
};

const footerBtn: React.CSSProperties = {
  padding: '6px 10px',
  border: 0,
  background: 'transparent',
  color: 'var(--text-2)',
  fontSize: 11.5,
  cursor: 'pointer',
  fontFamily: 'inherit',
  fontWeight: 500,
};
