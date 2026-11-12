// A grading job's graded row and its rubric review (ROUNDS-00A-L03 PR 3).
//
// While ROUNDS_GATE_EXECUTION_GRADING is on, a grade or a take-home
// submission is a durable job, and the server writes its graded row in
// the transaction that ends it with an authoritative result. The page
// reads that row back as the account: the job's envelope
// (execution_envelopes, which only its own account reads) names the row,
// and the row is the account's own attempt. A page never writes one.
//
// The review route asks the account's AI provider for the rubric review
// of that result, and the server charges it once per result, whoever
// asks. Every answer says where the review stands:
//
//   { job_id, rubric_state, rubric_review, unavailable }
//
// `rubric_review` is the review that call wrote; a review written before
// is in the graded row.

import { pb } from './pocketbase';
import { RunnerError, runnerJSON } from './runnerFetch';

const RECORD_ID = /^[a-z0-9]{15}$/;

export type GradedCollection = 'ai_coding_attempts' | 'take_home_attempts';

export type RubricReview = {
  items: Array<{
    id: string;
    score: number;
    evidence: string;
    suggestions: string[];
    evidence_quotes?: Array<{ file: string; line: number; quote: string }>;
  }>;
  total: number;
  skipped?: boolean;
  reason?: string;
  parse_error?: string;
};

export const RUBRIC_STATES = ['requested', 'completed', 'lost'] as const;
export type RubricState = (typeof RUBRIC_STATES)[number];
export const REVIEW_UNAVAILABLE = ['no_provider', 'not_reviewable', 'files_changed'] as const;
export type ReviewUnavailable = (typeof REVIEW_UNAVAILABLE)[number];

export interface ReviewAnswer {
  job_id: string;
  rubric_state: RubricState | null;
  rubric_review: RubricReview | null;
  unavailable: ReviewUnavailable | null;
}

type EnvelopeRecord = { id: string; job?: string; graded_collection?: string; graded_row?: string };

function status(err: unknown): number | undefined {
  return (err as { status?: number } | null)?.status;
}

/** The account's graded row that grading job `jobId` wrote in
 *  `collection`, or null when it wrote none. */
export async function readGradedRow<T>(jobId: string, collection: GradedCollection): Promise<T | null> {
  if (!RECORD_ID.test(jobId)) return null;
  let envelope: EnvelopeRecord;
  try {
    envelope = await pb
      .collection('execution_envelopes')
      .getFirstListItem<EnvelopeRecord>(`job="${jobId}" && graded_row!=""`, { sort: '-created' });
  } catch (err) {
    if (status(err) === 404) return null;
    throw err;
  }
  const rowId = envelope.graded_row ?? '';
  if (envelope.graded_collection !== collection || !RECORD_ID.test(rowId)) return null;
  return pb.collection(collection).getOne<T>(rowId);
}

/** The job a graded row's envelope was written for, so a row read on its
 *  own can ask for its review; null when there's none. */
export async function envelopeJob(envelopeId: string | null | undefined): Promise<string | null> {
  if (!envelopeId || !RECORD_ID.test(envelopeId)) return null;
  const envelope = await pb.collection('execution_envelopes').getOne<EnvelopeRecord>(envelopeId);
  return typeof envelope.job === 'string' && RECORD_ID.test(envelope.job) ? envelope.job : null;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

/** Where an envelope's review stands: null before anyone asked. */
export function rubricState(envelope: { rubric?: unknown } | null | undefined): RubricState | null {
  const rubric = envelope?.rubric;
  if (!isObject(rubric)) return null;
  return (RUBRIC_STATES as readonly unknown[]).includes(rubric.state) ? (rubric.state as RubricState) : null;
}

function isReview(value: unknown): value is RubricReview {
  return isObject(value) && Array.isArray(value.items) && typeof value.total === 'number';
}

/** Whether a review route's answer is in the shape it answers. */
export function isReviewAnswer(value: unknown): value is ReviewAnswer {
  if (!isObject(value)) return false;
  const { job_id, rubric_state, rubric_review, unavailable } = value;
  return (
    typeof job_id === 'string' &&
    (rubric_state === null || (RUBRIC_STATES as readonly unknown[]).includes(rubric_state)) &&
    (rubric_review === null || isReview(rubric_review)) &&
    (unavailable === null || (REVIEW_UNAVAILABLE as readonly unknown[]).includes(unavailable))
  );
}

/** Asks for the rubric review of grading job `jobId`'s result on `route`
 *  (`/api/ai-coding/grade` or `/api/take-home/submit`), with the files
 *  that were graded: other files are refused as changed. */
export async function requestReview(
  route: string,
  jobId: string,
  files: Record<string, string>,
  idempotencyKey: string,
  signal?: AbortSignal,
): Promise<ReviewAnswer> {
  const answer = await runnerJSON<unknown>(`${route}/${encodeURIComponent(jobId)}/review`, {
    method: 'POST',
    body: { files },
    auth: 'required',
    errorPrefix: 'review',
    idempotencyKey,
    signal,
  });
  if (!isReviewAnswer(answer)) {
    throw new RunnerError({ message: "review 502: The server's answer wasn't a review.", status: 502 });
  }
  return answer;
}
