import { slugify } from '../lib/slug';
import type { TimelineEntity } from './experienceApi';

/** Resolve a `?anecdote=` value (id or slugified title) to its entity, or null
 *  (also null for the sentinel "new" and for unknown values). */
export function resolveAnecdoteParam(
  value: string,
  entities: TimelineEntity[],
): TimelineEntity | null {
  if (!value || value === 'new') return null;
  const anecdotes = entities.filter((e) => e.kind === 'anecdote');
  return (
    anecdotes.find((e) => e.id === value) ??
    anecdotes.find((e) => slugify(e.title) === value) ??
    null
  );
}
