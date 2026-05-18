/**
 * Themed date + time picker. Combines the app's existing DatePicker
 * (calendar popover, theme-matched) with a tiny time input that uses
 * `color-scheme` to make the native time popup match the app's
 * theme.
 *
 * Round-trip value: a single string. We accept and emit one of:
 *   - "YYYY-MM-DD"           — date only
 *   - "YYYY-MM-DDTHH:mm"     — date + time (ISO-ish, what we prefer)
 *   - "YYYY-MM-DD HH:mm"     — legacy from the old ScheduleRound page;
 *                              parsed leniently, re-emitted with "T"
 * Anything else is passed back unchanged. The "empty" sentinel is
 * the empty string.
 *
 * The component is used by InlineEditField (kind="date") and by
 * InlineAddRound. Native <input type="datetime-local"> is not used
 * anywhere in the app any more so the calendar / clock popovers
 * match the rest of the chrome.
 */
import { useMemo } from 'react';
import DatePicker from './DatePicker';

type Props = {
  value: string;
  onChange: (next: string) => void;
  ariaLabel?: string;
  disabled?: boolean;
  /** Show a "Clear" action in the calendar popover. */
  clearable?: boolean;
};

function splitValue(value: string): { date: string; time: string } {
  if (!value) return { date: '', time: '' };
  // Accept both ISO ("T") and the legacy " " separator.
  const sep = value.includes('T') ? 'T' : value.includes(' ') ? ' ' : null;
  if (sep) {
    const [d, t] = value.split(sep);
    return { date: d ?? '', time: (t ?? '').slice(0, 5) };
  }
  // Date-only or arbitrary string — return as date with empty time
  // when it looks like an ISO date, otherwise pass the whole thing
  // through as the date so the user can fix it manually.
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return { date: value, time: '' };
  return { date: value, time: '' };
}

function joinValue(date: string, time: string): string {
  if (!date && !time) return '';
  if (date && time) return `${date}T${time}`;
  return date || '';
}

export default function DateTimePicker({
  value,
  onChange,
  ariaLabel,
  disabled,
  clearable = true,
}: Props) {
  const { date, time } = useMemo(() => splitValue(value), [value]);

  return (
    <div
      className="flex items-center"
      style={{ gap: 6, width: '100%' }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <DatePicker
          value={date}
          onChange={(d) => onChange(joinValue(d, time))}
          ariaLabel={ariaLabel ?? 'Date'}
          disabled={disabled}
          clearable={clearable}
        />
      </div>
      <input
        type="time"
        value={time}
        onChange={(e) => onChange(joinValue(date, e.target.value))}
        aria-label="Time"
        disabled={disabled}
        style={{
          padding: '8px 10px',
          background: 'var(--bg-elev)',
          border: 0,
          boxShadow: 'inset 0 0 0 1px var(--border-strong)',
          borderRadius: 'var(--radius)',
          color: 'var(--text)',
          fontSize: 13,
          // Tell the native time-picker chrome to match the app's
          // current theme (light vs dark). Without this the popup
          // ignores the surrounding palette entirely.
          colorScheme: 'light dark',
          width: 110,
          fontFamily: 'var(--font-mono)',
        }}
      />
    </div>
  );
}
