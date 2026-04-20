type Level = 'Easy' | 'Medium' | 'Hard' | string;

const map: Record<string, { bg: string; fg: string }> = {
  Easy: { bg: 'var(--ease-soft)', fg: 'var(--ease)' },
  Medium: { bg: 'var(--med-soft)', fg: 'var(--med)' },
  Hard: { bg: 'var(--hard-soft)', fg: 'var(--hard)' },
};

export default function DifficultyPill({ level }: { level: Level }) {
  const s = map[level] ?? { bg: 'var(--paper-3)', fg: 'var(--text-3)' };
  return (
    <span className="pill" style={{ background: s.bg, color: s.fg }}>
      {String(level).toLowerCase()}
    </span>
  );
}
