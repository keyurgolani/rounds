import { LaneCard } from '../primitives';

export type DecisionEntry = {
  id: string;
  trigger: string;
  move: string;
  watch?: string;
  eyebrow?: string;
};

export default function DecisionDeck({
  entries,
  minCardWidth = 280,
}: {
  entries: DecisionEntry[];
  minCardWidth?: number;
}) {
  return (
    <div
      className="grid"
      style={{
        gap: 'var(--gap-md)',
        gridTemplateColumns: `repeat(auto-fit, minmax(${minCardWidth}px, 1fr))`,
      }}
    >
      {entries.map((entry) => (
        <LaneCard
          key={entry.id}
          eyebrow={entry.eyebrow}
          title={entry.trigger}
          body={entry.move}
          footer={entry.watch ? `Watch for: ${entry.watch}` : undefined}
        />
      ))}
    </div>
  );
}
