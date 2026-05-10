import type { AICodingModel } from '../../pages/ai-coding/aiCodingApi';

export type ModelOverride = { provider_id: string; model: string } | null;

type Props = {
  models: AICodingModel[];
  value: ModelOverride;
  onChange: (next: ModelOverride) => void;
  disabled?: boolean;
};

const SEP = '::';

export default function ModelSwitcher({ models, value, onChange, disabled }: Props) {
  const current = value ? `${value.provider_id}${SEP}${value.model}` : '';
  return (
    <select
      aria-label="AI model"
      value={current}
      disabled={disabled}
      onChange={(e) => {
        const v = e.target.value;
        if (!v) {
          onChange(null);
          return;
        }
        const [provider_id, model] = v.split(SEP);
        onChange({ provider_id, model });
      }}
      style={{ fontSize: 12, padding: '2px 6px', borderRadius: 4 }}
    >
      <option value="">Default model</option>
      {Array.from(new Map(models.map((m) => [`${m.provider_id}${SEP}${m.model}`, m])).values()).map((m) => (
        <option
          key={`${m.provider_id}${SEP}${m.model}`}
          value={`${m.provider_id}${SEP}${m.model}`}
        >
          {m.provider_label} · {m.model}
        </option>
      ))}
    </select>
  );
}
