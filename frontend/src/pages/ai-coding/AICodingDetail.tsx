import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import AppHeader from '../../components/shell/AppHeader';
import PageShell from '../../components/shell/PageShell';
import BackLink from '../../components/shell/BackLink';
import BlockMarkdown from '../../components/shell/BlockMarkdown';
import StatusAction from '../../components/shell/StatusAction';
import MultiFileEditor from '../../components/editor/MultiFileEditor';
import AIChatPanel from '../../components/ai/AIChatPanel';
import CheckpointStepper from './CheckpointStepper';
import GradeReport from './GradeReport';
import {
  getRound,
  gradeAttempt,
  persistAttempt,
  runProject,
  type AIChatLogEntry,
  type AICodingRound,
  type GradeResponse,
  type RunProjectResult,
} from './aiCodingApi';
import { useAICodingDrafts } from '../../hooks/useAICodingDrafts';
import { usePracticeStatus } from '../../hooks/usePracticeStatus';
import { useCampaign } from '../../campaign/CampaignContext';

export default function AICodingDetail() {
  const { slug = '' } = useParams<{ slug: string }>();
  const { currentId: campaignId } = useCampaign();
  const [round, setRound] = useState<AICodingRound | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activePath, setActivePath] = useState<string>('');
  const [checkpointIdx, setCheckpointIdx] = useState(0);
  const [runResult, setRunResult] = useState<RunProjectResult | null>(null);
  const [running, setRunning] = useState(false);
  const [passedByCheckpoint, setPassedByCheckpoint] = useState<boolean[]>([]);
  const [chatLog, setChatLog] = useState<AIChatLogEntry[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [report, setReport] = useState<GradeResponse | null>(null);
  // Setter only — display lives in <StatusAction />, which subscribes to
  // the same key via rounds:status events.
  const [, setPracticeStatus] = usePracticeStatus('ai-coding', slug);
  const startedAtRef = useRef(Date.now());
  const runReqIdRef = useRef(0);

  useEffect(() => {
    let cancelled = false;
    setRound(null);
    setError(null);
    setCheckpointIdx(0);
    setRunResult(null);
    setChatLog([]);
    setReport(null);
    startedAtRef.current = Date.now();
    getRound(slug)
      .then((r) => {
        if (cancelled) return;
        setRound(r);
        setPassedByCheckpoint(new Array(r.checkpoints.length).fill(false));
      })
      .catch((e) => { if (!cancelled) setError(e instanceof Error ? e.message : String(e)); });
    return () => { cancelled = true; };
  }, [slug]);

  const { files, savedFiles, setFile, hydrated } = useAICodingDrafts(round, campaignId ?? undefined);

  useEffect(() => {
    if (!hydrated) return;
    if (activePath && files[activePath] !== undefined) return;
    const first = Object.keys(files).sort()[0];
    if (first) setActivePath(first);
  }, [hydrated, files, activePath]);

  async function handleRun() {
    if (!round) return;
    const cp = round.checkpoints[checkpointIdx];
    if (!cp) return;
    const reqId = ++runReqIdRef.current;
    setRunning(true);
    setRunResult(null);
    try {
      const r = await runProject({
        files,
        language: round.language,
        test_command: cp.test_command,
        timeout_s: 30,
      });
      if (reqId !== runReqIdRef.current) return;
      setRunResult(r);
      if (r.passed) {
        setPassedByCheckpoint((prev) => {
          const next = [...prev];
          next[checkpointIdx] = true;
          return next;
        });
      }
    } catch (e) {
      if (reqId !== runReqIdRef.current) return;
      setRunResult({
        passed: false,
        passed_count: 0,
        failed_count: 0,
        stdout: '',
        stderr: '',
        error: e instanceof Error ? e.message : String(e),
        duration_ms: 0,
        truncated: false,
      });
    } finally {
      if (reqId === runReqIdRef.current) {
        setRunning(false);
      }
    }
  }

  async function handleSubmit() {
    if (!round) return;
    setSubmitting(true);
    setReport(null);
    try {
      const result = await gradeAttempt({
        round_slug: round.slug,
        files,
        ai_chats: chatLog,
      });
      setReport(result);
      // Auto-mark mastered when every checkpoint passes. No-op if the
      // user has already cycled the status to mastered manually.
      if (
        result.test_results.length > 0 &&
        result.test_results.every((tr) => tr.passed)
      ) {
        setPracticeStatus('mastered');
      }
      await persistAttempt({
        roundId: round.id,
        campaignId: campaignId ?? undefined,
        currentCheckpoint: checkpointIdx,
        files,
        test_results: result.test_results,
        rubric_review: result.rubric_review,
        ai_chats: chatLog,
        duration_ms: Date.now() - startedAtRef.current,
      });
    } catch (e) {
      // Surface error in the report; render a synthetic skipped state.
      setReport({
        test_results: [],
        rubric_review: {
          items: [],
          total: 0,
          skipped: true,
          reason: e instanceof Error ? e.message : String(e),
        },
      });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <PageShell
      header={
        <AppHeader
          eyebrow={<BackLink to="/ai-coding" label="All AI rounds" />}
          title={round?.title ?? 'AI Round'}
          chromeActions={<StatusAction kind="ai-coding" id={slug} />}
          compactActions={<StatusAction kind="ai-coding" id={slug} compact />}
        />
      }
    >
      <div
        className="grid grid-cols-1 lg:grid-cols-[280px_1fr_320px] xl:grid-cols-[320px_1fr_360px]"
        style={{
          gap: 0,
          minHeight: 480,
        }}
      >
        <aside
          className="card"
          style={{ overflow: 'auto', borderRadius: 0, padding: 16 }}
        >
          {error && <div>Error: {error}</div>}
          {round && (
            <>
              <BlockMarkdown text={round.description} />
              <div className="text-3 text-sm mt-3">
                {round.checkpoints.length} checkpoints · {round.language}
              </div>
              <div className="mt-4">
                <div className="text-3 text-xs mb-2" style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Current checkpoint
                </div>
                <CheckpointStepper
                  checkpoints={round.checkpoints}
                  currentIndex={checkpointIdx}
                  passed={passedByCheckpoint}
                  onSelect={(i) => {
                    runReqIdRef.current++;
                    setCheckpointIdx(i);
                    setRunResult(null);
                    setRunning(false);
                  }}
                />
                <div className="mt-3 text-sm" style={{ whiteSpace: 'pre-wrap' }}>
                  {round.checkpoints[checkpointIdx]?.prompt}
                </div>
              </div>
            </>
          )}
        </aside>
        <main className="flex flex-col" style={{ minHeight: 0 }}>
          <div
            className="flex items-center gap-2 border-b"
            style={{ padding: '8px 12px', background: 'var(--bg-elev)' }}
          >
            <button
              type="button"
              onClick={handleRun}
              disabled={!round || !hydrated || running}
              className="px-3 py-1.5 text-sm"
              style={{
                background: running ? 'var(--bg-elev-2)' : 'var(--accent)',
                color: running ? 'var(--text-3)' : 'var(--bg)',
                borderRadius: 6,
              }}
            >
              {running ? 'Running…' : 'Run tests'}
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!round || !hydrated || submitting || running}
              className="px-3 py-1.5 text-sm"
              style={{
                background: submitting ? 'var(--bg-elev-2)' : 'var(--success)',
                color: submitting ? 'var(--text-3)' : 'var(--bg)',
                borderRadius: 6,
              }}
            >
              {submitting ? 'Grading…' : 'Submit'}
            </button>
            {runResult && (
              <span className="text-sm" style={{ color: runResult.passed ? 'var(--success)' : 'var(--danger)' }}>
                {runResult.passed ? 'pass' : 'fail'} · {runResult.passed_count} passed · {runResult.failed_count} failed · {runResult.duration_ms}ms
              </span>
            )}
          </div>
          <div style={{ flex: 1, minHeight: 0 }}>
            {round && hydrated && activePath && (
              <MultiFileEditor
                files={files}
                savedFiles={savedFiles}
                activePath={activePath}
                onActivePathChange={setActivePath}
                onFileChange={setFile}
              />
            )}
          </div>
          {report ? (
            <div
              className="border-t"
              style={{ background: 'var(--bg-elev)', padding: 16, maxHeight: 360, overflow: 'auto' }}
            >
              <GradeReport
                testResults={report.test_results}
                rubric={round!.rubric}
                rubricReview={report.rubric_review}
                aiChats={chatLog}
              />
            </div>
          ) : runResult ? (
            <div
              className="border-t"
              style={{ background: 'var(--bg-elev)', padding: 12, maxHeight: 220, overflow: 'auto' }}
            >
              <div className="text-3 text-xs mb-2" style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Run output
                {runResult.truncated && (
                  <span className="ml-2" style={{ color: 'var(--warn)' }}>· truncated</span>
                )}
              </div>
              {runResult.error && (
                <pre className="text-sm" style={{ color: 'var(--danger)', whiteSpace: 'pre-wrap', margin: 0 }}>
                  {runResult.error}
                </pre>
              )}
              {runResult.stdout && (
                <pre className="text-sm" style={{ whiteSpace: 'pre-wrap', margin: 0 }}>
                  {runResult.stdout}
                </pre>
              )}
              {runResult.stderr && (
                <pre className="text-sm" style={{ color: 'var(--text-3)', whiteSpace: 'pre-wrap', margin: '8px 0 0 0' }}>
                  {runResult.stderr}
                </pre>
              )}
              {!runResult.error && !runResult.stdout && !runResult.stderr && (
                <div className="text-3 text-sm">(no output)</div>
              )}
            </div>
          ) : null}
        </main>
        <aside style={{ borderLeft: '1px solid var(--border)', minHeight: 0 }}>
          {round && hydrated && (
            <AIChatPanel
              key={round.id}
              roundSlug={round.slug}
              checkpointIndex={checkpointIdx}
              files={files}
              checkpointPrompt={round.checkpoints[checkpointIdx]?.prompt}
              disabled={!round.checkpoints[checkpointIdx]?.ai_allowed}
              onMessageRecorded={(m) =>
                setChatLog((log) => [
                  ...log,
                  { checkpoint: checkpointIdx, role: m.role, content: m.content, ts: Date.now() },
                ])
              }
              onApplyPatches={(patches) => {
                for (const p of patches) {
                  setFile(p.file, p.contents);
                }
              }}
            />
          )}
        </aside>
      </div>
    </PageShell>
  );
}
