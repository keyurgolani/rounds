/**
 * Shared interview-type vocabulary used by ScheduleRound, RoundDetail,
 * Interviews aggregate, and ApplicationDetail.
 *
 * `round_type` on interview_rounds is a freeform text field — we
 * deliberately don't enum-lock it at the schema layer so legacy data
 * (and future types) flow through without migration. This vocabulary
 * is the suggested set the UI presents in pickers + filter chips.
 *
 * The list covers:
 *   - Legacy short codes (phone / coding / system / behavioral /
 *     onsite) so existing rows render with a known label.
 *   - The full question-type vocabulary used elsewhere in the app
 *     (System Design, Coding, AI-Assisted Coding, Behavioral,
 *     Real-World).
 *   - The two new AI-Native types from item 26 (AI-Native
 *     Behavioral, AI-Native SWE System Design).
 */

export type InterviewTypeEntry = {
  /** Canonical key stored in interview_rounds.round_type. */
  key: string;
  /** Human label shown in pickers, filter chips, and row pills. */
  label: string;
  /** Short label for compact contexts (filter chip, row pill on
   *  narrow screens). Defaults to `label`. */
  shortLabel?: string;
  /** When set, the round detail surface shows an "Open guide" button
   *  that deep-links to the matching question-type guide page. */
  guidePath?: string;
};

/** The canonical vocabulary in display order. */
export const INTERVIEW_TYPES: InterviewTypeEntry[] = [
  // Renamed from "phone" — "Introduction" matches how candidates
  // actually describe a recruiter / HM intro call.
  { key: 'intro', label: 'Introduction', shortLabel: 'Intro' },
  {
    key: 'coding',
    label: 'Coding',
    shortLabel: 'Coding',
    guidePath: '/coding/guide',
  },
  {
    key: 'ai-assisted-coding',
    label: 'AI-Assisted Coding',
    shortLabel: 'AI Code',
    guidePath: '/ai-coding/guide',
  },
  {
    key: 'system',
    label: 'System Design',
    shortLabel: 'System',
    guidePath: '/system-design/guide',
  },
  {
    key: 'ai-native-system',
    label: 'AI-Native SWE System Design',
    shortLabel: 'AI System',
    guidePath: '/system-design/guide',
  },
  {
    key: 'behavioral',
    label: 'Behavioral',
    shortLabel: 'Behavioral',
    guidePath: '/behavioral/guide',
  },
  {
    key: 'ai-native-behavioral',
    label: 'AI-Native Behavioral',
    shortLabel: 'AI Behav',
    guidePath: '/behavioral/guide',
  },
  {
    key: 'real-world',
    label: 'Real-World Problem',
    shortLabel: 'Real-World',
    guidePath: '/builder/guide',
  },
  {
    key: 'take-home',
    label: 'Take-Home',
    shortLabel: 'Take-Home',
    guidePath: '/take-home/guide',
  },
  { key: 'onsite', label: 'On-site / panel', shortLabel: 'Onsite' },
  // Legacy "phone" key kept as an alias-only entry (hidden from the
  // canonical list above so it doesn't show up in pickers, but
  // interviewTypeLabel() still resolves old rows to "Introduction").
];

/** Aliases — old keys that should resolve to a canonical entry but
 *  shouldn't surface in pickers. The label lookup walks aliases so
 *  legacy "phone" rows render as "Introduction" without a migration. */
const INTERVIEW_TYPE_ALIASES: Record<string, string> = {
  phone: 'intro',
};

const _ENTRY_BY_KEY = new Map(INTERVIEW_TYPES.map((t) => [t.key, t]));

/** Resolve a key (or alias) to its canonical entry. */
export function resolveInterviewType(rt: string): InterviewTypeEntry | undefined {
  if (!rt) return undefined;
  const canonical = INTERVIEW_TYPE_ALIASES[rt] ?? rt;
  return _ENTRY_BY_KEY.get(canonical);
}

/** Resolve a `round_type` value to its display label. Unknown values
 *  fall through verbatim so legacy / custom types still render. */
export function interviewTypeLabel(rt: string): string {
  if (!rt) return 'Untagged';
  return resolveInterviewType(rt)?.label ?? rt;
}

/** Resolve to the short label (for tight UI). Falls back to label,
 *  then to the verbatim value. */
export function interviewTypeShort(rt: string): string {
  if (!rt) return 'Untagged';
  const entry = resolveInterviewType(rt);
  return entry?.shortLabel ?? entry?.label ?? rt;
}

/** Resolve a key (or alias) to its guide path (or undefined). */
export function interviewTypeGuidePath(rt: string): string | undefined {
  return resolveInterviewType(rt)?.guidePath;
}

/** Stable accent color per type — used by the TypePill so a glance
 *  at a calendar of rounds shows the mix of types. Values are CSS
 *  custom-property fallbacks so they integrate with the design
 *  tokens. */
export function interviewTypeAccent(rt: string): {
  bg: string;
  fg: string;
  border: string;
} {
  // Walk legacy aliases so old "phone" rows pick up the intro accent.
  const key = INTERVIEW_TYPE_ALIASES[rt] ?? rt;
  switch (key) {
    case 'intro':
      return {
        bg: 'color-mix(in oklab, var(--text-3) 12%, transparent)',
        fg: 'var(--text-2)',
        border: 'var(--border)',
      };
    case 'coding':
      return {
        bg: 'color-mix(in oklab, var(--accent) 14%, transparent)',
        fg: 'var(--accent)',
        border: 'color-mix(in oklab, var(--accent) 40%, transparent)',
      };
    case 'ai-assisted-coding':
    case 'ai-native-behavioral':
    case 'ai-native-system':
      return {
        // The three AI-flavored types share a single indigo accent so
        // they're visually grouped at a glance.
        bg: 'color-mix(in oklab, #6366f1 16%, transparent)',
        fg: '#6366f1',
        border: 'color-mix(in oklab, #6366f1 40%, transparent)',
      };
    case 'system':
      return {
        bg: 'color-mix(in oklab, #db2777 12%, transparent)',
        fg: '#db2777',
        border: 'color-mix(in oklab, #db2777 40%, transparent)',
      };
    case 'behavioral':
      return {
        bg: 'color-mix(in oklab, #d97706 14%, transparent)',
        fg: '#d97706',
        border: 'color-mix(in oklab, #d97706 40%, transparent)',
      };
    case 'real-world':
    case 'take-home':
      return {
        bg: 'color-mix(in oklab, #16a34a 14%, transparent)',
        fg: '#16a34a',
        border: 'color-mix(in oklab, #16a34a 40%, transparent)',
      };
    case 'onsite':
      return {
        bg: 'color-mix(in oklab, var(--text-2) 14%, transparent)',
        fg: 'var(--text-2)',
        border: 'var(--border-strong)',
      };
    default:
      return {
        bg: 'var(--bg-sunken)',
        fg: 'var(--text-3)',
        border: 'var(--border)',
      };
  }
}
