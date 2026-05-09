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
  view_count: number;
};

export type PublicResumePayload = {
  data: ResumeData;
  template_id: string;
  design: TemplateConfig;
  name: string;
  kind: 'resume' | 'variant';
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

export function buildShareUrl(token: string): string {
  return `${window.location.origin}/r/${token}`;
}
