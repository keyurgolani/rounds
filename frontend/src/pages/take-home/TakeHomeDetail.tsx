import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Bot,
  ChevronsLeft,
  Clock,
  History,
  MessageSquare,
  Play,
  Send,
} from 'lucide-react';
import ResizeHandle from '../../components/layout/ResizeHandle';
import AppHeader from '../../components/shell/AppHeader';
import BackLink from '../../components/shell/BackLink';
import BlockMarkdown from '../../components/shell/BlockMarkdown';
import DifficultyPill from '../../components/shell/DifficultyPill';
import FloatingPanelTab from '../../components/shell/FloatingPanelTab';
import StatusAction from '../../components/shell/StatusAction';
import SubmissionModal from '../../components/shell/SubmissionModal';
import MultiFileEditor from '../../components/editor/MultiFileEditor';
import TakeHomeChatPanel from '../../components/take-home/TakeHomeChatPanel';
import { useResizableWidth } from '../../hooks/useResizableWidth';
import { NARROW_SCREEN_QUERY, useMediaQuery } from '../../hooks/useMediaQuery';
import { RunDock } from '../coding/RunDock';
import {
  deleteInProgressTakeHomeAttempt,
  getAssignment,
  getGradedTakeHomeAttempt,
  getLatestTakeHomeAttempt,
  requestSubmissionReview,
  runProject,
  submitAttempt,
  upsertInProgressTakeHomeAttempt,
  type HarnessOutput,
  type RunResult,
  type SubmitResponse,
  type TakeHomeAssignment,
  type TakeHomeChatEntry,
} from './takeHomeApi';
import { useTakeHomeDrafts } from '../../hooks/useTakeHomeDrafts';
import { reloadPage, retrySuperseded } from '../../lib/definitions';
import { useEditorFocus } from '../../hooks/useEditorFocus';
import { usePracticeStatus } from '../../hooks/usePracticeStatus';
import { usePersistedState } from '../../hooks/usePersistedState';
import { useCampaign } from '../../campaign/CampaignContext';
import {
  RunnerDenialNotice,
  type RunnerAction,
} from '../../components/runner/RunnerDenialNotice';
import {
  activeTrigger,
  classifyRunnerError,
  gradeFailureText,
  runFailureText,
  type RunnerDenial,
} from '../../lib/runnerDenial';
import { useRunnerJob } from '../../hooks/useRunnerJob';
import { useRubricReview, type ReviewStatus } from '../../hooks/useRubricReview';
import { earnedOutput, isJobAnswer, type JobAnswer } from '../../lib/executionJobs';
import { envelopeJob, rubricState, type RubricReview, type RubricState } from '../../lib/gradedRows';
import { limitTitle, type RunnerJobView } from '../../components/runner/RunnerJobStatus';
import { RunErrorOutput } from '../../components/runner/RunErrorOutput';
import { ReportProblem } from '../../components/runner/ReportProblem';
import { ReviewStatusNote } from '../../components/runner/ReviewStatus';

type SideTab = 'rubric' | 'notes' | 'guidance';

// The report the modal shows: a submission's harness result and its
// review, and for a row the server wrote, the job and envelope its review
// asks by.
type ReportView = {
  harness: HarnessOutput;
  rubric_review: RubricReview | null;
  jobId?: string | null;
  envelope?: string | null;
};

// A report that can't show: what happened, as a fixed sentence.
type ReportTrouble = { title: string; body: string; retry?: () => void };

const REPORT_UNREAD =
  "The submission was graded and saved, but this page couldn't load its report. Try again in a moment.";

// The words a review state's tile shows in place of a score.
const REVIEW_TILE: Partial<Record<ReviewStatus, string>> = {
  reviewing: 'reviewing',
  not_requested: 'not reviewed',
  no_provider: 'no provider',
  files_changed: 'files changed',
  lost: "didn't finish",
  not_reviewable: 'unavailable',
  limit: 'limit reached',
  unavailable: 'unavailable',
};

/** The report's subtitle: the harness score, or the limit that stopped it
 *  (no score), and the review's score or where it stands. */
function reportSubtitle(report: ReportView, review: RubricReview | null): string {
  const harness = report.harness;
  const harnessText =
    harness.score === null
      ? harness.outcome_class === 'resource-limit'
        ? `Harness stopped: ${limitTitle(harness.limit).toLowerCase()}`
        : 'Harness not scored'
      : `Harness ${Math.round(harness.score * 100)}/100`;
  const reviewText =
    review === null ? 'not reviewed' : review.skipped ? 'skipped' : `${Math.round(review.total * 100)}/100`;
  return `${harnessText} · Rubric ${reviewText}`;
}

// A run job's output as the route's in-request body, when the run earned
// its end (ROUNDS-00A-L03). Any other end shows only its own notice.
function runOutput(job: JobAnswer): RunResult | null {
  const out = earnedOutput(job);
  return out && typeof out.score === 'number' && Array.isArray(out.criteria)
    ? (out as unknown as RunResult)
    : null;
}

const SIDE_TABS: ReadonlyArray<{ key: SideTab; label: string }> = [
  { key: 'rubric', label: 'Rubric' },
  { key: 'notes', label: 'Notes' },
  { key: 'guidance', label: 'Guidance' },
];

const AI_POLICY_LABEL: Record<TakeHomeAssignment['ai_policy'], string> = {
  off: 'no AI',
  on: 'AI required',
  'candidate-choice': 'AI optional',
};

const FOCUS_KEY = 'rounds:editor-focus.take-home';
const SIDE_RAIL_KEY = 'rounds.takeHome.sideWidth';
const CHAT_RAIL_KEY = 'rounds.takeHome.chatWidth';
const SIDE_RAIL_DEFAULT = 340;
const CHAT_RAIL_DEFAULT = 360;
const RAIL_MIN = 240;
const RAIL_MAX = 560;

function formatBudget(min: number): string {
  if (min < 60) return `${min}m`;
  const hrs = Math.floor(min / 60);
  const rem = min % 60;
  return rem === 0 ? `${hrs}h` : `${hrs}h ${rem}m`;
}

export default function TakeHomeDetail() {
  const { slug = '' } = useParams<{ slug: string }>();
  const { currentId: campaignId } = useCampaign();
  const [assignment, setAssignment] = useState<TakeHomeAssignment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activePath, setActivePath] = useState<string>('');
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  // A run that failed without a result: its error, never a fake score.
  const [runError, setRunError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [report, setReport] = useState<ReportView | null>(null);
  const [reportTrouble, setReportTrouble] = useState<ReportTrouble | null>(null);
  const [reportOpen, setReportOpen] = useState(false);
  // Which action's job the runner notice shows: the one last started, or
  // a submission the tab picked back up.
  const [jobShown, setJobShown] = useState<'run' | 'submit' | null>(null);
  const [chatLog, setChatLog] = useState<TakeHomeChatEntry[]>([]);
  const [notes, setNotes] = useState('');
  const [aiEnabled, setAiEnabled] = usePersistedState<boolean>(
    'rounds.takeHome.aiEnabled',
    false,
  );
  const [chatOpen, setChatOpen] = usePersistedState<boolean>(
    'rounds.takeHome.chatOpen',
    true,
  );
  const [sideTab, setSideTab] = usePersistedState<SideTab>(
    'rounds.takeHome.sideTab',
    'rubric',
  );
  const [filesCollapsed, setFilesCollapsed] = usePersistedState<boolean>(
    'rounds.takeHome.filesCollapsed',
    false,
  );
  const [dockOpen, setDockOpen] = useState(false);
  // On a phone the side rail leaves the center column too narrow for the
  // runner notice, so the notice takes the page's full width below it.
  const narrow = useMediaQuery(NARROW_SCREEN_QUERY);
  // A run or submission the runner refused or couldn't serve. Shown
  // above the console in place of a result or report.
  const [runDenial, setRunDenial] = useState<{
    action: RunnerAction;
    denial: RunnerDenial;
  } | null>(null);
  const [virtualFolders, setVirtualFolders] = useState<string[]>([]);
  const [chatResetVersion, setChatResetVersion] = useState(0);
  const { focus, toggle: toggleFocus } = useEditorFocus(FOCUS_KEY);
  const startedAtRef = useRef(Date.now());
  const runReqIdRef = useRef(0);
  const [, setPracticeStatus] = usePracticeStatus('take-home', slug);
  // The submission's review (ROUNDS-00A-L03 PR 3), asked once per graded
  // result with the files this page sent.
  const gradedRef = useRef<{ jobId: string; files: Record<string, string> } | null>(null);
  const review = useRubricReview(
    (jobId, sent, key, signal) => requestSubmissionReview(jobId, sent, key, signal),
    async (jobId) => (await getGradedTakeHomeAttempt(jobId))?.rubric_review ?? null,
  );
  const { ask: askReview, show: showReview, reset: resetReview, retry: retryReview } = review;

  useEffect(() => {
    let cancelled = false;
    setAssignment(null);
    setError(null);
    setRunResult(null);
    setRunError(null);
    setReport(null);
    setReportTrouble(null);
    setReportOpen(false);
    setChatLog([]);
    setNotes('');
    setDockOpen(false);
    setRunDenial(null);
    setJobShown(null);
    resetReview();
    gradedRef.current = null;
    startedAtRef.current = Date.now();
    getAssignment(slug)
      .then(async (a) => {
        if (cancelled) return;
        setAssignment(a);
        // Rehydrate persisted chat log + most recent submission so a
        // refresh doesn't lose the conversation or the last report.
        try {
          const latest = await getLatestTakeHomeAttempt(
            a.id,
            campaignId ?? undefined,
          );
          if (cancelled || !latest) return;
          if (latest.ai_chats?.length) setChatLog(latest.ai_chats);
          // A row the server wrote has no review until one finishes.
          if (latest.status === 'graded' && latest.harness_output && (latest.rubric_review || latest.envelope)) {
            setReport({
              harness: latest.harness_output,
              rubric_review: latest.rubric_review ?? null,
              envelope: latest.envelope || null,
            });
            // Asks only when the candidate does: only they know the
            // files are the ones submitted.
            if (latest.rubric_review) showReview(latest.rubric_review);
            else showReview(null, 'not_requested');
          }
        } catch {
          /* best-effort */
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [slug, campaignId, resetReview, showReview]);

  // Persist chat log to PocketBase (debounced) so a refresh doesn't
  // discard the conversation. Mirrors the same pattern in AICodingDetail.
  const lastSavedChatRef = useRef<string>('[]');
  useEffect(() => {
    if (!assignment) return;
    const serialised = JSON.stringify(chatLog);
    if (serialised === lastSavedChatRef.current) return;
    if (chatLog.length === 0) return;
    const timer = window.setTimeout(() => {
      upsertInProgressTakeHomeAttempt({
        assignmentId: assignment.id,
        campaignId: campaignId ?? undefined,
        chats: chatLog,
      })
        .then(() => {
          lastSavedChatRef.current = serialised;
        })
        .catch(() => {
          /* best-effort */
        });
    }, 600);
    return () => window.clearTimeout(timer);
  }, [chatLog, assignment, campaignId]);

  const { files, savedFiles, setFile, hydrated, resetToStarter, saveNow } =
    useTakeHomeDrafts(assignment, campaignId ?? undefined);

  // The definition version runs and submits name: the row's, until a
  // superseded answer rereads it (ROUNDS-00A-L02).
  const definitionVersionRef = useRef<number | null | undefined>(undefined);
  useEffect(() => {
    definitionVersionRef.current = assignment?.definition_version;
  }, [assignment]);
  const rereadDefinitionVersion = useCallback(async () => {
    const fresh = await getAssignment(slug);
    definitionVersionRef.current = fresh.definition_version;
    return fresh.definition_version;
  }, [slug]);

  // While ROUNDS_GATE_EXECUTION_SCRATCH is on, a run is a durable job
  // (ROUNDS-00A-L03); its end shows the result.
  const jobTriggerRef = useRef<HTMLElement | null>(null);
  const runJob = useRunnerJob(assignment ? `take-home:${assignment.slug}:${assignment.language}:run` : null, {
    onEnded: (job) => {
      const out = runOutput(job);
      if (!out) return;
      setRunResult(out);
      setDockOpen(true);
    },
    onDenied: (err) => {
      const denial = classifyRunnerError(err, jobTriggerRef.current);
      if (denial) setRunDenial({ action: 'run', denial });
    },
  });
  // While ROUNDS_GATE_EXECUTION_GRADING is on, a submission is a durable
  // job too (ROUNDS-00A-L03 PR 3). An authoritative end has a graded row
  // the server wrote, and the report opens from it.
  const submitTriggerRef = useRef<HTMLElement | null>(null);
  const submitJob = useRunnerJob(
    assignment ? `take-home:${assignment.slug}:${assignment.language}:${campaignId ?? ''}:submit` : null,
    {
      onEnded: (job) => void openGraded(job),
      onDenied: (err) => {
        const denial = classifyRunnerError(err, submitTriggerRef.current);
        if (denial) setRunDenial({ action: 'submit', denial });
      },
    },
  );
  const busy = running || runJob.active;
  const grading = submitting || submitJob.active;
  const jobView: RunnerJobView = {
    job: runJob.job,
    gone: runJob.gone,
    reconnecting: runJob.reconnecting,
    runningSince: runJob.runningSince,
    action: 'run',
    onCancel: () => void runJob.cancel(),
    // None while a retry is on its way, so one press sends one.
    onRetry: busy || grading ? undefined : () => void handleRun(true),
    trigger: jobTriggerRef.current,
  };
  const submitView: RunnerJobView = {
    job: submitJob.job,
    gone: submitJob.gone,
    reconnecting: submitJob.reconnecting,
    runningSince: submitJob.runningSince,
    action: 'submit',
    onCancel: () => void submitJob.cancel(),
    onRetry: busy || grading ? undefined : () => void handleSubmit(true),
    trigger: submitTriggerRef.current,
  };
  const shownJob = jobShown ?? (submitJob.job !== null || submitJob.gone ? 'submit' : 'run');

  // A reload the denial asks for saves the files first. When a save
  // fails the page stays, so nothing is lost, and the notice says the
  // draft wasn't saved and keeps Reload for another try.
  async function reloadKeepingDrafts() {
    let saved = false;
    try {
      saved = (await saveNow()) !== false;
    } catch {
      saved = false;
    }
    if (saved) {
      reloadPage();
      return;
    }
    setRunDenial((current) =>
      current ? { ...current, denial: { ...current.denial, saveFailed: true } } : current,
    );
  }

  const showChat =
    assignment != null &&
    (assignment.ai_policy === 'on' ||
      (assignment.ai_policy === 'candidate-choice' && aiEnabled));

  useEffect(() => {
    if (!hydrated) return;
    if (activePath && files[activePath] !== undefined) return;
    const first = Object.keys(files).sort()[0];
    if (first) setActivePath(first);
  }, [hydrated, files, activePath]);

  async function handleRun(retry = false) {
    if (!assignment) return;
    const trigger = activeTrigger();
    jobTriggerRef.current = trigger;
    const reqId = ++runReqIdRef.current;
    setJobShown('run');
    setRunning(true);
    setRunResult(null);
    setRunError(null);
    setRunDenial(null);
    setDockOpen(true);
    try {
      const r = await retrySuperseded(
        definitionVersionRef.current,
        (version) => {
          const definition = { language: assignment.language, definition_version: version };
          const key = runJob.begin({ slug: assignment.slug, files, definition }, retry);
          return runProject(assignment.slug, files, definition, { idempotencyKey: key });
        },
        rereadDefinitionVersion,
      );
      if (reqId !== runReqIdRef.current) return;
      // A job: the notice follows it, and its end shows the result.
      if (runJob.follow(r)) {
        setDockOpen(false);
        return;
      }
      setRunResult(r as RunResult);
    } catch (e) {
      if (reqId !== runReqIdRef.current) return;
      const denial = classifyRunnerError(e, trigger);
      if (denial) {
        // Nothing ran, so there's no harness score or output to show.
        setRunDenial({ action: 'run', denial });
        setDockOpen(false);
        return;
      }
      // Nothing came back to score, so no score shows: only the error, as
      // a fixed sentence, never the server's own text.
      setRunError(runFailureText(e));
    } finally {
      if (reqId === runReqIdRef.current) setRunning(false);
    }
  }

  async function handleSubmit(retry = false) {
    if (!assignment) return;
    const trigger = activeTrigger();
    submitTriggerRef.current = trigger;
    setJobShown('submit');
    setSubmitting(true);
    setReport(null);
    setReportTrouble(null);
    setRunDenial(null);
    resetReview();
    // What this submission sends, which its review sends again.
    const sent = files;
    try {
      const answer = await retrySuperseded(
        definitionVersionRef.current,
        (version) => {
          const work = {
            assignment_slug: assignment.slug,
            files: sent,
            notes,
            ai_chats: chatLog,
            campaign_id: campaignId ?? undefined,
            language: assignment.language,
            definition_version: version,
          };
          // The session time isn't part of the work, so a retry of the
          // same files, notes, and chats stays the same command.
          return submitAttempt(
            { ...work, duration_ms: Date.now() - startedAtRef.current },
            { idempotencyKey: submitJob.begin(work, retry) },
          );
        },
        rereadDefinitionVersion,
      );
      // A job: the notice follows it, and an authoritative end opens the
      // report from the row the server wrote.
      if (isJobAnswer(answer)) gradedRef.current = { jobId: answer.job_id, files: sent };
      if (submitJob.follow(answer)) return;
      // TODO(ROUNDS-00A-L03): PR 4 retires the in-request submission.
      const result = answer as SubmitResponse;
      setReport({ harness: result.harness, rubric_review: result.rubric_review });
      showReview(result.rubric_review);
      setReportOpen(true);
      if (
        result.harness.criteria.length > 0 &&
        result.harness.criteria.every((c) => c.passed)
      ) {
        setPracticeStatus('mastered');
      }
    } catch (e) {
      // A denied submission isn't graded, so no report opens.
      const denial = classifyRunnerError(e, trigger);
      if (denial) {
        setRunDenial({ action: 'submit', denial });
        return;
      }
      // Nothing came back to grade, so no report or score shows: only
      // what happened, as a fixed sentence, never the server's own text.
      setReportTrouble({ title: "Grading didn't finish", body: gradeFailureText(e) });
      setReportOpen(true);
    } finally {
      setSubmitting(false);
    }
  }

  // A submission job ended. Only an end the candidate's code earned, or a
  // limit it reached, has a graded row; every other end shows its notice.
  async function openGraded(job: JobAnswer) {
    const envelope = job.envelope;
    if (envelope === null || !envelope.authoritative || job.outcome_class !== envelope.outcome_class) return;
    // Mastered only when every criterion passed, which is what a passed
    // envelope means.
    if (envelope.outcome_class === 'passed') setPracticeStatus('mastered');
    const sent = gradedRef.current?.jobId === job.job_id ? gradedRef.current.files : null;
    await loadGraded(job.job_id, sent, rubricState(envelope));
  }

  async function loadGraded(jobId: string, sent: Record<string, string> | null, state: RubricState | null) {
    setReportTrouble(null);
    let row: Awaited<ReturnType<typeof getGradedTakeHomeAttempt>> = null;
    try {
      row = await getGradedTakeHomeAttempt(jobId);
    } catch {
      row = null;
    }
    if (row === null || !row.harness_output) {
      setReport(null);
      setReportTrouble({
        title: "Couldn't load the report",
        body: REPORT_UNREAD,
        retry: () => void loadGraded(jobId, sent, state),
      });
      setReportOpen(true);
      return;
    }
    setReport({
      harness: row.harness_output,
      rubric_review: row.rubric_review ?? null,
      jobId,
      envelope: row.envelope || null,
    });
    setReportOpen(true);
    if (row.rubric_review) showReview(row.rubric_review);
    else if (state === 'lost') showReview(null, 'lost');
    // Asked once, with the files this page sent; a submission the tab
    // picked back up asks when the candidate does.
    else if (sent !== null) askReview(jobId, sent);
    else showReview(null, 'not_requested');
  }

  // Asks for the review of the report on show, by its job: the one this
  // page followed, or the one its row's envelope names.
  async function requestReview() {
    const shown = report;
    if (shown === null) return;
    let jobId = shown.jobId ?? null;
    if (jobId === null) {
      try {
        jobId = await envelopeJob(shown.envelope);
      } catch {
        jobId = null;
      }
    }
    if (jobId === null) {
      showReview(null, 'unavailable');
      return;
    }
    const sent = gradedRef.current?.jobId === jobId ? gradedRef.current.files : files;
    askReview(jobId, sent);
  }

  return (
    <div className="h-full flex flex-col min-h-0 relative">
      <AppHeader
        eyebrow={
          <span
            style={{
              display: 'inline-flex',
              gap: 8,
              alignItems: 'center',
              flexWrap: 'wrap',
            }}
          >
            <BackLink to="/take-home" label="Back to practice" />
            {assignment && <DifficultyPill level={assignment.difficulty} />}
            {assignment && (
              <span
                className="pill"
                style={{
                  background: 'transparent',
                  color: 'var(--text-3)',
                  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                }}
              >
                {assignment.language}
              </span>
            )}
            {assignment && (
              <span
                className="pill inline-flex items-center gap-1"
                style={{
                  background: 'var(--accent-soft)',
                  color: 'var(--accent)',
                }}
              >
                <Clock size={11} strokeWidth={2} />
                {formatBudget(assignment.time_budget_min)}
              </span>
            )}
            {assignment && (
              <span
                className="pill inline-flex items-center gap-1"
                style={{
                  background: 'transparent',
                  color: 'var(--text-3)',
                  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                }}
              >
                <Bot size={11} strokeWidth={2} />
                {AI_POLICY_LABEL[assignment.ai_policy]}
              </span>
            )}
          </span>
        }
        title={assignment?.title ?? 'Real World Problem'}
        description={
          assignment?.prompt_md ? toLeadSummary(assignment.prompt_md) : undefined
        }
        chromeActions={<StatusAction kind="take-home" id={slug} />}
        compactActions={<StatusAction kind="take-home" id={slug} compact />}
        timer={slug ? { kind: 'take-home', id: slug } : undefined}
      />

      {error && (
        <div className="p-4" style={{ color: 'var(--danger)' }}>
          Couldn't load problem: {error}
        </div>
      )}
      {!error && !assignment && (
        <div className="p-4 text-3 text-sm">Loading problem…</div>
      )}

      {assignment && (() => {
        const floatingTabs: Array<{ key: string; label: string; onClick: () => void }> = [];
        if (filesCollapsed) {
          floatingTabs.push({
            key: 'files',
            label: 'Files',
            onClick: () => setFilesCollapsed(false),
          });
        }
        // Chat now toggles via the editor's floating toolbar button —
        // no longer surfaced as a left-edge floating tab.

        // One live region for the page: in the center column, or on a
        // phone at full width below the body, where its buttons are 44 px
        // touch targets.
        const runnerNotice = (
          <RunnerDenialNotice
            denial={runDenial?.denial ?? null}
            action={runDenial?.action ?? 'run'}
            onReload={reloadKeepingDrafts}
            className="flex-shrink-0"
            contentStyle={{ margin: '8px 12px' }}
            job={shownJob === 'submit' ? submitView : jobView}
            actionMinHeight={narrow ? 44 : undefined}
          />
        );

        return (
        <>
        <div
          className="flex-1 min-h-0 flex overflow-hidden"
          style={{ minHeight: 0, position: 'relative' }}
        >
          {floatingTabs.length > 0 && <FloatingPanelTab tabs={floatingTabs} />}

          {/* CENTER — problem above editor (hidden in focus), editor with floating actions, console below. */}
          <div
            data-take-home-pane="center"
            className="flex-1 flex flex-col"
            style={{ minWidth: 0, minHeight: 0 }}
          >
            {!focus && (
              <ProblemBar
                prompt={assignment.prompt_md}
                topics={assignment.topics ?? []}
                companies={assignment.companies ?? []}
              />
            )}

            <div style={{ flex: 1, minHeight: 0 }}>
              {hydrated && activePath && (
                <MultiFileEditor
                  files={files}
                  savedFiles={savedFiles}
                  activePath={activePath}
                  onActivePathChange={setActivePath}
                  onFileChange={setFile}
                  virtualFolders={virtualFolders}
                  onCreateFile={(p) => {
                    if (files[p] !== undefined) return;
                    setFile(p, '');
                  }}
                  onCreateFolder={(p) => {
                    setVirtualFolders((prev) =>
                      prev.includes(p) ? prev : [...prev, p],
                    );
                  }}
                  explorerCollapsed={filesCollapsed}
                  onToggleExplorer={() => setFilesCollapsed(!filesCollapsed)}
                  onResetFiles={() => {
                    resetToStarter();
                    setVirtualFolders([]);
                    setChatLog([]);
                    setChatResetVersion((v) => v + 1);
                    lastSavedChatRef.current = '[]';
                    if (assignment) {
                      deleteInProgressTakeHomeAttempt(
                        assignment.id,
                        campaignId ?? undefined,
                      ).catch(() => {
                        /* best-effort */
                      });
                    }
                  }}
                  storageKey="rounds:editor.explorer.take-home"
                  focused={focus}
                  onFocusToggle={toggleFocus}
                  aiChatOpen={showChat && chatOpen}
                  onToggleAiChat={
                    showChat ? () => setChatOpen(!chatOpen) : undefined
                  }
                  aiChat={
                    showChat ? (
                      <TakeHomeChatPanel
                        key={`${assignment.id}:${chatResetVersion}`}
                        assignmentSlug={assignment.slug}
                        files={files}
                        disabled={!hydrated}
                        initialMessages={chatLog
                          .filter(
                            (c) => c.role === 'user' || c.role === 'assistant',
                          )
                          .map((c) => ({
                            role: c.role as 'user' | 'assistant',
                            content: c.content,
                          }))}
                        onMessageRecorded={(m) =>
                          setChatLog((log) => [
                            ...log,
                            {
                              checkpoint: 0,
                              role: m.role,
                              content: m.content,
                              ts: Date.now(),
                            },
                          ])
                        }
                      />
                    ) : undefined
                  }
                  bottomActions={
                    <EditorActions
                      onRun={() => void handleRun()}
                      onSubmit={() => void handleSubmit()}
                      onOpenLast={() => setReportOpen(true)}
                      running={busy}
                      submitting={grading}
                      hasReport={Boolean(report)}
                      runResult={runResult}
                    />
                  }
                />
              )}
            </div>

            {!narrow && runnerNotice}

            <RunDock
              open={dockOpen}
              onOpenChange={setDockOpen}
              hasOutput={Boolean(runResult) || runError !== null}
              rightActions={
                runResult && !runResult.error ? (
                  <span
                    className="mono"
                    style={{
                      fontSize: 10.5,
                      color: 'var(--text-2)',
                      letterSpacing: '0.08em',
                    }}
                  >
                    HARNESS · {Math.round(runResult.score * 100)}/100 ·{' '}
                    {runResult.duration_ms}MS
                  </span>
                ) : runResult?.error || runError !== null ? (
                  <span
                    className="mono"
                    style={{
                      fontSize: 10.5,
                      color: 'var(--plum)',
                      letterSpacing: '0.08em',
                    }}
                  >
                    HARNESS ERROR
                  </span>
                ) : null
              }
            >
              {runResult ? (
                <RunOutput result={runResult} />
              ) : runError !== null ? (
                <RunErrorOutput message={runError} />
              ) : null}
            </RunDock>
          </div>

          {/* RIGHT RAIL — tabbed details. Hidden in focus mode. */}
          {!focus && (
            <SideRail
              tabs={SIDE_TABS}
              activeTab={sideTab}
              onTabChange={setSideTab}
            >
              {sideTab === 'rubric' && <RubricPanel assignment={assignment} />}
              {sideTab === 'notes' && (
                <NotesPanel notes={notes} onNotesChange={setNotes} />
              )}
              {sideTab === 'guidance' && (
                <GuidancePanel
                  assignment={assignment}
                  aiEnabled={aiEnabled}
                  onAiEnabledChange={setAiEnabled}
                />
              )}
            </SideRail>
          )}
        </div>
        {narrow && (
          <div data-take-home-pane="notice" className="flex-shrink-0">
            {runnerNotice}
          </div>
        )}
        </>
        );
      })()}

      <SubmissionModal
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        title={`Submission · ${assignment?.title ?? 'Real World Problem'}`}
        subtitle={
          reportTrouble === null && report ? reportSubtitle(report, review.review ?? report.rubric_review) : undefined
        }
      >
        {reportTrouble !== null ? (
          <ReportProblem title={reportTrouble.title} body={reportTrouble.body} onRetry={reportTrouble.retry} />
        ) : (
          report && (
            <ReportPanel
              harness={report.harness}
              review={review.review ?? report.rubric_review}
              reviewStatus={review.status}
              retryAfterSeconds={review.retryAfterSeconds}
              onRetryReview={() => {
                if (!retryReview()) void requestReview();
              }}
              onRequestReview={() => void requestReview()}
            />
          )
        )}
      </SubmissionModal>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Helpers + local subcomponents.
// ---------------------------------------------------------------------------

function toLeadSummary(desc: string): string {
  const stripped = desc
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`[^`]*`/g, '')
    .replace(/^#+\s+.*$/gm, '')
    .replace(/[*_>~]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  const sentenceMatch = stripped.match(/^(.{20,180}?[.!?])\s/);
  if (sentenceMatch) return sentenceMatch[1];
  return stripped.length > 180 ? stripped.slice(0, 177).trimEnd() + '…' : stripped;
}

function ProblemBar({
  prompt,
  topics,
  companies,
}: {
  prompt: string;
  topics: string[];
  companies: string[];
}) {
  return (
    <div
      style={{
        flexShrink: 0,
        background: 'var(--bg)',
        borderBottom: '1px solid var(--border)',
        maxHeight: '20vh',
        overflow: 'auto',
      }}
    >
      <div
        className="flex items-center"
        style={{
          padding: '8px 16px 4px',
          gap: 10,
          minHeight: 28,
        }}
      >
        <span
          className="eyebrow"
          style={{ color: 'var(--text-3)', flexShrink: 0 }}
        >
          The brief
        </span>
      </div>
      <div
        style={{
          padding: '4px 16px 14px',
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        <div
          style={{
            fontSize: 13.5,
            color: 'var(--text-2)',
            lineHeight: 1.6,
          }}
        >
          <BlockMarkdown text={prompt} />
        </div>
        {(topics.length > 0 || companies.length > 0) && (
          <div className="flex flex-wrap gap-1.5">
            {topics.map((t) => (
              <span
                key={`t-${t}`}
                className="pill"
                style={{
                  background: 'transparent',
                  color: 'var(--text-3)',
                  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                }}
              >
                {t}
              </span>
            ))}
            {companies.map((c) => (
              <span
                key={`c-${c}`}
                className="pill"
                style={{
                  background: 'transparent',
                  color: 'var(--text-4)',
                  boxShadow: 'inset 0 0 0 1px var(--border)',
                  letterSpacing: '0.04em',
                }}
              >
                {c}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ChatRail({
  onToggle,
  children,
}: {
  onToggle: () => void;
  children: React.ReactNode;
}) {
  const { width, onResizeStart } = useResizableWidth({
    storageKey: CHAT_RAIL_KEY,
    defaultWidth: CHAT_RAIL_DEFAULT,
    min: RAIL_MIN,
    max: RAIL_MAX,
    edge: 'right',
  });
  return (
    <aside
      style={{
        width,
        flexShrink: 0,
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        position: 'relative',
        transition: 'width 160ms cubic-bezier(0.22, 0.8, 0.36, 1)',
      }}
    >
      <div
        className="flex items-center"
        style={{
          padding: '6px 10px',
          height: 36,
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg-elev)',
          flexShrink: 0,
          gap: 6,
        }}
      >
        <MessageSquare
          size={12}
          strokeWidth={2}
          style={{ color: 'var(--text-3)' }}
        />
        <span className="eyebrow" style={{ color: 'var(--text-3)' }}>
          AI Chat
        </span>
        <button
          type="button"
          onClick={onToggle}
          aria-label="Collapse AI chat"
          title="Collapse"
          style={{
            marginLeft: 'auto',
            width: 24,
            height: 24,
            border: 0,
            borderRadius: 6,
            background: 'transparent',
            color: 'var(--text-3)',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <ChevronsLeft size={14} strokeWidth={2} />
        </button>
      </div>
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {children}
      </div>
      <ResizeHandle onMouseDown={onResizeStart} edge="right" />
    </aside>
  );
}

function SideRail({
  tabs,
  activeTab,
  onTabChange,
  children,
}: {
  tabs: ReadonlyArray<{ key: SideTab; label: string }>;
  activeTab: SideTab;
  onTabChange: (k: SideTab) => void;
  children: React.ReactNode;
}) {
  const { width, onResizeStart } = useResizableWidth({
    storageKey: SIDE_RAIL_KEY,
    defaultWidth: SIDE_RAIL_DEFAULT,
    min: RAIL_MIN,
    max: RAIL_MAX,
    edge: 'left',
  });
  return (
    <aside
      style={{
        width,
        flexShrink: 0,
        borderLeft: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        minHeight: 0,
        background: 'var(--bg)',
        position: 'relative',
        transition: 'width 160ms cubic-bezier(0.22, 0.8, 0.36, 1)',
      }}
    >
      <div
        className="flex"
        style={{
          borderBottom: '1px solid var(--border)',
          background: 'var(--bg)',
          flexShrink: 0,
          alignItems: 'center',
        }}
      >
        {tabs.map((t) => {
          const on = activeTab === t.key;
          return (
            <button
              key={t.key}
              type="button"
              onClick={() => onTabChange(t.key)}
              role="tab"
              aria-selected={on}
              className="relative whitespace-nowrap"
              style={{
                padding: '10px 16px',
                border: 0,
                background: 'transparent',
                color: on ? 'var(--text)' : 'var(--text-3)',
                fontSize: 12.5,
                fontWeight: on ? 600 : 400,
                cursor: 'pointer',
              }}
            >
              {t.label}
              {on && (
                <span
                  style={{
                    position: 'absolute',
                    left: 14,
                    right: 14,
                    bottom: -1,
                    height: 2,
                    background: 'var(--accent)',
                    borderRadius: 1,
                  }}
                />
              )}
            </button>
          );
        })}
      </div>
      <div style={{ flex: 1, overflow: 'auto', minHeight: 0 }}>{children}</div>
      <ResizeHandle onMouseDown={onResizeStart} edge="left" />
    </aside>
  );
}

function RubricPanel({ assignment }: { assignment: TakeHomeAssignment }) {
  const items = assignment.rubric?.items ?? [];
  if (items.length === 0) {
    return (
      <div className="p-4 text-3 text-sm">
        No rubric defined for this problem.
      </div>
    );
  }
  const totalWeight = items.reduce((s, it) => s + it.weight, 0) || 1;
  return (
    <div style={{ padding: '14px 18px' }}>
      <p
        style={{
          margin: '0 0 14px',
          fontSize: 12,
          color: 'var(--text-3)',
          lineHeight: 1.55,
        }}
      >
        Submit triggers an AI reviewer that scores against each criterion below.
      </p>
      <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 12 }}>
        {items.map((it) => {
          const pct = Math.round((it.weight / totalWeight) * 100);
          return (
            <li key={it.id}>
              <div
                style={{
                  display: 'flex',
                  alignItems: 'baseline',
                  gap: 6,
                  marginBottom: 4,
                }}
              >
                <span
                  style={{
                    fontSize: 13,
                    color: 'var(--text)',
                    fontWeight: 500,
                  }}
                >
                  {it.label}
                </span>
                <span
                  className="mono"
                  style={{
                    marginLeft: 'auto',
                    fontSize: 10.5,
                    color: 'var(--text-4)',
                    letterSpacing: '0.04em',
                  }}
                >
                  {pct}%
                </span>
              </div>
              <div
                style={{
                  height: 4,
                  borderRadius: 2,
                  background: 'var(--bg-sunken)',
                  overflow: 'hidden',
                }}
              >
                <div
                  style={{
                    width: `${pct}%`,
                    height: '100%',
                    background: 'var(--accent-soft)',
                  }}
                />
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function NotesPanel({
  notes,
  onNotesChange,
}: {
  notes: string;
  onNotesChange: (n: string) => void;
}) {
  return (
    <div
      className="flex flex-col"
      style={{ padding: '14px 18px', gap: 10, height: '100%' }}
    >
      <div>
        <div
          className="eyebrow"
          style={{ marginBottom: 6, color: 'var(--text-3)' }}
        >
          Design notes
        </div>
        <p
          style={{
            margin: 0,
            fontSize: 12.5,
            color: 'var(--text-3)',
            lineHeight: 1.5,
          }}
        >
          Trade-offs, what you'd build next, what you cut for time. The rubric
          reviewer reads this alongside your code.
        </p>
      </div>
      <textarea
        aria-label="Design notes for the reviewer"
        value={notes}
        onChange={(e) => onNotesChange(e.target.value)}
        placeholder="Optional. A short paragraph helps the rubric reviewer."
        style={{
          flex: 1,
          minHeight: 200,
          resize: 'none',
          padding: 12,
          fontSize: 13,
          background: 'var(--bg-elev)',
          color: 'var(--text)',
          border: 0,
          boxShadow: 'inset 0 0 0 1px var(--border-strong)',
          borderRadius: 'var(--radius)',
          fontFamily: 'var(--font-sans)',
          outline: 'none',
          lineHeight: 1.55,
        }}
      />
      <div
        className="mono"
        style={{
          fontSize: 10.5,
          color: 'var(--text-4)',
          letterSpacing: '0.04em',
        }}
      >
        {notes.trim().length} CHARS
      </div>
    </div>
  );
}

function GuidancePanel({
  assignment,
  aiEnabled,
  onAiEnabledChange,
}: {
  assignment: TakeHomeAssignment;
  aiEnabled: boolean;
  onAiEnabledChange: (b: boolean) => void;
}) {
  return (
    <div
      style={{
        padding: '14px 18px',
        display: 'flex',
        flexDirection: 'column',
        gap: 14,
      }}
    >
      <div>
        <div
          className="eyebrow"
          style={{ marginBottom: 6, color: 'var(--text-3)' }}
        >
          How this problem works
        </div>
        <p
          style={{
            margin: 0,
            fontSize: 12.5,
            color: 'var(--text-2)',
            lineHeight: 1.6,
          }}
        >
          Project-shaped prompt with a fixed time budget.{' '}
          <strong style={{ color: 'var(--text)' }}>Run</strong> scores against
          the grading harness as often as you like.{' '}
          <strong style={{ color: 'var(--text)' }}>Submit</strong> locks the
          attempt and adds an AI rubric review of your code and design notes.
        </p>
      </div>
      {assignment.ai_policy === 'candidate-choice' && (
        <div
          style={{
            padding: '10px 12px',
            borderRadius: 'var(--radius)',
            background: aiEnabled ? 'var(--accent-soft)' : 'var(--bg-sunken)',
            boxShadow: aiEnabled
              ? 'inset 0 0 0 1px var(--accent)'
              : 'inset 0 0 0 1px var(--border)',
          }}
        >
          <label
            className="flex items-center gap-2"
            style={{ fontSize: 12.5, cursor: 'pointer' }}
          >
            <input
              type="checkbox"
              checked={aiEnabled}
              onChange={(e) => onAiEnabledChange(e.target.checked)}
            />
            <span style={{ color: aiEnabled ? 'var(--accent)' : 'var(--text-2)' }}>
              Pair with the AI assistant
            </span>
          </label>
          <p
            style={{
              margin: '6px 0 0 22px',
              fontSize: 11.5,
              color: 'var(--text-3)',
              lineHeight: 1.45,
            }}
          >
            The reviewer reads your chat log alongside your code. Be honest
            about how much help you took.
          </p>
        </div>
      )}
      <div>
        <div
          className="eyebrow"
          style={{ marginBottom: 6, color: 'var(--text-4)' }}
        >
          Problem metadata
        </div>
        <div
          style={{
            fontSize: 12,
            color: 'var(--text-3)',
            lineHeight: 1.7,
          }}
        >
          <div>
            Language:{' '}
            <strong style={{ color: 'var(--text-2)' }}>{assignment.language}</strong>
          </div>
          <div>
            Time budget:{' '}
            <strong style={{ color: 'var(--text-2)' }}>
              {formatBudget(assignment.time_budget_min)}
            </strong>
          </div>
          <div>
            AI policy:{' '}
            <strong style={{ color: 'var(--text-2)' }}>
              {AI_POLICY_LABEL[assignment.ai_policy]}
            </strong>
          </div>
        </div>
      </div>
    </div>
  );
}

function EditorActions({
  onRun,
  onSubmit,
  onOpenLast,
  running,
  submitting,
  hasReport,
  runResult,
}: {
  onRun: () => void;
  onSubmit: () => void;
  onOpenLast: () => void;
  running: boolean;
  submitting: boolean;
  hasReport: boolean;
  runResult: RunResult | null;
}) {
  const busy = running || submitting;
  return (
    <>
      {runResult && !runResult.error && (
        <span
          className="mono pill"
          style={{
            fontSize: 10.5,
            background: 'var(--bg-sunken)',
            color: 'var(--text-2)',
            letterSpacing: '0.08em',
          }}
        >
          {Math.round(runResult.score * 100)}/100
        </span>
      )}
      <button
        type="button"
        onClick={onOpenLast}
        disabled={!hasReport}
        title={hasReport ? 'Open last submission' : 'Submit to view results'}
        aria-label="Open last submission"
        style={{
          width: 32,
          height: 32,
          border: 0,
          borderRadius: 999,
          background: 'var(--bg-elev)',
          color: hasReport ? 'var(--text-2)' : 'var(--text-4)',
          boxShadow: 'inset 0 0 0 1px var(--border-strong)',
          cursor: hasReport ? 'pointer' : 'default',
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <History size={13} strokeWidth={1.8} />
      </button>
      <button
        type="button"
        onClick={onRun}
        disabled={busy}
        title="Run against the grading harness"
        aria-label="Run"
        className="inline-flex items-center gap-1.5"
        style={{
          height: 32,
          padding: '0 14px',
          border: 0,
          borderRadius: 999,
          background: busy ? 'var(--bg-sunken)' : 'var(--bg-elev)',
          color: busy ? 'var(--text-3)' : 'var(--text)',
          boxShadow: 'inset 0 0 0 1px var(--border-strong)',
          cursor: busy ? 'default' : 'pointer',
          fontSize: 13,
          fontWeight: 500,
        }}
      >
        <Play size={12} strokeWidth={2} />
        {running ? 'Running…' : 'Run'}
      </button>
      <button
        type="button"
        onClick={onSubmit}
        disabled={busy}
        title="Lock the attempt and add an AI rubric review"
        aria-label="Submit"
        data-ai-processing-glow={submitting ? 'true' : undefined}
        className="inline-flex items-center gap-1.5"
        style={{
          height: 32,
          padding: '0 16px',
          border: 0,
          borderRadius: 999,
          background: busy ? 'var(--bg-sunken)' : 'var(--accent)',
          color: busy ? 'var(--text-3)' : 'var(--bg)',
          cursor: busy ? 'default' : 'pointer',
          fontSize: 13,
          fontWeight: 500,
          boxShadow: busy ? 'none' : 'var(--shadow-card)',
        }}
      >
        <Send size={12} strokeWidth={2} />
        {submitting ? 'Grading…' : 'Submit'}
      </button>
    </>
  );
}

function RunOutput({ result }: { result: RunResult }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3" style={{ fontSize: 12 }}>
        <span
          className="pill"
          style={{
            background: result.error ? 'var(--plum-soft)' : 'var(--bg-sunken)',
            color: result.error ? 'var(--plum)' : 'var(--text)',
          }}
        >
          {result.error ? 'ERROR' : `${Math.round(result.score * 100)} / 100`}
        </span>
        <span className="text-3">
          {result.criteria.length} criteria · {result.duration_ms}ms
        </span>
      </div>
      {result.error && (
        <pre
          className="mono"
          style={{
            fontSize: 12,
            color: 'var(--plum)',
            background: 'var(--bg-sunken)',
            padding: 10,
            borderRadius: 'var(--radius)',
            margin: 0,
            whiteSpace: 'pre-wrap',
          }}
        >
          {result.error}
        </pre>
      )}
      {result.criteria.length > 0 && (
        <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 6 }}>
          {result.criteria.map((c) => (
            <li
              key={c.id}
              style={{
                fontSize: 12.5,
                display: 'flex',
                alignItems: 'baseline',
                gap: 8,
              }}
            >
              <span
                style={{
                  color: c.passed ? 'var(--forest)' : 'var(--plum)',
                  fontWeight: 600,
                  width: 12,
                }}
              >
                {c.passed ? '✓' : '✗'}
              </span>
              <span style={{ color: 'var(--text)' }}>{c.id}</span>
              {!c.passed && c.logs && (
                <span className="text-3" style={{ fontSize: 11.5 }}>
                  — {c.logs.slice(0, 200)}
                </span>
              )}
              <span
                className="mono"
                style={{
                  marginLeft: 'auto',
                  fontSize: 10.5,
                  color: 'var(--text-4)',
                  letterSpacing: '0.04em',
                }}
              >
                ×{c.weight}
              </span>
            </li>
          ))}
        </ul>
      )}
      {result.stderr && (
        <div>
          <div className="eyebrow" style={{ marginBottom: 4 }}>
            stderr
          </div>
          <pre
            className="mono"
            style={{
              fontSize: 12,
              color: 'var(--text-3)',
              background: 'var(--bg-sunken)',
              padding: 10,
              borderRadius: 'var(--radius)',
              margin: 0,
              whiteSpace: 'pre-wrap',
            }}
          >
            {result.stderr}
          </pre>
        </div>
      )}
    </div>
  );
}

// A criterion's mark: passed, missed, or no verdict where a limit stopped
// the grader before it could earn one.
function criterionMark(passed: boolean | null): { mark: string; label: string; color: string } {
  if (passed === null) return { mark: '○', label: 'not scored', color: 'var(--text-4)' };
  return passed
    ? { mark: '✓', label: 'passed', color: 'var(--forest)' }
    : { mark: '✗', label: 'missed', color: 'var(--plum)' };
}

function ReportPanel({
  harness,
  review,
  reviewStatus,
  retryAfterSeconds,
  onRetryReview,
  onRequestReview,
}: {
  harness: HarnessOutput;
  review: RubricReview | null;
  reviewStatus: ReviewStatus | null;
  retryAfterSeconds: number | null;
  onRetryReview: () => void;
  onRequestReview: () => void;
}) {
  // A limit stopped the grader: no score, and the tile names the limit.
  const limited = harness.outcome_class === 'resource-limit';
  const harnessPct = harness.score === null ? 0 : Math.round(harness.score * 100);
  const reviewPct = review ? Math.round(review.total * 100) : 0;
  const reviewMuted = review === null || Boolean(review.skipped);
  const reviewSubline = review?.skipped
    ? 'skipped'
    : review === null && reviewStatus
      ? REVIEW_TILE[reviewStatus]
      : undefined;

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-3" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <ScoreTile
          label="Harness"
          pct={harnessPct}
          muted={harness.score === null}
          subline={harness.score === null && limited ? limitTitle(harness.limit) : undefined}
        />
        <ScoreTile label="Rubric review" pct={reviewPct} muted={reviewMuted} subline={reviewSubline} />
      </div>

      <div>
        <div className="eyebrow" style={{ marginBottom: 8 }}>
          Harness criteria
        </div>
        {harness.error && (
          <pre
            className="mono"
            style={{
              fontSize: 12,
              color: limited ? 'var(--text-2)' : 'var(--plum)',
              background: 'var(--bg-sunken)',
              padding: 10,
              borderRadius: 'var(--radius)',
              margin: '0 0 8px',
              whiteSpace: 'pre-wrap',
            }}
          >
            {harness.error}
          </pre>
        )}
        <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 6 }}>
          {harness.criteria.map((c) => (
            <li
              key={c.id}
              data-criterion={criterionMark(c.passed).label}
              style={{
                fontSize: 12.5,
                display: 'flex',
                alignItems: 'baseline',
                gap: 8,
              }}
            >
              <span
                style={{
                  color: criterionMark(c.passed).color,
                  fontWeight: 600,
                  width: 12,
                }}
              >
                <span aria-hidden="true">{criterionMark(c.passed).mark}</span>
                <span className="sr-only">{criterionMark(c.passed).label}</span>
              </span>
              <span style={{ color: 'var(--text)' }}>{c.id}</span>
              {c.passed === false && c.logs && (
                <span className="text-3" style={{ fontSize: 11.5 }}>
                  — {c.logs.slice(0, 200)}
                </span>
              )}
              <span
                className="mono"
                style={{
                  marginLeft: 'auto',
                  fontSize: 10.5,
                  color: 'var(--text-4)',
                  letterSpacing: '0.04em',
                }}
              >
                ×{c.weight}
              </span>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <div className="eyebrow" style={{ marginBottom: 8 }}>
          AI rubric review
        </div>
        <ReviewStatusNote
          status={reviewStatus}
          skipped={Boolean(review?.skipped)}
          retryAfterSeconds={retryAfterSeconds}
          onRetry={onRetryReview}
          onRequest={onRequestReview}
        />
        {review === null ? (
          !reviewStatus && (
            <div style={{ fontSize: 12.5, color: 'var(--text-3)' }}>This submission has no rubric review.</div>
          )
        ) : review.skipped ? (
          <div
            style={{
              padding: 12,
              background: 'var(--bg-sunken)',
              borderRadius: 'var(--radius)',
              fontSize: 12.5,
              color: 'var(--text-3)',
            }}
          >
            Skipped: {(review.reason ?? 'no AI provider configured').replace(/\.$/, '')}.
          </div>
        ) : review.parse_error ? (
          <pre
            className="mono"
            style={{
              fontSize: 12,
              color: 'var(--plum)',
              background: 'var(--bg-sunken)',
              padding: 10,
              borderRadius: 'var(--radius)',
              margin: 0,
              whiteSpace: 'pre-wrap',
            }}
          >
            Couldn't parse rubric output: {review.parse_error}
          </pre>
        ) : (
          <ul
            style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 10 }}
          >
            {review.items.map((it) => (
              <li
                key={it.id}
                style={{
                  background: 'var(--bg-sunken)',
                  borderRadius: 'var(--radius)',
                  padding: 12,
                  fontSize: 12.5,
                }}
              >
                <div className="flex items-center gap-2">
                  <strong style={{ color: 'var(--text)' }}>{it.id}</strong>
                  <span
                    className="mono"
                    style={{
                      marginLeft: 'auto',
                      fontSize: 10.5,
                      color: 'var(--text-3)',
                      letterSpacing: '0.04em',
                    }}
                  >
                    {Math.round(it.score * 100)}/100
                  </span>
                </div>
                {it.evidence && (
                  <p
                    style={{
                      margin: '6px 0 0',
                      color: 'var(--text-2)',
                      lineHeight: 1.55,
                    }}
                  >
                    {it.evidence}
                  </p>
                )}
                {it.evidence_quotes && it.evidence_quotes.length > 0 && (
                  <ul
                    style={{
                      margin: '8px 0 0',
                      padding: 0,
                      listStyle: 'none',
                      display: 'grid',
                      gap: 6,
                    }}
                  >
                    {it.evidence_quotes.map((q, j) => (
                      <li key={j} style={{ fontSize: 11.5 }}>
                        <code
                          className="mono"
                          style={{ color: 'var(--text-3)' }}
                        >
                          {q.file}:{q.line}
                        </code>
                        <blockquote
                          style={{
                            margin: '2px 0 0 8px',
                            paddingLeft: 8,
                            borderLeft: '2px solid var(--border)',
                            color: 'var(--text-2)',
                            whiteSpace: 'pre-wrap',
                            fontFamily: 'var(--font-mono)',
                            fontSize: 11.5,
                          }}
                        >
                          {q.quote}
                        </blockquote>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function ScoreTile({
  label,
  pct,
  subline,
  muted = false,
}: {
  label: string;
  pct: number;
  subline?: string;
  muted?: boolean;
}) {
  return (
    <div
      style={{
        padding: 12,
        background: 'var(--bg-sunken)',
        borderRadius: 'var(--radius)',
      }}
    >
      <div className="eyebrow" style={{ marginBottom: 4, color: 'var(--text-4)' }}>
        {label}
      </div>
      <div
        className="display-italic"
        style={{
          fontSize: 28,
          lineHeight: 1.05,
          color: muted ? 'var(--text-4)' : 'var(--text)',
        }}
      >
        {muted ? '—' : `${pct}`}
        {!muted && (
          <span
            className="mono"
            style={{
              fontSize: 11,
              color: 'var(--text-4)',
              marginLeft: 4,
              letterSpacing: '0.04em',
            }}
          >
            /100
          </span>
        )}
      </div>
      {subline && (
        <div
          className="mono"
          style={{
            fontSize: 10.5,
            color: 'var(--text-4)',
            letterSpacing: '0.04em',
            marginTop: 4,
          }}
        >
          {subline.toUpperCase()}
        </div>
      )}
    </div>
  );
}
