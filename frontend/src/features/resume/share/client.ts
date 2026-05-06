// Thin wrapper around /api/share. Authed endpoints carry a Bearer
// PocketBase token; the by-token public read is anonymous.

import { pb } from '../../../lib/pocketbase';
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

function authHeaders(): HeadersInit {
  const token = pb.authStore.token;
  if (!token) throw new Error('Not authenticated.');
  return { Authorization: `Bearer ${token}` };
}

async function send<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    let detail = text;
    try {
      const j = JSON.parse(text) as { detail?: string };
      if (j.detail) detail = j.detail;
    } catch {
      /* keep raw */
    }
    throw new Error(`Share ${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

export function listShareLinks(): Promise<ShareLink[]> {
  return send<ShareLink[]>('/api/share', {
    method: 'GET',
    headers: authHeaders(),
  });
}

export function createShareLink(input: {
  resume_id?: string;
  variant_id?: string;
}): Promise<ShareLink> {
  return send<ShareLink>('/api/share', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({
      resume_id: input.resume_id ?? null,
      variant_id: input.variant_id ?? null,
    }),
  });
}

export function deleteShareLink(id: string): Promise<{ ok: boolean }> {
  return send(`/api/share/${id}`, { method: 'DELETE', headers: authHeaders() });
}

export function fetchPublicResume(token: string): Promise<PublicResumePayload> {
  // Public — no auth header.
  return send<PublicResumePayload>(`/api/share/by-token/${encodeURIComponent(token)}`, {
    method: 'GET',
  });
}

export function buildShareUrl(token: string): string {
  return `${window.location.origin}/r/${token}`;
}
