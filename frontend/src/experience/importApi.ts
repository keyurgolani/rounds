import { runnerJSON } from '../lib/runnerFetch';
import type { EntityKind } from './experienceApi';

// ---------------------------------------------------------------------------
// Extracted item types — each carries existing_id ("" => new, else => edit).
// ---------------------------------------------------------------------------

export interface ExtractedJob {
  existing_id: string;
  company: string;
  role: string;
  location: string;
  employment_type: string;
  start_date: string;
  end_date: string;
  description: string;
  tags: string[];
}

export interface ExtractedProject {
  existing_id: string;
  title: string;
  company: string;
  role: string;
  team_size: number | null;
  tech_stack: string[];
  start_date: string;
  end_date: string;
  description: string;
  tags: string[];
}

export interface ExtractedAnecdote {
  existing_id: string;
  title: string;
  situation: string;
  task: string;
  action: string;
  result: string;
  impact: string;
  company: string;
  project: string;
  date: string;
  tags: string[];
}

export interface ExtractedBullet {
  existing_id: string;
  title: string;
  impact: string;
  category: string;
  date: string;
  tags: string[];
}

/** A connection endpoint: a new item (index) or an existing element (id). */
export interface EndpointRef {
  type: EntityKind;
  index?: number;
  id?: string;
}

export interface ExtractedConnection {
  parent: EndpointRef;
  child: EndpointRef;
}

export interface ExtractionResult {
  jobs: ExtractedJob[];
  projects: ExtractedProject[];
  anecdotes: ExtractedAnecdote[];
  bullets: ExtractedBullet[];
  connections: ExtractedConnection[];
  warnings: string[];
}

// ---------------------------------------------------------------------------
// Inputs sent to the AI so it can dedup / edit / connect to existing data.
// ---------------------------------------------------------------------------

export interface ExistingElement {
  id: string;
  type: EntityKind;
  label: string;
  role: string;
  date: string;
}

export interface ExistingConnectionRef {
  parent_type: EntityKind;
  parent_id: string;
  child_type: EntityKind;
  child_id: string;
}

// ---------------------------------------------------------------------------
// API call
// ---------------------------------------------------------------------------

export async function importExperienceFromText(
  text: string,
  existing: ExistingElement[],
  existingConnections: ExistingConnectionRef[],
): Promise<ExtractionResult> {
  const res = await runnerJSON<{ data: Omit<ExtractionResult, 'warnings'>; warnings: string[] }>(
    '/api/ai/experience-import',
    {
      method: 'POST',
      body: JSON.stringify({ text, existing, existing_connections: existingConnections }),
      errorPrefix: 'AI',
    },
  );
  return {
    jobs: res.data.jobs ?? [],
    projects: res.data.projects ?? [],
    anecdotes: res.data.anecdotes ?? [],
    bullets: res.data.bullets ?? [],
    connections: res.data.connections ?? [],
    warnings: res.warnings ?? [],
  };
}
