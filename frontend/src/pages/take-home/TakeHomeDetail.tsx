import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import AppHeader from '../../components/shell/AppHeader';
import PageShell from '../../components/shell/PageShell';
import BackLink from '../../components/shell/BackLink';
import BlockMarkdown from '../../components/shell/BlockMarkdown';
import StatusAction from '../../components/shell/StatusAction';
import MultiFileEditor from '../../components/editor/MultiFileEditor';
import {
  getAssignment,
  runProject,
  submitAttempt,
  type RunResult,
  type SubmitResponse,
  type TakeHomeAssignment,
} from './takeHomeApi';
import { useTakeHomeDrafts } from '../../hooks/useTakeHomeDrafts';
import { usePracticeStatus } from '../../hooks/usePracticeStatus';
import { useCampaign } from '../../campaign/CampaignContext';

export default function TakeHomeDetail() {
  const { slug = '' } = useParams<{ slug: string }>();
  const { currentId: campaignId } = useCampaign();
  const [assignment, setAssignment] = useState<TakeHomeAssignment | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activePath, setActivePath] = useState<string>('');
  const [runResult, setRunResult] = useState<RunResult | null>(null);
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [report, setReport] = useState<SubmitResponse | null>(null);
  const [notes, setNotes] = useState('');
  const startedAtRef = useRef(Date.now());
  const runReqIdRef = useRef(0);
  // Setter only — display lives in <StatusAction />, which subscribes to
  // the same key via rounds:status events. `take-home` isn't yet in
  // PracticeKind; the cast keeps the same persistence key the list page
  // already uses (TakeHomeList), so the filter and detail page agree.
  const [, setPracticeStatus] = usePracticeStatus('take-home', slug);

  useEffect(() => {
    let cancelled = false;
    setAssignment(null);
    setError(null);
    setRunResult(null);
    setReport(null);
    setNotes('');
    startedAtRef.current = Date.now();
    getAssignment(slug)
      .then((a) => {
        if (!cancelled) setAssignment(a);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const { files, savedFiles, setFile, hydrated } = useTakeHomeDrafts(
    assignment,
    campaignId ?? undefined,
  );

  useEffect(() => {
    if (!hydrated) return;
    if (activePath && files[activePath] !== undefined) return;
    const first = Object.keys(files).sort()[0];
    if (first) setActivePath(first);
  }, [hydrated, files, activePath]);

  async function handleRun() {
    if (!assignment) return;
    const reqId = ++runReqIdRef.current;
    setRunning(true);
    setRunResult(null);
    setReport(null);
    try {
      const r = await runProject(assignment.slug, files);
      if (reqId !== runReqIdRef.current) return;
      setRunResult(r);
    } catch (e) {
      if (reqId !== runReqIdRef.current) return;
      setRunResult({
        score: 0,
        criteria: [],
        stdout: '',
        stderr: '',
        error: e instanceof Error ? e.message : String(e),
        duration_ms: 0,
        truncated: false,
      });
    } finally {
      if (reqId === runReqIdRef.current) setRunning(false);
    }
  }

  async function handleSubmit() {
    if (!assignment) return;
    setSubmitting(true);
    setReport(null);
    try {
      const result = await submitAttempt({
        assignment_slug: assignment.slug,
        files,
        notes,
        ai_chats: [],
        campaign_id: campaignId ?? undefined,
        duration_ms: Date.now() - startedAtRef.current,
      });
      setReport(result);
      // Auto-mark mastered when every criterion passed.
      if (
        result.harness.criteria.length > 0 &&
        result.harness.criteria.every((c) => c.passed)
      ) {
        setPracticeStatus('mastered');
      }
    } catch (e) {
      setReport({
        harness: {
          score: 0,
          criteria: [],
          stdout: '',
          stderr: '',
          error: e instanceof Error ? e.message : String(e),
          duration_ms: 0,
        },
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
          eyebrow={<BackLink to="/take-home" label="All assignments" />}
          title={assignment?.title ?? 'Take-Home'}
          chromeActions={<StatusAction kind="take-home" id={slug} />}
          compactActions={<StatusAction kind="take-home" id={slug} compact />}
          timer={slug ? { kind: 'take-home', id: slug } : undefined}
        />
      }
    >
      <div
        className="grid grid-cols-1 lg:grid-cols-[320px_1fr]"
        style={{ gap: 0, minHeight: 480 }}
      >
        <aside
          className="card"
          style={{ overflow: 'auto', borderRadius: 0, padding: 16 }}
        >
          {error && <div>Error: {error}</div>}
          {assignment && (
            <>
              <div className="text-3 text-sm mb-3">
                {assignment.language} · {assignment.time_budget_min}m budget · ai:{' '}
                {assignment.ai_policy}
              </div>
              <BlockMarkdown text={assignment.prompt_md} />
              <div className="mt-4">
                <div
                  className="text-3 text-xs mb-2"
                  style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}
                >
                  Design notes
                </div>
                <textarea
                  aria-label="Design notes for the reviewer"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Trade-offs you'd want a reviewer to know about. Optional."
                  rows={6}
                  style={{ width: '100%', resize: 'vertical', padding: 8, fontSize: 13 }}
                />
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
              disabled={!assignment || !hydrated || running || submitting}
              className="px-3 py-1.5 text-sm"
              style={{
                background: running ? 'var(--bg-elev-2)' : 'var(--accent)',
                color: running ? 'var(--text-3)' : 'var(--bg)',
                borderRadius: 6,
              }}
            >
              {running ? 'Running…' : 'Run'}
            </button>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!assignment || !hydrated || submitting || running}
              className="px-3 py-1.5 text-sm"
              style={{
                background: submitting ? 'var(--bg-elev-2)' : 'var(--success)',
                color: submitting ? 'var(--text-3)' : 'var(--bg)',
                borderRadius: 6,
              }}
            >
              {submitting ? 'Grading…' : 'Submit'}
            </button>
            {runResult && !report && (
              <span
                className="text-sm"
                style={{ color: runResult.error ? 'var(--danger)' : 'var(--text-3)' }}
              >
                {runResult.error
                  ? `error · ${runResult.error.slice(0, 80)}`
                  : `${Math.round(runResult.score * 100)} / 100 · ${runResult.duration_ms}ms`}
              </span>
            )}
          </div>
          <div style={{ flex: 1, minHeight: 0 }}>
            {assignment && hydrated && activePath && (
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
              style={{
                background: 'var(--bg-elev)',
                padding: 16,
                maxHeight: 420,
                overflow: 'auto',
              }}
            >
              <h3>Harness — {Math.round(report.harness.score * 100)} / 100</h3>
              {report.harness.error && (
                <pre
                  className="text-xs"
                  style={{ color: 'var(--danger)', whiteSpace: 'pre-wrap' }}
                >
                  {report.harness.error}
                </pre>
              )}
              <ul className="grid gap-2 mt-2">
                {report.harness.criteria.map((c) => (
                  <li key={c.id} className="card" style={{ padding: 10 }}>
                    <div className="flex items-center gap-2">
                      <strong>{c.id}</strong>
                      <span
                        style={{ color: c.passed ? 'var(--success)' : 'var(--danger)' }}
                      >
                        {c.passed ? 'pass' : 'fail'}
                      </span>
                      <span className="text-3 text-sm">weight {c.weight}</span>
                    </div>
                    {c.logs && (
                      <pre
                        className="text-xs mt-1"
                        style={{ whiteSpace: 'pre-wrap', color: 'var(--text-3)' }}
                      >
                        {c.logs}
                      </pre>
                    )}
                  </li>
                ))}
              </ul>
              <h3 className="mt-4">AI rubric review</h3>
              {report.rubric_review.skipped ? (
                <div className="card" style={{ padding: 12 }}>
                  Rubric review skipped:{' '}
                  {report.rubric_review.reason ?? 'no AI provider configured'}.
                </div>
              ) : (
                <>
                  <div style={{ fontSize: 24, fontWeight: 600 }}>
                    {Math.round(report.rubric_review.total * 100)} / 100
                  </div>
                  {report.rubric_review.parse_error && (
                    <div className="card mt-2" style={{ padding: 10 }}>
                      Couldn't parse rubric output:{' '}
                      <pre style={{ whiteSpace: 'pre-wrap' }}>
                        {report.rubric_review.parse_error}
                      </pre>
                    </div>
                  )}
                  <ul className="grid gap-2 mt-2">
                    {report.rubric_review.items.map((it) => (
                      <li key={it.id} className="card" style={{ padding: 10 }}>
                        <div className="flex items-center gap-2">
                          <strong>{it.id}</strong>
                          <span style={{ marginLeft: 'auto' }}>
                            {Math.round(it.score * 100)} / 100
                          </span>
                        </div>
                        {it.evidence && <p style={{ marginTop: 6 }}>{it.evidence}</p>}
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          ) : runResult ? (
            <div
              className="border-t"
              style={{
                background: 'var(--bg-elev)',
                padding: 12,
                maxHeight: 280,
                overflow: 'auto',
              }}
            >
              <div
                className="text-3 text-xs mb-2"
                style={{ textTransform: 'uppercase', letterSpacing: '0.08em' }}
              >
                Run output
              </div>
              {runResult.error && (
                <pre
                  className="text-sm"
                  style={{ color: 'var(--danger)', whiteSpace: 'pre-wrap' }}
                >
                  {runResult.error}
                </pre>
              )}
              <ul className="grid gap-1.5">
                {runResult.criteria.map((c) => (
                  <li key={c.id} className="text-sm">
                    <span
                      style={{ color: c.passed ? 'var(--success)' : 'var(--danger)' }}
                    >
                      {c.passed ? '✓' : '✗'}
                    </span>{' '}
                    {c.id}
                    {!c.passed && c.logs && (
                      <span className="text-3 ml-2">— {c.logs.slice(0, 120)}</span>
                    )}
                  </li>
                ))}
              </ul>
              {runResult.stderr && (
                <pre
                  className="text-xs mt-2"
                  style={{ color: 'var(--text-3)', whiteSpace: 'pre-wrap' }}
                >
                  {runResult.stderr}
                </pre>
              )}
            </div>
          ) : null}
        </main>
      </div>
    </PageShell>
  );
}
