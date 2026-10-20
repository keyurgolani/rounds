// Thin client for the FastAPI runner's /api/run and /api/evaluate
// endpoints. Used only by CodingDetail today. The runner loads the
// question's entry and test cases itself, so a call names the
// question by slug and sends only the code and, for a run, the input.
//
// Replaces the legacy `api.post('/api/run', ...)` /
// `api.post('/api/evaluate', ...)` calls that flowed through
// frontend/src/api/client.ts. The PocketBase-collection callers all
// have their own typed modules now; this is the last piece.
//
// Demo limits are the server's: the runner's demo tier answers 429
// `demo_limit_reached`, which the coding page shows as limit reached.
// The SPA no longer writes `demo_run_used` or `demo_evaluate_used`, and
// PocketBase refuses a client write to either (#1 stage 3).

import { runnerJSON } from '../../lib/runnerFetch';
import type { CodeEvaluateResult, CodeRunResult, EvaluateFilter } from './types';

export interface RunPayload {
  question_slug: string;
  language: string;
  code: string;
  input: Record<string, unknown>;
}

export interface EvaluatePayload {
  question_slug: string;
  language: string;
  code: string;
  filter?: EvaluateFilter;
}

export async function runCode(payload: RunPayload): Promise<CodeRunResult> {
  return runnerJSON<CodeRunResult>('/api/run', {
    method: 'POST',
    body: payload,
  });
}

export async function evaluateCode(
  payload: EvaluatePayload,
): Promise<CodeEvaluateResult> {
  return runnerJSON<CodeEvaluateResult>('/api/evaluate', {
    method: 'POST',
    body: payload,
  });
}
