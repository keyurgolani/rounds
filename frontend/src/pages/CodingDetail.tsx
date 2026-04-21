import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams } from 'react-router-dom';
import Editor from '@monaco-editor/react';
import { api } from '../api/client';
import { RunPanel } from './coding/RunPanel';
import { EvaluatePanel } from './coding/EvaluatePanel';
import type {
  TestCase,
  CodeRunResult,
  CodeEvaluateResult,
  EvaluateFilter,
} from './coding/types';
import { ArrowRight, Check, ChevronDown, ChevronUp, Copy, WrapText } from 'lucide-react';
import DifficultyPill from '../components/shell/DifficultyPill';
import PracticeStatusControl from '../components/shell/PracticeStatusControl';
import BackLink from '../components/shell/BackLink';
import InlineMarkdown from '../components/shell/InlineMarkdown';
import { usePracticeStatus } from '../hooks/usePracticeStatus';
import { useTheme } from '../theme/ThemeProvider';
import { useAuth } from '../auth/AuthProvider';
import { loadLocal, loadRemote, saveLocal, saveRemote } from '../lib/codeDraft';

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
}

const LANGUAGES = [
  { key: 'python', label: 'Python', monaco: 'python' },
  { key: 'javascript', label: 'JavaScript', monaco: 'javascript' },
  { key: 'java', label: 'Java', monaco: 'java' },
];

function extractFunctionName(code: string, lang: string): string {
  if (lang === 'java') {
    const m = code.match(/public\s+\w+\s+(\w+)\s*\(/);
    return m ? m[1] : 'Solution';
  }
  if (lang === 'javascript') {
    const m = code.match(/(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=|class\s+(\w+))/);
    if (m) return m[1] || m[2] || m[3];
    return 'solution';
  }
  const cls = code.match(/class\s+(\w+)/);
  if (cls) return cls[1];
  const m = code.match(/def\s+(\w+)\s*\(/);
  return m ? m[1] : 'solution';
}

type LeftPanel = 'solutions' | 'hints';
type RightPanel = 'run' | 'evaluate';

function StatusBar({ questionId }: { questionId: number }) {
  const [status, setStatus] = usePracticeStatus('coding', questionId, 'todo');
  return <PracticeStatusControl size="sm" status={status} onChange={setStatus} />;
}

export default function CodingDetail() {
  const { slug } = useParams<{ slug: string }>();
  const { theme } = useTheme();
  const { user } = useAuth();
  const userId = user?.id ?? null;
  const [q, setQ] = useState<CQ | null>(null);
  const [loading, setLoading] = useState(true);
  const [lang, setLang] = useState('python');
  const [code, setCode] = useState('');
  const [running, setRunning] = useState(false);
  const [runResult, setRunResult] = useState<CodeRunResult | undefined>();
  const [evalResults, setEvalResults] = useState<CodeEvaluateResult | undefined>();
  const [leftPanel, setLeftPanel] = useState<LeftPanel>('hints');
  const [rightPanel, setRightPanel] = useState<RightPanel>('evaluate');
  const [showSolution, setShowSolution] = useState(-1);
  const [leftWidth, setLeftWidth] = useState(440);
  const [rightWidth, setRightWidth] = useState(420);
  const [wordWrap, setWordWrap] = useState<'on' | 'off'>('off');
  const [copied, setCopied] = useState(false);

  // Refs for the 10-second backend sync — avoids re-creating the interval on every keystroke.
  const codeRef = useRef(code);
  useEffect(() => { codeRef.current = code; }, [code]);
  const lastSyncedRef = useRef<{ code: string; lang: string; qid: number } | null>(null);

  useEffect(() => {
    if (!slug) return;
    api
      .get<CQ>(`/api/coding/${slug}`)
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
  }, [lang, q]);

  // Load draft with precedence: remote > local > starter template.
  useEffect(() => {
    if (!q) return;
    let cancelled = false;
    async function load() {
      // Immediately apply a local draft if any — prevents flicker.
      const local = loadLocal(userId, q!.id, lang);
      if (local !== null) setCode(local);
      else setCode(q!.starter_code?.[lang] || '');
      // Then overlay a remote draft if authenticated.
      if (userId) {
        const remote = await loadRemote(userId, q!.id, lang);
        if (!cancelled && remote !== null) {
          setCode(remote);
          saveLocal(userId, q!.id, lang, remote); // sync local cache
        }
      }
    }
    load();
    return () => { cancelled = true; };
  }, [q, lang, userId]);

  // 10-second backend sync — only fires when code differs from starter and last synced value.
  useEffect(() => {
    if (!userId || !q) return;
    const interval = window.setInterval(() => {
      const current = codeRef.current;
      const starter = q.starter_code?.[lang] || '';
      if (!current || current === starter) return;
      const last = lastSyncedRef.current;
      if (last && last.code === current && last.lang === lang && last.qid === q.id) return;
      saveRemote(userId, q.id, lang, current).then(() => {
        lastSyncedRef.current = { code: current, lang, qid: q.id };
      });
    }, 10000);
    return () => window.clearInterval(interval);
  }, [userId, q, lang]);

  const handleRun = useCallback(
    async (input: Record<string, unknown>) => {
      if (!q || !code.trim()) return;
      setRunning(true);
      setRunResult(undefined);
      try {
        const res = await api.post<CodeRunResult>('/api/run', {
          code,
          language: lang === 'javascript' ? 'javascript' : lang,
          function_name: extractFunctionName(code, lang),
          input,
        });
        setRunResult(res);
      } catch (e) {
        setRunResult({
          stdout: '',
          stderr: '',
          return_value: null,
          error: String(e),
          duration_ms: 0,
          truncated: false,
        });
      } finally {
        setRunning(false);
      }
    },
    [q, code, lang]
  );

  const handleEvaluate = useCallback(
    async (filter?: EvaluateFilter) => {
      if (!q || !code.trim()) return;
      setRunning(true);
      try {
        const res = await api.post<CodeEvaluateResult>('/api/evaluate', {
          code,
          language: lang === 'javascript' ? 'javascript' : lang,
          function_name: extractFunctionName(code, lang),
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
    [q, code, lang]
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
        <BackLink to="/coding" label="Back to problems" />
      </div>
    );
  }

  const monacoTheme = theme === 'dark' ? 'vs-dark' : 'vs';

  return (
    <div className="h-full flex flex-col">
      {/* Top bar */}
      <header
        className="flex-shrink-0 flex items-center justify-between gap-3 px-5 py-2.5"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <div className="flex items-center gap-3 min-w-0">
          <BackLink to="/coding" label="Back" />
          <span style={{ color: 'var(--border-strong)' }} className="hidden sm:inline">
            |
          </span>
          <DifficultyPill level={q.difficulty} />
          <h1
            className="display-italic truncate"
            style={{ margin: 0, fontSize: 20, fontWeight: 400, color: 'var(--text)' }}
          >
            #{q.id} · {q.title}
          </h1>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <StatusBar questionId={q.id} />
        </div>
      </header>

      {/* Three-column body */}
      <div className="flex-1 min-h-0 flex flex-col lg:flex-row overflow-hidden">

        {/* Left sidebar — description + Solutions/Hints */}
        <aside
          className="flex-shrink-0 overflow-y-auto min-h-[45%] lg:min-h-0 max-h-[60%] lg:max-h-none p-5 space-y-4"
          style={{
            width: `${leftWidth}px`,
            borderRight: '1px solid var(--border)',
            borderBottom: '1px solid var(--border)',
            background: 'var(--bg)',
          }}
        >
          <InlineMarkdown
            as="div"
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

          {q.topics && q.topics.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {q.topics.map((t) => (
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
            </div>
          )}

          {/* Solutions | Hints tabs */}
          <div className="pt-2" style={{ borderTop: '1px solid var(--border)' }}>
            <div className="flex gap-1 flex-wrap">
              {(
                [
                  { key: 'solutions', label: 'Solutions' },
                  { key: 'hints', label: 'Hints' },
                ] as { key: LeftPanel; label: string }[]
              ).map((p) => {
                const on = leftPanel === p.key;
                return (
                  <button
                    key={p.key}
                    type="button"
                    onClick={() => setLeftPanel(p.key)}
                    style={{
                      padding: '5px 10px',
                      border: 0,
                      borderRadius: 999,
                      background: on ? 'var(--bg-elev)' : 'transparent',
                      boxShadow: on ? '0 0 0 1px var(--border)' : 'none',
                      color: on ? 'var(--text)' : 'var(--text-3)',
                      fontSize: 11.5,
                      fontWeight: on ? 500 : 400,
                      cursor: 'pointer',
                    }}
                  >
                    {p.label}
                  </button>
                );
              })}
            </div>

            <div className="mt-3">
              {leftPanel === 'solutions' && (
                <div className="space-y-2">
                  {q.solutions.map((sol, i) => (
                    <div key={i} className="card overflow-hidden">
                      <button
                        type="button"
                        onClick={() => setShowSolution(showSolution === i ? -1 : i)}
                        className="w-full text-left p-3 flex items-center justify-between"
                        style={{ background: 'transparent', border: 0, cursor: 'pointer' }}
                      >
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 500 }}>{sol.title}</div>
                          <div
                            className="mono"
                            style={{ fontSize: 11, color: 'var(--text-4)', marginTop: 2 }}
                          >
                            {sol.time_complexity} · {sol.space_complexity}
                          </div>
                        </div>
                        <span style={{ color: 'var(--text-3)', display: 'inline-flex' }}>
                          {showSolution === i ? (
                            <ChevronUp size={14} strokeWidth={1.7} />
                          ) : (
                            <ChevronDown size={14} strokeWidth={1.7} />
                          )}
                        </span>
                      </button>
                      {showSolution === i && (
                        <div className="px-3 pb-3 space-y-2">
                          <InlineMarkdown
                            as="p"
                            text={sol.description}
                            style={{ fontSize: 12, color: 'var(--text-3)', margin: 0 }}
                          />
                          {sol.code[lang] && (
                            <pre
                              className="mono"
                              style={{
                                fontSize: 11.5,
                                background: 'var(--bg-sunken)',
                                borderRadius: 6,
                                padding: 10,
                                color: 'var(--text-2)',
                                overflowX: 'auto',
                              }}
                            >
                              {sol.code[lang]}
                            </pre>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {leftPanel === 'hints' && (
                <div className="space-y-3">
                  {q.hints.map((hint, i) => (
                    <div key={i} className="flex items-start gap-2">
                      <span
                        className="mono"
                        style={{ fontSize: 11, color: 'var(--accent)', marginTop: 1 }}
                      >
                        {i + 1}.
                      </span>
                      <InlineMarkdown
                        text={hint}
                        style={{ fontSize: 12, color: 'var(--text-2)' }}
                      />
                    </div>
                  ))}
                  {q.tips.length > 0 && (
                    <>
                      <div
                        className="pt-2"
                        style={{ borderTop: '1px solid var(--border)' }}
                      >
                        <span className="eyebrow">Tips</span>
                      </div>
                      {q.tips.map((tip, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <ArrowRight
                            size={12}
                            strokeWidth={1.8}
                            style={{ color: 'var(--ochre)', flexShrink: 0, marginTop: 3 }}
                          />
                          <InlineMarkdown
                            text={tip}
                            style={{ fontSize: 12, color: 'var(--text-2)' }}
                          />
                        </div>
                      ))}
                    </>
                  )}
                  {q.thought_process.length > 0 && (
                    <>
                      <div
                        className="pt-2"
                        style={{ borderTop: '1px solid var(--border)' }}
                      >
                        <span className="eyebrow">Thought process</span>
                      </div>
                      {q.thought_process.map((step, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <span
                            className="mono"
                            style={{ fontSize: 11, color: 'var(--text-4)' }}
                          >
                            {i + 1}.
                          </span>
                          <InlineMarkdown
                            text={step}
                            style={{ fontSize: 12, color: 'var(--text-2)' }}
                          />
                        </div>
                      ))}
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        </aside>

        <Resizer
          onResize={(dx) =>
            setLeftWidth((w) => Math.max(260, Math.min(720, w + dx)))
          }
        />

        {/* Monaco editor */}
        <section className="flex-1 min-w-0 min-h-0 flex flex-col">
          {q.boilerplate_code?.[lang] && (
            <div
              className="flex-shrink-0 px-3 py-1.5"
              style={{ background: 'var(--bg-sunken)', borderBottom: '1px solid var(--border)' }}
            >
              <div className="flex items-center gap-2">
                <span className="mono" style={{ fontSize: 11, color: 'var(--text-4)' }}>
                  Boilerplate
                </span>
                <span style={{ fontSize: 11, color: 'var(--text-4)' }}>(read-only)</span>
              </div>
              <pre
                className="mono"
                style={{
                  fontSize: 11.5,
                  color: 'var(--text-3)',
                  marginTop: 4,
                  overflowX: 'auto',
                }}
              >
                {q.boilerplate_code[lang]}
              </pre>
            </div>
          )}
          <div className="flex-1 min-h-0 relative" style={{ background: 'var(--bg-sunken)' }}>
            <div
              className="flex items-center gap-1"
              style={{
                position: 'absolute',
                top: 10,
                right: 16,
                zIndex: 10,
              }}
            >
              <button
                type="button"
                onClick={() => setWordWrap((w) => (w === 'on' ? 'off' : 'on'))}
                aria-label={wordWrap === 'on' ? 'Disable word wrap' : 'Enable word wrap'}
                aria-pressed={wordWrap === 'on'}
                title={wordWrap === 'on' ? 'Disable word wrap' : 'Enable word wrap'}
                style={{
                  width: 28,
                  height: 28,
                  border: 0,
                  borderRadius: 6,
                  background: wordWrap === 'on' ? 'var(--accent-soft)' : 'var(--bg-elev)',
                  color: wordWrap === 'on' ? 'var(--accent)' : 'var(--text-3)',
                  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <WrapText size={14} strokeWidth={1.8} />
              </button>
              <button
                type="button"
                onClick={async () => {
                  try {
                    await navigator.clipboard.writeText(code);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1400);
                  } catch {
                    /* noop */
                  }
                }}
                aria-label="Copy code to clipboard"
                title="Copy code"
                style={{
                  width: 28,
                  height: 28,
                  border: 0,
                  borderRadius: 6,
                  background: 'var(--bg-elev)',
                  color: copied ? 'var(--forest)' : 'var(--text-3)',
                  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                {copied ? <Check size={14} strokeWidth={2} /> : <Copy size={14} strokeWidth={1.8} />}
              </button>
            </div>
            <Editor
              height="100%"
              language={LANGUAGES.find((l) => l.key === lang)?.monaco || 'python'}
              value={code}
              onChange={(val) => {
                const next = val || '';
                setCode(next);
                if (q) saveLocal(userId, q.id, lang, next);
              }}
              theme={monacoTheme}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                fontFamily: "'JetBrains Mono', monospace",
                lineNumbers: 'on',
                scrollBeyondLastLine: false,
                padding: { top: 14, bottom: 14 },
                renderLineHighlight: 'none',
                overviewRulerBorder: false,
                automaticLayout: true,
                wordWrap,
                scrollbar: {
                  verticalScrollbarSize: 6,
                  horizontalScrollbarSize: 6,
                },
              }}
            />
          </div>
        </section>

        <Resizer
          onResize={(dx) =>
            setRightWidth((w) => Math.max(260, Math.min(720, w - dx)))
          }
        />

        {/* Right sidebar — Run | Evaluate */}
        <aside
          className="flex-shrink-0 min-h-[45%] lg:min-h-0 max-h-[60%] lg:max-h-none flex flex-col"
          style={{
            width: `${rightWidth}px`,
            borderLeft: '1px solid var(--border)',
            borderTop: '1px solid var(--border)',
            background: 'var(--bg)',
          }}
        >
          {/* Run | Evaluate tab bar + language picker */}
          <div className="flex items-center gap-2 flex-shrink-0 px-5 pt-5 pb-3">
            <div className="flex gap-1 flex-wrap">
              {(
                [
                  { key: 'run', label: 'Run' },
                  { key: 'evaluate', label: 'Evaluate' },
                ] as { key: RightPanel; label: string }[]
              ).map((p) => {
                const on = rightPanel === p.key;
                return (
                  <button
                    key={p.key}
                    type="button"
                    onClick={() => setRightPanel(p.key)}
                    style={{
                      padding: '5px 10px',
                      border: 0,
                      borderRadius: 999,
                      background: on ? 'var(--bg-elev)' : 'transparent',
                      boxShadow: on ? '0 0 0 1px var(--border)' : 'none',
                      color: on ? 'var(--text)' : 'var(--text-3)',
                      fontSize: 11.5,
                      fontWeight: on ? 500 : 400,
                      cursor: 'pointer',
                    }}
                  >
                    {p.label}
                  </button>
                );
              })}
            </div>
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value)}
              className="mono ml-auto"
              aria-label="Language"
              style={{
                fontSize: 11.5,
                background: 'var(--bg-sunken)',
                border: 0,
                borderRadius: 6,
                padding: '5px 10px',
                color: 'var(--text-2)',
                boxShadow: 'inset 0 0 0 1px var(--border)',
                cursor: 'pointer',
              }}
            >
              {LANGUAGES.map((l) => (
                <option key={l.key} value={l.key}>
                  {l.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex-1 min-h-0 overflow-y-auto px-5 pb-5">
            {rightPanel === 'run' && (
              <RunPanel
                samples={q.test_cases}
                running={running}
                onRun={handleRun}
                result={runResult}
              />
            )}

            {rightPanel === 'evaluate' && (
              <EvaluatePanel
                testCases={q.test_cases}
                running={running}
                onEvaluate={handleEvaluate}
                results={evalResults?.results}
              />
            )}
          </div>
        </aside>
      </div>
    </div>
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
