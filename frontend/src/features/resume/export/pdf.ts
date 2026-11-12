// PDF export. Two paths:
//
//   `exportPdfServer()` — server PDF (ROUNDS-00A-L04). The browser sends
//     ids, never markup: it asks the runner for a Legacy Artifact Snapshot
//     of the saved resume (`POST /api/pdf/snapshots`, naming the `updated`
//     the save returned), then renders that snapshot by id and checksum
//     (`POST /api/pdf/render`, `render-request/v1`) and downloads the PDF.
//     Each call goes through `runnerFetch` with its own `Idempotency-Key`,
//     which a short-wait retry of that same call reuses; the render's key
//     is also its body's `idempotency_id`. A refusal is a `RunnerError`
//     with the status, `code`, and `Retry-After`; a resume the server
//     can't render safely is a `SnapshotIneligible` with its reason.
//
//   `exportPdfPrint()` — `window.print()`. Works offline, gives the
//     user the standard system print dialog. Acts as a fallback when
//     the renderer service is down.

import { downloadBlob } from './index';
import { mintIdempotencyKey } from '../../../lib/idempotency';
import { runnerFetch, runnerJSON } from '../../../lib/runnerFetch';

/** Why the server builds no snapshot for a resume (the hook's reasons). */
export type IneligibleReason =
  | 'design_out_of_domain'
  | 'data_malformed'
  | 'data_too_large'
  | 'markup_unsafe'
  | 'parent_invalid'
  | 'demo_account';

const REASONS: ReadonlySet<string> = new Set<IneligibleReason>([
  'design_out_of_domain',
  'data_malformed',
  'data_too_large',
  'markup_unsafe',
  'parent_invalid',
  'demo_account',
]);

/** The server won't render this resume until its reason is fixed. */
export class SnapshotIneligible extends Error {
  readonly reason: IneligibleReason | null;

  constructor(reason: unknown) {
    super('Server PDF is not available for this resume.');
    this.name = 'SnapshotIneligible';
    this.reason = typeof reason === 'string' && REASONS.has(reason) ? (reason as IneligibleReason) : null;
  }
}

/** The snapshot step answered in a shape it never sends. */
export class SnapshotAnswerInvalid extends Error {
  constructor() {
    super('The server answered the snapshot request in an unexpected shape.');
    this.name = 'SnapshotAnswerInvalid';
  }
}

export type ServerPdfPhase = 'preparing' | 'rendering';

export type ServerPdfRequest = {
  /** The resume's record id. */
  sourceId: string;
  /** The resume's `updated` as its last save returned it. */
  expectedUpdated: string;
  filenameBase: string;
  /** Called as each step starts, so the page can say what's happening. */
  onPhase?: (phase: ServerPdfPhase) => void;
};

type SnapshotAnswer = {
  status?: unknown;
  snapshot_id?: unknown;
  content_checksum?: unknown;
  reason?: unknown;
};

const SNAPSHOT_ID = /^[a-z0-9]{15}$/;
const CHECKSUM = /^sha256:[0-9a-f]{64}$/;

export async function exportPdfServer({
  sourceId,
  expectedUpdated,
  filenameBase,
  onPhase,
}: ServerPdfRequest): Promise<void> {
  onPhase?.('preparing');
  const made = await runnerJSON<SnapshotAnswer>('/api/pdf/snapshots', {
    method: 'POST',
    body: { source_kind: 'resume', source_id: sourceId, expected_updated: expectedUpdated },
    errorPrefix: 'Server PDF failed',
  });
  if (made?.status === 'ineligible') throw new SnapshotIneligible(made.reason);
  const { snapshot_id: snapshotId, content_checksum: checksum } = made ?? {};
  if (
    (made?.status !== 'created' && made?.status !== 'reused') ||
    typeof snapshotId !== 'string' ||
    !SNAPSHOT_ID.test(snapshotId) ||
    typeof checksum !== 'string' ||
    !CHECKSUM.test(checksum)
  ) {
    throw new SnapshotAnswerInvalid();
  }

  onPhase?.('rendering');
  const key = mintIdempotencyKey();
  const res = await runnerFetch('/api/pdf/render', {
    method: 'POST',
    idempotencyKey: key,
    body: {
      snapshot_id: snapshotId,
      expected_checksum: checksum,
      format: 'pdf',
      page_size: 'A4',
      // The snapshot's own spacing is its margin.
      margin_mm: 0,
      locale: 'en',
      idempotency_id: key,
    },
    errorPrefix: 'PDF render failed',
  });
  const blob = await res.blob();
  downloadBlob(blob, `${filenameBase}.pdf`);
}

export function exportPdfPrint(): void {
  window.print();
}
