import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { CircleDot, Plus, Target } from 'lucide-react';
import { useCampaign } from '../campaign/CampaignContext';
import AppHeader from '../components/shell/AppHeader';
import DatePicker from '../components/shell/DatePicker';
import type { Campaign } from '../campaign/types';

const STATUS_COLORS: Record<string, { bg: string; fg: string }> = {
  planning: { bg: 'var(--paper-3)', fg: 'var(--text-3)' },
  active: { bg: 'var(--accent-soft)', fg: 'var(--accent)' },
  wrapped: { bg: 'var(--forest-soft)', fg: 'var(--forest)' },
};

export default function Campaigns() {
  const navigate = useNavigate();
  const { campaigns, createCampaign, ready } = useCampaign();
  const [params, setParams] = useSearchParams();
  const [creating, setCreating] = useState(() => params.get('new') === '1');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (params.get('new') === '1') {
      setCreating(true);
      const next = new URLSearchParams(params);
      next.delete('new');
      setParams(next, { replace: true });
    }
  }, [params, setParams]);

  const active = useMemo(
    () => campaigns.filter((c) => c.status === 'active'),
    [campaigns],
  );
  const wrapped = useMemo(
    () => campaigns.filter((c) => c.status === 'wrapped'),
    [campaigns],
  );

  return (
    <div className="h-full flex flex-col">
      <AppHeader
        title="Campaigns"
        description="One workspace per job hunt."
        chromeActions={
          <button
            type="button"
            onClick={() => setCreating(true)}
            className="inline-flex items-center gap-1.5"
            style={primaryBtn}
          >
            <Plus size={13} strokeWidth={1.8} />
            New campaign
          </button>
        }
      />
      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="flex flex-col gap-6 px-5 sm:px-8 py-6">
          <p
            style={{
              margin: 0,
              color: 'var(--text-3)',
              fontSize: 13,
              lineHeight: 1.55,
              maxWidth: 560,
            }}
          >
            Every job hunt is its own workspace — different timelines, different targets,
            different prep. Switch between them without losing context.
          </p>

          {creating && (
            <NewCampaignForm
              onCancel={() => setCreating(false)}
              onError={setError}
              onCreate={async (payload) => {
                setError(null);
                try {
                  const c = await createCampaign(payload);
                  setCreating(false);
                  navigate(`/campaigns/${c.slug}`);
                } catch (e) {
                  setError(e instanceof Error ? e.message : 'Could not create campaign.');
                }
              }}
            />
          )}
          {error && (
            <div className="card p-3" style={{ color: 'var(--plum)', fontSize: 13 }}>
              {error}
            </div>
          )}

          {ready && campaigns.length === 0 && !creating && (
            <div
              className="card p-8 text-center"
              style={{ color: 'var(--text-3)', fontSize: 13 }}
            >
              No campaigns yet. Use "New campaign" above to start one.
            </div>
          )}

          <CampaignGrid title="Active" campaigns={active} linkBase="/campaigns" />
          {wrapped.length > 0 && (
            <CampaignGrid title="Wrapped" campaigns={wrapped} linkBase="/campaigns" />
          )}
        </div>
      </div>
    </div>
  );
}

function CampaignGrid({
  title,
  campaigns,
  linkBase,
}: {
  title: string;
  campaigns: Campaign[];
  linkBase: string;
}) {
  if (campaigns.length === 0) return null;
  return (
    <section>
      <div className="eyebrow mb-3">{title}</div>
      <div
        className="grid gap-4"
        style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))' }}
      >
        {campaigns.map((c) => (
          <Link
            key={c.id}
            to={`${linkBase}/${c.slug}`}
            className="card card-hover"
            style={{ textDecoration: 'none', color: 'inherit', padding: '18px 20px' }}
          >
            <div className="flex items-center justify-between gap-2">
              <span
                className="flex items-center gap-2"
                style={{ fontSize: 15, fontWeight: 500 }}
              >
                <CircleDot size={12} strokeWidth={1.9} style={{ color: 'var(--accent)' }} />
                {c.name}
              </span>
              <StatusPill status={c.status} />
            </div>
            {c.target_role_level && (
              <div
                className="flex items-center gap-1.5 mt-2"
                style={{ fontSize: 12, color: 'var(--text-3)' }}
              >
                <Target size={11} strokeWidth={1.7} />
                {c.target_role_level}
              </div>
            )}
            {c.description && (
              <p
                className="mt-2"
                style={{
                  fontSize: 12.5,
                  color: 'var(--text-2)',
                  lineHeight: 1.55,
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                }}
              >
                {c.description}
              </p>
            )}
            <div
              className="mono mt-3 flex items-center gap-3"
              style={{ fontSize: 10.5, color: 'var(--text-4)' }}
            >
              {c.start_date && <span>{c.start_date}</span>}
              {c.start_date && c.end_date && <span>→</span>}
              {c.end_date && <span>{c.end_date}</span>}
            </div>
          </Link>
        ))}
      </div>
    </section>
  );
}

function NewCampaignForm({
  onCancel,
  onCreate,
  onError,
}: {
  onCancel: () => void;
  onCreate: (payload: Partial<Campaign>) => Promise<void>;
  onError: (msg: string) => void;
}) {
  const [name, setName] = useState('');
  const [targetRoleLevel, setTargetRoleLevel] = useState('');
  const [description, setDescription] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [saving, setSaving] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      onError('Name is required.');
      return;
    }
    setSaving(true);
    await onCreate({
      name: name.trim(),
      target_role_level: targetRoleLevel.trim(),
      description: description.trim(),
      start_date: startDate,
      end_date: endDate,
      status: 'active',
    });
    setSaving(false);
  }

  return (
    <form className="card p-5 flex flex-col gap-3" onSubmit={submit}>
      <div className="eyebrow">New campaign</div>
      <div
        className="grid gap-3"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}
      >
        <Field label="Name">
          <input
            type="text"
            placeholder="e.g. SWE Summer 2026"
            value={name}
            onChange={(e) => setName(e.target.value)}
            style={inputStyle}
            autoFocus
          />
        </Field>
        <Field label="Target role level">
          <input
            type="text"
            placeholder="Staff backend · FAANG"
            value={targetRoleLevel}
            onChange={(e) => setTargetRoleLevel(e.target.value)}
            style={inputStyle}
          />
        </Field>
        <Field label="Start">
          <DatePicker value={startDate} onChange={setStartDate} placeholder="Pick a date" />
        </Field>
        <Field label="End">
          <DatePicker value={endDate} onChange={setEndDate} placeholder="Pick a date" />
        </Field>
      </div>
      <Field label="What's this hunt about?">
        <textarea
          rows={2}
          placeholder="A sentence or two about the goal — so when you return later, context is obvious."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          style={{ ...inputStyle, fontFamily: 'inherit', resize: 'vertical' }}
        />
      </Field>
      <div className="flex gap-2 justify-end">
        <button type="button" onClick={onCancel} disabled={saving} style={secondaryBtn}>
          Cancel
        </button>
        <button type="submit" disabled={saving} style={primaryBtn}>
          {saving ? 'Creating…' : 'Create campaign'}
        </button>
      </div>
    </form>
  );
}

function StatusPill({ status }: { status: string }) {
  const c = STATUS_COLORS[status] ?? STATUS_COLORS.planning;
  return (
    <span className="pill" style={{ background: c.bg, color: c.fg }}>
      {status}
    </span>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1 min-w-0">
      <span className="eyebrow">{label}</span>
      {children}
    </label>
  );
}

const inputStyle: React.CSSProperties = {
  padding: '8px 10px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--border)',
  background: 'var(--bg-elev)',
  color: 'var(--text)',
  fontSize: 13,
};

const primaryBtn: React.CSSProperties = {
  padding: '8px 14px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'var(--accent)',
  color: 'var(--bg-elev)',
  fontSize: 12.5,
  fontWeight: 500,
  cursor: 'pointer',
};

const secondaryBtn: React.CSSProperties = {
  padding: '8px 14px',
  borderRadius: 'var(--radius)',
  border: '1px solid var(--border)',
  background: 'transparent',
  color: 'var(--text-2)',
  fontSize: 12.5,
  fontWeight: 500,
  cursor: 'pointer',
};

