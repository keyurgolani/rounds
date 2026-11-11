// Thin wrapper around /api/share. Authed endpoints carry a Bearer
// PocketBase token; the by-token public read is anonymous.

import { runnerJSON } from '../../../lib/runnerFetch';
import type { ResumeData, TemplateConfig } from '../types';

export type ShareLink = {
  id: string;
  token: string;
  resume_id: string | null;
  variant_id: string | null;
  created: string;
};

// The only shape a public read answers (backend/routers/share.py,
// project()): no owner name, link kind, ids, or view counts.
export type PublicResumePayload = {
  data: ResumeData;
  template_id: string;
  design: TemplateConfig;
};

export function listShareLinks(): Promise<ShareLink[]> {
  return runnerJSON<ShareLink[]>('/api/share', {
    method: 'GET',
    errorPrefix: 'Share',
  });
}

export function createShareLink(input: {
  resume_id?: string;
  variant_id?: string;
}): Promise<ShareLink> {
  return runnerJSON<ShareLink>('/api/share', {
    method: 'POST',
    body: {
      resume_id: input.resume_id ?? null,
      variant_id: input.variant_id ?? null,
    },
    errorPrefix: 'Share',
  });
}

export function deleteShareLink(id: string): Promise<{ ok: boolean }> {
  return runnerJSON(`/api/share/${id}`, {
    method: 'DELETE',
    errorPrefix: 'Share',
  });
}

export function fetchPublicResume(token: string): Promise<PublicResumePayload> {
  return runnerJSON<PublicResumePayload>(
    `/api/share/by-token/${encodeURIComponent(token)}`,
    { method: 'GET', auth: 'none', errorPrefix: 'Share' },
  );
}

// What the Share Capability resolver answers for a capability that
// resolves (backend/app/share_capabilities.py): its snapshot's markup and
// the projection version, nothing else.
export type SharedArtifact = {
  projection_version: 1;
  markup: string;
};

function isSharedArtifact(value: unknown): value is SharedArtifact {
  if (!value || typeof value !== 'object') return false;
  const v = value as Record<string, unknown>;
  return (
    Object.keys(v).length === 2 &&
    v.projection_version === 1 &&
    typeof v.markup === 'string' &&
    v.markup.length > 0
  );
}

// The token reaches the server only in the request body, and the call
// carries no account token (ROUNDS-00B-L03 stage 2). Every answer but a
// well-formed artifact throws, and callers show only the fixed not-found.
export async function resolveSharedArtifact(token: string): Promise<SharedArtifact> {
  const answer = await runnerJSON<unknown>('/api/share/resolve', {
    method: 'POST',
    auth: 'none',
    body: { token },
    retries: 0,
    errorPrefix: 'Share',
  });
  if (!isSharedArtifact(answer)) throw new Error('Share: not available');
  return { projection_version: 1, markup: answer.markup };
}

export function buildShareUrl(token: string): string {
  return `${window.location.origin}/r/${token}`;
}
