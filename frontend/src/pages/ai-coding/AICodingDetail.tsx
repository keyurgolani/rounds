import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  ArrowRight,
  Check,
  ChevronsLeft,
  ChevronsRight,
  Circle,
  History,
  MessageSquare,
  MessageSquareOff,
  Play,
  RotateCcw,
  Send,
} from 'lucide-react';
import { useResizableWidth } from '../../hooks/useResizableWidth';
import { NARROW_SCREEN_QUERY, useMediaQuery } from '../../hooks/useMediaQuery';
import ResizeHandle from '../../components/layout/ResizeHandle';
import AppHeader from '../../components/shell/AppHeader';
import BackLink from '../../components/shell/BackLink';
import BlockMarkdown from '../../components/shell/BlockMarkdown';
import DifficultyPill from '../../components/shell/DifficultyPill';
import FloatingPanelTab from '../../components/shell/FloatingPanelTab';
import StatusAction from '../../components/shell/StatusAction';
import SubmissionModal from '../../components/shell/SubmissionModal';
import MultiFileEditor from '../../components/editor/MultiFileEditor';
import AIChatPanel from '../../components/ai/AIChatPanel';
import { RunDock } from '../coding/RunDock';
import GradeReport, { gradeSummary } from './GradeReport';
import HeaderCheckpointStepper from './HeaderCheckpointStepper';
import {
  deleteInProgressAttempt,
  effectiveLanguages,
  getGradedAttempt,
  getLatestAttempt,
  getRound,
  gradeAttempt,
  requestGradeReview,
  resolveRound,
  runProject,
  upsertInProgressAttempt,
  type AIChatLogEntry,
  type AICodingRound,
  type AICodingRoundRaw,
  type CheckpointResult,
  type RunProjectResult,
} from './aiCodingApi';
import { useAICodingDrafts } from '../../hooks/useAICodingDrafts';
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
import { useRubricReview } from '../../hooks/useRubricReview';
import { earnedOutput, isJobAnswer, notAJobAnswer, type JobAnswer } from '../../lib/executionJobs';
import { envelopeJob, rubricState, type RubricReview, type RubricState } from '../../lib/gradedRows';
import type { RunnerJobView } from '../../components/runner/RunnerJobStatus';
import { RunErrorOutput } from '../../components/runner/RunErrorOutput';
import { ReportProblem } from '../../components/runner/ReportProblem';

type SideTab = 'checkpoints' | 'rubric' | 'guidance';

// The report the modal shows: a grade's checkpoints and its review, and
// for a row the server wrote, the job and envelope its review asks by.
type ReportView = {
  test_results: CheckpointResult[];
  rubric_review: RubricReview | null;
  jobId?: string | null;
  envelope?: string | null;
};

// A report that can't show: what happened, as a fixed sentence.
type ReportTrouble = { title: string; body: string; retry?: () => void };

const REPORT_UNREAD = "The grade finished and was saved, but this page couldn't load its report. Try again in a moment.";

// A run job's output as the route's in-request body, when the run earned
// its end (ROUNDS-00A-L03). Any other end shows only its own notice.
function projectOutput(job: JobAnswer): RunProjectResult | null {
  const out = earnedOutput(job);
  return out && typeof out.passed === 'boolean' ? (out as unknown as RunProjectResult) : null;
}

const SIDE_TABS: ReadonlyArray<{ key: SideTab; label: string }> = [
  { key: 'checkpoints', label: 'Checkpoints' },
  { key: 'rubric', label: 'Rubric' },
  { key: 'guidance', label: 'Guidance' },
];

const SIDE_TABS_NO_CP: ReadonlyArray<{ key: SideTab; label: string }> = [
  { key: 'rubric', label: 'Rubric' },
  { key: 'guidance', label: 'Guidance' },
];

const FOCUS_KEY = 'rounds:editor-focus.ai-coding';
const SIDE_RAIL_KEY = 'rounds.aiCoding.sideWidth';
const CHAT_RAIL_KEY = 'rounds.aiCoding.chatWidth';
const SIDE_RAIL_DEFAULT = 340;
const CHAT_RAIL_DEFAULT = 360;
const RAIL_MIN = 240;
const RAIL_MAX = 560;

// Storage key for the per-slug "last picked language" preference. Multi-
// language rounds default to their first supported language; once the
// candidate picks, we remember it so a refresh keeps them where they
// were rather than snapping back to the alphabetical default.
function languageStorageKey(slug: string): string {
  return `rounds.aiCoding.lang:${slug}`;
}

export default function AICodingDetail() {
  const { slug = '' } = useParams<{ slug: string }>();
  const { currentId: campaignId } = useCampaign();
  const [rawRound, setRawRound] = useState<AICodingRoundRaw | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('');
  const round: AICodingRound | null =
    rawRound && selectedLanguage ? resolveRound(rawRound, selectedLanguage) : null;
  const availableLanguages = rawRound ? effectiveLanguages(rawRound) : [];
  const [error, setError] = useState<string | null>(null);
  const [activePath, setActivePath] = useState<string>('');
  const [checkpointIdx, setCheckpointIdx] = useState(0);
  const [runResult, setRunResult] = useState<RunProjectResult | null>(null);
  // A run that failed without a result: its error, never a fake verdict.
  const [runError, setRunError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [passedByCheckpoint, setPassedByCheckpoint] = useState<boolean[]>([]);
  const [chatLog, setChatLog] = useState<AIChatLogEntry[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [report, setReport] = useState<ReportView | null>(null);
  const [reportTrouble, setReportTrouble] = useState<ReportTrouble | null>(null);
  const [reportOpen, setReportOpen] = useState(false);
  // Which action's job the runner notice shows: the one last started, or
  // a grade the tab picked back up.
  const [jobShown, setJobShown] = useState<'run' | 'grade' | null>(null);
  const [chatOpen, setChatOpen] = usePersistedState<boolean>(
    'rounds.aiCoding.chatOpen',
    true,
  );
  const [sideTab, setSideTab] = usePersistedState<SideTab>(
    'rounds.aiCoding.sideTab',
    'checkpoints',
  );
  const [filesCollapsed, setFilesCollapsed] = usePersistedState<boolean>(
    'rounds.aiCoding.filesCollapsed',
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
  // Bumped on Reset Files so the chat panel remounts and rereads the
  // (now-empty) initialMessages — without this the panel would keep
  // showing stale bubbles even though parent chatLog has been wiped.
  const [chatResetVersion, setChatResetVersion] = useState(0);
  const { focus, toggle: toggleFocus } = useEditorFocus(FOCUS_KEY);
  // Setter only — display lives in <StatusAction />, which subscribes
  // to the same key via rounds:status events.
  const [, setPracticeStatus] = usePracticeStatus('ai-coding', slug);
  const startedAtRef = useRef(Date.now());
  const runReqIdRef = useRef(0);
  // The definition version runs and grades name: the row's, until a
  // superseded answer rereads it (ROUNDS-00A-L02).
  const definitionVersionRef = useRef<number | null | undefined>(undefined);
  const rereadDefinitionVersion = useCallback(async () => {
    const fresh = await getRound(slug);
    definitionVersionRef.current = fresh.definition_version;
    return fresh.definition_version;
  }, [slug]);
  // While ROUNDS_GATE_EXECUTION_SCRATCH is on, a run is a durable job
  // (ROUNDS-00A-L03), one per checkpoint; its end shows the result.
  const jobTriggerRef = useRef<HTMLElement | null>(null);
  const runJob = useRunnerJob(
    round ? `ai-coding:${round.slug}:${round.language}:${checkpointIdx}:run` : null,
    {
      onEnded: (job) => {
        const out = projectOutput(job);
        if (!out) return;
        setRunResult(out);
        setDockOpen(true);
        if (out.passed) {
          setPassedByCheckpoint((prev) => {
            const next = [...prev];
            next[checkpointIdx] = true;
            return next;
          });
        }
      },
      onDenied: (err) => {
        const denial = classifyRunnerError(err, jobTriggerRef.current);
        if (denial) setRunDenial({ action: 'run', denial });
      },
    },
  );
  // While ROUNDS_GATE_EXECUTION_GRADING is on, a grade is a durable job
  // too (ROUNDS-00A-L03 PR 3). An authoritative end has a graded row the
  // server wrote: the report opens from it, and asks for the review once
  // with the files this page sent.
  const gradeTriggerRef = useRef<HTMLElement | null>(null);
  const gradedRef = useRef<{ jobId: string; files: Record<string, string> } | null>(null);
  const review = useRubricReview(
    (jobId, sent, key, signal) => requestGradeReview(jobId, sent, key, signal),
    async (jobId) => (await getGradedAttempt(jobId))?.rubric_review ?? null,
  );
  const { ask: askReview, show: showReview, reset: resetReview, retry: retryReview } = review;
  const gradeJob = useRunnerJob(
    round ? `ai-coding:${round.slug}:${round.language}:${campaignId ?? ''}:grade` : null,
    {
      onEnded: (job) => void openGraded(job),
      onDenied: (err) => {
        const denial = classifyRunnerError(err, gradeTriggerRef.current);
        if (denial) setRunDenial({ action: 'grade', denial });
      },
    },
  );
  const busy = running || runJob.active;
  const grading = submitting || gradeJob.active;
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
  const gradeView: RunnerJobView = {
    job: gradeJob.job,
    gone: gradeJob.gone,
    reconnecting: gradeJob.reconnecting,
    runningSince: gradeJob.runningSince,
    action: 'grade',
    onCancel: () => void gradeJob.cancel(),
    onRetry: busy || grading ? undefined : () => void handleSubmit(true),
    trigger: gradeTriggerRef.current,
  };
  const shownJob = jobShown ?? (gradeJob.job !== null || gradeJob.gone ? 'grade' : 'run');

  useEffect(() => {
    let cancelled = false;
    setRawRound(null);
    setSelectedLanguage('');
    setError(null);
    setCheckpointIdx(0);
    setRunResult(null);
    setRunError(null);
    setChatLog([]);
    setReport(null);
    setReportTrouble(null);
    setReportOpen(false);
    setDockOpen(false);
    setRunDenial(null);
    setJobShown(null);
    resetReview();
    gradedRef.current = null;
    startedAtRef.current = Date.now();
    getRound(slug)
      .then(async (r) => {
        if (cancelled) return;
        definitionVersionRef.current = r.definition_version;
        setRawRound(r);
        // Pick the candidate's last-used language for this slug, or
        // fall back to the round's first supported language.
        const langs = effectiveLanguages(r);
        let initialLang = langs[0] ?? r.language;
        try {
          const stored = window.localStorage.getItem(languageStorageKey(slug));
          if (stored && langs.includes(stored)) initialLang = stored;
        } catch {
          /* localStorage unavailable — defaults are fine */
        }
        setSelectedLanguage(initialLang);
        const cps = Array.isArray(r.checkpoints)
          ? r.checkpoints
          : r.checkpoints[initialLang] ?? [];
        setPassedByCheckpoint(new Array(cps.length).fill(false));
        // Rehydrate persisted chat log + most recent submission so
        // refresh doesn't lose them. We grab the most recent attempt
        // row (any status) for chat log; if it's `graded` we also
        // restore the report so the "open last submission" affordance
        // works on first paint without requiring another submit.
        try {
          const latest = await getLatestAttempt(r.id, campaignId ?? undefined);
          if (cancelled || !latest) return;
          if (latest.ai_chats?.length) setChatLog(latest.ai_chats);
          if (latest.status === 'graded' && latest.test_results) {
            setReport({
              test_results: latest.test_results,
              rubric_review: latest.rubric_review ?? null,
              envelope: latest.envelope || null,
            });
            // A row the server wrote and nobody reviewed yet asks only
            // when the candidate does: only they know the files are the
            // ones graded.
            if (latest.rubric_review) showReview(latest.rubric_review);
            else showReview(null, latest.envelope ? 'not_requested' : null);
          }
        } catch {
          /* best-effort rehydrate — safe to ignore */
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [slug, campaignId, resetReview, showReview]);

  // Persist chat log to PocketBase (debounced) so a refresh won't
  // discard in-flight conversations. Only fires once we have a round
  // and an ai_chats payload to write.
  const lastSavedChatRef = useRef<string>('[]');
  useEffect(() => {
    if (!round) return;
    const serialised = JSON.stringify(chatLog);
    if (serialised === lastSavedChatRef.current) return;
    if (chatLog.length === 0) return;
    const timer = window.setTimeout(() => {
      upsertInProgressAttempt({
        roundId: round.id,
        campaignId: campaignId ?? undefined,
        currentCheckpoint: checkpointIdx,
        chats: chatLog,
      })
        .then(() => {
          lastSavedChatRef.current = serialised;
        })
        .catch(() => {
          /* best-effort — retry on next change */
        });
    }, 600);
    return () => window.clearTimeout(timer);
  }, [chatLog, round, campaignId, checkpointIdx]);

  const {
    files,
    savedFiles,
    setFile,
    hydrated,
    resetToStarter,
    persistImmediately,
    saveNow,
  } = useAICodingDrafts(round, campaignId ?? undefined, rawRound);

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

  useEffect(() => {
    if (!hydrated) return;
    if (activePath && files[activePath] !== undefined) return;
    const first = Object.keys(files).sort()[0];
    if (first) setActivePath(first);
  }, [hydrated, files, activePath]);

  async function handleRun(retry = false) {
    if (!round) return;
    const cp = round.checkpoints[checkpointIdx];
    if (!cp) return;
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
      const answer = await retrySuperseded(
        definitionVersionRef.current,
        (version) => {
          const input = {
            round_slug: round.slug,
            language: round.language,
            checkpoint_index: checkpointIdx,
            files,
            definition_version: version,
          };
          return runProject(input, { idempotencyKey: runJob.begin(input, retry) });
        },
        rereadDefinitionVersion,
      );
      if (reqId !== runReqIdRef.current) return;
      // A job: the notice follows it, and its end shows the result.
      // Anything else is a failure.
      if (!runJob.follow(answer)) throw notAJobAnswer();
      setDockOpen(false);
    } catch (e) {
      if (reqId !== runReqIdRef.current) return;
      const denial = classifyRunnerError(e, trigger);
      if (denial) {
        // Nothing ran, so there's no console output to show.
        setRunDenial({ action: 'run', denial });
        setDockOpen(false);
        return;
      }
      // Nothing came back to score, so no verdict shows: only the error,
      // as a fixed sentence, never the server's own text.
      setRunError(runFailureText(e));
    } finally {
      if (reqId === runReqIdRef.current) {
        setRunning(false);
      }
    }
  }

  async function handleSubmit(retry = false) {
    if (!round) return;
    const trigger = activeTrigger();
    gradeTriggerRef.current = trigger;
    setJobShown('grade');
    setSubmitting(true);
    setReport(null);
    setReportTrouble(null);
    setRunDenial(null);
    resetReview();
    // What this grade sends, which its review sends again.
    const sent = files;
    const chats = chatLog;
    try {
      const answer = await retrySuperseded(
        definitionVersionRef.current,
        (version) => {
          const work = {
            round_slug: round.slug,
            files: sent,
            ai_chats: chats,
            language: round.language,
            definition_version: version,
            campaign_id: campaignId ?? undefined,
          };
          // The session time isn't part of the work, so a retry of the
          // same files and chats stays the same command.
          return gradeAttempt(
            { ...work, duration_ms: Date.now() - startedAtRef.current },
            { idempotencyKey: gradeJob.begin(work, retry) },
          );
        },
        rereadDefinitionVersion,
      );
      // A job: the notice follows it, and an authoritative end opens the
      // report from the row the server wrote. The page writes no row, and
      // anything but a job is a failure.
      if (isJobAnswer(answer)) gradedRef.current = { jobId: answer.job_id, files: sent };
      if (!gradeJob.follow(answer)) throw notAJobAnswer();
    } catch (e) {
      // A denied grade isn't a graded attempt, so no report opens.
      const denial = classifyRunnerError(e, trigger);
      if (denial) {
        setRunDenial({ action: 'grade', denial });
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

  // A grading job ended. Only an end the candidate's code earned, or a
  // limit it reached, has a graded row; every other end shows its notice.
  async function openGraded(job: JobAnswer) {
    const envelope = job.envelope;
    if (envelope === null || !envelope.authoritative || job.outcome_class !== envelope.outcome_class) return;
    // Mastered only when every checkpoint passed, which is what a passed
    // envelope means.
    if (envelope.outcome_class === 'passed') setPracticeStatus('mastered');
    const sent = gradedRef.current?.jobId === job.job_id ? gradedRef.current.files : null;
    await loadGraded(job.job_id, sent, rubricState(envelope));
  }

  async function loadGraded(jobId: string, sent: Record<string, string> | null, state: RubricState | null) {
    setReportTrouble(null);
    let row: Awaited<ReturnType<typeof getGradedAttempt>> = null;
    try {
      row = await getGradedAttempt(jobId);
    } catch {
      row = null;
    }
    if (row === null) {
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
      test_results: row.test_results ?? [],
      rubric_review: row.rubric_review ?? null,
      jobId,
      envelope: row.envelope || null,
    });
    setReportOpen(true);
    if (row.rubric_review) showReview(row.rubric_review);
    else if (state === 'lost') showReview(null, 'lost');
    // Asked once, with the files this page sent; a grade the tab picked
    // back up asks when the candidate does.
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

  function selectCheckpoint(i: number) {
    runReqIdRef.current++;
    setCheckpointIdx(i);
    setRunResult(null);
    setRunError(null);
    setRunDenial(null);
    setRunning(false);
  }

  function resetCheckpoint(i: number) {
    setPassedByCheckpoint((prev) => {
      const next = [...prev];
      next[i] = false;
      return next;
    });
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
            <BackLink to="/ai-coding" label="Back to practice" />
            {round && <DifficultyPill level={round.difficulty} />}
            {round?.topics?.map((t) => (
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
            {round?.companies?.map((c) => (
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
          </span>
        }
        title={round?.title ?? 'AI Round'}
        description={round?.description ? toLeadSummary(round.description) : undefined}
        chromeActions={
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            {round && (
              <LanguageControl
                languages={availableLanguages}
                selected={selectedLanguage}
                onPick={(lang) => {
                  if (lang === selectedLanguage) return;
                  setSelectedLanguage(lang);
                  try {
                    window.localStorage.setItem(languageStorageKey(slug), lang);
                  } catch {
                    /* localStorage unavailable — ignore */
                  }
                  setCheckpointIdx(0);
                  setRunResult(null);
                  setRunError(null);
                  if (rawRound) {
                    const cps = Array.isArray(rawRound.checkpoints)
                      ? rawRound.checkpoints
                      : rawRound.checkpoints[lang] ?? [];
                    setPassedByCheckpoint(new Array(cps.length).fill(false));
                  }
                }}
              />
            )}
            {round && round.checkpoints.length > 1 && (
              <HeaderCheckpointStepper
                checkpoints={round.checkpoints}
                currentIndex={checkpointIdx}
                passed={passedByCheckpoint}
                onResetCheckpoint={resetCheckpoint}
              />
            )}
            <StatusAction kind="ai-coding" id={slug} />
          </span>
        }
        compactActions={<StatusAction kind="ai-coding" id={slug} compact />}
        timer={slug ? { kind: 'ai-coding', id: slug } : undefined}
      />

      {error && (
        <div className="p-4" style={{ color: 'var(--danger)' }}>
          Couldn't load round: {error}
        </div>
      )}
      {!error && !round && (
        <div className="p-4 text-3 text-sm">Loading round…</div>
      )}

      {round && (() => {
        const aiAllowed = !!round.checkpoints[checkpointIdx]?.ai_allowed;
        const tabs =
          round.checkpoints.length > 1 ? SIDE_TABS : SIDE_TABS_NO_CP;
        const effectiveSideTab =
          tabs.find((t) => t.key === sideTab)?.key ??
          (round.checkpoints.length > 1 ? 'checkpoints' : 'rubric');

        // Floating tabs anchored to the body row's left edge — appear
        // when their respective panel is collapsed. Stacked vertically.
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
            job={shownJob === 'grade' ? gradeView : jobView}
            actionMinHeight={narrow ? 44 : undefined}
          />
        );

        return (
          <>
          <div
            className="flex-1 min-h-0 flex overflow-hidden"
            style={{ minHeight: 0, position: 'relative' }}
          >
            {/* AI chat now lives INSIDE the editor as a right column,
                toggled by a Sparkles button in the editor's floating
                top-right toolbar. The chat element is built here and
                handed to MultiFileEditor via its `aiChat` slot below. */}

            {floatingTabs.length > 0 && <FloatingPanelTab tabs={floatingTabs} />}

            {/* CENTER: the problem above the editor (hidden in focus), the editor with Run and Submit in a bar under it, the console below. */}
            <div
              data-ai-coding-pane="center"
              className="flex-1 flex flex-col"
              style={{ minWidth: 0, minHeight: 0 }}
            >
              {!focus && (
                <ProblemBar
                  description={round.description}
                  currentCheckpointPrompt={round.checkpoints[checkpointIdx]?.prompt}
                  currentCheckpointLabel={round.checkpoints[checkpointIdx]?.label}
                  checkpointNumber={checkpointIdx + 1}
                  checkpointTotal={round.checkpoints.length}
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
                      // Also wipe the AI chat log + the in-progress
                      // attempt row — chats often reference now-discarded
                      // code and would be misleading after a reset.
                      setChatLog([]);
                      setChatResetVersion((v) => v + 1);
                      lastSavedChatRef.current = '[]';
                      if (round) {
                        deleteInProgressAttempt(
                          round.id,
                          campaignId ?? undefined,
                        ).catch(() => {
                          /* best-effort — local state already reset */
                        });
                      }
                    }}
                    storageKey="rounds:editor.explorer.ai-coding"
                    focused={focus}
                    onFocusToggle={toggleFocus}
                    aiChatOpen={aiAllowed && chatOpen}
                    onToggleAiChat={
                      aiAllowed ? () => setChatOpen(!chatOpen) : undefined
                    }
                    aiChat={
                      aiAllowed ? (
                        <AIChatPanel
                          // Re-mount on checkpoint switch so the bubble
                          // history rehydrates from the persisted log
                          // scoped to that checkpoint. Bumped on Reset
                          // Files via chatResetVersion.
                          key={`${round.id}:${checkpointIdx}:${chatResetVersion}`}
                          roundSlug={round.slug}
                          checkpointIndex={checkpointIdx}
                          files={files}
                          checkpointPrompt={
                            round.checkpoints[checkpointIdx]?.prompt
                          }
                          disabled={false}
                          initialMessages={chatLog
                            .filter(
                              (c) =>
                                c.checkpoint === checkpointIdx &&
                                (c.role === 'user' || c.role === 'assistant'),
                            )
                            .map((c) => ({
                              role: c.role as 'user' | 'assistant',
                              content: c.content,
                            }))}
                          onMessageRecorded={(m) =>
                            setChatLog((log) => [
                              ...log,
                              {
                                checkpoint: checkpointIdx,
                                role: m.role,
                                content: m.content,
                                ts: Date.now(),
                              },
                            ])
                          }
                          onApplyPatches={(patches) => {
                            // Persist to PocketBase RIGHT NOW so a
                            // refresh-within-the-autosave-window
                            // doesn't lose the post-apply contents
                            // (the user would see "Applied" in chat
                            // but pre-apply code in the editor —
                            // confusing mismatch reported in the wild).
                            const updates: Record<string, string> = {};
                            for (const p of patches) updates[p.file] = p.contents;
                            persistImmediately(updates).catch(() => {
                              for (const p of patches) {
                                setFile(p.file, p.contents);
                              }
                            });
                          }}
                        />
                      ) : undefined
                    }
                    // The AI chat narrows the code, so Run and Submit sit
                    // in a bar under it rather than over its gutter.
                    actionsBar
                    bottomActions={
                      <EditorActions
                        onRun={() => void handleRun()}
                        onSubmit={() => void handleSubmit()}
                        onOpenLast={() => setReportOpen(true)}
                        running={busy}
                        submitting={grading}
                        hasReport={Boolean(report)}
                        hideRunResult={runResult ? false : true}
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
                  runResult ? (
                    <span
                      className="mono"
                      style={{
                        fontSize: 10.5,
                        color: runResult.passed ? 'var(--forest)' : 'var(--plum)',
                        letterSpacing: '0.08em',
                      }}
                    >
                      {runResult.passed ? 'PASS' : 'FAIL'} ·{' '}
                      {runResult.duration_ms}MS
                    </span>
                  ) : runError !== null ? (
                    <span
                      className="mono"
                      style={{ fontSize: 10.5, color: 'var(--plum)', letterSpacing: '0.08em' }}
                    >
                      RUN ERROR
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
                tabs={tabs}
                activeTab={effectiveSideTab}
                onTabChange={setSideTab}
              >
                {effectiveSideTab === 'checkpoints' && (
                  <CheckpointsTabPanel
                    round={round}
                    currentIdx={checkpointIdx}
                    passed={passedByCheckpoint}
                    onSelect={selectCheckpoint}
                    onResetCheckpoint={resetCheckpoint}
                  />
                )}
                {effectiveSideTab === 'rubric' && <RubricPanel round={round} />}
                {effectiveSideTab === 'guidance' && (
                  <GuidancePanel round={round} />
                )}
              </SideRail>
            )}
          </div>
          {narrow && (
            <div data-ai-coding-pane="notice" className="flex-shrink-0">
              {runnerNotice}
            </div>
          )}
          </>
        );
      })()}

      <SubmissionModal
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        title={`Submission · ${round?.title ?? 'AI Round'}`}
        subtitle={reportTrouble === null && report ? gradeSummary(report.test_results) : undefined}
      >
        {reportTrouble !== null ? (
          <ReportProblem title={reportTrouble.title} body={reportTrouble.body} onRetry={reportTrouble.retry} />
        ) : (
          report &&
          round && (
            <GradeReport
              testResults={report.test_results}
              rubric={round.rubric}
              rubricReview={review.review ?? report.rubric_review}
              review={{
                status: review.status,
                retryAfterSeconds: review.retryAfterSeconds,
                onRetry: () => {
                  if (!retryReview()) void requestReview();
                },
                onRequest: () => void requestReview(),
              }}
              aiChats={chatLog}
              files={files}
            />
          )
        )}
      </SubmissionModal>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Local subcomponents — small enough to live alongside the page.
// ---------------------------------------------------------------------------

/**
 * Compact language selector that lives in the header's chrome action
 * slot. Matches the closed-state aesthetic of HeaderCheckpointStepper:
 * sunken pill chamber, monospaced eyebrow label, accent-filled active
 * option. For single-language rounds it collapses to a read-only chip
 * (no buttons) so the visual weight stays consistent with the multi-
 * language case.
 */
function LanguageControl({
  languages,
  selected,
  onPick,
}: {
  languages: string[];
  selected: string;
  onPick: (lang: string) => void;
}) {
  if (languages.length === 0) return null;
  const single = languages.length === 1;
  return (
    <span
      role={single ? undefined : 'radiogroup'}
      aria-label="Language"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        height: 24,
        padding: single ? '0 8px 0 8px' : '0 3px 0 8px',
        gap: 8,
        borderRadius: 6,
        background: 'var(--bg-sunken)',
        boxShadow: 'inset 0 0 0 1px var(--border)',
      }}
    >
      <span
        className="mono"
        aria-hidden="true"
        style={{
          fontSize: 9.5,
          color: 'var(--text-4)',
          letterSpacing: '0.1em',
        }}
      >
        LANGUAGE
      </span>
      {single ? (
        <span
          style={{
            fontSize: 11.5,
            color: 'var(--text-2)',
            fontWeight: 500,
            letterSpacing: '0.01em',
            textTransform: 'lowercase',
          }}
        >
          {languages[0]}
        </span>
      ) : (
        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 2,
          }}
        >
          {languages.map((lang) => {
            const active = lang === selected;
            return (
              <button
                key={lang}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => onPick(lang)}
                title={`Switch to ${lang}`}
                style={{
                  height: 18,
                  padding: '0 8px',
                  border: 0,
                  borderRadius: 4,
                  background: active ? 'var(--accent)' : 'transparent',
                  color: active ? 'var(--accent-fg)' : 'var(--text-3)',
                  fontSize: 11.5,
                  fontWeight: active ? 600 : 500,
                  letterSpacing: '0.01em',
                  cursor: active ? 'default' : 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  textTransform: 'lowercase',
                  transition: 'background 100ms ease, color 100ms ease',
                }}
              >
                {lang}
              </button>
            );
          })}
        </span>
      )}
    </span>
  );
}

/**
 * Returns a 1-2 sentence header summary derived from the long-form
 * description, capped so it never blows past the available header
 * width. Strips markdown markup.
 */
function toLeadSummary(desc: string): string {
  const stripped = desc
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/`[^`]*`/g, '')
    .replace(/[#*_>~]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  const sentenceMatch = stripped.match(/^(.{20,180}?[.!?])\s/);
  if (sentenceMatch) return sentenceMatch[1];
  return stripped.length > 180 ? stripped.slice(0, 177).trimEnd() + '…' : stripped;
}

function ProblemBar({
  description,
  currentCheckpointPrompt,
  currentCheckpointLabel,
  checkpointNumber,
  checkpointTotal,
}: {
  description: string;
  currentCheckpointPrompt?: string;
  currentCheckpointLabel?: string;
  checkpointNumber: number;
  checkpointTotal: number;
}) {
  const hasCheckpointStrip = !!currentCheckpointLabel && checkpointTotal > 1;
  return (
    <div
      style={{
        flexShrink: 0,
        background: 'var(--bg)',
        borderBottom: '1px solid var(--border)',
        maxHeight: '32vh',
        overflow: 'auto',
      }}
    >
      {hasCheckpointStrip && (
        <div
          className="flex items-center"
          style={{
            padding: '8px 16px 4px',
            gap: 10,
            minHeight: 22,
          }}
        >
          <span
            className="mono"
            style={{
              fontSize: 10.5,
              color: 'var(--text-4)',
              letterSpacing: '0.08em',
            }}
          >
            CP {checkpointNumber}/{checkpointTotal} ·{' '}
            {currentCheckpointLabel!.toUpperCase()}
          </span>
        </div>
      )}
      <div
        style={{
          padding: hasCheckpointStrip ? '4px 16px 14px' : '12px 16px 14px',
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
          <BlockMarkdown text={description} />
        </div>
        {currentCheckpointPrompt && checkpointTotal > 1 && (
          <div
            style={{
              paddingLeft: 12,
              borderLeft: '2px solid var(--accent)',
              fontSize: 13,
              color: 'var(--text-2)',
              lineHeight: 1.55,
            }}
          >
            <div
              className="eyebrow"
              style={{ marginBottom: 4, color: 'var(--accent)' }}
            >
              Current checkpoint
            </div>
            <BlockMarkdown text={currentCheckpointPrompt} />
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
      <ResizeHandle onMouseDown={onResizeStart} edge="left" />
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
    </aside>
  );
}

function CheckpointsTabPanel({
  round,
  currentIdx,
  passed,
  onSelect,
  onResetCheckpoint,
}: {
  round: AICodingRound;
  currentIdx: number;
  passed: boolean[];
  onSelect: (i: number) => void;
  onResetCheckpoint: (i: number) => void;
}) {
  return (
    <div style={{ padding: '12px 0' }}>
      <p
        style={{
          margin: '0 18px 12px',
          fontSize: 12,
          color: 'var(--text-3)',
          lineHeight: 1.55,
        }}
      >
        Tap a checkpoint to switch the editor to it. The header stepper is
        view-only — actual navigation lives here.
      </p>
      {round.checkpoints.map((cp, i) => {
        const isPassed = passed[i];
        const isActive = i === currentIdx;
        const Icon = isPassed ? Check : Circle;
        return (
          <div key={i}>
            <button
              type="button"
              onClick={() => onSelect(i)}
              aria-current={isActive ? 'step' : undefined}
              className="w-full text-left flex items-start gap-3"
              style={{
                padding: '10px 18px',
                border: 0,
                background: isActive ? 'var(--bg-sunken)' : 'transparent',
                cursor: 'pointer',
                borderLeft: isActive
                  ? '2px solid var(--accent)'
                  : '2px solid transparent',
              }}
            >
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: 20,
                  height: 20,
                  marginTop: 1,
                  borderRadius: 999,
                  background: isPassed
                    ? 'var(--forest)'
                    : isActive
                      ? 'var(--accent)'
                      : 'transparent',
                  color: isPassed || isActive ? 'var(--bg)' : 'var(--text-4)',
                  boxShadow:
                    isPassed || isActive
                      ? 'none'
                      : 'inset 0 0 0 1px var(--border-strong)',
                  flexShrink: 0,
                  fontSize: 10,
                  fontFamily: 'var(--font-mono)',
                  fontWeight: 600,
                }}
              >
                {isPassed ? <Icon size={11} strokeWidth={2.5} /> : i + 1}
              </span>
              <span
                style={{
                  flex: 1,
                  fontSize: 13,
                  fontWeight: isActive ? 500 : 400,
                  color: isActive ? 'var(--text)' : 'var(--text-2)',
                  lineHeight: 1.4,
                }}
              >
                {cp.label}
              </span>
              {!cp.ai_allowed && (
                <span
                  className="pill inline-flex items-center gap-1"
                  style={{
                    background: 'transparent',
                    color: 'var(--text-4)',
                    boxShadow: 'inset 0 0 0 1px var(--border)',
                    flexShrink: 0,
                  }}
                  title="AI assistant disabled for this checkpoint"
                >
                  <MessageSquareOff size={10} strokeWidth={2} />
                  solo
                </span>
              )}
            </button>
            {isActive && (
              <div
                style={{
                  padding: '4px 18px 14px 41px',
                  fontSize: 13,
                  color: 'var(--text-2)',
                  lineHeight: 1.55,
                }}
              >
                <BlockMarkdown text={cp.prompt} />
                <div className="flex items-center gap-2" style={{ marginTop: 10 }}>
                  <span
                    className="mono"
                    style={{
                      fontSize: 10.5,
                      color: 'var(--accent)',
                      letterSpacing: '0.08em',
                    }}
                  >
                    CURRENTLY ACTIVE
                  </span>
                  {isPassed && (
                    <button
                      type="button"
                      onClick={() => onResetCheckpoint(i)}
                      title="Reset this checkpoint"
                      className="inline-flex items-center gap-1"
                      style={{
                        marginLeft: 'auto',
                        padding: '2px 8px',
                        fontSize: 10.5,
                        letterSpacing: '0.08em',
                        border: 0,
                        borderRadius: 999,
                        background: 'transparent',
                        color: 'var(--text-3)',
                        boxShadow: 'inset 0 0 0 1px var(--border)',
                        cursor: 'pointer',
                      }}
                    >
                      <RotateCcw size={9} strokeWidth={2} />
                      RESET
                    </button>
                  )}
                </div>
              </div>
            )}
            {!isActive && i < round.checkpoints.length - 1 && (
              <div style={{ height: 1, background: 'var(--border)', margin: '0 18px' }} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function RubricPanel({ round }: { round: AICodingRound }) {
  const items = round.rubric?.items ?? [];
  if (items.length === 0) {
    return (
      <div className="p-4 text-3 text-sm">
        No rubric defined for this round.
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
        On submit, an AI reviewer scores your code against each criterion below.
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

function GuidancePanel({ round }: { round: AICodingRound }) {
  return (
    <div style={{ padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div>
        <div
          className="eyebrow"
          style={{ marginBottom: 6, color: 'var(--text-3)' }}
        >
          How this round works
        </div>
        <p
          style={{
            margin: 0,
            fontSize: 12.5,
            color: 'var(--text-2)',
            lineHeight: 1.6,
          }}
        >
          You're working a multi-file project alongside the AI pair on the
          left. Each checkpoint targets one slice of the work — usually a
          fix, then a feature, then an optimization. Use{' '}
          <strong style={{ color: 'var(--text)' }}>Run</strong> to test only
          the current checkpoint, and{' '}
          <strong style={{ color: 'var(--text)' }}>Submit</strong> to grade
          everything plus the AI rubric.
        </p>
      </div>
      <div>
        <div
          className="eyebrow"
          style={{ marginBottom: 6, color: 'var(--text-3)' }}
        >
          Tips
        </div>
        <ul
          style={{
            margin: 0,
            paddingLeft: 18,
            fontSize: 12.5,
            color: 'var(--text-2)',
            lineHeight: 1.55,
          }}
        >
          <li>
            Solo checkpoints disable the assistant — that's the cue to think
            it through yourself.
          </li>
          <li>
            The AI rubric reads your chat log alongside your code, so
            verbosity is a tell.
          </li>
          <li>
            You can run as often as you like — the harness is fast and your
            attempts aren't recorded until you Submit.
          </li>
        </ul>
      </div>
      <div>
        <div
          className="eyebrow"
          style={{ marginBottom: 6, color: 'var(--text-4)' }}
        >
          Round metadata
        </div>
        <div
          style={{
            fontSize: 12,
            color: 'var(--text-3)',
            lineHeight: 1.7,
          }}
        >
          <div>Language: <strong style={{ color: 'var(--text-2)' }}>{round.language}</strong></div>
          <div>Checkpoints: <strong style={{ color: 'var(--text-2)' }}>{round.checkpoints.length}</strong></div>
          <div>Difficulty: <strong style={{ color: 'var(--text-2)' }}>{round.difficulty}</strong></div>
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
  hideRunResult,
  runResult,
}: {
  onRun: () => void;
  onSubmit: () => void;
  onOpenLast: () => void;
  running: boolean;
  submitting: boolean;
  hasReport: boolean;
  hideRunResult: boolean;
  runResult: RunProjectResult | null;
}) {
  const busy = running || submitting;
  return (
    <>
      {!hideRunResult && runResult && (
        <span
          className="mono pill"
          style={{
            fontSize: 10.5,
            background: runResult.passed
              ? 'var(--forest-soft)'
              : 'var(--plum-soft)',
            color: runResult.passed ? 'var(--forest)' : 'var(--plum)',
            letterSpacing: '0.08em',
          }}
        >
          {runResult.passed ? 'PASS' : 'FAIL'} · {runResult.duration_ms}MS
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
        title="Run the current checkpoint tests"
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
        title="Grade every checkpoint and run the AI rubric review"
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

function RunOutput({ result }: { result: RunProjectResult }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-3" style={{ fontSize: 12 }}>
        <span
          className="pill"
          style={{
            background: result.passed ? 'var(--forest-soft)' : 'var(--plum-soft)',
            color: result.passed ? 'var(--forest)' : 'var(--plum)',
          }}
        >
          {result.passed ? 'PASS' : 'FAIL'}
        </span>
        <span className="text-3">
          {result.passed_count} passed · {result.failed_count} failed
        </span>
        <span
          className="mono ml-auto"
          style={{ fontSize: 10.5, color: 'var(--text-4)' }}
        >
          {result.duration_ms}ms
          {result.truncated ? ' · truncated' : ''}
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
      {result.stdout && (
        <Block label="stdout" body={result.stdout} />
      )}
      {result.stderr && (
        <Block label="stderr" body={result.stderr} muted />
      )}
      {!result.error && !result.stdout && !result.stderr && (
        <div className="mono text-3" style={{ fontSize: 12 }}>
          (no console output)
        </div>
      )}
    </div>
  );
}

function Block({
  label,
  body,
  muted = false,
}: {
  label: string;
  body: string;
  muted?: boolean;
}) {
  return (
    <div>
      <div className="eyebrow" style={{ marginBottom: 4 }}>
        {label}
      </div>
      <pre
        className="mono"
        style={{
          fontSize: 12,
          color: muted ? 'var(--text-3)' : 'var(--text-2)',
          background: 'var(--bg-sunken)',
          padding: 10,
          borderRadius: 'var(--radius)',
          margin: 0,
          whiteSpace: 'pre-wrap',
        }}
      >
        {body}
      </pre>
    </div>
  );
}

