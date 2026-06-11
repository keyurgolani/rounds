import { runnerJSON } from '../lib/runnerFetch';
import type { EntityKind } from './experienceApi';

// ---------------------------------------------------------------------------
// Types — match the AI endpoint response
// ---------------------------------------------------------------------------

export interface ExtractedJob {
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
  title: string;
  impact: string;
  category: string;
  date: string;
  tags: string[];
}

export interface ExtractedConnection {
  parent_type: EntityKind;
  parent_index: number;
  child_type: EntityKind;
  child_index: number;
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
// API call
// ---------------------------------------------------------------------------

export async function importExperienceFromText(text: string): Promise<ExtractionResult> {
  const res = await runnerJSON<{ data: Omit<ExtractionResult, 'warnings'>; warnings: string[] }>(
    '/api/ai/experience-import',
    {
      method: 'POST',
      body: JSON.stringify({ text }),
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