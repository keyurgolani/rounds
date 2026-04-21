import { useEffect, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import PageHeader from '../components/shell/PageHeader';
import BackLink from '../components/shell/BackLink';

type App = { id: number; company: string; role: string; status: string };

const roundTypes = [
  { key: 'phone', label: 'Phone / recruiter screen' },
  { key: 'coding', label: 'Coding' },
  { key: 'system', label: 'System design' },
  { key: 'behavioral', label: 'Behavioral / leadership' },
  { key: 'onsite', label: 'On-site / panel' },
];

export default function ScheduleRound() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselectId = Number(searchParams.get('applicationId')) || 0;
  const [apps, setApps] = useState<App[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    application_id: preselectId,
    round_type: 'coding',
    date: '',
    time: '',
    interviewer: '',
    notes: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<App[]>('/api/applications')
      .then((xs) => {
        setApps(xs);
        if (xs.length > 0) {
          setForm((f) => {
            if (f.application_id && xs.some((a) => a.id === f.application_id)) return f;
            return { ...f, application_id: xs[0].id };
          });
        }
      })
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.application_id) {
      setError('Pick an application first.');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const when = [form.date, form.time].filter(Boolean).join(' ').trim();
      await api.post(`/api/applications/${form.application_id}/rounds`, {
        application_id: form.application_id,
        round_type: roundTypes.find((r) => r.key === form.round_type)?.label ?? form.round_type,
        date: when,
        interviewer: form.interviewer,
        questions_asked: [],
        notes: form.notes,
        result: 'Pending',
      });
      navigate('/interviews');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not save round');
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="px-8 pt-5">
        <BackLink to="/interviews" label="All interviews" />
      </div>
      <PageHeader
        eyebrow="Track · Schedule"
        title="Schedule a round"
        subtitle="Put it on the calendar and Rounds will surface tailored prep on your dashboard — coding warmups for coding rounds, anecdotes for behavioral ones."
      />

      <form
        onSubmit={handleSubmit}
        className="px-8 py-6 grid gap-5"
        style={{ gridTemplateColumns: 'minmax(0, 1fr) 320px' }}
      >
        <div className="card p-6 flex flex-col gap-4">
          <div className="eyebrow">Round details</div>

          <div className="flex flex-col gap-1.5">
            <span className="eyebrow">Application</span>
            {loading ? (
              <div
                style={{ ...inputStyle, color: 'var(--text-4)', paddingTop: 11, paddingBottom: 11 }}
              >
                Loading…
              </div>
            ) : apps.length === 0 ? (
              <div
                className="card p-3.5 flex items-center justify-between"
                style={{ background: 'var(--bg-sunken)', boxShadow: 'none' }}
              >
                <span style={{ fontSize: 12.5, color: 'var(--text-2)' }}>
                  You'll need an application first.
                </span>
                <Link to="/applications/new" style={{ ...secondaryLink, color: 'var(--accent)' }}>
                  + Add a company →
                </Link>
              </div>
            ) : (
              <select
                value={form.application_id}
                onChange={(e) =>
                  setForm({ ...form, application_id: Number(e.target.value) })
                }
                style={inputStyle}
              >
                {apps.map((a) => (
                  <option key={a.id} value={a.id}>
                    {a.company} — {a.role}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <span className="eyebrow">Round type</span>
            <div className="flex flex-wrap gap-2">
              {roundTypes.map((r) => (
                <button
                  key={r.key}
                  type="button"
                  onClick={() => setForm({ ...form, round_type: r.key })}
                  style={{
                    padding: '7px 12px',
                    border: 0,
                    borderRadius: 999,
                    background:
                      form.round_type === r.key ? 'var(--accent)' : 'var(--bg-sunken)',
                    color:
                      form.round_type === r.key ? 'var(--bg-elev)' : 'var(--text-2)',
                    boxShadow:
                      form.round_type === r.key ? 'none' : 'inset 0 0 0 1px var(--border)',
                    fontSize: 12,
                    fontWeight: 500,
                    cursor: 'pointer',
                  }}
                >
                  {r.label}
                </button>
              ))}
            </div>
          </div>

          <div className="grid gap-4" style={{ gridTemplateColumns: '1fr 1fr' }}>
            <Field
              label="Date"
              type="date"
              value={form.date}
              onChange={(v) => setForm({ ...form, date: v })}
            />
            <Field
              label="Time"
              type="time"
              value={form.time}
              onChange={(v) => setForm({ ...form, time: v })}
            />
          </div>

          <Field
            label="Interviewer(s)"
            value={form.interviewer}
            onChange={(v) => setForm({ ...form, interviewer: v })}
            placeholder="Name, role, timezone"
          />

          <label className="flex flex-col gap-1.5">
            <span className="eyebrow">Prep notes</span>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              rows={4}
              placeholder="What you're expecting, topics to review, specific anecdotes you want at the ready."
              style={{ ...inputStyle, resize: 'vertical', minHeight: 100 }}
            />
          </label>

          {error && (
            <div className="mono" style={{ fontSize: 11.5, color: 'var(--plum)' }}>
              {error}
            </div>
          )}

          <div className="flex items-center gap-3 pt-2">
            <button
              type="submit"
              disabled={saving || apps.length === 0}
              style={primaryBtn(saving || apps.length === 0)}
            >
              {saving ? 'Scheduling…' : 'Schedule round'}
            </button>
            <Link to="/interviews" style={secondaryLink}>
              Cancel
            </Link>
          </div>
        </div>

        <aside className="flex flex-col gap-4">
          <div className="card p-5">
            <div className="eyebrow mb-2.5">What we'll surface</div>
            <ul
              className="flex flex-col gap-2"
              style={{ listStyle: 'none', padding: 0, margin: 0, fontSize: 12.5, color: 'var(--text-2)', lineHeight: 1.55 }}
            >
              <li>
                <span style={{ color: 'var(--forest)', marginRight: 6 }}>✓</span>
                Practice questions matching the round type
              </li>
              <li>
                <span style={{ color: 'var(--forest)', marginRight: 6 }}>✓</span>
                Anecdotes linked to the same categories
              </li>
              <li>
                <span style={{ color: 'var(--forest)', marginRight: 6 }}>✓</span>
                Debrief prompt afterward
              </li>
            </ul>
          </div>
          <div className="card p-5">
            <div className="eyebrow mb-2.5">Tip</div>
            <p style={{ margin: 0, fontSize: 13, color: 'var(--text-2)', lineHeight: 1.55 }}>
              Block off 30 minutes of decompression right after the round. You'll write a better
              debrief while the details are still warm.
            </p>
          </div>
        </aside>
      </form>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  type = 'text',
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  placeholder?: string;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="eyebrow">{label}</span>
      <input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
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
    cursor: busy ? 'not-allowed' : 'pointer',
    opacity: busy ? 0.6 : 1,
  };
}
