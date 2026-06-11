// frontend/src/experience/ImportReview.tsx
import { useState, useMemo } from 'react';
import { Check } from 'lucide-react';
import {
  createJob, createProject, createAnecdote, createBullet,
  updateJob, updateProject, updateAnecdote, updateBullet,
  deleteJob, deleteProject, deleteAnecdote, deleteBullet,
  type ExperienceJob, type ExperienceProject, type ExperienceAnecdote, type ExperienceBullet,
  type TimelineEntity, type EntityKind,
} from './experienceApi';
import { batchCreateConnections, getJunctionTable } from './connectionApi';
import type {
  ExtractionResult, ExistingConnectionRef,
  ExtractedJob, ExtractedProject, ExtractedAnecdote, ExtractedBullet,
} from './importApi';
import {
  buildReviewModel, diffFields,
  type ReviewItem, type LocalConnection, type ItemMode,
} from './importReconcile';
import ConnectionCanvas, { TYPE_COLORS, TYPE_LABELS, type CanvasItem } from './ConnectionCanvas';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface Props {
  result: ExtractionResult;
  existingEntities: TimelineEntity[];
  existingConnections: ExistingConnectionRef[];
  onComplete: () => void;
  onCancel: () => void;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const MODE_BADGE: Record<ItemMode, { label: string; color: string } | null> = {
  new: null,
  edit: { label: 'EDIT', color: 'var(--ochre)' },
  existing: { label: 'EXISTING', color: 'var(--text-4)' },
};

function labelFor(item: ReviewItem): { primary: string; secondary?: string } {
  if (item.mode === 'existing' && item.original) {
    const o = item.original;
    return {
      primary: o.kind === 'job' ? o.company : o.title,
      secondary: o.kind === 'job' ? o.role : o.kind === 'project' ? o.company : undefined,
    };
  }
  const d = item.data;
  switch (item.kind) {
    case 'job': return { primary: (d as ExtractedJob).company || 'Untitled Job', secondary: (d as ExtractedJob).role || undefined };
    case 'project': return { primary: (d as ExtractedProject).title || 'Untitled Project', secondary: (d as ExtractedProject).company || undefined };
    case 'anecdote': return { primary: (d as ExtractedAnecdote).title || 'Untitled Anecdote', secondary: (d as ExtractedAnecdote).situation?.slice(0, 80) || undefined };
    case 'bullet': return { primary: (d as ExtractedBullet).title || 'Untitled Bullet', secondary: (d as ExtractedBullet).impact || undefined };
    default: return { primary: 'Untitled' };
  }
}

// ---------------------------------------------------------------------------
// Field sanitizers — AI extraction may leave required fields empty or malformed.
// Required fields must be non-empty or PocketBase rejects the create.
// ---------------------------------------------------------------------------

const EMPLOYMENT_TYPES = ['full-time', 'contract', 'part-time', 'internship', 'freelance'];
const BULLET_CATEGORIES = ['leadership', 'technical', 'process', 'business', 'other'];

function today(): string {
  return new Date().toISOString().split('T')[0];
}

/** A required date: keep a valid YYYY-MM-DD, otherwise fall back to today. */
function reqDate(value?: string): string {
  const v = value?.trim();
  return v && /^\d{4}-\d{2}-\d{2}/.test(v) ? v : today();
}

/** An optional date (e.g. end_date): valid YYYY-MM-DD or null ("Present"). */
function optDate(value?: string): string | null {
  const v = value?.trim();
  return v && /^\d{4}-\d{2}-\d{2}/.test(v) ? v : null;
}

/** A required text field: trimmed value, or the provided fallback if empty. */
function reqText(value: string | undefined, fallback: string): string {
  return value?.trim() || fallback;
}

/** A select value: keep only if it's one of the allowed options, else empty. */
function oneOf(value: string | undefined, allowed: string[]): string {
  const v = value?.trim().toLowerCase();
  return v && allowed.includes(v) ? v : '';
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function ImportReview({ result, existingEntities, existingConnections, onComplete, onCancel }: Props) {
  const existingById = useMemo(() => {
    const map: Record<string, TimelineEntity> = {};
    for (const e of existingEntities) map[e.id] = e;
    return map;
  }, [existingEntities]);

  const initialModel = useMemo(
    () => buildReviewModel(result, existingById, existingConnections),
    [result, existingById, existingConnections],
  );

  const [items, setItems] = useState<ReviewItem[]>(initialModel.items);
  const [connections, setConnections] = useState<LocalConnection[]>(initialModel.connections);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState<string | null>(null);

  const itemById = useMemo(() => {
    const m: Record<string, ReviewItem> = {};
    for (const i of items) m[i.localId] = i;
    return m;
  }, [items]);

  const grouped = useMemo(() => {
    const groups: Record<EntityKind, ReviewItem[]> = { job: [], project: [], anecdote: [], bullet: [] };
    for (const item of items) groups[item.kind].push(item);
    return groups;
  }, [items]);

  const canvasItems: CanvasItem[] = useMemo(
    () => items.map((i) => ({ localId: i.localId, kind: i.kind })),
    [items],
  );

  // Toggle included — 'existing' items can't be toggled (they aren't imported).
  function toggleIncluded(localId: string) {
    setItems((prev) => prev.map((i) =>
      i.localId === localId && i.mode !== 'existing' ? { ...i, included: !i.included } : i,
    ));
  }

  // Add/remove a connection from a drag. The canvas has already ordered + validated.
  function onToggleLink(parentLocalId: string, childLocalId: string, alreadyLinked: boolean) {
    if (alreadyLinked) {
      setConnections((prev) => prev.filter((c) => !(c.parentLocalId === parentLocalId && c.childLocalId === childLocalId)));
      return;
    }
    const p = itemById[parentLocalId];
    const c = itemById[childLocalId];
    const dashed = !p || !c ? false : (p.mode !== 'new' || c.mode !== 'new');
    setConnections((prev) => [...prev, { parentLocalId, childLocalId, dashed }]);
  }

  // --- Counts (existing cards aren't imported) ---
  const includedItems = useMemo(() => items.filter((i) => i.mode !== 'existing' && i.included), [items]);
  const includedConnections = useMemo(
    () => connections.filter((c) =>
      items.some((i) => i.localId === c.parentLocalId && (i.mode === 'existing' || i.included)) &&
      items.some((i) => i.localId === c.childLocalId && (i.mode === 'existing' || i.included)),
    ),
    [connections, items],
  );

  // Roll back: delete created records (cascade removes their junctions) and
  // restore edited records to their captured prior values.
  async function rollback(
    created: Array<{ kind: EntityKind; id: string }>,
    edited: Array<{ kind: EntityKind; id: string; prev: Record<string, unknown> }>,
  ) {
    for (const c of [...created].reverse()) {
      try {
        if (c.kind === 'job') await deleteJob(c.id);
        else if (c.kind === 'project') await deleteProject(c.id);
        else if (c.kind === 'anecdote') await deleteAnecdote(c.id);
        else await deleteBullet(c.id);
      } catch { /* best effort */ }
    }
    for (const e of edited) {
      try {
        if (e.kind === 'job') await updateJob(e.id, e.prev as Partial<ExperienceJob>);
        else if (e.kind === 'project') await updateProject(e.id, e.prev as Partial<ExperienceProject>);
        else if (e.kind === 'anecdote') await updateAnecdote(e.id, e.prev as Partial<ExperienceAnecdote>);
        else await updateBullet(e.id, e.prev as Partial<ExperienceBullet>);
      } catch { /* best effort */ }
    }
  }

  // --- Import execution (atomic: any failure rolls back everything) ---
  async function executeImport() {
    setImporting(true);
    setImportError(null);
    const idMap: Record<string, string> = {};   // localId -> PB id
    const created: Array<{ kind: EntityKind; id: string }> = [];
    const edited: Array<{ kind: EntityKind; id: string; prev: Record<string, unknown> }> = [];

    const editable: Record<EntityKind, string[]> = {
      job: ['company', 'role', 'location', 'employment_type', 'start_date', 'end_date', 'description', 'tags'],
      project: ['title', 'company', 'role', 'team_size', 'tech_stack', 'start_date', 'end_date', 'description', 'tags'],
      anecdote: ['title', 'situation', 'task', 'action', 'result', 'impact', 'company', 'project', 'date', 'tags'],
      bullet: ['title', 'impact', 'category', 'date', 'tags'],
    };
    const pick = (src: Record<string, unknown>, keys: string[]) =>
      Object.fromEntries(keys.map((k) => [k, src[k]]));

    try {
      for (const item of items) {
        if (item.mode === 'existing') { idMap[item.localId] = item.existingId!; continue; }
        if (!item.included) continue;

        if (item.mode === 'edit') {
          const id = item.existingId!;
          const prev = pick(item.original as unknown as Record<string, unknown>, editable[item.kind]);
          const next = pick(item.data as unknown as Record<string, unknown>, editable[item.kind]);
          if (item.kind === 'job') await updateJob(id, next as Partial<ExperienceJob>);
          else if (item.kind === 'project') await updateProject(id, next as Partial<ExperienceProject>);
          else if (item.kind === 'anecdote') await updateAnecdote(id, next as Partial<ExperienceAnecdote>);
          else await updateBullet(id, next as Partial<ExperienceBullet>);
          edited.push({ kind: item.kind, id, prev });
          idMap[item.localId] = id;
          continue;
        }

        // mode === 'new' — create with sanitization
        const d = item.data!;
        let pbId: string;
        if (item.kind === 'job') {
          const j = d as ExtractedJob;
          pbId = (await createJob({
            company: reqText(j.company, 'Untitled'), role: reqText(j.role, '—'),
            location: j.location, employment_type: oneOf(j.employment_type, EMPLOYMENT_TYPES),
            start_date: reqDate(j.start_date), end_date: optDate(j.end_date),
            description: j.description, tags: j.tags,
          })).id;
        } else if (item.kind === 'project') {
          const p = d as ExtractedProject;
          pbId = (await createProject({
            title: reqText(p.title, 'Untitled Project'), company: p.company, role: p.role,
            team_size: p.team_size, tech_stack: p.tech_stack,
            start_date: reqDate(p.start_date), end_date: optDate(p.end_date),
            description: p.description, tags: p.tags,
          })).id;
        } else if (item.kind === 'anecdote') {
          const a = d as ExtractedAnecdote;
          pbId = (await createAnecdote({
            title: reqText(a.title, 'Untitled Anecdote'), situation: a.situation, task: a.task,
            action: a.action, result: a.result, impact: a.impact, company: a.company,
            project: a.project, date: reqDate(a.date), tags: a.tags,
          })).id;
        } else {
          const b = d as ExtractedBullet;
          pbId = (await createBullet({
            title: reqText(b.title, 'Untitled Bullet'), impact: b.impact,
            category: oneOf(b.category, BULLET_CATEGORIES), date: reqDate(b.date), tags: b.tags,
          })).id;
        }
        created.push({ kind: item.kind, id: pbId });
        idMap[item.localId] = pbId;
      }

      // Connections — only those whose endpoints both resolved (included/existing).
      const pairs = connections
        .map((c) => {
          const a = itemById[c.parentLocalId];
          const b = itemById[c.childLocalId];
          if (!a || !b) return null;
          if (!idMap[a.localId] || !idMap[b.localId]) return null; // an endpoint was excluded
          if (!getJunctionTable(a.kind, b.kind)) return null;
          return { parentKind: a.kind, parentId: idMap[a.localId], childKind: b.kind, childId: idMap[b.localId] };
        })
        .filter(Boolean) as Array<{ parentKind: EntityKind; parentId: string; childKind: EntityKind; childId: string }>;

      await batchCreateConnections(pairs);
      onComplete();
    } catch (e) {
      await rollback(created, edited);
      setImportError(`Import failed and was rolled back — nothing was saved. ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setImporting(false);
    }
  }

  // --- Card content (review-specific: checkbox, badge, secondary, field diff) ---
  function renderCardContent(ci: CanvasItem) {
    const item = itemById[ci.localId];
    if (!item) return null;
    const { primary, secondary } = labelFor(item);
    const badge = MODE_BADGE[item.mode];
    const colors = TYPE_COLORS[item.kind];
    return (
      <div className="flex items-start gap-2" style={{ opacity: item.mode === 'existing' ? 0.7 : 1 }}>
        {item.mode !== 'existing' && (
          <input
            type="checkbox"
            checked={item.included}
            onChange={() => toggleIncluded(item.localId)}
            style={{ marginTop: 2, accentColor: colors.text }}
          />
        )}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5" style={{ flexWrap: 'wrap' }}>
            {badge && (
              <span className="mono" style={{ fontSize: 8.5, letterSpacing: '0.06em', padding: '1px 5px', borderRadius: 4, color: badge.color, boxShadow: `inset 0 0 0 1px ${badge.color}` }}>
                {badge.label}
              </span>
            )}
            <span style={{ fontSize: 14, fontWeight: 500, color: item.mode !== 'new' || item.included ? 'var(--text)' : 'var(--text-4)', lineHeight: 1.3 }}>
              {primary}
            </span>
          </div>
          {secondary && (
            <div className="line-clamp-1" style={{ fontSize: 12, color: 'var(--text-3)', marginTop: 2 }}>
              {secondary}
            </div>
          )}
          {item.mode === 'edit' && item.original && item.data && (
            <div style={{ marginTop: 6, display: 'flex', flexDirection: 'column', gap: 2 }}>
              {diffFields(item.original, item.data, item.kind).map((diff) => (
                <div key={diff.field} className="mono" style={{ fontSize: 10, color: 'var(--text-3)', lineHeight: 1.4 }}>
                  <span style={{ color: 'var(--text-4)' }}>{diff.field}: </span>
                  <span style={{ textDecoration: 'line-through', color: 'var(--text-4)' }}>{diff.from || '—'}</span>
                  {' → '}
                  <span style={{ color: 'var(--ochre)' }}>{diff.to || '—'}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  function renderGroupHeader(kind: EntityKind) {
    const groupItems = grouped[kind];
    const included = groupItems.filter((i) => i.mode === 'existing' || i.included).length;
    return (
      <span className="mono" style={{ fontSize: 11, letterSpacing: '0.08em', color: TYPE_COLORS[kind].text }}>
        {TYPE_LABELS[kind].toUpperCase()} ({included}/{groupItems.length})
      </span>
    );
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Import Review"
      onClick={onCancel}
      style={{
        position: 'fixed', inset: 0, zIndex: 50,
        background: 'rgba(0, 0, 0, 0.45)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 24,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: '95vw',
          height: '95vh',
          background: 'var(--bg)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-elev)',
          display: 'flex', flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{ padding: '16px 24px', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
          <h2 style={{ fontSize: 20, fontWeight: 600, margin: 0, color: 'var(--text)' }}>Import Review</h2>
          <p style={{ fontSize: 13, color: 'var(--text-3)', margin: '4px 0 0' }}>
            Review extracted items. Check/uncheck to include. Drag between cards to connect.
            <span style={{ marginLeft: 8, color: 'var(--ochre)' }}>EDIT</span> updates an existing element;
            <span style={{ marginLeft: 6, color: 'var(--text-4)' }}>EXISTING</span> stays as-is.
          </p>
        </div>

        {/* Content */}
        <div className="flex-1 min-h-0 overflow-auto" style={{ padding: 24 }}>
          <ConnectionCanvas
            items={canvasItems}
            connections={connections}
            renderCardContent={renderCardContent}
            renderGroupHeader={renderGroupHeader}
            onToggleLink={onToggleLink}
          />
        </div>

        {/* Footer */}
        <div style={{ padding: '12px 24px', borderTop: '1px solid var(--border)', flexShrink: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 16 }}>
          {importError ? (
            <span style={{ fontSize: 12, color: 'var(--plum)', lineHeight: 1.4, minWidth: 0 }}>
              {importError}
            </span>
          ) : (
            <span className="mono" style={{ fontSize: 11, color: 'var(--text-4)' }}>
              {includedItems.length} items · {includedConnections.length} connections
            </span>
          )}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={onCancel}
              style={{ padding: '8px 16px', border: 0, borderRadius: 'var(--radius)', background: 'var(--bg-sunken)', color: 'var(--text-2)', fontSize: 13, cursor: 'pointer' }}
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={executeImport}
              disabled={importing || includedItems.length === 0}
              data-ai-processing-glow={importing ? 'true' : undefined}
              className="flex items-center gap-1.5"
              style={{
                padding: '8px 20px', border: 0, borderRadius: 'var(--radius)',
                background: 'var(--accent)', color: 'var(--accent-fg, var(--paper))',
                fontSize: 13, fontWeight: 500, cursor: importing ? 'wait' : 'pointer',
                opacity: !importing && includedItems.length === 0 ? 0.6 : 1,
              }}
            >
              <Check size={14} />
              {importing ? 'Importing…' : `Import ${includedItems.length} items`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
