import { useState } from 'react';
import { useCampaign } from '../../campaign/CampaignContext';
import DatePicker from '../../components/shell/DatePicker';
import Select from '../../components/shell/Select';

export default function CampaignView({ onComplete }: { onComplete: () => void }) {
  const { campaigns, currentId, setCurrent, createCampaign } = useCampaign();
  const [name, setName] = useState('');
  const [targetRoleLevel, setTargetRoleLevel] = useState('');
  const [description, setDescription] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function switchCampaign(id: string) {
    setCurrent(id === 'all' ? null : id);
    window.dispatchEvent(new CustomEvent('rounds:campaigns-changed'));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError('Name is required.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await createCampaign({ name: name.trim(), target_role_level: targetRoleLevel.trim(), description: description.trim(), start_date: startDate, end_date: endDate, status: 'active' });
      window.dispatchEvent(new CustomEvent('rounds:campaigns-changed'));
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create campaign.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="grid gap-4">
      <section className="grid gap-2">
        <div>
          <div className="eyebrow mb-1">Switch campaign</div>
          <p style={helpText}>Change the active workspace without leaving the command flow.</p>
        </div>
        <Select
          value={currentId ?? 'all'}
          onChange={switchCampaign}
          options={[{ value: 'all', label: 'All active campaigns', sub: 'rollup view' }, ...campaigns.map((c) => ({ value: c.id, label: c.name, sub: c.target_role_level || c.status }))]}
          ariaLabel="Campaign"
        />
      </section>

      <form onSubmit={submit} className="grid gap-3" style={{ paddingTop: 14, borderTop: '1px solid var(--border)' }}>
        <div>
          <div className="eyebrow mb-1">New campaign</div>
          <p style={helpText}>Create a separate workspace for a new hunt or role target.</p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="Name" value={name} onChange={setName} placeholder="SWE Summer 2026" />
          <Field label="Target" value={targetRoleLevel} onChange={setTargetRoleLevel} placeholder="Staff backend" />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="grid gap-1.5">
            <span className="eyebrow">Start</span>
            <DatePicker value={startDate} onChange={setStartDate} placeholder="Optional" />
          </label>
          <label className="grid gap-1.5">
            <span className="eyebrow">End</span>
            <DatePicker value={endDate} onChange={setEndDate} placeholder="Optional" />
          </label>
        </div>
        <label className="grid gap-1.5">
          <span className="eyebrow">Goal</span>
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} placeholder="What this hunt is about." style={{ ...inputStyle, resize: 'vertical' }} />
        </label>
        {error && <div className="mono" style={errorStyle}>{error}</div>}
        <div className="flex items-center gap-3 pt-1">
          <button type="submit" disabled={saving} style={primaryButton(saving)}>{saving ? 'Creating...' : 'Create campaign'}</button>
          <button type="button" onClick={onComplete} style={secondaryButton}>Cancel</button>
        </div>
      </form>
    </div>
  );
}

function Field({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return (
    <label className="grid gap-1.5">
      <span className="eyebrow">{label}</span>
      <input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} style={inputStyle} />
    </label>
  );
}

const helpText: React.CSSProperties = { margin: 0, color: 'var(--text-3)', fontSize: 12.5, lineHeight: 1.5 };
const inputStyle: React.CSSProperties = { width: '100%', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '8px 10px', background: 'var(--bg-elev)', color: 'var(--text)', fontSize: 13, outline: 'none', fontFamily: 'inherit' };
const errorStyle: React.CSSProperties = { fontSize: 11.5, color: 'var(--plum)' };
const secondaryButton: React.CSSProperties = { border: 0, background: 'transparent', color: 'var(--text-3)', fontSize: 12.5, cursor: 'pointer' };
function primaryButton(disabled: boolean): React.CSSProperties {
  return { border: 0, borderRadius: 'var(--radius)', background: disabled ? 'var(--paper-3)' : 'var(--accent)', color: disabled ? 'var(--text-4)' : 'var(--bg-elev)', padding: '8px 13px', fontSize: 12.5, fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer' };
}
