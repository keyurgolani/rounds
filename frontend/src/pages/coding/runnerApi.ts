// Thin client for the FastAPI runner's /api/run and /api/evaluate
// endpoints. Used only by CodingDetail today.
//
// Replaces the legacy `api.post('/api/run', ...)` /
// `api.post('/api/evaluate', ...)` calls that flowed through
// frontend/src/api/client.ts. The PocketBase-collection callers all
// have their own typed modules now; this is the last piece.
//
// Demo gating: anonymous "demo" accounts are limited to one /run and
// one /evaluate per session. We track that on the user record itself
// (`demo_run_used`, `demo_evaluate_used`) and reject further calls
// client-side. Real users skip the gate entirely.

import { pb } from '../../lib/pocketbase';
import { runnerJSON } from '../../lib/runnerFetch';
import type {
  CodeEvaluateResult,
  CodeRunResult,
  EvaluateFilter,
  Entry,
  TestCase,
} from './types';

interface RunPayload {
  code: string;
  language: string;
  entry: Entry;
  input: Record<string, unknown>;
}

interface EvaluatePayload {
  code: string;
  language: string;
  entry: Entry;
  test_cases: TestCase[];
  filter?: EvaluateFilter;
}

async function consumeDemoAllowance(kind: 'run' | 'evaluate'): Promise<void> {
  const record = pb.authStore.record as
    | (Record<string, unknown> & { id: string })
    | null;
  if (!record || record.is_demo !== true) return;

  const field = kind === 'run' ? 'demo_run_used' : 'demo_evaluate_used';
  const label = kind === 'run' ? 'run a custom snippet' : 'evaluate test cases';
  if (record[field] === true) {
    throw new Error(
      `Demo users can only ${label} once. Log out to reset the demo account.`,
    );
  }

  const updated = await pb.collection('users').update(record.id, { [field]: true });
  pb.authStore.save(pb.authStore.token, updated);
}

export async function runCode(payload: RunPayload): Promise<CodeRunResult> {
  await consumeDemoAllowance('run');
  return runnerJSON<CodeRunResult>('/api/run', {
    method: 'POST',
    body: payload,
    auth: 'optional',
  });
}

export async function evaluateCode(
  payload: EvaluatePayload,
): Promise<CodeEvaluateResult> {
  await consumeDemoAllowance('evaluate');
  return runnerJSON<CodeEvaluateResult>('/api/evaluate', {
    method: 'POST',
    body: payload,
    auth: 'optional',
  });
}
