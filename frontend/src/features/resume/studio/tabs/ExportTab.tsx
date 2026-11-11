// Export tab. Replaces the prior modal — exports always render the
// current resume, so a tab keeps the live preview visible alongside
// the format picker instead of covering it. One row per format with a
// short label, blurb, and per-action button. Server PDF + browser
// print sit next to each other so a renderer outage never blocks an
// export entirely.
//
// Server PDF (ROUNDS-00A-L04) renders the server's own snapshot of the
// saved resume, never what's on screen: the tab saves pending edits,
// asks for the snapshot, renders it by id, and downloads it. Each step
// and every outcome lands in the row's polite live region as words with
// an icon beside them, so no state rests on color. While server PDF
// can't act for this resume (ineligible, turned off, or at a limit), its
// button keeps keyboard focus, reports itself unavailable through
// aria-disabled, and points at the message. No button is ever
// `disabled` mid-export, so focus stays where the user left it. The six
// other formats export what's on screen whatever server PDF says.

import { useEffect, useId, useRef, useState, type CSSProperties, type ReactNode } from 'react';
import {
  CircleCheck,
  CirclePause,
  CircleSlash,
  Download,
  FileWarning,
  Files,
  LoaderCircle,
  Printer,
  RotateCw,
  SearchX,
  type LucideIcon,
} from 'lucide-react';
import type { Resume, ResumeData } from '../../types';
import {
  exportPdfPrint,
  exportPdfServer,
  SnapshotIneligible,
  type IneligibleReason,
  type ServerPdfPhase,
} from '../../export/pdf';
import { RunnerDenialNotice } from '../../../../components/runner/RunnerDenialNotice';
import { reloadPage } from '../../../../lib/definitions';
import {
  activeTrigger,
  classifyRunnerError,
  type RunnerDenial,
  type RunnerDenialKind,
} from '../../../../lib/runnerDenial';
import { isRunnerError } from '../../../../lib/runnerFetch';
import { exportDocx } from '../../export/docx';
import { exportStandaloneHtml } from '../../export/html';
import { exportMarkdown } from '../../export/markdown';
import { exportText } from '../../export/text';
import { exportJsonResume } from '../../export/jsonResume';

type Props = {
  resume: Resume | null;
  data: ResumeData;
  // Push pending in-flight edits before any export so the rendered
  // copy reflects everything the user has typed. Provided by the
  // host (ResumeStudio) which owns the resume hook: it waits for a save
  // in flight, rejects when a save fails, and resolves with the saved
  // `updated` (useResume's flush, ROUNDS-00A-L04).
  onBeforeExport: () => Promise<string>;
};

type Slot = {
  key: string;
  label: string;
  blurb: string;
  action: 'server-pdf' | 'print' | 'docx' | 'html' | 'markdown' | 'text' | 'json';
  primary?: boolean;
};

const SLOTS: Slot[] = [
  {
    key: 'server-pdf',
    label: 'PDF (high-fidelity)',
    blurb: 'Rendered on the server from your saved resume. The closest match to the preview.',
    action: 'server-pdf',
    primary: true,
  },
  {
    key: 'print',
    label: 'Print to PDF (browser)',
    blurb:
      'Opens the system print dialog. Works offline; appearance varies by browser.',
    action: 'print',
  },
  {
    key: 'docx',
    label: 'Word (.docx)',
    blurb:
      "When a recruiter asks for the Word version. Clean, ATS-parseable, doesn't try to mimic the on-screen typography.",
    action: 'docx',
  },
  {
    key: 'html',
    label: 'Standalone HTML',
    blurb: 'Self-contained .html file. Email-attachable, prints nicely.',
    action: 'html',
  },
  {
    key: 'markdown',
    label: 'Markdown',
    blurb: 'Paste into a GitHub README or a blog post.',
    action: 'markdown',
  },
  {
    key: 'text',
    label: 'Plain text',
    blurb: 'For ATS systems that mangle PDFs. The "always works" companion file.',
    action: 'text',
  },
  {
    key: 'json',
    label: 'JSON Resume',
    blurb:
      'jsonresume.org schema. Portable across dozens of community themes outside Rounds.',
    action: 'json',
  },
];

type Phase = 'saving' | ServerPdfPhase;

// What happened to the last server PDF. `denial` is a runner refusal the
// shared notice explains; the rest are this tab's own.
type Outcome =
  | { kind: 'done' }
  | { kind: 'save_failed' }
  | { kind: 'conflict' }
  | { kind: 'ineligible'; reason: IneligibleReason | null }
  | { kind: 'quota' }
  | { kind: 'gone' }
  | { kind: 'denial'; denial: RunnerDenial };

const PHASE_TEXT: Record<Phase, string> = {
  saving: 'Saving your latest edits…',
  preparing: 'Preparing the server copy…',
  rendering: 'Rendering the PDF…',
};

// Each reason, in the words a user can act on.
const REASON_TEXT: Record<IneligibleReason, string> = {
  design_out_of_domain:
    'One of its design settings, such as a color, font, size, or margin, is outside what the templates render.',
  data_malformed: "Part of its content isn't in a shape the templates can read.",
  data_too_large: "It's too large to prepare on the server.",
  markup_unsafe: "The page the server prepared from it didn't pass the server's safety checks.",
  parent_invalid: 'The resume it comes from is missing.',
  demo_account: "The demo account can't make server PDFs.",
};
const DESIGN_FIX = 'Change that setting back in the Design tab, then try again.';
const OTHER_FORMATS = 'Word, HTML, Markdown, plain text, JSON Resume, and browser print still work.';

// Refusals that leave server PDF off until something changes on the
// server's side, so its button says so instead of inviting a retry.
const BLOCKING_DENIALS = new Set<RunnerDenialKind>(['turned_off', 'limit', 'not_permitted']);
// A refusal that only waits this long or less unblocks by itself.
const MAX_UNBLOCK_WAIT_S = 3600;

function blocks(outcome: Outcome | null): boolean {
  if (outcome === null) return false;
  if (outcome.kind === 'ineligible' || outcome.kind === 'quota') return true;
  return outcome.kind === 'denial' && BLOCKING_DENIALS.has(outcome.denial.kind);
}

// A refusal the shared notice reads as "unavailable, try again".
function unavailable(err: unknown, trigger: HTMLElement | null): RunnerDenial {
  return {
    kind: 'unavailable',
    status: isRunnerError(err) ? err.status : 0,
    code: isRunnerError(err) ? err.code : null,
    retryAfterSeconds: null,
    correlationId: isRunnerError(err) ? err.correlationId : null,
    trigger,
  };
}

function outcomeFor(err: unknown, trigger: HTMLElement | null): Outcome {
  if (err instanceof SnapshotIneligible) return { kind: 'ineligible', reason: err.reason };
  if (isRunnerError(err)) {
    if (err.code === 'snapshot_conflict') return { kind: 'conflict' };
    if (err.code === 'snapshot_quota_exceeded') return { kind: 'quota' };
    if (err.code === 'not_found') return { kind: 'gone' };
    // The saved copy changed mid-export, or this page and the server
    // disagree about the request: a fresh try sorts out either.
    if (err.code === 'checksum_mismatch' || err.code === 'invalid_request') {
      return { kind: 'denial', denial: unavailable(err, trigger) };
    }
  }
  // Anything else unexpected reads as unavailable, never as raw text.
  return { kind: 'denial', denial: classifyRunnerError(err, trigger) ?? unavailable(err, trigger) };
}

export default function ExportTab({ resume, data, onBeforeExport }: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [phase, setPhase] = useState<Phase | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const messageId = useId();
  const savedAt = resume?.updated_at ?? null;
  const lastSavedAt = useRef(savedAt);

  // A newer save can change what the server makes of this resume, so an
  // answer about the old one no longer stands.
  useEffect(() => {
    if (lastSavedAt.current === savedAt) return;
    lastSavedAt.current = savedAt;
    setOutcome((o) =>
      o !== null && ['done', 'save_failed', 'conflict', 'ineligible', 'gone'].includes(o.kind) ? null : o,
    );
  }, [savedAt]);

  // A limit with a known wait lifts by itself.
  useEffect(() => {
    if (outcome?.kind !== 'denial' || outcome.denial.kind !== 'limit') return;
    const wait = outcome.denial.retryAfterSeconds;
    if (wait === null || wait <= 0 || wait > MAX_UNBLOCK_WAIT_S) return;
    const timer = setTimeout(() => setOutcome((o) => (o === outcome ? null : o)), wait * 1000);
    return () => clearTimeout(timer);
  }, [outcome]);

  if (!resume) {
    return (
      <div style={{ fontSize: 12, color: 'var(--text-3)' }}>
        Loading resume…
      </div>
    );
  }

  const filenameBase = (resume.slug || resume.name || 'resume').replace(
    /[^a-z0-9._-]+/gi,
    '-',
  );
  const pdfBlocked = blocks(outcome);

  const runServerPdf = async (trigger: HTMLElement | null) => {
    setOutcome(null);
    setPhase('saving');
    let expectedUpdated: string;
    try {
      expectedUpdated = await onBeforeExport();
    } catch {
      // Server PDF renders what the server holds, so it waits for the
      // save; nothing is asked of the server meanwhile.
      setPhase(null);
      setOutcome({ kind: 'save_failed' });
      return;
    }
    try {
      await exportPdfServer({
        sourceId: resume.id,
        expectedUpdated,
        filenameBase,
        onPhase: setPhase,
      });
      setOutcome({ kind: 'done' });
    } catch (err) {
      setOutcome(outcomeFor(err, trigger));
    } finally {
      setPhase(null);
    }
  };

  const run = async (slot: Slot) => {
    if (busy !== null) return;
    if (slot.action === 'server-pdf' && pdfBlocked) return;
    const trigger = activeTrigger();
    setBusy(slot.key);
    setErrors((e) => {
      const next = { ...e };
      delete next[slot.key];
      return next;
    });
    try {
      if (slot.action === 'server-pdf') {
        await runServerPdf(trigger);
        return;
      }
      // Flush pending edits so the export reflects the latest text. A
      // failed save still exports what's on screen.
      await onBeforeExport().catch(() => undefined);
      switch (slot.action) {
        case 'print':
          exportPdfPrint();
          break;
        case 'docx':
          await exportDocx(data, filenameBase);
          break;
        case 'html':
          if (!exportStandaloneHtml(filenameBase)) {
            throw new Error('No preview is currently rendered.');
          }
          break;
        case 'markdown':
          exportMarkdown(data, filenameBase);
          break;
        case 'text':
          exportText(data, filenameBase);
          break;
        case 'json':
          exportJsonResume(data, filenameBase);
          break;
      }
    } catch (err) {
      setErrors((e) => ({ ...e, [slot.key]: (err as Error).message }));
    } finally {
      setBusy(null);
    }
  };
  const printSlot = SLOTS.find((s) => s.action === 'print');
  const denial = outcome?.kind === 'denial' ? outcome.denial : null;
  const hasMessage = phase !== null || (outcome !== null && outcome.kind !== 'denial') || denial !== null;

  return (
    <div className="flex flex-col gap-1.5">
      {SLOTS.map((s) => {
        const isPdf = s.action === 'server-pdf';
        const unavailableNow = isPdf && pdfBlocked;
        return (
          <div
            key={s.key}
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
              padding: 12,
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              background: s.primary ? 'var(--bg-elev)' : 'transparent',
            }}
          >
            <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', columnGap: 12, rowGap: 8 }}>
              <div style={{ flex: '1 1 12rem', minWidth: 0 }}>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{s.label}</div>
                <div style={{ fontSize: 11.5, color: 'var(--text-3)', lineHeight: 1.45 }}>
                  {s.blurb}
                </div>
                {errors[s.key] && (
                  <div style={{ marginTop: 4, fontSize: 11, color: 'var(--plum)', lineHeight: 1.4 }}>
                    {errors[s.key]}
                  </div>
                )}
              </div>
              <ExportButton
                slot={s}
                working={busy === s.key}
                inert={busy !== null && busy !== s.key}
                unavailable={unavailableNow}
                describedBy={isPdf && hasMessage ? messageId : undefined}
                onClick={() => void run(s)}
              />
            </div>
            {isPdf && (
              <div id={messageId}>
                <ServerPdfStatus
                  phase={phase}
                  outcome={outcome}
                  onReload={reloadPage}
                />
                <RunnerDenialNotice
                  denial={denial}
                  action="pdf"
                  onPrint={printSlot ? () => void run(printSlot) : undefined}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---- the server PDF row's status -------------------------------------------------

function ServerPdfStatus({
  phase,
  outcome,
  onReload,
}: {
  phase: Phase | null;
  outcome: Outcome | null;
  onReload: () => void;
}) {
  let content: ReactNode = null;
  if (phase !== null) {
    content = (
      <StatusLine icon={LoaderCircle} spinning>
        {PHASE_TEXT[phase]}
      </StatusLine>
    );
  } else if (outcome?.kind === 'done') {
    content = (
      <StatusLine icon={CircleCheck} tone="var(--forest)">
        PDF downloaded.
      </StatusLine>
    );
  } else if (outcome?.kind === 'save_failed') {
    content = (
      <Notice icon={CirclePause} title="Waiting on your edits">
        Your latest changes haven&apos;t saved, so server PDF is on hold until they do. {OTHER_FORMATS}
      </Notice>
    );
  } else if (outcome?.kind === 'conflict') {
    content = (
      <Notice
        icon={Files}
        title="Changed somewhere else"
        action={
          <button type="button" onClick={onReload} style={noticeAction}>
            <RotateCw aria-hidden="true" size={13} strokeWidth={1.8} />
            Reload
          </button>
        }
      >
        This resume was edited in another tab or window after this page loaded. Reload to get those
        changes, then download again. Nothing was saved over them.
      </Notice>
    );
  } else if (outcome?.kind === 'ineligible') {
    const why = outcome.reason ? REASON_TEXT[outcome.reason] : "The server can't render it safely.";
    content = (
      <Notice icon={FileWarning} title="No server PDF for this resume">
        {why} {outcome.reason === 'design_out_of_domain' ? `${DESIGN_FIX} ` : ''}
        {OTHER_FORMATS}
      </Notice>
    );
  } else if (outcome?.kind === 'quota') {
    content = (
      <Notice icon={CircleSlash} title="Server copy limit reached">
        This account holds as many server copies of its resumes as it can, so a changed resume can&apos;t
        get a new one. {OTHER_FORMATS}
      </Notice>
    );
  } else if (outcome?.kind === 'gone') {
    content = (
      <Notice icon={SearchX} title="Not on the server">
        The server no longer has this resume, so there&apos;s nothing to render. It may have been deleted
        in another tab.
      </Notice>
    );
  }
  return (
    <div role="status" aria-live="polite" aria-atomic="true" data-testid="server-pdf-status">
      {content}
    </div>
  );
}

function StatusLine({
  icon: Icon,
  tone,
  spinning = false,
  children,
}: {
  icon: LucideIcon;
  tone?: string;
  spinning?: boolean;
  children: ReactNode;
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        fontSize: 12.5,
        lineHeight: 1.45,
        color: 'var(--text-2)',
      }}
    >
      <Icon
        aria-hidden="true"
        size={15}
        strokeWidth={1.8}
        className={spinning ? 'animate-spin motion-reduce:animate-none' : undefined}
        style={{ flexShrink: 0, color: tone }}
      />
      <span>{children}</span>
    </div>
  );
}

// The same notice shape as RunnerDenialNotice: an icon, a written title,
// the explanation, and at most one action.
function Notice({
  icon: Icon,
  title,
  action,
  children,
}: {
  icon: LucideIcon;
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div
      style={{
        display: 'flex',
        gap: 10,
        alignItems: 'flex-start',
        padding: '10px 12px',
        borderRadius: 'var(--radius)',
        background: 'var(--bg-elev)',
        boxShadow: 'inset 0 0 0 1px var(--border-strong)',
        fontSize: 12.5,
        lineHeight: 1.45,
        color: 'var(--text-2)',
      }}
    >
      <Icon aria-hidden="true" size={16} strokeWidth={1.8} style={{ flexShrink: 0, marginTop: 1 }} />
      <div style={{ minWidth: 0, flex: 1 }}>
        <strong style={{ display: 'block', color: 'var(--text)', fontWeight: 600 }}>
          {title}
          {/* Ends the title when a screen reader reads the region in one pass. */}
          <span className="sr-only">. </span>
        </strong>
        <span>{children}</span>
        {action && <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>{action}</div>}
      </div>
    </div>
  );
}

const noticeAction: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 6,
  minHeight: 44,
  padding: '0 14px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'transparent',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
  color: 'var(--text)',
  fontSize: 12.5,
  fontWeight: 500,
};

// ---- the per-format button -------------------------------------------------------

function ExportButton({
  slot,
  working,
  inert,
  unavailable,
  describedBy,
  onClick,
}: {
  slot: Slot;
  working: boolean;
  inert: boolean;
  unavailable: boolean;
  describedBy?: string;
  onClick: () => void;
}) {
  // Never `disabled`: a disabled button drops focus mid-export. A button
  // that can't act now says so with aria-disabled and ignores the click.
  const quiet = working || inert || unavailable;
  const Icon = slot.action === 'print' ? Printer : Download;
  const style: CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    minHeight: 44,
    minWidth: 44,
    padding: '0 14px',
    borderRadius: 'var(--radius)',
    border: 0,
    // The board's primary action shade: the accent a step toward the
    // text color and away from the label's, so the label passes 4.5:1 in
    // the light and dark themes and gains contrast in every other one.
    background: slot.primary ? 'color-mix(in srgb, var(--accent) 86%, var(--text))' : 'transparent',
    color: slot.primary ? 'var(--bg-elev)' : 'var(--text-2)',
    boxShadow: slot.primary ? 'none' : 'inset 0 0 0 1px var(--border-strong)',
    fontSize: 13,
    fontWeight: 600,
    cursor: working ? 'wait' : unavailable || inert ? 'not-allowed' : 'pointer',
    opacity: unavailable ? 0.55 : inert ? 0.7 : 1,
    flexShrink: 0,
  };
  return (
    <button
      type="button"
      onClick={onClick}
      aria-disabled={quiet ? true : undefined}
      aria-busy={working ? true : undefined}
      aria-describedby={describedBy}
      style={style}
    >
      <Icon aria-hidden="true" size={14} strokeWidth={1.8} />
      {working ? 'Working…' : slot.action === 'print' ? 'Print' : 'Download'}
    </button>
  );
}
