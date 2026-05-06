type GlyphProps = { size?: number };

export function CampaignGlyph({ size = 18 }: GlyphProps) {
  return (
    <svg viewBox="0 0 18 18" fill="none" width={size} height={size} aria-hidden="true">
      <circle cx="9" cy="9" r="6.5" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="9" cy="9" r="2.5" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="9" cy="9" r="0.8" fill="currentColor" />
    </svg>
  );
}

export function TodoGlyph({ size = 18 }: GlyphProps) {
  return (
    <svg viewBox="0 0 18 18" fill="none" width={size} height={size} aria-hidden="true">
      <rect x="2.5" y="3" width="13" height="12" rx="2" stroke="currentColor" strokeWidth="1.4" />
      <path d="M5.5 7 L7.3 8.8 L10.5 5.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M5.5 11.5 L12 11.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

export function DashGlyph({ size = 18 }: GlyphProps) {
  return (
    <svg viewBox="0 0 18 18" fill="none" width={size} height={size} aria-hidden="true">
      <circle cx="9" cy="9" r="7" stroke="currentColor" strokeWidth="1.6" />
      <path d="M9 9 L9 3.5" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
      <path d="M9 9 L13 11" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}

export function SystemGlyph({ size = 18 }: GlyphProps) {
  return (
    <svg viewBox="0 0 18 18" fill="none" width={size} height={size} aria-hidden="true">
      <rect x="2" y="3" width="5" height="4" rx="1" stroke="currentColor" strokeWidth="1.4" />
      <rect x="11" y="3" width="5" height="4" rx="1" stroke="currentColor" strokeWidth="1.4" />
      <rect x="6.5" y="11" width="5" height="4" rx="1" stroke="currentColor" strokeWidth="1.4" />
      <path
        d="M4.5 7 L4.5 9 L9 9 L9 11"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <path d="M13.5 7 L13.5 9 L9 9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  );
}

export function CodeGlyph({ size = 18 }: GlyphProps) {
  return (
    <svg viewBox="0 0 18 18" fill="none" width={size} height={size} aria-hidden="true">
      <path
        d="M6.5 5 L3 9 L6.5 13"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M11.5 5 L15 9 L11.5 13"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function BehaviorGlyph({ size = 18 }: GlyphProps) {
  return (
    <svg viewBox="0 0 18 18" fill="none" width={size} height={size} aria-hidden="true">
      <path
        d="M4 6C4 4.3 5.3 3 7 3H11C12.7 3 14 4.3 14 6V10C14 11.7 12.7 13 11 13H8L5 15.5V13H7C5.3 13 4 11.7 4 10V6Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function AppsGlyph({ size = 18 }: GlyphProps) {
  return (
    <svg viewBox="0 0 18 18" fill="none" width={size} height={size} aria-hidden="true">
      <path
        d="M4 5C4 4.45 4.45 4 5 4H13C13.55 4 14 4.45 14 5V14C14 14.55 13.55 15 13 15H5C4.45 15 4 14.55 4 14V5Z"
        stroke="currentColor"
        strokeWidth="1.4"
      />
      <path d="M7 3V5M11 3V5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <path
        d="M6.5 8.5H11.5M6.5 11H10"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
    </svg>
  );
}

export function AIGlyph({ size = 18 }: GlyphProps) {
  return (
    <svg viewBox="0 0 18 18" fill="none" width={size} height={size} aria-hidden="true">
      <path
        d="M9 2.5 L10.1 6.2 L13.8 7.3 L10.1 8.4 L9 12 L7.9 8.4 L4.2 7.3 L7.9 6.2 Z"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinejoin="round"
      />
      <path
        d="M13.5 11.5 L14 13 L15.5 13.5 L14 14 L13.5 15.5 L13 14 L11.5 13.5 L13 13 Z"
        stroke="currentColor"
        strokeWidth="1.1"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function CalendarGlyph({ size = 18 }: GlyphProps) {
  return (
    <svg viewBox="0 0 18 18" fill="none" width={size} height={size} aria-hidden="true">
      <rect x="3" y="4.5" width="12" height="10" rx="1.2" stroke="currentColor" strokeWidth="1.4" />
      <path
        d="M6 3V6M12 3V6M3 8H15"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
      />
      <circle cx="9" cy="11.5" r="1.2" fill="currentColor" />
    </svg>
  );
}

export function ResumeGlyph({ size = 18 }: GlyphProps) {
  return (
    <svg viewBox="0 0 18 18" fill="none" width={size} height={size} aria-hidden="true">
      <path
        d="M4.5 2.5H11L13.5 5V15C13.5 15.55 13.05 16 12.5 16H4.5C3.95 16 3.5 15.55 3.5 15V3.5C3.5 2.95 3.95 2.5 4.5 2.5Z"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path d="M11 2.5V5H13.5" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      <circle cx="6.5" cy="8" r="1.2" stroke="currentColor" strokeWidth="1.3" />
      <path
        d="M9 7.5H11.5M5.5 11H11.5M5.5 13H10"
        stroke="currentColor"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
    </svg>
  );
}
