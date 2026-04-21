type Level = 'Easy' | 'Medium' | 'Hard' | string;

const map: Record<string, { bg: string; fg: string }> = {
  Easy: { bg: 'var(--ease-soft)', fg: 'var(--ease)' },
  Medium: { bg: 'var(--med-soft)', fg: 'var(--med)' },
  Hard: { bg: 'var(--hard-soft)', fg: 'var(--hard)' },
};

export default function DifficultyPill({ level }: { level: Level }) {
  const s = map[level] ?? { bg: 'var(--paper-3)', fg: 'var(--text-3)' };
  // `justifySelf` + `alignSelf` pin the pill to its intrinsic size even
  // when it lands directly inside a CSS grid cell (e.g. the coding list
  // table), where grid items default to `stretch` and balloon the pill
  // to fill the whole column.
  return (
    <span
      className="pill"
      style={{
        background: s.bg,
        color: s.fg,
        justifySelf: 'start',
        alignSelf: 'start',
        width: 'fit-content',
      }}
    >
      {String(level).toLowerCase()}
    </span>
  );
}
