type CP = { label: string; ai_allowed: boolean };

type Props = {
  checkpoints: CP[];
  currentIndex: number;
  passed: boolean[];
  onSelect: (idx: number) => void;
};

// Free navigation by design — these rounds double as practice and as
// learning material, so candidates can jump to any checkpoint to peek
// at the prompt or revisit a passed one. The done/active/todo coloring
// communicates progress, not gating.
export default function CheckpointStepper({ checkpoints, currentIndex, passed, onSelect }: Props) {
  return (
    <ol className="flex items-center gap-2" style={{ padding: '8px 16px', borderBottom: '1px solid var(--border)' }}>
      {checkpoints.map((cp, i) => {
        const state = passed[i] ? 'done' : i === currentIndex ? 'active' : 'todo';
        return (
          <li key={i}>
            <button
              type="button"
              onClick={() => onSelect(i)}
              aria-current={i === currentIndex ? 'step' : undefined}
              className={`pill ${state}`}
              style={{
                background:
                  state === 'done'
                    ? 'var(--success-soft)'
                    : state === 'active'
                    ? 'var(--accent-soft)'
                    : 'transparent',
                color:
                  state === 'done'
                    ? 'var(--success)'
                    : state === 'active'
                    ? 'var(--accent)'
                    : 'var(--text-3)',
                border: '1px solid var(--border)',
                padding: '4px 10px',
                fontSize: 12,
                cursor: 'pointer',
              }}
            >
              <span style={{ marginRight: 4 }}>{i + 1}.</span>
              <span className={state}>{cp.label}</span>
              {!cp.ai_allowed && <span style={{ marginLeft: 6, fontSize: 10 }}>AI off</span>}
            </button>
          </li>
        );
      })}
    </ol>
  );
}
