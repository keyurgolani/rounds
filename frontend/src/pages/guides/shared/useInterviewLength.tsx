import { useCallback, useEffect, useState } from 'react';
import type { GuideTrack } from '../guideTypes';

/** Per-track interview length presets.
 *
 *  Each track has its own duration vocabulary because the rounds are
 *  fundamentally different shapes:
 *
 *  - Question-style tracks (SD / Coding / Behavioral / AI Coding) think
 *    in minutes within a single round.
 *  - Builder / Real-World Problems is a take-home, so it thinks in
 *    days/weeks of calendar time the candidate can spend.
 */

export type LengthPreset = {
  /** Stable identifier persisted to localStorage. */
  id: string;
  /** Display label shown in the picker. */
  label: string;
  /** Round length expressed in minutes — the canonical unit. For
   *  multi-day tracks this is the total minutes the candidate is
   *  expected to spend (assume 4 focused hours per day for week-long
   *  estimates — used by `<Duration>` to scale per-step budgets). */
  minutes: number;
};

const QUESTION_PRESETS: LengthPreset[] = [
  { id: '30',  label: '30 min',  minutes: 30  },
  { id: '45',  label: '45 min',  minutes: 45  },
  { id: '60',  label: '60 min',  minutes: 60  },
  { id: '90',  label: '90 min',  minutes: 90  },
  { id: '120', label: '2 hr',    minutes: 120 },
];

const BUILDER_PRESETS: LengthPreset[] = [
  { id: 'd1',  label: '1 day',   minutes: 60 * 4 * 1  },
  { id: 'd3',  label: '3 days',  minutes: 60 * 4 * 3  },
  { id: 'w1',  label: '1 week',  minutes: 60 * 4 * 7  },
  { id: 'w2',  label: '2 weeks', minutes: 60 * 4 * 14 },
];

const DEFAULT_ID: Record<GuideTrack, string> = {
  'system-design': '45',
  coding: '45',
  behavioral: '45',
  'ai-coding': '60',
  builder: 'w1',
};

export function presetsForTrack(track: GuideTrack): LengthPreset[] {
  return track === 'builder' ? BUILDER_PRESETS : QUESTION_PRESETS;
}

function storageKey(track: GuideTrack) {
  return `rounds.guide.length.${track}`;
}

function readStored(track: GuideTrack): string | null {
  try {
    return localStorage.getItem(storageKey(track));
  } catch {
    return null;
  }
}

function writeStored(track: GuideTrack, id: string) {
  try {
    localStorage.setItem(storageKey(track), id);
  } catch {
    /* noop */
  }
}

/** Returns the active preset for the given track plus a setter that
 *  persists the choice to localStorage. Re-renders subscribed
 *  components when the value changes (cross-component via a window
 *  event so a picker in the header updates Duration values rendered
 *  elsewhere on the page). */
export function useInterviewLength(track: GuideTrack): [LengthPreset, (id: string) => void] {
  const presets = presetsForTrack(track);
  const resolveById = (id: string | null) =>
    presets.find((p) => p.id === id) ??
    presets.find((p) => p.id === DEFAULT_ID[track]) ??
    presets[0];

  const [preset, setPreset] = useState<LengthPreset>(() =>
    resolveById(readStored(track)),
  );

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<{ track: GuideTrack; id: string }>).detail;
      if (detail?.track === track) {
        setPreset(resolveById(detail.id));
      }
    };
    window.addEventListener('rounds:guide-length', handler);
    return () => window.removeEventListener('rounds:guide-length', handler);
    // resolveById is intentionally omitted; it closes over the stable
    // `track` argument so re-creating it on every render is fine.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [track]);

  const setById = useCallback(
    (id: string) => {
      writeStored(track, id);
      setPreset(resolveById(id));
      window.dispatchEvent(
        new CustomEvent('rounds:guide-length', { detail: { track, id } }),
      );
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [track],
  );

  return [preset, setById];
}

/** Resolve a percentage of the active round to absolute minutes.
 *  Rounds to the nearest minute, with a floor of 1. */
export function minutesForPercent(preset: LengthPreset, percent: number): number {
  return Math.max(1, Math.round((preset.minutes * percent) / 100));
}

/** Render a duration label that scales with the user-selected round
 *  length.
 *
 *  - Pass `percent` to express the duration as a portion of the round
 *    (e.g. 10% of a 45-min round = 5 min; same percent of a 60-min
 *    round = 6 min).
 *  - Pass `minutes` for fixed values that don't scale.
 *
 *  Renders inline text: `"5 min"` (or "5 min · 11%" with `showPercent`).
 *  Wrapped in a subtle pill background so it stands out as actionable
 *  guidance, not just prose. */
export function Duration({
  preset,
  percent,
  minutes,
  showPercent = false,
}: {
  preset: LengthPreset;
  percent?: number;
  minutes?: number;
  showPercent?: boolean;
}) {
  let mins: number;
  let percentLabel: string | null = null;
  if (typeof minutes === 'number') {
    mins = minutes;
    if (showPercent && preset.minutes > 0) {
      const pct = Math.round((mins / preset.minutes) * 100);
      percentLabel = `${pct}%`;
    }
  } else if (typeof percent === 'number') {
    mins = minutesForPercent(preset, percent);
    if (showPercent) percentLabel = `${percent}%`;
  } else {
    mins = 0;
  }

  const text =
    mins >= 60 && mins % 60 === 0
      ? `${mins / 60} hr`
      : mins >= 60
      ? `${Math.floor(mins / 60)} hr ${mins % 60} min`
      : `${mins} min`;

  return (
    <span
      className="mono"
      style={{
        display: 'inline-flex',
        alignItems: 'baseline',
        gap: 4,
        padding: '1px 7px',
        borderRadius: 6,
        background: 'var(--accent-soft)',
        color: 'var(--accent)',
        fontSize: 12,
        fontWeight: 600,
        letterSpacing: '0.01em',
        whiteSpace: 'nowrap',
      }}
    >
      {text}
      {percentLabel && (
        <span style={{ color: 'var(--text-4)', fontWeight: 400, fontSize: 11 }}>
          · {percentLabel}
        </span>
      )}
    </span>
  );
}
