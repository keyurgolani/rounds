export type PracticeStatus = 'todo' | 'in-progress' | 'mastered';

const map: Record<PracticeStatus, { label: string; color: string; fill: string }> = {
  todo: { label: 'todo', color: 'var(--text-4)', fill: 'transparent' },
  'in-progress': { label: 'practicing', color: 'var(--ochre)', fill: 'var(--ochre)' },
  mastered: { label: 'mastered', color: 'var(--forest)', fill: 'var(--forest)' },
};

export default function StatusDot({ status }: { status: PracticeStatus }) {
  const s = map[status] ?? map.todo;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: 999,
          background: s.fill,
          boxShadow: status === 'todo' ? 'inset 0 0 0 1px var(--text-4)' : 'none',
        }}
      />
      <span
        className="mono uppercase"
        style={{ fontSize: 10.5, color: s.color, letterSpacing: '0.12em' }}
      >
        {s.label}
      </span>
    </span>
  );
}
