import { useCallback, useEffect, useRef, useState } from 'react';
import { Download, FolderInput, Upload } from 'lucide-react';
import {
  createApplication,
  createOffer,
  createRound,
  getOffer,
  listApplications,
  listRounds,
  type ApplicationInput,
  type InterviewRoundInput,
  type OfferInput,
} from '../applications/api';
import { createCampaign as apiCreateCampaign } from '../campaign/api';
import { useCampaign } from '../campaign/CampaignContext';
import type { Campaign } from '../campaign/types';
import {
  createUserProgress,
  listUserProgress,
  type UserProgressInput,
} from '../hooks/progressApi';
import {
  listCodeDrafts,
  upsertCodeDraft,
  type CodeDraftInput,
} from '../lib/codeDraftsApi';
import { createTodo, listTodos, type TodoInput } from '../todos/api';
import { listAnecdotes } from '../experience/experienceApi';

interface OfferSnapshot extends Record<string, unknown> {
  id: string;
  application_id: string;
  status: string;
}

interface RoundSnapshot extends Record<string, unknown> {
  id: string;
  application_id: string;
}

interface ApplicationSnapshot extends Record<string, unknown> {
  id: string;
  campaign?: string;
  rounds?: RoundSnapshot[];
  offer?: OfferSnapshot | null;
}

interface TodoSnapshot extends Record<string, unknown> {
  id: string;
  campaign_id?: string;
}

interface ProgressSnapshot extends Record<string, unknown> {
  id: string;
  campaign_id?: string;
}

interface DraftSnapshot extends Record<string, unknown> {
  id: string;
  campaign_id?: string;
}

interface AnecdoteRef {
  slug: string;
  title: string;
}

interface Bundle {
  format_version: 1;
  exported_at: string;
  campaign: Partial<Campaign>;
  applications: ApplicationSnapshot[];
  todos: TodoSnapshot[];
  user_progress: ProgressSnapshot[];
  code_drafts: DraftSnapshot[];
  anecdotes_referenced: AnecdoteRef[];
}

export default function DataSection() {
  const { campaigns, currentId, refresh } = useCampaign();
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Preselect a sensible target so Export is actionable the moment the
  // user lands here: current campaign if set, otherwise the default,
  // otherwise the first one. Every user has at least the auto-created
  // default campaign, so this is never empty in practice.
  useEffect(() => {
    if (campaigns.length === 0) {
      setSelected(new Set());
      return;
    }
    const preferred =
      campaigns.find((c) => c.id === currentId) ??
      campaigns.find((c) => c.is_default) ??
      campaigns[0];
    setSelected(new Set([preferred.id]));
  }, [campaigns, currentId]);

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function selectAll() {
    setSelected(new Set(campaigns.map((c) => c.id)));
  }

  function clearSelection() {
    setSelected(new Set());
  }

  const doExport = useCallback(async () => {
    if (selected.size === 0) return;
    setExporting(true);
    setMessage(null);
    setError(null);
    try {
      const bundles = await Promise.all(
        [...selected].map((id) =>
          buildBundle(campaigns.find((c) => c.id === id)!),
        ),
      );
      if (bundles.length === 1) {
        download(bundles[0], `${bundles[0].campaign.slug ?? 'campaign'}.json`);
      } else {
        // Multi-select: a single aggregate file. On import we detect
        // the array shape and treat each element as its own bundle.
        const aggregate = {
          format_version: 1 as const,
          exported_at: new Date().toISOString(),
          bundles,
        };
        download(aggregate, `rounds-campaigns-${today()}.json`);
      }
      setMessage(`Exported ${bundles.length} campaign${bundles.length === 1 ? '' : 's'}.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Export failed.');
    } finally {
      setExporting(false);
    }
  }, [selected, campaigns]);

  const doImport = useCallback(
    async (file: File) => {
      setImporting(true);
      setMessage(null);
      setError(null);
      try {
        const text = await file.text();
        const parsed = JSON.parse(text) as Bundle | { bundles: Bundle[] };
        const bundles: Bundle[] =
          'bundles' in parsed && Array.isArray(parsed.bundles)
            ? parsed.bundles
            : [parsed as Bundle];

        let created = 0;
        let droppedAnecdotes = 0;
        for (const bundle of bundles) {
          const result = await importBundle(bundle, campaigns);
          created += 1;
          droppedAnecdotes += result.droppedAnecdotes;
        }
        await refresh();
        const parts = [`Imported ${created} campaign${created === 1 ? '' : 's'}.`];
        if (droppedAnecdotes > 0) {
          parts.push(
            `${droppedAnecdotes} anecdote reference${droppedAnecdotes === 1 ? '' : 's'} could not be resolved and were skipped.`,
          );
        }
        setMessage(parts.join(' '));
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Import failed.');
      } finally {
        setImporting(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    },
    [campaigns, refresh],
  );

  return (
    <div className="card p-5 grid gap-3 grid-cols-1 sm:[grid-template-columns:220px_1fr]">
      <div>
        <div className="eyebrow mb-1.5">Data</div>
        <p
          style={{ margin: 0, fontSize: 12.5, color: 'var(--text-3)', lineHeight: 1.55 }}
        >
          Export one or more campaigns as self-contained JSON. Import always creates a new
          campaign — no merge, no conflicts, so moving a snapshot between devices or keeping
          a frozen reference is safe.
        </p>
      </div>
      <div className="flex flex-col gap-3">
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <span className="eyebrow">Campaigns to export</span>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={selectAll}
                className="mono uppercase"
                style={linkBtn}
              >
                Select all
              </button>
              <button
                type="button"
                onClick={clearSelection}
                className="mono uppercase"
                style={linkBtn}
              >
                Clear
              </button>
            </div>
          </div>
          <div className="flex flex-col gap-1">
            {campaigns.map((c) => (
              <label
                key={c.id}
                className="flex items-center gap-2"
                style={{
                  padding: '6px 10px',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  fontSize: 12.5,
                  color: 'var(--text)',
                }}
              >
                <input
                  type="checkbox"
                  checked={selected.has(c.id)}
                  onChange={() => toggle(c.id)}
                />
                <span style={{ flex: 1 }}>{c.name}</span>
                <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
                  {c.status}
                </span>
              </label>
            ))}
            {campaigns.length === 0 && (
              <div style={{ fontSize: 12, color: 'var(--text-4)', fontStyle: 'italic' }}>
                No campaigns to export yet.
              </div>
            )}
          </div>
          <div className="flex gap-2 justify-end">
            <button
              type="button"
              onClick={doExport}
              disabled={exporting || selected.size === 0}
              className="inline-flex items-center gap-1.5"
              style={{
                ...primaryBtn,
                opacity: exporting || selected.size === 0 ? 0.6 : 1,
              }}
            >
              <Download size={13} strokeWidth={1.8} />
              {exporting ? 'Exporting…' : `Export ${selected.size || ''}`}
            </button>
          </div>
        </div>

        <div
          style={{
            borderTop: '1px solid var(--border)',
            paddingTop: 12,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}
        >
          <span className="eyebrow">Import a campaign</span>
          <p
            style={{
              margin: 0,
              fontSize: 12,
              color: 'var(--text-3)',
              lineHeight: 1.55,
            }}
          >
            Each file becomes a new campaign. If the name collides with an existing one, the
            imported copy is suffixed so you keep both.
          </p>
          <div className="flex items-center gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept=".json,application/json"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) void doImport(f);
              }}
              style={{ display: 'none' }}
              id="data-import-file"
            />
            <label
              htmlFor="data-import-file"
              className="inline-flex items-center gap-1.5"
              style={{
                ...secondaryBtn,
                cursor: importing ? 'wait' : 'pointer',
                opacity: importing ? 0.7 : 1,
              }}
            >
              <Upload size={13} strokeWidth={1.8} />
              {importing ? 'Importing…' : 'Pick a JSON file'}
            </label>
            <span
              className="mono"
              style={{ fontSize: 10.5, color: 'var(--text-4)' }}
            >
              <FolderInput size={10} strokeWidth={1.8} style={{ display: 'inline' }} />{' '}
              JSON only
            </span>
          </div>
        </div>

        {message && (
          <div
            style={{ fontSize: 12, color: 'var(--forest)', marginTop: 6 }}
          >
            {message}
          </div>
        )}
        {error && (
          <div style={{ fontSize: 12, color: 'var(--plum)', marginTop: 6 }}>{error}</div>
        )}
      </div>
    </div>
  );
}

async function buildBundle(campaign: Campaign): Promise<Bundle> {
  const [todos, progress, drafts, apps, anecdotes] = await Promise.all([
    listTodos(campaign.id).catch(() => []),
    listUserProgress(campaign.id).catch(() => []),
    listCodeDrafts({ campaign_id: campaign.id }).catch(() => []),
    listApplications(campaign.id).catch(() => []),
    listAnecdotes().catch(() => []),
  ]);

  // Attach per-application rounds and offer.
  const appsFull: ApplicationSnapshot[] = [];
  for (const app of apps) {
    const [rounds, offer] = await Promise.all([
      listRounds(app.id).catch(() => []),
      getOffer(app.id).catch(() => null),
    ]);
    appsFull.push({ ...app, rounds: rounds as RoundSnapshot[], offer: offer as OfferSnapshot | null });
  }

  const referencedSlugs = new Set<string>();
  for (const t of todos) {
    const mentions = (t as { mentions?: { type: string; slug: string }[] }).mentions ?? [];
    for (const m of mentions) {
      if (m.type === 'anecdote') referencedSlugs.add(m.slug);
    }
  }
  const byTitle = new Map(anecdotes.map((a) => [slugify(a.title), a]));
  const anecdotes_referenced: AnecdoteRef[] = [];
  for (const slug of referencedSlugs) {
    const match = byTitle.get(slug);
    if (match) anecdotes_referenced.push({ slug, title: match.title });
  }

  return {
    format_version: 1,
    exported_at: new Date().toISOString(),
    campaign,
    applications: appsFull,
    todos: todos as TodoSnapshot[],
    user_progress: progress as ProgressSnapshot[],
    code_drafts: drafts as DraftSnapshot[],
    anecdotes_referenced,
  };
}

async function importBundle(
  bundle: Bundle,
  existing: Campaign[],
): Promise<{ droppedAnecdotes: number }> {
  const baseSlug = bundle.campaign?.slug ?? 'imported';
  const slug = await resolveImportSlug(baseSlug, existing);
  const name = (bundle.campaign?.name ?? 'Imported campaign') + ' (imported)';

  const created = await apiCreateCampaign({
    ...bundle.campaign,
    name,
    slug,
    status: 'active',
    is_default: false,
  });

  // Create applications and remember mapping old ID → new ID so rounds
  // and offers can be re-parented correctly.
  const appIdMap = new Map<string, string>();
  for (const app of bundle.applications ?? []) {
    const payload: Record<string, unknown> = { ...app, campaign_id: created.id };
    delete payload.id;
    delete payload.rounds;
    delete payload.offer;
    delete payload.campaign;
    const newApp = await createApplication(payload as ApplicationInput);
    appIdMap.set(app.id, newApp.id);

    for (const round of app.rounds ?? []) {
      const rp: Record<string, unknown> = { ...round, campaign_id: created.id };
      delete rp.id;
      delete rp.application_id;
      delete rp.application;
      await createRound(newApp.id, rp as InterviewRoundInput);
    }
    if (app.offer) {
      const op: Record<string, unknown> = { ...app.offer };
      delete op.id;
      delete op.application_id;
      delete op.application;
      await createOffer(newApp.id, op as OfferInput);
    }
  }

  // Todos (with campaign reassigned; application mentions remapped
  // when possible).
  for (const todo of bundle.todos ?? []) {
    const payload: Record<string, unknown> = { ...todo, campaign_id: created.id };
    delete payload.id;
    const mentions = (todo as { mentions?: { type: string; slug: string }[] }).mentions;
    if (Array.isArray(mentions)) {
      payload.mentions = mentions.map((m) => {
        if (m.type !== 'application') return m;
        const mapped = appIdMap.get(m.slug);
        return mapped ? { ...m, slug: mapped } : m;
      });
    }
    await createTodo(payload as unknown as TodoInput);
  }

  for (const p of bundle.user_progress ?? []) {
    const payload: Record<string, unknown> = { ...p, campaign_id: created.id };
    delete payload.id;
    await createUserProgress(payload as unknown as UserProgressInput);
  }

  for (const d of bundle.code_drafts ?? []) {
    const payload: Record<string, unknown> = { ...d, campaign_id: created.id };
    delete payload.id;
    await upsertCodeDraft(payload as unknown as CodeDraftInput);
  }

  // Anecdote references — count ones we cannot resolve against the
  // user's existing anecdote library. We do not create anecdotes on
  // import; the library is intentionally campaign-independent.
  let droppedAnecdotes = 0;
  try {
    const userAnecdotes = await listAnecdotes();
    const known = new Set(userAnecdotes.map((a) => slugify(a.title)));
    for (const ref of bundle.anecdotes_referenced ?? []) {
      if (!known.has(ref.slug)) droppedAnecdotes += 1;
    }
  } catch {
    /* counted as zero */
  }

  return { droppedAnecdotes };
}

async function resolveImportSlug(base: string, existing: Campaign[]): Promise<string> {
  const used = new Set(existing.map((c) => c.slug));
  const dated = `${base}-imported-${compactDate()}`;
  if (!used.has(dated)) return dated;
  let i = 2;
  while (used.has(`${dated}-${i}`)) i += 1;
  return `${dated}-${i}`;
}

function download(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

function slugify(s: string): string {
  return s
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64);
}

function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function compactDate(): string {
  const d = new Date();
  return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`;
}

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
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
};

const linkBtn: React.CSSProperties = {
  background: 'transparent',
  border: 0,
  color: 'var(--text-3)',
  fontSize: 10,
  letterSpacing: '0.1em',
  cursor: 'pointer',
  padding: 0,
};
