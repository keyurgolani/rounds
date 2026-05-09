// Thin wrapper around /api/ai/*. Multi-provider model: the user
// configures one or more `Provider` rows (with their own keys) and
// then assigns one model from any of them to a role — `text` (drives
// import / improve / tailor / ATS) or `vision` (reserved for future
// image-first features). Each call carries the user's PocketBase
// auth token as a Bearer header; the runner validates it on every
// request.

import { runnerJSON, runnerSSE, type RunnerInit } from '../../../lib/runnerFetch';
import type { ResumeData } from '../types';

export type ProviderKind =
  | 'anthropic'
  | 'openai'
  | 'openai-compatible'
  | 'anthropic-compatible';

export type Provider = {
  id: string;
  kind: ProviderKind | string;
  label: string;
  base_url: string;
  has_key: boolean;
  models: string[];
  models_cached_at: string;
};

export type ProviderInput = {
  kind: ProviderKind | string;
  label: string;
  base_url?: string;
  // null = clear an existing key, '' = leave it (only valid on update),
  // any other string = set/replace the key.
  key?: string | null;
};

export type AIRoleSettings = {
  text_provider_id: string | null;
  text_model: string;
  vision_provider_id: string | null;
  vision_model: string;
};

export type ATSErrorKind =
  | 'quota'
  | 'auth'
  | 'rate_limit'
  | 'model_not_found'
  | 'timeout'
  | 'network'
  | 'unconfigured'
  | 'unknown';

export type ATSRuleResponse = {
  rule_score: number;
  breakdown: Record<string, number>;
  suggestions: string[];
  missing_keywords: string[];
};

export type ATSAIResponse = {
  ai_score: number | null;
  ai: null | {
    impact?: number;
    action_verbs?: number;
    clarity?: number;
    semantic?: number;
  };
  ai_status: 'off' | 'unconfigured' | 'error' | 'ok';
  ai_error?: string;
  ai_error_kind?: ATSErrorKind;
  ai_suggestions: string[];
};

function jsonRequest<T>(path: string, init: RunnerInit = {}): Promise<T> {
  return runnerJSON<T>(path, { errorPrefix: 'AI', ...init });
}

// --- providers ----------------------------------------------------------

export function listProviders(): Promise<Provider[]> {
  return jsonRequest<Provider[]>('/api/ai/providers', { method: 'GET' });
}

export function createProvider(input: ProviderInput): Promise<Provider> {
  return jsonRequest<Provider>('/api/ai/providers', {
    method: 'POST',
    body: JSON.stringify(input),
  });
}

export function updateProvider(
  id: string,
  input: ProviderInput,
): Promise<Provider> {
  return jsonRequest<Provider>(`/api/ai/providers/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  });
}

export function deleteProvider(id: string): Promise<{ ok: boolean }> {
  return jsonRequest(`/api/ai/providers/${id}`, { method: 'DELETE' });
}

export function testProvider(
  id: string,
): Promise<{ ok: boolean; model: string; reply: string }> {
  return jsonRequest(`/api/ai/providers/${id}/test`, { method: 'POST', body: '{}' });
}

export function refreshModels(
  id: string,
): Promise<{ models: string[]; models_cached_at: string }> {
  return jsonRequest(`/api/ai/providers/${id}/refresh-models`, {
    method: 'POST',
    body: '{}',
  });
}

// --- role settings ------------------------------------------------------

export function getSettings(): Promise<AIRoleSettings> {
  return jsonRequest<AIRoleSettings>('/api/ai/settings', { method: 'GET' });
}

export function saveSettings(input: AIRoleSettings): Promise<AIRoleSettings> {
  return jsonRequest<AIRoleSettings>('/api/ai/settings', {
    method: 'PUT',
    body: JSON.stringify(input),
  });
}

// --- inference (unchanged surface) --------------------------------------

export function importFromText(text: string): Promise<{ data: ResumeData }> {
  return jsonRequest('/api/ai/import', {
    method: 'POST',
    body: JSON.stringify({ text }),
  });
}

export type TailorInput = {
  data: ResumeData;
  job_description: string;
  tone?: string;
  role_focus?: string[];
  target_company?: string;
  job_title?: string;
};

export function tailorResume(input: TailorInput): Promise<{ data: ResumeData }> {
  return jsonRequest('/api/ai/tailor', {
    method: 'POST',
    body: JSON.stringify({
      data: input.data,
      job_description: input.job_description,
      tone: input.tone ?? 'professional',
      role_focus: input.role_focus ?? [],
      target_company: input.target_company ?? '',
      job_title: input.job_title ?? '',
    }),
  });
}

export function getATSRuleScore(
  data: ResumeData,
  jobDescription: string | undefined,
): Promise<ATSRuleResponse> {
  return jsonRequest('/api/ai/ats-rule', {
    method: 'POST',
    body: JSON.stringify({
      data,
      job_description: jobDescription || null,
      use_ai: false,
    }),
  });
}

export type EnhanceProjectInput = {
  name: string;
  // owner/repo. When present the backend pulls markdown docs from
  // GitHub and runs a per-doc + aggregator agent pipeline; otherwise
  // it falls back to a single-pass enhancement over just the metadata.
  full_name?: string;
  description?: string;
  language?: string | null;
  topics?: string[];
  stargazers?: number;
  url?: string;
  homepage?: string | null;
};

export type EnhancedProject = {
  description: string;
  highlights: string[];
};

export async function enhanceProjects(
  projects: EnhanceProjectInput[],
): Promise<EnhancedProject[]> {
  const res = await jsonRequest<{ projects: EnhancedProject[] }>(
    '/api/ai/enhance-projects',
    {
      method: 'POST',
      body: JSON.stringify({ projects }),
    },
  );
  return res.projects ?? [];
}

export function getATSAIScore(
  data: ResumeData,
  jobDescription: string | undefined,
  useAI: boolean,
): Promise<ATSAIResponse> {
  return jsonRequest('/api/ai/ats-ai', {
    method: 'POST',
    body: JSON.stringify({
      data,
      job_description: jobDescription || null,
      use_ai: useAI,
    }),
  });
}

// --- SSE: improve --------------------------------------------------------

export type ImproveStyle = 'improve' | 'fix' | 'shorten';

export type ImproveContext = {
  position?: string;
  company?: string;
  job_description?: string;
  // Set on Publication summary improves so the backend can fetch
  // the paper text (HTML or PDF) and ground the rewrite in it.
  paper_url?: string;
};

// Snapshot of ATS context an editor wants to forward into a single
// improve call. Static suggestions (rule-derived) are computed
// server-side from `resume`; AI suggestions, when available, are
// passed in here.
export type ImproveATSSnapshot = {
  ai_suggestions?: string[];
  ai_signals?: {
    impact?: number;
    action_verbs?: number;
    clarity?: number;
    semantic?: number;
  };
};

export type ImproveStreamHandlers = {
  onDelta: (chunk: string) => void;
  onDone?: () => void;
  onError?: (err: Error) => void;
  signal?: AbortSignal;
};

export type CoverLetterInput = {
  data: ResumeData;
  job_description: string;
  tone?: string;
  target_company?: string;
  job_title?: string;
};

export function coverLetterStream(
  input: CoverLetterInput,
  handlers: ImproveStreamHandlers,
): Promise<void> {
  return runnerSSE('/api/ai/cover-letter', {
    method: 'POST',
    body: {
      data: input.data,
      job_description: input.job_description,
      tone: input.tone ?? 'professional',
      target_company: input.target_company ?? '',
      job_title: input.job_title ?? '',
    },
    signal: handlers.signal,
    errorPrefix: 'AI',
    onDelta: handlers.onDelta,
    onDone: handlers.onDone,
    onError: handlers.onError,
  });
}

export type ImproveStreamInput = {
  text: string;
  style: ImproveStyle;
  context?: ImproveContext;
  resume?: ResumeData;
  ats?: ImproveATSSnapshot;
  field?: string;
};

export function improveStream(
  input: ImproveStreamInput,
  handlers: ImproveStreamHandlers,
): Promise<void> {
  return runnerSSE('/api/ai/improve', {
    method: 'POST',
    body: {
      text: input.text,
      style: input.style,
      context: input.context,
      resume: input.resume,
      ats: input.ats,
      field: input.field,
    },
    signal: handlers.signal,
    errorPrefix: 'AI',
    onDelta: handlers.onDelta,
    onDone: handlers.onDone,
    onError: handlers.onError,
  });
}
