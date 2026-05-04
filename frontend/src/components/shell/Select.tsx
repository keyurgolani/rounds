import { useEffect, useRef, useState } from 'react';
import { Check, ChevronDown } from 'lucide-react';

// Themed single-select that mirrors the native <select> API: pass a
// `value` and an `onChange(next)` plus `options`. Popover flips above
// the trigger when there isn't enough room below, matching DatePicker.

export interface SelectOption<T extends string = string> {
  value: T;
  label: string;
  sub?: string;
  disabled?: boolean;
}

interface Props<T extends string = string> {
  value: T;
  options: SelectOption<T>[];
  onChange: (next: T) => void;
  placeholder?: string;
  ariaLabel?: string;
  style?: React.CSSProperties;
  className?: string;
  disabled?: boolean;
  fullWidth?: boolean;
  // Which edge the popover anchors to. "right" is useful when the
  // trigger sits flush against a container's right edge — a left-
  // anchored popover would clip past the edge.
  align?: 'left' | 'right';
}

export default function Select<T extends string = string>({
  value,
  options,
  onChange,
  placeholder = 'Choose…',
  ariaLabel,
  style,
  className,
  disabled,
  fullWidth = true,
  align = 'left',
}: Props<T>) {
  const [open, setOpen] = useState(false);
  const [placement, setPlacement] = useState<'down' | 'up'>('down');
  const ref = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

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

  useEffect(() => {
    if (!open) return;
    const t = triggerRef.current;
    if (!t) return;
    const rect = t.getBoundingClientRect();
    const panelH = Math.min(320, 44 + Math.min(options.length, 8) * 36);
    const below = window.innerHeight - rect.bottom;
    const above = rect.top;
    if (below < panelH && above > below) setPlacement('up');
    else setPlacement('down');
  }, [open, options.length]);

  const current = options.find((o) => o.value === value);
  const label = current?.label ?? placeholder;

  return (
    <div
      ref={ref}
      className={className}
      style={{ position: 'relative', width: fullWidth ? '100%' : undefined, ...style }}
    >
      <button
        ref={triggerRef}
        type="button"
        aria-label={ariaLabel ?? placeholder}
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-2"
        style={{
          width: fullWidth ? '100%' : undefined,
          padding: '7px 10px',
          borderRadius: 'var(--radius)',
          border: '1px solid var(--border)',
          background: 'var(--bg-elev)',
          color: current ? 'var(--text)' : 'var(--text-4)',
          fontSize: 13,
          textAlign: 'left',
          cursor: disabled ? 'not-allowed' : 'pointer',
          fontFamily: 'inherit',
        }}
      >
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
        <ChevronDown
          size={12}
          strokeWidth={1.8}
          style={{
            color: 'var(--text-4)',
            transform: open ? 'rotate(180deg)' : undefined,
            transition: 'transform 120ms',
            flexShrink: 0,
          }}
        />
      </button>

      {open && !disabled && (
        <div
          role="listbox"
          className="card"
          style={{
            position: 'absolute',
            ...(placement === 'up'
              ? { bottom: 'calc(100% + 6px)' }
              : { top: 'calc(100% + 6px)' }),
            ...(align === 'right'
              ? { right: 0 }
              : { left: 0, right: fullWidth ? 0 : undefined }),
            minWidth: triggerRef.current?.offsetWidth ?? 200,
            maxHeight: 280,
            overflowY: 'auto',
            padding: 4,
            zIndex: 100,
            boxShadow: 'var(--shadow-elev)',
            background: 'var(--bg-elev)',
          }}
        >
          {options.map((o) => {
            const selected = o.value === value;
            return (
              <button
                key={o.value}
                type="button"
                disabled={o.disabled}
                onClick={() => {
                  onChange(o.value);
                  setOpen(false);
                }}
                role="option"
                aria-selected={selected}
                className="flex items-center justify-between w-full"
                style={{
                  padding: '7px 10px',
                  border: 0,
                  background: selected ? 'var(--bg-sunken)' : 'transparent',
                  color: o.disabled ? 'var(--text-4)' : 'var(--text)',
                  cursor: o.disabled ? 'not-allowed' : 'pointer',
                  borderRadius: 'var(--radius)',
                  textAlign: 'left',
                  fontFamily: 'inherit',
                  fontSize: 13,
                  gap: 8,
                }}
                onMouseEnter={(e) => {
                  if (!selected && !o.disabled)
                    e.currentTarget.style.background = 'var(--bg-sunken)';
                }}
                onMouseLeave={(e) => {
                  if (!selected)
                    e.currentTarget.style.background = 'transparent';
                }}
              >
                <span
                  className="flex flex-col"
                  style={{ minWidth: 0, flex: 1, textAlign: 'left' }}
                >
                  <span
                    style={{
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      fontWeight: selected ? 500 : 400,
                    }}
                  >
                    {o.label}
                  </span>
                  {o.sub && (
                    <span
                      className="mono"
                      style={{
                        fontSize: 10.5,
                        color: 'var(--text-4)',
                        letterSpacing: '0.04em',
                      }}
                    >
                      {o.sub}
                    </span>
                  )}
                </span>
                {selected && (
                  <Check
                    size={13}
                    strokeWidth={2}
                    style={{ color: 'var(--accent)', flexShrink: 0 }}
                  />
                )}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
