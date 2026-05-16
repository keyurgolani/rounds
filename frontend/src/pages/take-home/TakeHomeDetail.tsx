import { useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Bot,
  ChevronsLeft,
  Clock,
  GripVertical,
  History,
  MessageSquare,
  Play,
  Send,
} from 'lucide-react';
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
import { RunDock } from '../coding/RunDock';
import {
  deleteInProgressTakeHomeAttempt,
  getAssignment,
  getLatestTakeHomeAttempt,
  runProject,
  submitAttempt,
  upsertInProgressTakeHomeAttempt,
  type RunResult,
  type SubmitResponse,
  type TakeHomeAssignment,
  type TakeHomeChatEntry,
} from './takeHomeApi';
import { useTakeHomeDrafts } from '../../hooks/useTakeHomeDrafts';
import { useEditorFocus } from '../../hooks/useEditorFocus';
import { usePracticeStatus } from '../../hooks/usePracticeStatus';
import { usePersistedState } from '../../hooks/usePersistedState';
import { useCampaign } from '../../campaign/CampaignContext';

type SideTab = 'rubric' | 'notes' | 'guidance';

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
  const [running, setRunning] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [report, setReport] = useState<SubmitResponse | null>(null);
  const [reportOpen, setReportOpen] = useState(false);
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
  const [virtualFolders, setVirtualFolders] = useState<string[]>([]);
  const [chatResetVersion, setChatResetVersion] = useState(0);
  const { focus, toggle: toggleFocus } = useEditorFocus(FOCUS_KEY);
  const startedAtRef = useRef(Date.now());
  const runReqIdRef = useRef(0);
  const [, setPracticeStatus] = usePracticeStatus('take-home', slug);

  useEffect(() => {
    let cancelled = false;
    setAssignment(null);
    setError(null);
    setRunResult(null);
    setReport(null);
    setReportOpen(false);
    setChatLog([]);
    setNotes('');
    setDockOpen(false);
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
          if (
            latest.status === 'graded' &&
            latest.harness_output &&
            latest.rubric_review
          ) {
            setReport({
              harness: latest.harness_output,
              rubric_review: latest.rubric_review,
            });
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
  }, [slug, campaignId]);

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

  const { files, savedFiles, setFile, hydrated, resetToStarter } =
    useTakeHomeDrafts(assignment, campaignId ?? undefined);

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

  async function handleRun() {
    if (!assignment) return;
    const reqId = ++runReqIdRef.current;
    setRunning(true);
    setRunResult(null);
    setDockOpen(true);
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
        ai_chats: chatLog,
        campaign_id: campaignId ?? undefined,
        duration_ms: Date.now() - startedAtRef.current,
      });
      setReport(result);
      setReportOpen(true);
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
      setReportOpen(true);
    } finally {
      setSubmitting(false);
    }
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
        return (
        <div
          className="flex-1 min-h-0 flex overflow-hidden"
          style={{ minHeight: 0, position: 'relative' }}
        >
          {floatingTabs.length > 0 && <FloatingPanelTab tabs={floatingTabs} />}

          {/* CENTER — problem above editor (hidden in focus), editor with floating actions, console below. */}
          <div
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
                      onRun={handleRun}
                      onSubmit={handleSubmit}
                      onOpenLast={() => setReportOpen(true)}
                      running={running}
                      submitting={submitting}
                      hasReport={Boolean(report)}
                      runResult={runResult}
                    />
                  }
                />
              )}
            </div>

            <RunDock
              open={dockOpen}
              onOpenChange={setDockOpen}
              hasOutput={Boolean(runResult)}
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
                ) : runResult?.error ? (
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
              {runResult && <RunOutput result={runResult} />}
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
        );
      })()}

      <SubmissionModal
        open={reportOpen}
        onClose={() => setReportOpen(false)}
        title={`Submission · ${assignment?.title ?? 'Real World Problem'}`}
        subtitle={
          report
            ? `Harness ${Math.round(report.harness.score * 100)}/100 · Rubric ${report.rubric_review.skipped ? '—' : Math.round(report.rubric_review.total * 100) + '/100'}`
            : undefined
        }
      >
        {report && <ReportPanel report={report} />}
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

function ResizeHandle({
  onMouseDown,
  edge,
}: {
  onMouseDown: (e: React.MouseEvent) => void;
  edge: 'left' | 'right';
}) {
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize panel"
      onMouseDown={onMouseDown}
      style={{
        position: 'absolute',
        top: 0,
        bottom: 0,
        width: 6,
        cursor: 'col-resize',
        zIndex: 5,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        ...(edge === 'right' ? { right: -3 } : { left: -3 }),
      }}
    >
      <span
        aria-hidden="true"
        style={{ opacity: 0, color: 'var(--text-4)', transition: 'opacity 120ms' }}
        className="rounds-resize-grip"
      >
        <GripVertical size={12} strokeWidth={1.8} />
      </span>
      <style>{`
        .rounds-resize-grip { opacity: 0; }
        [role="separator"]:hover .rounds-resize-grip { opacity: 0.6; }
      `}</style>
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

function ReportPanel({ report }: { report: SubmitResponse }) {
  const harnessPct = Math.round(report.harness.score * 100);
  const review = report.rubric_review;
  const reviewPct = Math.round(review.total * 100);

  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-3" style={{ gridTemplateColumns: '1fr 1fr' }}>
        <ScoreTile label="Harness" pct={harnessPct} />
        <ScoreTile
          label="Rubric review"
          pct={reviewPct}
          muted={review.skipped}
          subline={review.skipped ? 'skipped' : undefined}
        />
      </div>

      <div>
        <div className="eyebrow" style={{ marginBottom: 8 }}>
          Harness criteria
        </div>
        {report.harness.error && (
          <pre
            className="mono"
            style={{
              fontSize: 12,
              color: 'var(--plum)',
              background: 'var(--bg-sunken)',
              padding: 10,
              borderRadius: 'var(--radius)',
              margin: '0 0 8px',
              whiteSpace: 'pre-wrap',
            }}
          >
            {report.harness.error}
          </pre>
        )}
        <ul style={{ margin: 0, padding: 0, listStyle: 'none', display: 'grid', gap: 6 }}>
          {report.harness.criteria.map((c) => (
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
      </div>

      <div>
        <div className="eyebrow" style={{ marginBottom: 8 }}>
          AI rubric review
        </div>
        {review.skipped ? (
          <div
            style={{
              padding: 12,
              background: 'var(--bg-sunken)',
              borderRadius: 'var(--radius)',
              fontSize: 12.5,
              color: 'var(--text-3)',
            }}
          >
            Skipped: {review.reason ?? 'no AI provider configured'}.
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
