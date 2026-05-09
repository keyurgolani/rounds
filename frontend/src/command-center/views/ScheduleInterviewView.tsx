import { useEffect, useState } from 'react';
import { createRound, listApplications } from '../../applications/api';
import { useCampaign } from '../../campaign/CampaignContext';
import DatePicker from '../../components/shell/DatePicker';
import Select from '../../components/shell/Select';

type App = { id: string; company: string; role: string; status: string };

const roundTypes = [
  { key: 'phone', label: 'Phone / recruiter screen' },
  { key: 'coding', label: 'Coding' },
  { key: 'system', label: 'System design' },
  { key: 'behavioral', label: 'Behavioral / leadership' },
  { key: 'onsite', label: 'On-site / panel' },
];

export default function ScheduleInterviewView({ onComplete }: { onComplete: () => void }) {
  const { currentId } = useCampaign();
  const [apps, setApps] = useState<App[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ application_id: '', round_type: 'coding', date: '', time: '', interviewer: '', notes: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listApplications(currentId ?? undefined)
      .then((list) => {
        setApps(list);
        setForm((current) => ({ ...current, application_id: current.application_id || (list[0]?.id ?? '') }));
      })
      .finally(() => setLoading(false));
  }, [currentId]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const appId = form.application_id;
    if (!appId) {
      setError('Pick an application first.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const when = [form.date, form.time].filter(Boolean).join(' ').trim();
      await createRound(appId, {
        round_type: roundTypes.find((round) => round.key === form.round_type)?.label ?? form.round_type,
        date: when,
        interviewer: form.interviewer,
        questions_asked: [],
        notes: form.notes,
        result: 'Pending',
        campaign_id: currentId ?? '',
      });
      window.dispatchEvent(new CustomEvent('rounds:interviews-changed'));
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not schedule interview.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-3">
      <div>
        <div className="eyebrow mb-1">Schedule interview</div>
        <p style={helpText}>Add the round without leaving the keyboard flow.</p>
      </div>
      <label className="grid gap-1.5">
        <span className="eyebrow">Application</span>
        {loading ? (
          <div style={{ ...inputStyle, color: 'var(--text-4)' }}>Loading applications...</div>
        ) : apps.length === 0 ? (
          <div className="card p-3" style={{ background: 'var(--bg-sunken)', color: 'var(--text-3)', fontSize: 12.5 }}>Create an application first, then schedule its rounds here.</div>
        ) : (
          <Select value={form.application_id} onChange={(application_id) => setForm({ ...form, application_id })} options={apps.map((app) => ({ value: app.id, label: `${app.company} - ${app.role}`, sub: app.status }))} ariaLabel="Application" />
        )}
      </label>
      <label className="grid gap-1.5">
        <span className="eyebrow">Round type</span>
        <Select value={form.round_type} onChange={(round_type) => setForm({ ...form, round_type })} options={roundTypes.map((round) => ({ value: round.key, label: round.label }))} ariaLabel="Round type" />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1.5">
          <span className="eyebrow">Date</span>
          <DatePicker value={form.date} onChange={(date) => setForm({ ...form, date })} placeholder="Optional" />
        </label>
        <Field label="Time" type="time" value={form.time} onChange={(time) => setForm({ ...form, time })} />
      </div>
      <Field label="Interviewer" value={form.interviewer} onChange={(interviewer) => setForm({ ...form, interviewer })} placeholder="Name, role, timezone" />
      <label className="grid gap-1.5">
        <span className="eyebrow">Prep notes</span>
        <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={3} placeholder="Expected topics, prep reminders, anecdotes to keep ready..." style={{ ...inputStyle, resize: 'vertical' }} />
      </label>
      {error && <div className="mono" style={errorStyle}>{error}</div>}
      <div className="flex items-center gap-3 pt-1">
        <button type="submit" disabled={saving || apps.length === 0} style={primaryButton(saving || apps.length === 0)}>{saving ? 'Scheduling...' : 'Schedule interview'}</button>
        <button type="button" onClick={onComplete} style={secondaryButton}>Cancel</button>
      </div>
    </form>
  );
}

function Field({ label, value, onChange, type = 'text', placeholder }: { label: string; value: string; onChange: (value: string) => void; type?: string; placeholder?: string }) {
  return (
    <label className="grid gap-1.5">
      <span className="eyebrow">{label}</span>
      <input type={type} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} style={inputStyle} />
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
