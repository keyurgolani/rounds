import type { AICodingRound, AIChatLogEntry } from './aiCodingApi';
import BlockMarkdown from '../../components/shell/BlockMarkdown';
import AIPatchView from '../../components/ai/AIPatchView';
import { normaliseProposedWhitespace } from '../../components/ai/AIChatPanel';
import { splitPatches } from '../../components/ai/aiPatches';

type Props = {
  testResults: Array<{
    passed: boolean;
    passed_count: number;
    failed_count: number;
    stdout: string;
    error: string | null;
  }>;
  rubric: AICodingRound['rubric'];
  rubricReview: {
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
  aiChats?: AIChatLogEntry[];
  /** Final workspace files — used as the baseline for any AI patch
   *  diffs in the chat history so the diff has a meaningful "original"
   *  side instead of just rendering every line as an addition. */
  files?: Record<string, string>;
};

export default function GradeReport({
  testResults,
  rubric,
  rubricReview,
  aiChats = [],
  files = {},
}: Props) {
  const labelById = new Map(rubric.items.map((it) => [it.id, { label: it.label, weight: it.weight }]));
  return (
    <div className="grid gap-4">
      <section>
        <h3>Deterministic checkpoint results</h3>
        <ul className="grid gap-2">
          {testResults.map((tr, i) => (
            <li key={i} className="card" style={{ padding: 12 }}>
              <div className="flex items-center gap-2">
                <strong>Checkpoint {i + 1}</strong>
                <span style={{ color: tr.passed ? 'var(--success)' : 'var(--danger)' }}>
                  {tr.passed ? 'pass' : 'fail'}
                </span>
                <span className="text-3 text-sm">
                  {tr.passed_count} passed · {tr.failed_count} failed
                </span>
              </div>
              {tr.error && (
                <pre className="text-xs mt-2" style={{ whiteSpace: 'pre-wrap' }}>
                  {tr.error}
                </pre>
              )}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3>AI rubric review</h3>
        {rubricReview.skipped ? (
          <div className="card" style={{ padding: 12 }}>
            Rubric review skipped: {rubricReview.reason ?? 'no AI provider configured'}.
          </div>
        ) : (
          <>
            {rubricReview.parse_error && (
              <div
                className="card"
                style={{
                  padding: 10,
                  marginBottom: 10,
                  background: 'var(--warn-soft, var(--bg-sunken))',
                  borderColor: 'var(--warn)',
                }}
              >
                <div className="text-sm" style={{ fontWeight: 600 }}>
                  Couldn't parse the model's rubric output as JSON.
                </div>
                <details style={{ marginTop: 6 }}>
                  <summary className="text-3 text-xs" style={{ cursor: 'pointer' }}>
                    Show raw response
                  </summary>
                  <pre
                    className="text-xs mt-2"
                    style={{ whiteSpace: 'pre-wrap', maxHeight: 200, overflow: 'auto' }}
                  >
                    {rubricReview.parse_error}
                  </pre>
                </details>
              </div>
            )}
            <div style={{ fontSize: 24, fontWeight: 600 }}>
              {Math.round(rubricReview.total * 100)} / 100
            </div>
            <ul className="grid gap-2">
              {rubricReview.items.map((it) => {
                const meta = labelById.get(it.id);
                return (
                  <li key={it.id} className="card" style={{ padding: 12 }}>
                    <div className="flex items-center gap-2">
                      <strong>{meta?.label ?? it.id}</strong>
                      <span className="text-3 text-sm">weight {meta?.weight ?? 0}</span>
                      <span style={{ marginLeft: 'auto' }}>{Math.round(it.score * 100)} / 100</span>
                    </div>
                    {it.evidence && <p style={{ marginTop: 6 }}>{it.evidence}</p>}
                    {it.evidence_quotes && it.evidence_quotes.length > 0 && (
                      <ul style={{ marginTop: 6, fontSize: 12 }}>
                        {it.evidence_quotes.map((q, j) => (
                          <li key={j} className="text-3" style={{ marginBottom: 4 }}>
                            <code style={{ fontWeight: 500, color: 'var(--text-2)' }}>
                              {q.file}:{q.line}
                            </code>
                            <blockquote
                              style={{
                                margin: '2px 0 0 12px',
                                paddingLeft: 8,
                                borderLeft: '2px solid var(--border)',
                                color: 'var(--text-2)',
                                whiteSpace: 'pre-wrap',
                                fontFamily: 'ui-monospace, monospace',
                                fontSize: 11.5,
                              }}
                            >
                              {q.quote}
                            </blockquote>
                          </li>
                        ))}
                      </ul>
                    )}
                    {it.suggestions?.length > 0 && (
                      <ul style={{ marginTop: 6, fontSize: 13 }}>
                        {it.suggestions.map((s, i) => (
                          <li key={i}>· {s}</li>
                        ))}
                      </ul>
                    )}
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </section>
      {aiChats.length > 0 && (
        <section>
          <h3>AI chat history</h3>
          <div className="text-3 text-sm mb-2">
            {aiChats.length} message{aiChats.length === 1 ? '' : 's'} across{' '}
            {new Set(aiChats.map((c) => c.checkpoint)).size} checkpoint
            {new Set(aiChats.map((c) => c.checkpoint)).size === 1 ? '' : 's'}
          </div>
          <ul className="grid gap-2">
            {Array.from(new Set(aiChats.map((c) => c.checkpoint)))
              .sort((a, b) => a - b)
              .map((cp, i) => {
                const msgs = aiChats.filter((c) => c.checkpoint === cp);
                return (
                  <li key={cp}>
                    <details open={i === 0}>
                      <summary style={{ cursor: 'pointer', padding: '6px 0' }}>
                        Checkpoint {cp + 1} — {msgs.length} message
                        {msgs.length === 1 ? '' : 's'}
                      </summary>
                      <ul className="grid gap-2" style={{ marginLeft: 16 }}>
                        {msgs.map((m, j) => {
                          const { prose, patches } =
                            m.role === 'assistant'
                              ? splitPatches(m.content)
                              : { prose: m.content, patches: null };
                          // Persisted patches are the raw model output —
                          // run them through the same whitespace
                          // normalisation pipeline the live chat uses
                          // so the historical diff card displays clean
                          // indentation instead of the model's mangled
                          // 16-/32-/1-space leads.
                          const cleanedPatches = patches?.map((p) => {
                            const original = files[p.file];
                            if (typeof original !== 'string') return p;
                            const fixed = normaliseProposedWhitespace(
                              original,
                              p.contents,
                            );
                            return fixed === p.contents
                              ? p
                              : { ...p, contents: fixed };
                          });
                          return (
                            <li key={j} className="card" style={{ padding: 10 }}>
                              <div
                                className="text-3 text-xs mb-1"
                                style={{ textTransform: 'uppercase', letterSpacing: '0.05em' }}
                              >
                                {m.role}
                              </div>
                              {m.role === 'assistant' ? (
                                <>
                                  {prose && (
                                    <div style={{ fontSize: 13.5 }}>
                                      <BlockMarkdown text={prose} />
                                    </div>
                                  )}
                                  {cleanedPatches && cleanedPatches.length > 0 && (
                                    <div style={{ marginTop: prose ? 8 : 0 }}>
                                      <AIPatchView
                                        patches={cleanedPatches}
                                        currentFiles={files}
                                        applied
                                      />
                                    </div>
                                  )}
                                  {!prose && (!patches || patches.length === 0) && (
                                    <div style={{ whiteSpace: 'pre-wrap', fontSize: 13.5 }}>
                                      {m.content}
                                    </div>
                                  )}
                                </>
                              ) : (
                                <div style={{ whiteSpace: 'pre-wrap', fontSize: 13.5 }}>
                                  {m.content}
                                </div>
                              )}
                            </li>
                          );
                        })}
                      </ul>
                    </details>
                  </li>
                );
              })}
          </ul>
        </section>
      )}
    </div>
  );
}
