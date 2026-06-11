import type { TimelineEntity, EntityKind } from './experienceApi';
import type {
  ExtractionResult, EndpointRef, ExistingConnectionRef,
  ExtractedJob, ExtractedProject, ExtractedAnecdote, ExtractedBullet,
} from './importApi';

export type ItemMode = 'new' | 'edit' | 'existing';
export type ExtractedAny = ExtractedJob | ExtractedProject | ExtractedAnecdote | ExtractedBullet;

export interface ReviewItem {
  localId: string;
  kind: EntityKind;
  mode: ItemMode;
  included: boolean;          // 'existing' items are always true (forced)
  existingId?: string;        // set for 'edit' and 'existing'
  data: ExtractedAny | null;  // proposal; null for 'existing' (use original)
  original?: TimelineEntity;  // for 'edit' diff and 'existing' display
}

export interface LocalConnection {
  parentLocalId: string;
  childLocalId: string;
  dashed: boolean;
}

export interface ReviewModel {
  items: ReviewItem[];
  connections: LocalConnection[];
}

export interface FieldDiff {
  field: string;
  from: string;
  to: string;
}

const KIND_ARRAYS: Array<{ kind: EntityKind; key: keyof Omit<ExtractionResult, 'connections' | 'warnings'> }> = [
  { kind: 'job', key: 'jobs' },
  { kind: 'project', key: 'projects' },
  { kind: 'anecdote', key: 'anecdotes' },
  { kind: 'bullet', key: 'bullets' },
];

const newLocalId = (kind: EntityKind, index: number) => `new:${kind}:${index}`;
const editLocalId = (id: string) => `edit:${id}`;
const existingLocalId = (id: string) => `existing:${id}`;

/** Build the review model: typed items (new/edit/existing) + deduped connections. */
export function buildReviewModel(
  result: ExtractionResult,
  existingById: Record<string, TimelineEntity>,
  existingConnections: ExistingConnectionRef[],
): ReviewModel {
  const items: ReviewItem[] = [];
  const editedIds = new Set<string>();

  for (const { kind, key } of KIND_ARRAYS) {
    const arr = (result[key] ?? []) as ExtractedAny[];
    arr.forEach((data, index) => {
      const existingId = (data.existing_id || '').trim();
      const original = existingId ? existingById[existingId] : undefined;
      if (existingId && original) {
        editedIds.add(existingId);
        items.push({ localId: editLocalId(existingId), kind, mode: 'edit', included: true, existingId, data, original });
      } else {
        items.push({ localId: newLocalId(kind, index), kind, mode: 'new', included: true, data });
      }
    });
  }

  // Resolve a connection endpoint to a localId, adding an 'existing' card on demand.
  const resolve = (ref: EndpointRef): string | null => {
    if (ref.id) {
      const id = ref.id;
      if (editedIds.has(id)) return editLocalId(id);
      const original = existingById[id];
      if (!original) return null; // unknown existing element — skip the connection
      const localId = existingLocalId(id);
      if (!items.some((i) => i.localId === localId)) {
        items.push({ localId, kind: original.kind, mode: 'existing', included: true, existingId: id, data: null, original });
      }
      return localId;
    }
    if (typeof ref.index === 'number') {
      const localId = newLocalId(ref.type, ref.index);
      return items.some((i) => i.localId === localId) ? localId : null;
    }
    return null;
  };

  const existingPairs = new Set(existingConnections.map((c) => `${c.parent_id}::${c.child_id}`));
  const seen = new Set<string>();
  const connections: LocalConnection[] = [];

  for (const c of result.connections ?? []) {
    const parentLocalId = resolve(c.parent);
    const childLocalId = resolve(c.child);
    if (!parentLocalId || !childLocalId || parentLocalId === childLocalId) continue;

    // Drop connections that already exist in the DB (by existing ids).
    if (c.parent.id && c.child.id && existingPairs.has(`${c.parent.id}::${c.child.id}`)) continue;

    const dedupKey = `${parentLocalId}::${childLocalId}`;
    if (seen.has(dedupKey)) continue;
    seen.add(dedupKey);

    const parentItem = items.find((i) => i.localId === parentLocalId)!;
    const childItem = items.find((i) => i.localId === childLocalId)!;
    const dashed = parentItem.mode !== 'new' || childItem.mode !== 'new';
    connections.push({ parentLocalId, childLocalId, dashed });
  }

  return { items, connections };
}

// ---------------------------------------------------------------------------
// Field diff (edit cards)
// ---------------------------------------------------------------------------

const DIFF_FIELDS: Record<EntityKind, string[]> = {
  job: ['company', 'role', 'location', 'employment_type', 'start_date', 'end_date', 'description', 'tags'],
  project: ['title', 'company', 'role', 'team_size', 'tech_stack', 'start_date', 'end_date', 'description', 'tags'],
  anecdote: ['title', 'situation', 'task', 'action', 'result', 'impact', 'company', 'project', 'date', 'tags'],
  bullet: ['title', 'impact', 'category', 'date', 'tags'],
};

function asText(value: unknown): string {
  if (value == null) return '';
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
}

/** Fields that differ between the existing record and the proposed (merged) edit. */
export function diffFields(original: TimelineEntity, proposed: ExtractedAny, kind: EntityKind): FieldDiff[] {
  const orig = original as unknown as Record<string, unknown>;
  const prop = proposed as unknown as Record<string, unknown>;
  const diffs: FieldDiff[] = [];
  for (const field of DIFF_FIELDS[kind]) {
    const from = asText(orig[field]);
    const to = asText(prop[field]);
    if (from !== to) diffs.push({ field, from, to });
  }
  return diffs;
}
