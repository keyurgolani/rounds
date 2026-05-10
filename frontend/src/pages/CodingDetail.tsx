import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import MultiFileEditor from '../components/editor/MultiFileEditor';
import { getCodingQuestion } from '../content/api';
import {
  deleteCodeDraft,
  listCodeDrafts,
  upsertCodeDraft,
} from '../lib/codeDraftsApi';
import { evaluateCode, runCode } from './coding/runnerApi';
import { RunDock } from './coding/RunDock';
import { RightDock, type SideTab } from './coding/RightDock';
import { ConsoleTab } from './coding/ConsoleTab';
import type {
  TestCase,
  CodeRunResult,
  CodeEvaluateResult,
  EvaluateFilter,
  Entry,
} from './coding/types';
import { Check, FileText, Play, Terminal, X } from 'lucide-react';
import AppHeader from '../components/shell/AppHeader';
import DifficultyPill from '../components/shell/DifficultyPill';
import StatusAction from '../components/shell/StatusAction';
import BackLink from '../components/shell/BackLink';
import InlineMarkdown from '../components/shell/InlineMarkdown';
import BlockMarkdown from '../components/shell/BlockMarkdown';
import { useAuth } from '../auth/AuthProvider';
import { loadLocal, saveLocal } from '../lib/codeDraft';
import { useCampaign } from '../campaign/CampaignContext';
import Select from '../components/shell/Select';

interface CQ {
  id: number;
  title: string;
  difficulty: string;
  description: string;
  hints: string[];
  constraints: string[];
  starter_code: Record<string, string>;
  boilerplate_code: Record<string, string>;
  test_cases: TestCase[];
  solutions: {
    title: string;
    time_complexity: string;
    space_complexity: string;
    description: string;
    code: Record<string, string>;
  }[];
  thought_process: string[];
  tips: string[];
  companies: string[];
  topics: string[];
  time_complexity: string;
  space_complexity: string;
  entry: Entry;
}

const LANGUAGES = [
  { key: 'python', label: 'Python', monaco: 'python' },
  { key: 'javascript', label: 'JavaScript', monaco: 'javascript' },
  { key: 'java', label: 'Java', monaco: 'java' },
];

// Mobile lives in "editor-first" mode: the editor owns the whole
// viewport and the two side panels become bottom sheets that slide up
// on demand. `null` = no sheet open (user is writing code).
type MobileSheet = 'problem' | 'results' | null;

const EDITOR_FOCUS_STORAGE_KEY = 'rounds:editor-focus';

// Editor focus mode — hides the left/right asides + bottom Console
// so the Monaco editor claims the whole flex row. Mirrors the
// useMinimalHeader pattern in AppHeader.tsx (localStorage-backed,
// no mobile auto-trigger because the Focus button is desktop-only).
function useEditorFocus() {
  const [focus, setFocus] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem(EDITOR_FOCUS_STORAGE_KEY) === 'true';
  });

  const toggle = useCallback(() => {
    setFocus((f) => {
      const next = !f;
      window.localStorage.setItem(EDITOR_FOCUS_STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  // Esc exits focus when active. No-op when inactive — pressing Esc
  // on a normal coding page should not toggle anything.
  useEffect(() => {
    if (!focus) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setFocus(false);
        window.localStorage.setItem(EDITOR_FOCUS_STORAGE_KEY, 'false');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [focus]);

  return { focus, toggle };
}

export default function CodingDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const [q, setQ] = useState<CQ | null>(null);
  const [loading, setLoading] = useState(true);
  const [lang, setLang] = useState('python');
  const [code, setCode] = useState('');
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<CodeRunResult | undefined>();
  const [lastRunInput, setLastRunInput] = useState<unknown>(undefined);
  const [evalResults, setEvalResults] = useState<CodeEvaluateResult | undefined>();
  const [consoleOpen, setConsoleOpen] = useState(false);
  const [sideTab, setSideTab] = useState<SideTab>('tests');
  const [mobileSheet, setMobileSheet] = useState<MobileSheet>(null);
  const [rightWidth, setRightWidth] = useState(440);
  const { focus, toggle: toggleFocus } = useEditorFocus();

  // Refs for the 10-second backend sync — avoids re-creating the interval on every keystroke.
  const codeRef = useRef(code);
  useEffect(() => { codeRef.current = code; }, [code]);

  const lastSyncedRef = useRef<{ code: string; lang: string; qid: string | number; draftId: string | null } | null>(null);
  const starterRef = useRef<string>('');

  const { currentId: campaignId } = useCampaign();

  useEffect(() => {
    if (!slug) return;
    getCodingQuestion<CQ>(slug)
      .then((data) => {
        setQ(data);
      })
      .finally(() => setLoading(false));
  }, [slug]);

  // Reset run/eval results when language or question changes.
  useEffect(() => {
    if (!q) return;
    setRunResult(undefined);
    setEvalResults(undefined);
    setConsoleOpen(false);
  }, [lang, q]);

  // Load draft in priority order: PocketBase (source of truth) → local
  // cache (continuity for offline tabs) → starter skeleton. The remote
  // row is tracked via lastSyncedRef so the 10s interval below can
  // decide whether to upsert, update, or delete.
  useEffect(() => {
    if (!q) return;
    const starter = q.starter_code?.[lang] || '';
    starterRef.current = starter;
    let cancelled = false;

    (async () => {
      let chosen: string | null = null;
      let draftId: string | null = null;

      if (campaignId) {
        try {
          const rows = await listCodeDrafts({
            campaign_id: campaignId,
            question: String(q.id),
            language: lang,
          });
          if (rows.length > 0) {
            chosen = rows[0].code;
            draftId = rows[0].id;
          }
        } catch {
          /* fall through to local */
        }
      }

      if (chosen === null) {
        const local = loadLocal(userId, q.id, lang);
        if (local !== null) chosen = local;
      }

      if (chosen === null) chosen = starter;

      if (cancelled) return;
      setCode(chosen);
      lastSyncedRef.current = {
        code: chosen,
        lang,
        qid: q.id,
        draftId,
      };
    })();

    return () => {
      cancelled = true;
    };
  }, [q, lang, userId, campaignId]);

  // 10-second remote sync: upserts the PB code_drafts row when the
  // local buffer has drifted, and deletes the row when the user has
  // reverted to the starter template so the listing stays clean.
  useEffect(() => {
    if (!q) return;
    if (!campaignId) return;
    // Capture the narrowed type so the nested `flush` closure doesn't
    // lose it through control-flow analysis.
    const cid = campaignId;
    const qid = q.id;

    async function flush() {
      const last = lastSyncedRef.current;
      if (!last) return;
      const code = codeRef.current;
      if (code === last.code) return;
      const starter = starterRef.current;

      try {
        if (code === starter) {
          if (last.draftId) {
            await deleteCodeDraft(last.draftId);
            lastSyncedRef.current = { ...last, code, draftId: null };
          }
          return;
        }
        const saved = await upsertCodeDraft({
          campaign_id: cid,
          question: String(qid),
          language: last.lang,
          code,
        });
        lastSyncedRef.current = { ...last, code, draftId: saved.id };
      } catch {
        /* retry next tick */
      }
    }

    const id = window.setInterval(flush, 10_000);
    function onVisibility() {
      if (document.visibilityState === 'hidden') void flush();
    }
    document.addEventListener('visibilitychange', onVisibility);
    return () => {
      window.clearInterval(id);
      document.removeEventListener('visibilitychange', onVisibility);
      void flush();
    };
  }, [q, campaignId]);

  // Escape key closes the open mobile sheet (common bottom-sheet UX).
  // Desktop ignores the state entirely so this is a no-op there.
  useEffect(() => {
    if (!mobileSheet) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileSheet(null);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [mobileSheet]);

  const hasConsoleOutput = Boolean(
    runResult && (runResult.stdout || runResult.stderr || runResult.truncated)
  );

  // MultiFileEditor expects a files map even in single-file mode. We
  // synthesise a one-entry map keyed by an extension that matches the
  // language so Monaco's path-based language detection lines up.
  const langExt = lang === 'javascript' ? 'js' : lang === 'java' ? 'java' : 'py';
  const singleFilePath = `solution.${langExt}`;
  const singleFile = useMemo(
    () => ({ [singleFilePath]: code }),
    [singleFilePath, code],
  );

  useEffect(() => {
    if (hasConsoleOutput) setConsoleOpen(true);
  }, [hasConsoleOutput]);

  const handleRun = useCallback(
    async (input: Record<string, unknown>) => {
      if (!q || !code.trim()) return;
      setLastRunInput(input);
      setRunning(true);
      setRunResult(undefined);
      setConsoleOpen(false);
      // Pop the Results sheet so the user sees output animate in.
      // Skip in focus mode — the right aside is unmounted and the
      // mobile dock is hidden, so leaving the dead state would
      // also confuse the Esc handler when exiting focus.
      if (!focus) setMobileSheet('results');
      try {
        const res = await runCode({
          code,
          language: lang === 'javascript' ? 'javascript' : lang,
          entry: q.entry,
          input,
        });
        setRunResult(res);
        setSideTab('run');
      } catch (e) {
        setRunResult({
          stdout: '',
          stderr: '',
          return_value: null,
          error: String(e),
          duration_ms: 0,
          truncated: false,
        });
        setSideTab('run');
      } finally {
        setRunning(false);
      }
    },
    [q, code, lang, focus]
  );

  const handleEvaluate = useCallback(
    async (filter?: EvaluateFilter) => {
      if (!q || !code.trim()) return;
      setSideTab('tests');
      setRunning(true);
      // See handleRun above — skip the mobile-sheet pop in focus mode.
      if (!focus) setMobileSheet('results');
      try {
        const res = await evaluateCode({
          code,
          language: lang === 'javascript' ? 'javascript' : lang,
          entry: q.entry,
          test_cases: q.test_cases,
          filter,
        });
        setEvalResults((prev) => {
          if (!prev) return res;
          const merged = [...prev.results];
          for (const r of res.results) {
            const idx = merged.findIndex((m) => m.index === r.index);
            if (idx >= 0) merged[idx] = r;
            else merged.push(r);
          }
          merged.sort((a, b) => a.index - b.index);
          const passed = merged.filter((r) => r.passed).length;
          const failed = merged.filter((r) => !r.passed).length;
          return { passed, failed, results: merged };
        });
      } finally {
        setRunning(false);
      }
    },
    [q, code, lang, focus]
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full" style={{ color: 'var(--text-4)' }}>
        Loading…
      </div>
    );
  }

  if (!q) {
    return (
      <div className="flex items-center justify-center h-full">
        <BackLink to="/coding/questions" label="Back to practice" />
      </div>
    );
  }


  return (
    <div className="h-full flex flex-col relative">
      <AppHeader
        title={q.title}
        eyebrow={
          <span
            style={{
              display: 'inline-flex',
              gap: 8,
              alignItems: 'center',
              flexWrap: 'wrap',
            }}
          >
            <BackLink to="/coding/questions" />
            <DifficultyPill level={q.difficulty} />
            {q.topics?.map((t) => (
              <span
                key={t}
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
          </span>
        }
        chromeActions={<StatusAction kind="coding" id={q.id} />}
        compactActions={<StatusAction kind="coding" id={q.id} compact />}
        timer={q ? { kind: 'coding', id: q.id } : undefined}
      />

      {/* Three-column body. On mobile (`data-mobile-sheet`) the editor
          owns the whole area and the two side asides position-absolute
          themselves as bottom sheets that slide up on demand. On lg+
          all three are visible side-by-side and `data-mobile-sheet`
          is inert. */}
      <div
        className="flex-1 min-h-0 flex flex-col lg:flex-row overflow-hidden relative"
        data-mobile-sheet={mobileSheet ?? ''}
      >
        {/* Sheet backdrop — only visible when a sheet is open. Tapping
            it closes the sheet. Pointer-events toggle on data-open so
            closed sheets never intercept taps on the editor. */}
        <div
          className="coding-sheet-backdrop lg:hidden"
          data-open={mobileSheet ? 'true' : 'false'}
          onClick={() => setMobileSheet(null)}
          aria-hidden="true"
        />

        {/* Mobile-only Problem sheet. Carries description + constraints
            because the mobile editor is full-screen (the desktop above-
            editor description bar is hidden on mobile). Hints + Solutions
            live in the right-dock tabs now, not here. */}
        {mobileSheet === 'problem' && (
          <aside
            className="flex-shrink-0 flex flex-col w-full coding-side-left lg:hidden"
            style={{
              borderBottom: '1px solid var(--border)',
              background: 'var(--bg)',
              maxHeight: '38vh',
            }}
          >
          <SheetHeader title="Problem" onClose={() => setMobileSheet(null)} />
          <div
            className="flex-1 overflow-y-auto px-4 sm:px-5 pt-4 pb-3 space-y-3"
            style={{ overscrollBehavior: 'contain' }}
          >
            <BlockMarkdown
              text={q.description}
              style={{
                fontSize: 13.5,
                color: 'var(--text-2)',
                lineHeight: 1.65,
              }}
            />
            {q.constraints.length > 0 && (
              <div>
                <h3 className="eyebrow mb-1.5">Constraints</h3>
                <ul className="space-y-0.5">
                  {q.constraints.map((c, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-1.5"
                      style={{ fontSize: 12, color: 'var(--text-3)' }}
                    >
                      <span style={{ color: 'var(--text-4)' }}>•</span>
                      <InlineMarkdown text={c} className="break-words" />
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          </aside>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minWidth: 0 }}>
        {/* Monaco editor — always visible on mobile (the sheet-over-
            editor pattern). On desktop a horizontal bar above the
            editor carries the problem description + constraints; on
            mobile those live in the Problem sheet (left aside). */}
        <section className="coding-editor flex-1 min-w-0 lg:min-h-0 flex flex-col" style={{ flex: 1, minHeight: 0 }}>
          {/* Desktop-only problem-detail bar above the editor. Capped
              at ~28vh and scrolled internally so a long description
              never starves the editor of vertical space. Hidden in
              focus mode along with the side panels. */}
          {!focus && (
            <div
              className="hidden lg:block flex-shrink-0"
              style={{
                background: 'var(--bg)',
                borderBottom: '1px solid var(--border)',
                maxHeight: '28vh',
                overflow: 'auto',
              }}
            >
              <div className="px-4 py-3 space-y-3">
                <BlockMarkdown
                  text={q.description}
                  style={{ fontSize: 13, color: 'var(--text-2)', lineHeight: 1.6 }}
                />
                {q.constraints.length > 0 && (
                  <div>
                    <h3 className="eyebrow mb-1">Constraints</h3>
                    <ul className="space-y-0.5">
                      {q.constraints.map((c, i) => (
                        <li
                          key={i}
                          className="flex items-start gap-1.5"
                          style={{ fontSize: 12, color: 'var(--text-3)' }}
                        >
                          <span style={{ color: 'var(--text-4)' }}>•</span>
                          <InlineMarkdown text={c} className="break-words" />
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="flex-1 min-h-0 relative" style={{ background: 'var(--bg-sunken)' }}>
            <MultiFileEditor
              hideExplorer
              files={singleFile}
              activePath={singleFilePath}
              onActivePathChange={() => { /* no-op — single-file mode */ }}
              onFileChange={(_p, contents) => {
                setCode(contents);
                if (q) saveLocal(userId, q.id, lang, contents);
              }}
              languageOverride={
                LANGUAGES.find((l) => l.key === lang)?.monaco || 'python'
              }
              storageKey="rounds:editor.coding"
              focused={focus}
              onFocusToggle={toggleFocus}
              editorOptions={{
                fontSize: 13,
                fontFamily: "'JetBrains Mono', monospace",
                lineNumbers: 'on',
                renderLineHighlight: 'none',
                overviewRulerBorder: false,
                automaticLayout: true,
                padding: { top: 14, bottom: 14 },
                scrollbar: {
                  verticalScrollbarSize: 6,
                  horizontalScrollbarSize: 6,
                },
              }}
              topRightExtras={
                <>
                  <Select
                    value={lang}
                    onChange={setLang}
                    options={LANGUAGES.map((l) => ({ value: l.key, label: l.label }))}
                    ariaLabel="Language"
                    fullWidth={false}
                    align="right"
                  />
                  {focus && (
                    <button
                      type="button"
                      onClick={() => handleEvaluate()}
                      disabled={running || (q?.test_cases.length ?? 0) === 0}
                      aria-label={
                        evalResults
                          ? `Run all tests. Last run: ${evalResults.passed} of ${evalResults.passed + evalResults.failed} passed.`
                          : 'Run all tests'
                      }
                      className="inline-flex items-center gap-1.5"
                      style={{
                        padding: '5px 12px',
                        height: 26,
                        fontSize: 11,
                        fontWeight: 500,
                        background: 'var(--ink)',
                        color: 'var(--paper)',
                        border: 0,
                        borderRadius: 999,
                        cursor: running ? 'wait' : 'pointer',
                        opacity: running ? 0.6 : 1,
                        whiteSpace: 'nowrap',
                      }}
                    >
                      <Play size={10} strokeWidth={1.9} />
                      {running
                        ? 'Running…'
                        : evalResults
                          ? (
                              <span
                                style={{
                                  color:
                                    evalResults.failed === 0
                                      ? 'var(--status-pass)'
                                      : 'var(--status-fail)',
                                }}
                              >
                                {evalResults.passed}/{evalResults.passed + evalResults.failed}
                              </span>
                            )
                          : `Run all (${q?.test_cases.length ?? 0})`}
                    </button>
                  )}
                </>
              }
            />
          </div>

          {/* Mobile-only editor bottom strip — just the language picker,
              since MultiFileEditor's own wrap/copy toolbar is hidden
              below the `sm` breakpoint. */}
          <div
            className="flex sm:hidden items-center flex-shrink-0 px-3 py-2"
            style={{ background: 'var(--bg)', borderTop: '1px solid var(--border)' }}
          >
            <Select
              value={lang}
              onChange={setLang}
              options={LANGUAGES.map((l) => ({ value: l.key, label: l.label }))}
              ariaLabel="Language"
              fullWidth={false}
              align="left"
              style={{ minWidth: 124 }}
            />
          </div>
        </section>

        {!focus && (
          <RunDock
            open={consoleOpen}
            onOpenChange={setConsoleOpen}
            hasOutput={hasConsoleOutput}
          >
            <ConsoleTab result={runResult} />
          </RunDock>
        )}
        </div>

        {!focus && (
          <Resizer
            onResize={(dx) =>
              setRightWidth((w) => Math.max(280, Math.min(720, w - dx)))
            }
          />
        )}

        {!focus && (
          <aside
            className="flex-shrink-0 flex flex-col w-full coding-side-right"
            style={{
              ['--side-width' as string]: `${rightWidth}px`,
              borderTop: '1px solid var(--border)',
              background: 'var(--bg)',
              maxHeight: '38vh',
            }}
          >
            <SheetHeader title="Run" onClose={() => setMobileSheet(null)} />
            <RightDock
              activeTab={sideTab}
              onTabChange={setSideTab}
              entry={q.entry}
              testCases={q.test_cases}
              running={running}
              onRun={(input) => handleRun(input as Record<string, unknown>)}
              onEvaluate={(filter) => handleEvaluate(filter)}
              runResult={runResult}
              runInput={lastRunInput}
              evalResult={evalResults}
              hints={q.hints}
              tips={q.tips}
              thoughtProcess={q.thought_process}
              solutions={q.solutions}
              language={lang}
              onLoadSolutionIntoEditor={(next) => {
                if (
                  code.trim() !== '' &&
                  code !== starterRef.current &&
                  !confirm('Replace current editor contents with this solution?')
                ) {
                  return;
                }
                setCode(next);
              }}
            />
          </aside>
        )}
      </div>

      {/* Mobile-only bottom dock. Two buttons to summon the Problem
          and Results sheets; the Evaluate FAB floats above the dock's
          right side. Hidden on lg+ where the 3-pane layout already
          exposes everything. */}
      <nav
        aria-label="Coding detail panels"
        className="coding-mobile-dock flex lg:hidden flex-shrink-0"
        style={{
          minHeight: 'var(--coding-mobile-dock-h)',
          borderTop: '1px solid var(--border)',
          background: 'var(--bg-elev)',
        }}
      >
        <DockButton
          icon={FileText}
          label="Problem"
          active={mobileSheet === 'problem'}
          onClick={() =>
            setMobileSheet(mobileSheet === 'problem' ? null : 'problem')
          }
        />
        <DockButton
          icon={Terminal}
          label="Results"
          active={mobileSheet === 'results'}
          onClick={() =>
            setMobileSheet(mobileSheet === 'results' ? null : 'results')
          }
        />
      </nav>
    </div>
  );
}

function SheetHeader({
  title,
  onClose,
}: {
  title: string;
  onClose: () => void;
}) {
  // Rendered inside each side aside. Hidden on desktop — the aside is
  // just a pinned panel there. On mobile it provides the drag handle,
  // drag-to-dismiss gesture, and close button expected of a bottom
  // sheet. `touch-action: none` blocks the browser's pull-to-refresh
  // while the user drags the handle so the page never reloads mid-
  // gesture.
  const startYRef = useRef<number | null>(null);
  const asideRef = useRef<HTMLElement | null>(null);
  const DISMISS_THRESHOLD = 80;

  const setSheetTranslate = (px: number | null) => {
    if (!asideRef.current) return;
    if (px === null) {
      asideRef.current.style.transform = '';
      asideRef.current.style.transition = '';
    } else {
      // Overrides the CSS `translateY(0)` while the finger is down.
      asideRef.current.style.transition = 'none';
      asideRef.current.style.transform = `translateY(${Math.max(0, px)}px)`;
    }
  };

  const onTouchStart = (e: React.TouchEvent<HTMLDivElement>) => {
    startYRef.current = e.touches[0].clientY;
    const el = e.currentTarget.closest(
      '.coding-side-left, .coding-side-right'
    ) as HTMLElement | null;
    asideRef.current = el;
    setSheetTranslate(0);
  };

  const onTouchMove = (e: React.TouchEvent<HTMLDivElement>) => {
    if (startYRef.current === null || !asideRef.current) return;
    const delta = e.touches[0].clientY - startYRef.current;
    setSheetTranslate(delta);
  };

  const onTouchEnd = (e: React.TouchEvent<HTMLDivElement>) => {
    if (startYRef.current === null || !asideRef.current) return;
    const endY = e.changedTouches[0]?.clientY ?? startYRef.current;
    const delta = endY - startYRef.current;
    // Let the CSS transition animate the final glide in either case.
    setSheetTranslate(null);
    if (delta > DISMISS_THRESHOLD) onClose();
    startYRef.current = null;
    asideRef.current = null;
  };

  return (
    <div
      className="lg:hidden flex-shrink-0 relative flex items-center px-4 pt-3 pb-2"
      style={{
        borderBottom: '1px solid var(--border)',
        touchAction: 'none',
        cursor: 'grab',
        userSelect: 'none',
      }}
      onTouchStart={onTouchStart}
      onTouchMove={onTouchMove}
      onTouchEnd={onTouchEnd}
      onTouchCancel={onTouchEnd}
    >
      <span
        aria-hidden="true"
        style={{
          position: 'absolute',
          left: '50%',
          top: 6,
          transform: 'translateX(-50%)',
          width: 36,
          height: 4,
          borderRadius: 999,
          background: 'var(--border-strong)',
        }}
      />
      <span
        className="mono uppercase"
        style={{ fontSize: 10.5, color: 'var(--text-3)', letterSpacing: '0.14em', marginTop: 8 }}
      >
        {title}
      </span>
      <button
        type="button"
        onClick={onClose}
        aria-label="Close sheet"
        className="ml-auto inline-flex items-center justify-center"
        style={{
          marginTop: 8,
          width: 28,
          height: 28,
          borderRadius: 999,
          border: 0,
          background: 'var(--bg-sunken)',
          color: 'var(--text-3)',
          boxShadow: 'inset 0 0 0 1px var(--border)',
          cursor: 'pointer',
        }}
      >
        <X size={13} strokeWidth={2} />
      </button>
    </div>
  );
}

function DockButton({
  icon: Icon,
  label,
  active,
  onClick,
}: {
  icon: typeof FileText;
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className="flex-1 relative inline-flex flex-col items-center justify-center gap-0.5"
      style={{
        border: 0,
        background: 'transparent',
        color: active ? 'var(--accent)' : 'var(--text-3)',
        fontSize: 10.5,
        fontWeight: active ? 600 : 500,
        letterSpacing: '0.02em',
        cursor: 'pointer',
        transition: 'color 140ms',
      }}
    >
      {active && (
        <span
          style={{
            position: 'absolute',
            left: '30%',
            right: '30%',
            top: 0,
            height: 2,
            background: 'var(--accent)',
            borderRadius: '0 0 2px 2px',
          }}
        />
      )}
      <Icon size={18} strokeWidth={active ? 2 : 1.6} />
      {label}
    </button>
  );
}

function Resizer({ onResize }: { onResize: (dx: number) => void }) {
  const [hovered, setHovered] = useState(false);

  const handleMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    let lastX = e.clientX;
    const onMove = (ev: MouseEvent) => {
      const dx = ev.clientX - lastX;
      lastX = ev.clientX;
      onResize(dx);
    };
    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  };

  return (
    <div
      onMouseDown={handleMouseDown}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      role="separator"
      aria-orientation="vertical"
      className="hidden lg:block flex-shrink-0"
      style={{
        width: 6,
        cursor: 'col-resize',
        background: 'transparent',
        position: 'relative',
      }}
    >
      {/* Full-height separator line */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          bottom: 0,
          left: '50%',
          width: 1,
          background: 'var(--border)',
          transform: 'translateX(-50%)',
          pointerEvents: 'none',
        }}
      />
      {/* Grip pill at vertical center */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          width: 6,
          height: 32,
          borderRadius: 4,
          background: hovered ? 'var(--accent)' : 'var(--border-strong)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 3,
          pointerEvents: 'none',
          transition: 'background 0.15s ease',
        }}
      >
        <span style={{ width: 2, height: 2, borderRadius: 999, background: 'var(--bg-elev)' }} />
        <span style={{ width: 2, height: 2, borderRadius: 999, background: 'var(--bg-elev)' }} />
        <span style={{ width: 2, height: 2, borderRadius: 999, background: 'var(--bg-elev)' }} />
      </div>
    </div>
  );
}
