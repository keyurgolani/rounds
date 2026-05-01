import { useMemo, useState } from 'react';
import { api } from '../../api/client';
import { useCampaign } from '../../campaign/CampaignContext';
import DatePicker from '../../components/shell/DatePicker';
import Select from '../../components/shell/Select';

const statuses = ['Wishlist', 'Applied', 'Interviewing', 'Offer', 'Rejected'];

type Form = {
  company: string;
  role: string;
  status: string;
  applied_date: string;
  url: string;
  notes: string;
};

const blank: Form = {
  company: '',
  role: '',
  status: 'Applied',
  applied_date: '',
  url: '',
  notes: '',
};

export default function AddApplicationView({ onComplete }: { onComplete: () => void }) {
  const { campaigns, currentId, currentCampaign } = useCampaign();
  const fallbackCampaignId = currentId ?? campaigns.find((c) => c.status === 'active')?.id ?? campaigns[0]?.id ?? '';
  const [form, setForm] = useState<Form>(blank);
  const [campaignId, setCampaignId] = useState(fallbackCampaignId);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const campaignOptions = useMemo(
    () => campaigns.map((c) => ({ value: c.id, label: c.name, sub: c.id === currentCampaign?.id ? 'current workspace' : c.target_role_level || undefined })),
    [campaigns, currentCampaign?.id],
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.company.trim() || !form.role.trim()) {
      setError('Company and role are required.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.post('/api/applications', { ...form, campaign_id: campaignId });
      window.dispatchEvent(new CustomEvent('rounds:applications-changed'));
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save application.');
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={submit} className="grid gap-3">
      <div>
        <div className="eyebrow mb-1">Quick application</div>
        <p style={helpText}>Capture the company now. You can enrich the full application later.</p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <Field label="Company" value={form.company} onChange={(company) => setForm({ ...form, company })} placeholder="Stripe" autoFocus />
        <Field label="Role" value={form.role} onChange={(role) => setForm({ ...form, role })} placeholder="Staff Backend Engineer" />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="grid gap-1.5">
          <span className="eyebrow">Status</span>
          <Select value={form.status} onChange={(status) => setForm({ ...form, status })} options={statuses.map((status) => ({ value: status, label: status }))} ariaLabel="Status" />
        </label>
        <label className="grid gap-1.5">
          <span className="eyebrow">Applied date</span>
          <DatePicker value={form.applied_date} onChange={(applied_date) => setForm({ ...form, applied_date })} placeholder="Optional" />
        </label>
      </div>
      {campaignOptions.length > 0 && (
        <label className="grid gap-1.5">
          <span className="eyebrow">Campaign</span>
          <Select value={campaignId} onChange={setCampaignId} options={campaignOptions} ariaLabel="Campaign" />
        </label>
      )}
      <Field label="Posting URL" value={form.url} onChange={(url) => setForm({ ...form, url })} placeholder="https://..." />
      <label className="grid gap-1.5">
        <span className="eyebrow">Notes</span>
        <textarea value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} rows={3} placeholder="Why this role matters, referral, recruiter context..." style={{ ...inputStyle, resize: 'vertical' }} />
      </label>
      {error && <div className="mono" style={errorStyle}>{error}</div>}
      <div className="flex items-center gap-3 pt-1">
        <button type="submit" disabled={saving} style={primaryButton(saving)}>{saving ? 'Saving...' : 'Create application'}</button>
        <button type="button" onClick={onComplete} style={secondaryButton}>Cancel</button>
      </div>
    </form>
  );
}

function Field({ label, value, onChange, placeholder, autoFocus }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string; autoFocus?: boolean }) {
  return (
    <label className="grid gap-1.5">
      <span className="eyebrow">{label}</span>
      <input autoFocus={autoFocus} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} style={inputStyle} />
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
