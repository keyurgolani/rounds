// Thin wrapper around /api/share. Authed endpoints carry a Bearer
// PocketBase token; the by-token public read is anonymous.
//
// Share capabilities (ROUNDS-00B-L04), while the resolution gate is open:
// CreateShare and RotateShareBearer answer a link's secret once, in the
// response that issues it, and a retry under the same Idempotency-Key
// answers `already-issued` without it. Links are `/r#<token>`, so the
// secret stays out of every request line.

import { isRunnerError, runnerFetch, runnerJSON } from '../../../lib/runnerFetch';
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

// The token, and a password when one is given, reach the server only in
// the request body, and the call carries no account token (ROUNDS-00B-L03
// stage 2). Every answer but a well-formed artifact throws, and callers
// show only the fixed not-found; a 429 throws ShareThrottled, which says
// only how long to wait.
export async function resolveSharedArtifact(token: string, password?: string): Promise<SharedArtifact> {
  let answer: unknown;
  try {
    answer = await runnerJSON<unknown>('/api/share/resolve', {
      method: 'POST',
      auth: 'none',
      body: password === undefined ? { token } : { token, password },
      retries: 0,
      errorPrefix: 'Share',
    });
  } catch (err) {
    if (isRunnerError(err) && err.status === 429) throw new ShareThrottled(err.retryAfterSeconds);
    throw err;
  }
  if (!isSharedArtifact(answer)) throw new Error('Share: not available');
  return { projection_version: 1, markup: answer.markup };
}

/** A resolve the server throttled, whether or not the link is live. */
export class ShareThrottled extends Error {
  /** Whole minutes to wait, at least one. */
  readonly minutes: number;

  constructor(retryAfterSeconds: number | null) {
    super('Share: too many attempts');
    const seconds = retryAfterSeconds !== null && retryAfterSeconds > 0 ? retryAfterSeconds : 60;
    this.minutes = Math.max(1, Math.ceil(seconds / 60));
  }
}

export function buildShareUrl(token: string): string {
  return `${window.location.origin}/r/${token}`;
}

// ---- share capabilities (ROUNDS-00B-L04) ------------------------------------

/** What the owner sees of one link (backend/app/share_capabilities.py
 *  OWNER_FIELDS): never its secret, digest, or password. */
export type ShareCapability = {
  id: string;
  status: 'active' | 'revoked';
  revoked_reason: string;
  purpose: string;
  expires_at: string;
  created: string;
  revoked_at: string;
  capability_version: number;
  password_set: boolean;
};

/** The fields CreateShare and RotateShareBearer answer for the link. */
export type IssuedFields = {
  capability_id: string;
  state: string;
  expires_at: string;
  capability_version: number;
};

export type CreateOutcome =
  | { kind: 'issued'; fields: IssuedFields; token: string }
  | { kind: 'already-issued'; fields: IssuedFields }
  | { kind: 'ineligible'; reason: string };

export type RotateOutcome =
  | { kind: 'issued'; fields: IssuedFields; token: string }
  | { kind: 'already-issued'; fields: IssuedFields };

const RECORD_ID = /^[a-z0-9]{15}$/;
const BEARER = /^sd1_[A-Za-z0-9_-]{22}$/;

function issuedFields(v: Record<string, unknown>): IssuedFields | null {
  if (typeof v.capability_id !== 'string' || !RECORD_ID.test(v.capability_id)) return null;
  if (typeof v.state !== 'string' || typeof v.expires_at !== 'string') return null;
  if (typeof v.capability_version !== 'number' || !Number.isInteger(v.capability_version)) return null;
  return {
    capability_id: v.capability_id,
    state: v.state,
    expires_at: v.expires_at,
    capability_version: v.capability_version,
  };
}

function delivered(answer: unknown): CreateOutcome | null {
  if (!answer || typeof answer !== 'object') return null;
  const v = answer as Record<string, unknown>;
  if (v.status === 'ineligible' && typeof v.reason === 'string') return { kind: 'ineligible', reason: v.reason };
  const fields = issuedFields(v);
  if (fields === null) return null;
  if (v.secret_delivery === 'issued' && typeof v.token === 'string' && BEARER.test(v.token)) {
    return { kind: 'issued', fields, token: v.token };
  }
  if (v.secret_delivery === 'already-issued' && !('token' in v)) return { kind: 'already-issued', fields };
  return null;
}

function isCapability(value: unknown): value is ShareCapability {
  if (!value || typeof value !== 'object') return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.id === 'string' &&
    (v.status === 'active' || v.status === 'revoked') &&
    ['revoked_reason', 'purpose', 'expires_at', 'created', 'revoked_at'].every((k) => typeof v[k] === 'string') &&
    typeof v.capability_version === 'number' &&
    typeof v.password_set === 'boolean'
  );
}

/** The caller's links, newest first. */
export async function listCapabilities(): Promise<ShareCapability[]> {
  const items = await runnerJSON<unknown>('/api/share/capabilities', { method: 'GET', errorPrefix: 'Share' });
  if (!Array.isArray(items) || !items.every(isCapability)) throw new Error('Share: unexpected answer');
  return items;
}

/** CreateShare under `key`, one per create form: a retry of the same form
 *  sends the same key and gets `already-issued`, never the secret again. */
export async function createCapability(
  input: { resume_id: string; expires_at: string | null; password: string | null },
  key: string,
): Promise<CreateOutcome> {
  const body: Record<string, string> = { resume_id: input.resume_id };
  if (input.expires_at !== null) body.expires_at = input.expires_at;
  if (input.password !== null) body.password = input.password;
  const res = await runnerFetch('/api/share', { method: 'POST', body, idempotencyKey: key, errorPrefix: 'Share' });
  const outcome = delivered(await res.json().catch(() => null));
  if (outcome === null) throw new Error('Share: unexpected answer');
  return outcome;
}

/** RotateShareBearer under `key`, one per Rotate click. */
export async function rotateCapability(id: string, expectedVersion: number, key: string): Promise<RotateOutcome> {
  const res = await runnerFetch(`/api/share/capabilities/${encodeURIComponent(id)}/rotate`, {
    method: 'POST',
    body: { expected_capability_version: expectedVersion },
    idempotencyKey: key,
    errorPrefix: 'Share',
  });
  const outcome = delivered(await res.json().catch(() => null));
  if (outcome === null || outcome.kind === 'ineligible' || outcome.fields.capability_id !== id) {
    throw new Error('Share: unexpected answer');
  }
  return outcome;
}

/** #11's revoke: revoking again answers the same. */
export async function revokeCapability(id: string): Promise<ShareCapability> {
  const answer = await runnerJSON<unknown>(`/api/share/capabilities/${encodeURIComponent(id)}/revoke`, {
    method: 'POST',
    errorPrefix: 'Share',
  });
  if (!isCapability(answer)) throw new Error('Share: unexpected answer');
  return answer;
}

/** A share link: the secret rides the fragment, which no request carries. */
export function buildCapabilityUrl(token: string): string {
  return `${window.location.origin}/r#${token}`;
}

/** The `YYYY-MM-DD` day `days` from now, in UTC; the link works through
 *  the end of it. */
export function expiryDay(days: number, now: number = Date.now()): string {
  return new Date(now + days * 86_400_000).toISOString().slice(0, 10);
}

/** PocketBase's datetime text as a Date, or null. */
export function parseShareDate(text: string): Date | null {
  if (!text) return null;
  const at = Date.parse(text.replace(' ', 'T'));
  return Number.isNaN(at) ? null : new Date(at);
}

export type CapabilityState =
  | { kind: 'expires'; at: Date }
  | { kind: 'expired' }
  | { kind: 'revoked'; at: Date | null }
  | { kind: 'source-deleted' };

/** The row's state, worked out from its expires_at, status, revoked_reason,
 *  and revoked_at. Only `expires` links still open. */
export function capabilityState(row: ShareCapability, now: number = Date.now()): CapabilityState {
  if (row.status === 'revoked') {
    return row.revoked_reason === 'source_deleted'
      ? { kind: 'source-deleted' }
      : { kind: 'revoked', at: parseShareDate(row.revoked_at) };
  }
  const at = parseShareDate(row.expires_at);
  if (at === null || at.getTime() <= now) return { kind: 'expired' };
  return { kind: 'expires', at };
}

