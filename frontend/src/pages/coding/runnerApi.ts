// Thin client for the FastAPI runner's /api/run and /api/evaluate
// endpoints. Used only by CodingDetail today. The runner owns the
// question's entry and test cases, so a call names the question and
// sends only the code and, for a run, the input.
//
// The shape follows ROUNDS_GATE_EXECUTION_DEFINITIONS (lib/definitions):
// at `enforce` a call names the compiled definition, {track, slug,
// variant, version}, and an evaluate picks cases by their compiled ids;
// otherwise it names the question by slug and language, as #1 does.
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

import { caseIdFor, definitionRef, definitionsEnforced } from '../../lib/definitions';
import { runnerJSON } from '../../lib/runnerFetch';
import type { CodeEvaluateResult, CodeRunResult, EvaluateFilter } from './types';

export interface RunPayload {
  question_slug: string;
  language: string;
  code: string;
  input: Record<string, unknown>;
  /** The question row's definition_version; sent only at enforce. */
  definition_version?: number | null;
}

export interface EvaluatePayload {
  question_slug: string;
  language: string;
  code: string;
  filter?: EvaluateFilter;
  definition_version?: number | null;
  /** The question row's definition_case_ids, in test-case order. */
  definition_case_ids?: string[] | null;
}

/** The body /api/run takes under the current gate value. */
export function runBody(payload: RunPayload): Record<string, unknown> {
  const { question_slug, language, code, input, definition_version } = payload;
  if (!definitionsEnforced()) return { question_slug, language, code, input };
  return { definition: definitionRef('coding', question_slug, language, definition_version), code, input };
}

/** The body /api/evaluate takes under the current gate value. */
export function evaluateBody(payload: EvaluatePayload): Record<string, unknown> {
  const { question_slug, language, code, filter, definition_version, definition_case_ids } = payload;
  if (!definitionsEnforced()) {
    return filter === undefined
      ? { question_slug, language, code }
      : { question_slug, language, code, filter };
  }
  const body: Record<string, unknown> = {
    definition: definitionRef('coding', question_slug, language, definition_version),
    code,
  };
  if (filter?.indices) body.case_ids = filter.indices.map((i) => caseIdFor(i, definition_case_ids));
  if (filter?.tags) body.tags = filter.tags;
  return body;
}

export async function runCode(payload: RunPayload): Promise<CodeRunResult> {
  return runnerJSON<CodeRunResult>('/api/run', {
    method: 'POST',
    body: runBody(payload),
  });
}

export async function evaluateCode(
  payload: EvaluatePayload,
): Promise<CodeEvaluateResult> {
  return runnerJSON<CodeEvaluateResult>('/api/evaluate', {
    method: 'POST',
    body: evaluateBody(payload),
  });
}
