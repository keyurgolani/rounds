// Tailor — rewrite a master resume's bullets to match a JD.
//
// The flow:
//   1. Pick (or paste) a JD.
//   2. Pick a tone — the AI honors it for voice + density of the
//      rewrite. Optional role-focus tags emphasize specific themes.
//   3. Click Generate. AI returns a full rewritten ResumeData.
//   4. We diff old vs new bullet-by-bullet and show only what changed,
//      so the user can spot any unwanted edits before they save.
//   5. Save. We persist the rewritten data as a `resume_variants` row
//      linked to the master and (when picked) the Application — that
//      Application card can then surface "this is the variant we used."

import { useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Sparkles, Wand2 } from 'lucide-react';
import { listApplications } from '../../../../applications/api';
import { usePersistedState } from '../../../../hooks/usePersistedState';
import type { Resume, ResumeData } from '../../types';
import { tailorResume } from '../../ai/client';
import { createVariant } from '../../api';
import { markEdits } from '../../links/maintain';
import type { ResumeLinks } from '../../links/types';

type Props = {
  data: ResumeData;
  resume: Resume | null;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
  links: ResumeLinks;
  setLinks: (next: ResumeLinks | ((p: ResumeLinks) => ResumeLinks)) => void;
};

type AppRow = {
  id: string;
  company: string;
  role: string;
  status?: string;
  job_description?: string;
};

const TONES = [
  { id: 'professional', label: 'Professional' },
  { id: 'concise', label: 'Concise' },
  { id: 'technical', label: 'Technical' },
  { id: 'impact', label: 'Impact-led' },
  { id: 'storytelling', label: 'Storytelling' },
];

export default function TailorTab({ data, resume, setData, links, setLinks }: Props) {
  const persistKey = `rounds.resume.tailor.${resume?.id ?? 'untitled'}`;
  const [searchParams] = useSearchParams();
  const urlAppId = searchParams.get('app');

  const [appId, setAppId] = usePersistedState<string | null>(
    `${persistKey}.appId`,
    null,
  );
  const [jd, setJd] = usePersistedState<string>(`${persistKey}.jd`, '');
  const [tone, setTone] = usePersistedState<string>(
    `${persistKey}.tone`,
    'professional',
  );
  const [roleFocus, setRoleFocus] = usePersistedState<string[]>(
    `${persistKey}.roleFocus`,
    [],
  );

  const [apps, setApps] = useState<AppRow[]>([]);
  const [appsLoading, setAppsLoading] = useState(true);

  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [proposed, setProposed] = useState<ResumeData | null>(null);
  const [savedVariantName, setSavedVariantName] = useState<string | null>(null);

  // Apply ?app=… from the URL once on mount, so the Application
  // bridge from ApplicationDetail can drop the user straight into a
  // pre-anchored Tailor session.
  const appliedUrlRef = useRef(false);
  useEffect(() => {
    if (appliedUrlRef.current) return;
    if (urlAppId && urlAppId !== appId) {
      setAppId(urlAppId);
      appliedUrlRef.current = true;
    } else if (urlAppId) {
      appliedUrlRef.current = true;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlAppId]);

  useEffect(() => {
    setAppsLoading(true);
    listApplications()
      .then(setApps)
      .catch(() => setApps([]))
      .finally(() => setAppsLoading(false));
  }, []);

  const selectedApp = useMemo(
    () => apps.find((a) => a.id === appId) ?? null,
    [apps, appId],
  );

  // When the user picks an Application, prefill JD if one's on file.
  function pickApp(id: string | null) {
    setAppId(id);
    if (!id) return;
    const target = apps.find((a) => a.id === id);
    if (target?.job_description && !jd.trim()) {
      setJd(target.job_description);
    }
  }

  async function generate() {
    if (!jd.trim() || !resume) return;
    setGenerating(true);
    setError(null);
    setSavedVariantName(null);
    try {
      const r = await tailorResume({
        data,
        job_description: jd,
        tone,
        role_focus: roleFocus,
        target_company: selectedApp?.company,
        job_title: selectedApp?.role,
      });
      setProposed(r.data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setGenerating(false);
    }
  }

  async function applyToMaster() {
    if (!proposed) return;
    setData(proposed);
    setLinks(markEdits(data, proposed, links));
    setProposed(null);
  }

  async function saveAsVariant() {
    if (!proposed || !resume) return;
    setSaving(true);
    setError(null);
    try {
      const baseName =
        selectedApp?.company && selectedApp?.role
          ? `${selectedApp.company} — ${selectedApp.role}`
          : selectedApp?.company ?? `Tailored — ${tone}`;
      const variant = await createVariant({
        resume_id: resume.id,
        name: baseName,
        data: proposed,
        links: markEdits(data, proposed, links),
        target_company: selectedApp?.company,
        job_title: selectedApp?.role,
        job_description: jd,
        tone,
        role_focus: roleFocus,
        application_id: selectedApp?.id,
      });
      setSavedVariantName(variant.name);
      setProposed(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  const diffs = useMemo(() => (proposed ? diffBullets(data, proposed) : []), [
    data,
    proposed,
  ]);
  const summaryDiff = useMemo(
    () => (proposed ? diffSummary(data, proposed) : null),
    [data, proposed],
  );

  return (
    <div className="flex flex-col gap-3">
      <div
        className="card"
        style={{
          padding: 14,
          display: 'flex',
          flexDirection: 'column',
          gap: 10,
        }}
      >
        <Field label="Anchor to a tracked application (optional)">
          <select
            value={appId ?? ''}
            onChange={(e) => pickApp(e.target.value || null)}
            aria-label="Application"
            style={selectStyle}
          >
            <option value="">{appsLoading ? 'Loading…' : '— No application —'}</option>
            {apps.map((a) => (
              <option key={a.id} value={a.id}>
                {a.company} — {a.role}
              </option>
            ))}
          </select>
          {selectedApp && (
            <span
              style={{
                marginTop: 6,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                fontSize: 11,
                color: 'var(--text-3)',
                flexWrap: 'wrap',
              }}
            >
              <span
                className="pill"
                style={{
                  background: 'var(--bg-elev)',
                  color: 'var(--accent)',
                  boxShadow: 'inset 0 0 0 1px var(--accent)',
                  fontSize: 10,
                  padding: '2px 8px',
                }}
              >
                {selectedApp.company} · {selectedApp.role}
              </span>
              {!selectedApp.job_description && (
                <span style={{ color: 'var(--ochre)' }}>
                  No JD on file — paste one below.
                </span>
              )}
            </span>
          )}
        </Field>

        <Field label="Target JD">
          <textarea
            value={jd}
            onChange={(e) => setJd(e.target.value)}
            placeholder="Paste the job description here. The richer the JD, the sharper the rewrite."
            rows={6}
            style={{ ...selectStyle, fontFamily: 'inherit', resize: 'vertical' }}
          />
        </Field>

        <Field label="Tone">
          <div className="flex flex-wrap gap-1.5">
            {TONES.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => setTone(t.id)}
                style={{
                  padding: '6px 12px',
                  borderRadius: 'var(--radius)',
                  border: 0,
                  background: tone === t.id ? 'var(--accent)' : 'var(--bg-sunken)',
                  color: tone === t.id ? 'var(--bg-elev)' : 'var(--text-2)',
                  boxShadow: tone === t.id ? 'none' : 'inset 0 0 0 1px var(--border)',
                  fontSize: 11.5,
                  fontWeight: 500,
                  cursor: 'pointer',
                }}
              >
                {t.label}
              </button>
            ))}
          </div>
        </Field>

        <Field
          label="Role focus (optional)"
          hint="Comma-separated themes the AI should emphasize, e.g. distributed systems, payments infrastructure."
        >
          <input
            value={roleFocus.join(', ')}
            onChange={(e) =>
              setRoleFocus(
                e.target.value
                  .split(',')
                  .map((s) => s.trim())
                  .filter(Boolean),
              )
            }
            placeholder="e.g. distributed systems, observability, leadership"
            style={selectStyle}
          />
        </Field>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={generate}
            disabled={generating || !jd.trim() || !resume}
            style={{
              padding: '8px 14px',
              borderRadius: 'var(--radius)',
              border: 0,
              background: 'var(--accent)',
              color: 'var(--bg-elev)',
              fontSize: 12.5,
              fontWeight: 500,
              cursor: generating || !jd.trim() || !resume ? 'not-allowed' : 'pointer',
              opacity: generating || !jd.trim() || !resume ? 0.6 : 1,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <Wand2 size={13} strokeWidth={1.7} />
            {generating ? 'Generating…' : 'Generate tailored draft'}
          </button>
          {savedVariantName && (
            <span style={{ fontSize: 11.5, color: 'var(--forest)' }}>
              Saved variant: {savedVariantName}
            </span>
          )}
          {error && (
            <span style={{ fontSize: 11.5, color: 'var(--plum)' }}>{error}</span>
          )}
        </div>
      </div>

      {generating && !proposed && <DiffSkeleton />}

      {proposed && (
        <div
          className="card"
          style={{
            padding: 14,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          <div className="flex items-center gap-2">
            <Sparkles size={13} strokeWidth={1.7} style={{ color: 'var(--accent)' }} />
            <div className="eyebrow" style={{ fontSize: 9.5 }}>
              Proposed rewrite
            </div>
            <span style={{ fontSize: 11, color: 'var(--text-3)', marginLeft: 'auto' }}>
              {diffs.length} bullet
              {diffs.length === 1 ? '' : 's'} changed
              {summaryDiff ? ' · summary updated' : ''}
            </span>
          </div>

          {summaryDiff && (
            <DiffPair label="Summary" before={summaryDiff.before} after={summaryDiff.after} />
          )}

          {diffs.length === 0 && !summaryDiff ? (
            <p style={{ margin: 0, fontSize: 12, color: 'var(--text-3)' }}>
              The AI didn't change any bullets — your master already aligns well with the JD.
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {diffs.map((d, i) => (
                <DiffPair
                  key={i}
                  label={`${d.section} · ${d.entryLabel}`}
                  before={d.before}
                  after={d.after}
                />
              ))}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={saveAsVariant}
              disabled={saving}
              style={btnStyle('primary')}
            >
              {saving ? 'Saving…' : 'Save as variant'}
            </button>
            <button
              type="button"
              onClick={applyToMaster}
              disabled={saving}
              style={btnStyle('outline')}
              title="Replace the master resume's bullets with the proposed rewrite"
            >
              Apply to master
            </button>
            <button
              type="button"
              onClick={() => setProposed(null)}
              disabled={saving}
              style={btnStyle('ghost')}
            >
              Discard
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
//                                Diff helpers
// ---------------------------------------------------------------------------

type BulletDiff = {
  section: string;
  entryLabel: string;
  before: string;
  after: string;
};

function diffBullets(before: ResumeData, after: ResumeData): BulletDiff[] {
  const out: BulletDiff[] = [];

  const pair = <T extends { id: string; highlights?: string[] }>(
    label: string,
    olds: T[] = [],
    news: T[] = [],
    nameOf: (e: T) => string,
  ) => {
    const oldById = new Map(olds.map((e) => [e.id, e]));
    for (const n of news) {
      const o = oldById.get(n.id);
      if (!o) continue;
      const oldH = o.highlights ?? [];
      const newH = n.highlights ?? [];
      const max = Math.max(oldH.length, newH.length);
      for (let i = 0; i < max; i++) {
        const a = oldH[i] ?? '';
        const b = newH[i] ?? '';
        if (a !== b) {
          out.push({ section: label, entryLabel: nameOf(n), before: a, after: b });
        }
      }
    }
  };

  pair('Experience', before.experience, after.experience, (e) =>
    e.position && e.company ? `${e.position} @ ${e.company}` : e.company || e.position || 'Role',
  );
  pair('Projects', before.projects, after.projects, (p) => p.name || 'Project');
  return out;
}

function diffSummary(
  before: ResumeData,
  after: ResumeData,
): { before: string; after: string } | null {
  const b = (before.personalInfo.summary ?? '').trim();
  const a = (after.personalInfo.summary ?? '').trim();
  return b !== a ? { before: b, after: a } : null;
}

// ---------------------------------------------------------------------------
//                                Pieces
// ---------------------------------------------------------------------------

function DiffPair({
  label,
  before,
  after,
}: {
  label: string;
  before: string;
  after: string;
}) {
  return (
    <div
      style={{
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '10px 12px',
        display: 'grid',
        gap: 8,
        gridTemplateColumns: '1fr',
      }}
    >
      <div className="eyebrow" style={{ fontSize: 9 }}>
        {label}
      </div>
      <div className="flex flex-col gap-1.5">
        <DiffSide tone="del" text={before} />
        <DiffSide tone="add" text={after} />
      </div>
    </div>
  );
}

function DiffSide({ tone, text }: { tone: 'add' | 'del'; text: string }) {
  const color = tone === 'add' ? 'var(--forest)' : 'var(--plum)';
  const glyph = tone === 'add' ? '＋' : '−';
  return (
    <div
      style={{
        display: 'flex',
        gap: 8,
        fontSize: 12,
        lineHeight: 1.5,
        color: 'var(--text)',
        opacity: text ? 1 : 0.5,
      }}
    >
      <span
        className="mono"
        style={{
          flexShrink: 0,
          width: 14,
          color,
          fontWeight: 600,
          textAlign: 'center',
        }}
      >
        {glyph}
      </span>
      <span style={{ minWidth: 0 }}>
        {text || <span style={{ fontStyle: 'italic' }}>(empty)</span>}
      </span>
    </div>
  );
}

function DiffSkeleton() {
  return (
    <div className="card" style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div className="eyebrow" style={{ fontSize: 9.5 }}>
        Generating…
      </div>
      {[78, 92, 65].map((w, i) => (
        <div
          key={i}
          style={{
            height: 8,
            borderRadius: 4,
            background: 'var(--bg-sunken)',
            width: `${w}%`,
            animation: 'rounds-pulse 1.4s ease-in-out infinite',
            animationDelay: `${i * 90}ms`,
          }}
        />
      ))}
    </div>
  );
}

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="eyebrow" style={{ fontSize: 9.5 }}>
        {label}
      </span>
      {children}
      {hint && (
        <span style={{ fontSize: 10.5, color: 'var(--text-4)', lineHeight: 1.45 }}>{hint}</span>
      )}
    </label>
  );
}

const selectStyle: React.CSSProperties = {
  padding: '8px 10px',
  background: 'var(--bg-elev)',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
  borderRadius: 'var(--radius)',
  border: 0,
  fontSize: 12.5,
  color: 'var(--text)',
  outline: 'none',
  width: '100%',
};

function btnStyle(kind: 'primary' | 'outline' | 'ghost'): React.CSSProperties {
  if (kind === 'primary') {
    return {
      padding: '7px 14px',
      borderRadius: 'var(--radius)',
      border: 0,
      background: 'var(--accent)',
      color: 'var(--bg-elev)',
      fontSize: 12,
      fontWeight: 500,
      cursor: 'pointer',
    };
  }
  if (kind === 'outline') {
    return {
      padding: '6px 10px',
      borderRadius: 'var(--radius)',
      border: 0,
      background: 'transparent',
      boxShadow: 'inset 0 0 0 1px var(--border-strong)',
      color: 'var(--text-2)',
      fontSize: 11.5,
      fontWeight: 500,
      cursor: 'pointer',
    };
  }
  return {
    padding: '6px 10px',
    background: 'transparent',
    border: 0,
    color: 'var(--text-3)',
    fontSize: 11.5,
    fontWeight: 500,
    cursor: 'pointer',
  };
}
