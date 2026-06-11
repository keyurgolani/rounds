import { describe, it, expect } from 'vitest';
import { buildReviewModel, diffFields } from '../importReconcile';
import type { ExtractionResult } from '../importApi';
import type { TimelineEntity } from '../experienceApi';

function emptyResult(partial: Partial<ExtractionResult> = {}): ExtractionResult {
  return { jobs: [], projects: [], anecdotes: [], bullets: [], connections: [], warnings: [], ...partial };
}

const existingJob: TimelineEntity = {
  kind: 'job', id: 'job1', company: 'Acme', role: 'SWE', location: '', employment_type: 'full-time',
  start_date: '2020-01-01', end_date: null, description: 'old desc', tags: ['python'],
};
const existingProject: TimelineEntity = {
  kind: 'project', id: 'proj1', title: 'Platform', company: 'Acme', role: 'Lead', team_size: null,
  tech_stack: [], start_date: '2021-01-01', end_date: null, description: '', tags: [],
};

function byId(...es: TimelineEntity[]): Record<string, TimelineEntity> {
  return Object.fromEntries(es.map((e) => [e.id, e]));
}

describe('buildReviewModel', () => {
  it('marks an item with no existing_id as new', () => {
    const result = emptyResult({
      jobs: [{ existing_id: '', company: 'New Co', role: 'PM', location: '', employment_type: '', start_date: '2023-01-01', end_date: '', description: '', tags: [] }],
    });
    const model = buildReviewModel(result, {}, []);
    expect(model.items).toHaveLength(1);
    expect(model.items[0].mode).toBe('new');
    expect(model.items[0].existingId).toBeUndefined();
  });

  it('marks an item with a known existing_id as edit and attaches the original', () => {
    const result = emptyResult({
      jobs: [{ existing_id: 'job1', company: 'Acme', role: 'Senior SWE', location: '', employment_type: 'full-time', start_date: '2020-01-01', end_date: '', description: 'old desc', tags: ['python'] }],
    });
    const model = buildReviewModel(result, byId(existingJob), []);
    expect(model.items[0].mode).toBe('edit');
    expect(model.items[0].existingId).toBe('job1');
    expect(model.items[0].original?.id).toBe('job1');
  });

  it('creates an existing card for a connection target that is not edited', () => {
    const result = emptyResult({
      jobs: [{ existing_id: '', company: 'New Co', role: '', location: '', employment_type: '', start_date: '2023-01-01', end_date: '', description: '', tags: [] }],
      connections: [{ parent: { type: 'job', index: 0 }, child: { type: 'project', id: 'proj1' } }],
    });
    const model = buildReviewModel(result, byId(existingProject), []);
    const existingCard = model.items.find((i) => i.mode === 'existing');
    expect(existingCard?.existingId).toBe('proj1');
    expect(model.connections).toHaveLength(1);
    expect(model.connections[0].dashed).toBe(true); // touches an existing element
  });

  it('drops a suggested connection that already exists', () => {
    const result = emptyResult({
      jobs: [{ existing_id: 'job1', company: 'Acme', role: 'SWE', location: '', employment_type: 'full-time', start_date: '2020-01-01', end_date: '', description: 'old desc', tags: ['python'] }],
      connections: [{ parent: { type: 'job', id: 'job1' }, child: { type: 'project', id: 'proj1' } }],
    });
    const model = buildReviewModel(result, byId(existingJob, existingProject), [
      { parent_type: 'job', parent_id: 'job1', child_type: 'project', child_id: 'proj1' },
    ]);
    expect(model.connections).toHaveLength(0);
  });

  it('keeps a new->new connection solid', () => {
    const result = emptyResult({
      jobs: [{ existing_id: '', company: 'C', role: '', location: '', employment_type: '', start_date: '2023-01-01', end_date: '', description: '', tags: [] }],
      projects: [{ existing_id: '', title: 'P', company: '', role: '', team_size: null, tech_stack: [], start_date: '2023-02-01', end_date: '', description: '', tags: [] }],
      connections: [{ parent: { type: 'job', index: 0 }, child: { type: 'project', index: 0 } }],
    });
    const model = buildReviewModel(result, {}, []);
    expect(model.connections).toHaveLength(1);
    expect(model.connections[0].dashed).toBe(false);
  });
});

describe('diffFields', () => {
  it('reports changed fields as from -> to', () => {
    const proposed = { existing_id: 'job1', company: 'Acme', role: 'Senior SWE', location: '', employment_type: 'full-time', start_date: '2020-01-01', end_date: '', description: 'old desc', tags: ['python'] };
    const diffs = diffFields(existingJob, proposed, 'job');
    expect(diffs).toEqual([{ field: 'role', from: 'SWE', to: 'Senior SWE' }]);
  });

  it('returns no diffs when nothing changed', () => {
    const proposed = { existing_id: 'proj1', title: 'Platform', company: 'Acme', role: 'Lead', team_size: null, tech_stack: [], start_date: '2021-01-01', end_date: '', description: '', tags: [] };
    expect(diffFields(existingProject, proposed, 'project')).toEqual([]);
  });
});
