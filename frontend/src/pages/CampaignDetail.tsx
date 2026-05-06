import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { AlertTriangle, Archive, RefreshCcw } from 'lucide-react';
import AppHeader from '../components/shell/AppHeader';
import PageShell from '../components/shell/PageShell';
import BackLink from '../components/shell/BackLink';
import DatePicker from '../components/shell/DatePicker';
import { useCampaign } from '../campaign/CampaignContext';
import type { Campaign } from '../campaign/types';

const STATUS_COLORS: Record<string, { bg: string; fg: string }> = {
  planning: { bg: 'var(--paper-3)', fg: 'var(--text-3)' },
  active: { bg: 'var(--accent-soft)', fg: 'var(--accent)' },
  wrapped: { bg: 'var(--forest-soft)', fg: 'var(--forest)' },
};

export default function CampaignDetail() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const {
    campaigns,
    ready,
    updateCampaign,
    wrapCampaign,
    resetProgress,
    setCurrent,
    currentId,
  } = useCampaign();

  const campaign = useMemo(
    () => campaigns.find((c) => c.slug === slug) ?? null,
    [campaigns, slug],
  );

  const [draft, setDraft] = useState<Campaign | null>(campaign);
  useEffect(() => {
    setDraft(campaign);
  }, [campaign]);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!ready) {
    return (
      <div
        className="h-full flex items-center justify-center"
        style={{ color: 'var(--text-4)', fontSize: 13 }}
      >
        Loading…
      </div>
    );
  }

  if (!campaign || !draft) {
    return (
      <PageShell
        header={
          <div className="px-8 pt-5">
            <BackLink to="/campaigns" label="All campaigns" />
          </div>
        }
      >
        <div
          className="flex items-center justify-center h-full"
          style={{ color: 'var(--text-3)', fontSize: 13 }}
        >
          Campaign not found.
        </div>
      </PageShell>
    );
  }

  const status = STATUS_COLORS[campaign.status] ?? STATUS_COLORS.planning;

  async function save() {
    if (!draft) return;
    setSaving(true);
    setError(null);
    try {
      await updateCampaign(draft.id, draft);
      setMessage('Saved.');
      setTimeout(() => setMessage(null), 1200);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed.');
    } finally {
      setSaving(false);
    }
  }

  async function onWrap() {
    if (!draft) return;
    if (!confirm(`Wrap "${draft.name}"? It'll move to Wrapped and drop out of the active rollup.`)) return;
    setSaving(true);
    try {
      await wrapCampaign(draft.id);
      setMessage('Wrapped.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Wrap failed.');
    } finally {
      setSaving(false);
    }
  }

  async function onReset() {
    if (!draft) return;
    if (
      !confirm(
        `Reset practice progress for "${draft.name}"? All question statuses and code drafts scoped to this campaign will be cleared. Applications, interview rounds, offers, and todos are untouched.`,
      )
    )
      return;
    setSaving(true);
    setError(null);
    try {
      await resetProgress(draft.id);
      setMessage('Practice progress cleared.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reset failed.');
    } finally {
      setSaving(false);
    }
  }

  const isCurrent = currentId === campaign.id;

  return (
    <PageShell
      header={
        <>
          <div className="px-8 pt-5">
            <BackLink to="/campaigns" label="All campaigns" />
          </div>
          <AppHeader
            eyebrow={`Track · Campaign · ${campaign.name}`}
            title={campaign.name}
            description={
              campaign.description ||
              'Practice progress, applications, interviews, offers, and todos all scope to this campaign.'
            }
            chromeActions={
              !isCurrent && (
                <button
                  type="button"
                  onClick={() => setCurrent(campaign.id)}
                  className="inline-flex items-center gap-1.5"
                  style={{ ...secondaryBtn, padding: '6px 14px', borderRadius: 8 }}
                >
                  Switch to this workspace
                </button>
              )
            }
          />
        </>
      }
    >
      <div className="px-5 sm:px-8 py-6 grid gap-5 grid-cols-1 lg:[grid-template-columns:minmax(0,1fr)_320px]">
        <div className="card p-6 flex flex-col gap-3">
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <div className="eyebrow">Details</div>
            <span className="pill" style={{ background: status.bg, color: status.fg }}>
              {campaign.status}
            </span>
          </div>
          <div
            className="grid gap-3"
            style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}
          >
            <Field label="Name">
              <input
                type="text"
                value={draft.name}
                onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                style={inputStyle}
              />
            </Field>
            <Field label="Target role level">
              <input
                type="text"
                value={draft.target_role_level}
                onChange={(e) => setDraft({ ...draft, target_role_level: e.target.value })}
                style={inputStyle}
              />
            </Field>
            <Field label="Start">
              <DatePicker
                value={draft.start_date}
                onChange={(v) => setDraft({ ...draft, start_date: v })}
                placeholder="Pick a date"
              />
            </Field>
            <Field label="End">
              <DatePicker
                value={draft.end_date}
                onChange={(v) => setDraft({ ...draft, end_date: v })}
                placeholder="Pick a date"
              />
            </Field>
          </div>
          <Field label="Description">
            <textarea
              rows={3}
              value={draft.description}
              onChange={(e) => setDraft({ ...draft, description: e.target.value })}
              style={{ ...inputStyle, fontFamily: 'inherit', resize: 'vertical' }}
            />
          </Field>
          <Field label="Target companies (comma-separated)">
            <input
              type="text"
              value={(draft.target_companies ?? []).join(', ')}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  target_companies: e.target.value
                    .split(',')
                    .map((s) => s.trim())
                    .filter(Boolean),
                })
              }
              style={inputStyle}
            />
          </Field>
          <div className="flex items-center gap-2 justify-between">
            <span
              style={{
                fontSize: 12,
                color: message ? 'var(--forest)' : error ? 'var(--plum)' : 'transparent',
              }}
            >
              {error ?? message ?? 'placeholder'}
            </span>
            <button type="button" onClick={save} disabled={saving} style={primaryBtn}>
              {saving ? 'Saving…' : 'Save changes'}
            </button>
          </div>
        </div>

        <aside className="flex flex-col gap-4">
          <div className="card p-5">
            <div className="eyebrow mb-2">Actions</div>
            <ActionButton
              tone="forest"
              Icon={RefreshCcw}
              label="Reset practice progress"
              description="Clear question statuses and code drafts — anecdotes, applications, rounds, offers, and todos remain."
              disabled={saving}
              onClick={onReset}
            />
            {campaign.status !== 'wrapped' && (
              <ActionButton
                tone="muted"
                Icon={Archive}
                label="Wrap this campaign"
                description="Marks the campaign done. Its data stays put; it just drops out of the active rollup."
                disabled={saving}
                onClick={onWrap}
              />
            )}
          </div>

          <div className="card p-5">
            <div className="eyebrow mb-2 flex items-center gap-1.5">
              <AlertTriangle size={11} strokeWidth={1.7} />
              About campaigns
            </div>
            <p style={{ margin: 0, fontSize: 12, color: 'var(--text-3)', lineHeight: 1.55 }}>
              Each campaign is its own workspace. Switch between them from the topbar pill.
              The dashboard and pipeline pages always read through whichever campaign you have
              active, or roll up across all active campaigns when you pick "All active".
            </p>
          </div>

          <button
            type="button"
            onClick={() => navigate('/campaigns')}
            style={secondaryBtn}
          >
            Back to campaigns
          </button>
        </aside>
      </div>
    </PageShell>
  );
}

function ActionButton({
  tone,
  Icon,
  label,
  description,
  disabled,
  onClick,
}: {
  tone: 'forest' | 'muted';
  Icon: (p: { size?: number; strokeWidth?: number }) => React.ReactNode;
  label: string;
  description: string;
  disabled?: boolean;
  onClick: () => void;
}) {
  const color = tone === 'forest' ? 'var(--forest)' : 'var(--text-2)';
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="flex items-start gap-3 w-full"
      style={{
        padding: '10px 12px',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        background: 'transparent',
        color,
        fontSize: 12.5,
        textAlign: 'left',
        cursor: disabled ? 'wait' : 'pointer',
        marginTop: 6,
      }}
    >
      <Icon size={14} strokeWidth={1.8} />
      <div className="flex flex-col" style={{ minWidth: 0 }}>
        <span style={{ fontWeight: 500 }}>{label}</span>
        <span style={{ fontSize: 11.5, color: 'var(--text-3)', lineHeight: 1.5 }}>
          {description}
        </span>
      </div>
    </button>
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
