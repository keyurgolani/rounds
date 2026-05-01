import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import AppHeader from '../components/shell/AppHeader';
import PageShell from '../components/shell/PageShell';
import BackLink from '../components/shell/BackLink';
import DatePicker from '../components/shell/DatePicker';
import Select from '../components/shell/Select';
import { useCampaign } from '../campaign/CampaignContext';

const statuses = ['Wishlist', 'Applied', 'Interviewing', 'Offer', 'Rejected'];

type Form = {
  company: string;
  role: string;
  status: string;
  applied_date: string;
  url: string;
  resume_variant: string;
  notes: string;
  job_description: string;
};

const blank: Form = {
  company: '',
  role: '',
  status: 'Applied',
  applied_date: '',
  url: '',
  resume_variant: '',
  notes: '',
  job_description: '',
};

export default function NewApplication() {
  const navigate = useNavigate();
  const { campaigns, currentId, currentCampaign } = useCampaign();
  const defaultCampaignId =
    currentId ?? campaigns.find((c) => c.is_default)?.id ?? campaigns[0]?.id ?? '';
  const [form, setForm] = useState<Form>(blank);
  const [campaignId, setCampaignId] = useState<string>(defaultCampaignId);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.company.trim() || !form.role.trim()) {
      setError('Company and role are required.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await api.post('/api/applications', { ...form, campaign_id: campaignId });
      navigate('/applications');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save');
    } finally {
      setSaving(false);
    }
  }

  return (
    <PageShell
      header={
        <>
          <div className="px-8 pt-5">
            <BackLink to="/applications" label="All applications" />
          </div>
          <AppHeader
            eyebrow="Track · New company"
            title="Add an application"
            description="Start with the basics — company and role. You can always come back and fill in resume variants, notes, and status as things progress."
          />
        </>
      }
    >
      <form
        onSubmit={handleSubmit}
        className="px-5 sm:px-8 py-6 grid gap-5 grid-cols-1 lg:[grid-template-columns:minmax(0,1fr)_320px]"
      >
        <div className="card p-6 flex flex-col gap-4">
          <div className="eyebrow">The essentials</div>

          <div className="grid gap-4 grid-cols-1 sm:[grid-template-columns:1.3fr_1fr]">
            <Field
              label="Company"
              value={form.company}
              onChange={(v) => setForm({ ...form, company: v })}
              placeholder="Stripe"
              required
            />
            <Field
              label="Role / title"
              value={form.role}
              onChange={(v) => setForm({ ...form, role: v })}
              placeholder="Staff Engineer, Backend"
              required
            />
          </div>

          <div className="grid gap-4 grid-cols-1 sm:grid-cols-2">
            <div className="flex flex-col gap-1.5">
              <span className="eyebrow">Status</span>
              <Select
                value={form.status}
                onChange={(v) => setForm({ ...form, status: v })}
                options={statuses.map((s) => ({ value: s, label: s }))}
                ariaLabel="Status"
              />
            </div>
            <Field
              label="Applied date"
              type="date"
              value={form.applied_date}
              onChange={(v) => setForm({ ...form, applied_date: v })}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <span className="eyebrow">Campaign</span>
            <Select
              value={campaignId}
              onChange={setCampaignId}
              options={campaigns.map((c) => ({
                value: c.id,
                label: c.name,
                sub: c.id === (currentCampaign?.id ?? '') ? 'current workspace' : c.target_role_level || undefined,
              }))}
              ariaLabel="Campaign"
            />
          </div>

          <Field
            label="Posting URL"
            value={form.url}
            onChange={(v) => setForm({ ...form, url: v })}
            placeholder="https://…"
          />

          <Field
            label="Resume variant"
            value={form.resume_variant}
            onChange={(v) => setForm({ ...form, resume_variant: v })}
            placeholder="e.g. resume-platform-backend.pdf"
          />

          <label className="flex flex-col gap-1.5">
            <span className="eyebrow">Job description</span>
            <textarea
              value={form.job_description}
              onChange={(e) => setForm({ ...form, job_description: e.target.value })}
              rows={6}
              placeholder="Paste the role description — requirements, scope, team context. Markdown-lite supported: `inline code`, **bold**, *italic*."
              style={{ ...inputStyle, resize: 'vertical', minHeight: 140, fontFamily: 'var(--font-sans)' }}
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="eyebrow">Notes</span>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={4}
              placeholder="Why this role, the contact who referred you, the thing that actually excites you about it."
              style={{ ...inputStyle, resize: 'vertical', minHeight: 100 }}
            />
          </label>

          {error && (
            <div className="mono" style={{ fontSize: 11.5, color: 'var(--plum)' }}>
              {error}
            </div>
          )}

          <div className="flex items-center gap-3 pt-2">
            <button type="submit" disabled={saving} style={primaryBtn(saving)}>
              {saving ? 'Saving…' : 'Save application'}
            </button>
            <Link to="/applications" style={secondaryLink}>
              Cancel
            </Link>
          </div>
        </div>

        <aside className="flex flex-col gap-4">
          <div className="card p-5">
            <div className="eyebrow mb-2.5">Tip</div>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-2)', lineHeight: 1.55 }}>
              Add a company even before you've applied. Wishlist entries surface on your dashboard
              and tie your practice sessions to real targets.
            </p>
          </div>
          <div className="card p-5">
            <div className="eyebrow mb-2.5">Status flow</div>
            <ul className="flex flex-col gap-1.5" style={{ listStyle: 'none', padding: 0, margin: 0 }}>
              {statuses.map((s, i) => (
                <li
                  key={s}
                  style={{
                    fontSize: 12.5,
                    color: form.status === s ? 'var(--text)' : 'var(--text-3)',
                    fontWeight: form.status === s ? 500 : 400,
                  }}
                >
                  <span
                    className="mono"
                    style={{ color: 'var(--text-4)', marginRight: 8, fontSize: 10.5 }}
                  >
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  {s}
                </li>
              ))}
            </ul>
          </div>
        </aside>
      </form>
    </PageShell>
  );
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
  required,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
  required?: boolean;
}) {
  if (type === 'date') {
    return (
      <label className="flex flex-col gap-1.5">
        <span className="eyebrow">{label}</span>
        <DatePicker
          value={value}
          onChange={onChange}
          placeholder={placeholder ?? 'Pick a date'}
          ariaLabel={label}
        />
      </label>
    );
  }
  return (
    <label className="flex flex-col gap-1.5">
      <span className="eyebrow">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        style={inputStyle}
      />
    </label>
  );
}

const inputStyle: React.CSSProperties = {
  padding: '10px 12px',
  background: 'var(--bg)',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
  borderRadius: 'var(--radius)',
  border: 0,
  fontSize: 13.5,
  color: 'var(--text)',
  outline: 'none',
  fontFamily: 'inherit',
};

const secondaryLink: React.CSSProperties = {
  fontSize: 12.5,
  color: 'var(--text-3)',
  textDecoration: 'none',
};

function primaryBtn(busy: boolean): React.CSSProperties {
  return {
    padding: '9px 16px',
    borderRadius: 'var(--radius)',
    border: 0,
    background: 'var(--accent)',
    color: 'var(--bg-elev)',
    fontSize: 13,
    fontWeight: 500,
    cursor: busy ? 'wait' : 'pointer',
    opacity: busy ? 0.7 : 1,
  };
}
