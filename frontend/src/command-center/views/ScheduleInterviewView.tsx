import { useEffect, useState } from 'react';
import { createRound, listApplications } from '../../applications/api';
import { useCampaign } from '../../campaign/CampaignContext';
import { INTERVIEW_TYPES } from '../../applications/interviewTypes';
import DatePicker from '../../components/shell/DatePicker';
import Select from '../../components/shell/Select';

type App = { id: string; company: string; role: string; status: string };

const DEFAULT_TYPE = 'coding';
const DEFAULT_DURATION = 60;

export default function ScheduleInterviewView({ onComplete }: { onComplete: () => void }) {
  const { currentId } = useCampaign();
  const [apps, setApps] = useState<App[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    application_id: '',
    round_type: DEFAULT_TYPE,
    date: '',
    time: '',
    interviewer: '',
    duration_minutes: DEFAULT_DURATION,
    loop_label: '',
    notes: '',
  });
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
        // Store the canonical key — InterviewTypePill + the type
        // accent palette key off this. Storing the human label would
        // break color-coding and guide-link resolution on every row.
        round_type: form.round_type,
        date: when,
        interviewer: form.interviewer,
        duration_minutes: form.duration_minutes || 0,
        loop_label: form.loop_label.trim(),
        questions_asked: [],
        notes: form.notes,
        result: 'Pending',
        campaign_id: currentId ?? '',
      });
      window.dispatchEvent(new CustomEvent('rounds:interviews-changed'));
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not add round.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-3">
      <div>
        <div className="eyebrow mb-1">Add round</div>
        <p style={helpText}>Track the round without leaving the keyboard flow.</p>
      </div>
      <label className="grid gap-1.5">
        <span className="eyebrow">Application</span>
        {loading ? (
          <div style={{ ...inputStyle, color: 'var(--text-4)' }}>Loading applications...</div>
        ) : apps.length === 0 ? (
          <div className="card p-3" style={{ background: 'var(--bg-sunken)', color: 'var(--text-3)', fontSize: 12.5 }}>Create an application first, then track its rounds here.</div>
        ) : (
          <Select value={form.application_id} onChange={(application_id) => setForm({ ...form, application_id })} options={apps.map((app) => ({ value: app.id, label: `${app.company} - ${app.role}`, sub: app.status }))} ariaLabel="Application" />
        )}
      </label>
      <label className="grid gap-1.5">
        <span className="eyebrow">Round type</span>
        <Select
          value={form.round_type}
          onChange={(round_type) => setForm({ ...form, round_type })}
          options={INTERVIEW_TYPES.map((t) => ({ value: t.key, label: t.label }))}
          ariaLabel="Round type"
        />
      </label>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1.5">
          <span className="eyebrow">Date</span>
          <DatePicker value={form.date} onChange={(date) => setForm({ ...form, date })} placeholder="Optional" />
        </label>
        <Field label="Time" type="time" value={form.time} onChange={(time) => setForm({ ...form, time })} />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1.5">
          <span className="eyebrow">Duration (min)</span>
          <input
            type="number"
            min={0}
            max={1440}
            step={5}
            value={form.duration_minutes || ''}
            onChange={(e) => setForm({ ...form, duration_minutes: Number(e.target.value) || 0 })}
            placeholder="e.g. 60"
            style={{ ...inputStyle, fontFamily: 'var(--font-mono)' }}
          />
        </label>
        <Field label="Loop label" value={form.loop_label} onChange={(loop_label) => setForm({ ...form, loop_label })} placeholder="Group into a loop (optional)" />
      </div>
      <Field label="Interviewer" value={form.interviewer} onChange={(interviewer) => setForm({ ...form, interviewer })} placeholder="Name, role, timezone" />
      <label className="grid gap-1.5">
        <span className="eyebrow">Prep notes</span>
        <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={3} placeholder="Expected topics, prep reminders, anecdotes to keep ready..." style={{ ...inputStyle, resize: 'vertical' }} />
      </label>
      {error && <div className="mono" style={errorStyle}>{error}</div>}
      <div className="flex items-center gap-3 pt-1">
        <button type="submit" disabled={saving || apps.length === 0} style={primaryButton(saving || apps.length === 0)}>{saving ? 'Adding…' : 'Add round'}</button>
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
