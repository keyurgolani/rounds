type Tab = { key: string; label: string };

type Props = {
  tabs: Tab[];
  active: string;
  onChange: (key: string) => void;
};

export default function Tabs({ tabs, active, onChange }: Props) {
  return (
    <div
      className="flex gap-1 overflow-x-auto no-scrollbar px-8"
      style={{ borderBottom: '1px solid var(--border)' }}
    >
      {tabs.map((t) => {
        const on = active === t.key;
        return (
          <button
            key={t.key}
            type="button"
            onClick={() => onChange(t.key)}
            className="relative whitespace-nowrap"
            style={{
              padding: '12px 14px',
              border: 0,
              background: 'transparent',
              color: on ? 'var(--text)' : 'var(--text-3)',
              fontSize: 13,
              fontWeight: on ? 500 : 400,
            }}
          >
            {t.label}
            {on && (
              <span
                style={{
                  position: 'absolute',
                  left: 14,
                  right: 14,
                  bottom: -1,
                  height: 2,
                  background: 'var(--accent)',
                  borderRadius: 1,
                }}
              />
            )}
          </button>
        );
      })}
    </div>
  );
}
