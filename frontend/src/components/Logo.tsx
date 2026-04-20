type MarkProps = {
  size?: number;
  color?: string;
  accent?: string;
  className?: string;
};

export function RoundsMark({
  size = 32,
  color = 'currentColor',
  accent = 'var(--accent)',
  className,
}: MarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      className={className}
      style={{ display: 'block' }}
      aria-hidden="true"
    >
      <path
        d="M11 6.5C7 9.5 7 22.5 11 25.5"
        stroke={color}
        strokeWidth="2.3"
        strokeLinecap="round"
      />
      <path
        d="M21 6.5C25 9.5 25 22.5 21 25.5"
        stroke={accent}
        strokeWidth="2.3"
        strokeLinecap="round"
      />
      <circle cx="16" cy="16" r="1.6" fill={color} />
    </svg>
  );
}

type WordmarkProps = {
  size?: number;
  color?: string;
  accent?: string;
};

export function RoundsWordmark({
  size = 22,
  color = 'var(--text)',
  accent = 'var(--accent)',
}: WordmarkProps) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'baseline',
        fontFamily: 'var(--font-display)',
        fontStyle: 'italic',
        fontWeight: 400,
        fontSize: size,
        color,
        letterSpacing: '-0.02em',
        lineHeight: 1,
      }}
    >
      Rounds
      <span style={{ color: accent, marginLeft: 1, fontStyle: 'italic' }}>.</span>
    </span>
  );
}

type LockupProps = {
  markSize?: number;
  textSize?: number;
};

export function RoundsLockup({ markSize = 22, textSize = 22 }: LockupProps) {
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10 }}>
      <RoundsMark size={markSize} />
      <RoundsWordmark size={textSize} />
    </div>
  );
}
