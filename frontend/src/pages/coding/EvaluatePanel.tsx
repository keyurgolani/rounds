import { useMemo, useState } from 'react';
import { Play } from 'lucide-react';
import type { TestCase, EvaluateCaseResult, EvaluateFilter } from './types';
import { TestCaseCard } from './TestCaseCard';

interface EvaluatePanelProps {
  testCases: TestCase[];
  running: boolean;
  onEvaluate: (filter?: EvaluateFilter) => void;
  results?: EvaluateCaseResult[];
}

export function EvaluatePanel({
  testCases,
  running,
  onEvaluate,
  results = [],
}: EvaluatePanelProps) {
  const [filterTag, setFilterTag] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());

  const tagCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const tc of testCases) {
      for (const t of tc.tags ?? []) {
        counts.set(t, (counts.get(t) ?? 0) + 1);
      }
    }
    return Array.from(counts.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [testCases]);

  const resultByIndex = useMemo(() => {
    const m = new Map<number, EvaluateCaseResult>();
    for (const r of results) m.set(r.index, r);
    return m;
  }, [results]);

  const visible = useMemo(() => {
    if (!filterTag) return testCases.map((tc, i) => ({ tc, i }));
    return testCases
      .map((tc, i) => ({ tc, i }))
      .filter(({ tc }) => (tc.tags ?? []).includes(filterTag));
  }, [testCases, filterTag]);

  const passed = results.filter((r) => r.passed).length;
  const failed = results.filter((r) => !r.passed).length;
  const notRun = testCases.length - results.length;
  const total = testCases.length;
  const run = results.length;
  const pct = total ? passed / total : 0;

  return (
    <div className="space-y-3">
      {/* Summary bar */}
      <div className="card" style={{ padding: '12px 14px' }}>
        <div className="flex items-center justify-between gap-3 mb-2.5">
          <div className="flex items-baseline gap-2">
            <span
              className="display-italic"
              style={{ fontSize: 24, lineHeight: 1, fontWeight: 400 }}
            >
              {run === 0 ? '—' : `${passed}/${total}`}
            </span>
            <span
              className="mono uppercase"
              style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.12em' }}
            >
              {run === 0 ? 'not run' : 'passing'}
            </span>
          </div>
          <button
            type="button"
            onClick={() => onEvaluate(undefined)}
            disabled={running}
            className="inline-flex items-center gap-1.5"
            style={{
              padding: '6px 12px',
              border: 0,
              borderRadius: 'var(--radius)',
              background: 'var(--accent)',
              color: 'var(--bg-elev)',
              fontSize: 11.5,
              fontWeight: 500,
              cursor: running ? 'wait' : 'pointer',
              opacity: running ? 0.6 : 1,
            }}
          >
            <Play size={10} strokeWidth={1.8} />
            {running ? 'Evaluating…' : `Evaluate all (${total})`}
          </button>
        </div>

        <div
          style={{
            position: 'relative',
            height: 6,
            borderRadius: 3,
            background: 'var(--paper-3)',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              position: 'absolute',
              inset: 0,
              width: `${pct * 100}%`,
              background: 'var(--forest)',
              borderRadius: 3,
            }}
          />
          {failed > 0 && (
            <div
              style={{
                position: 'absolute',
                top: 0,
                bottom: 0,
                left: `${pct * 100}%`,
                width: `${(failed / total) * 100}%`,
                background: 'var(--plum)',
              }}
            />
          )}
        </div>

        <div className="flex items-center gap-4 mt-2">
          <Tick color="var(--forest)" label="passed" count={passed} />
          <Tick color="var(--plum)" label="failed" count={failed} />
          <Tick color="var(--text-4)" label="not run" count={notRun} />
        </div>
      </div>

      {tagCounts.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span
            className="mono uppercase"
            style={{ fontSize: 9.5, color: 'var(--text-4)', letterSpacing: '0.12em' }}
          >
            Tags
          </span>
          {tagCounts.map(([tag, count]) => (
            <div key={tag} className="inline-flex items-center">
              <button
                type="button"
                onClick={() => setFilterTag(filterTag === tag ? null : tag)}
                aria-label={`filter tag ${tag}`}
                className="pill transition-colors"
                style={{
                  background:
                    filterTag === tag ? 'var(--accent)' : 'transparent',
                  color: filterTag === tag ? 'var(--bg-elev)' : 'var(--text-3)',
                  boxShadow:
                    filterTag === tag
                      ? 'none'
                      : 'inset 0 0 0 1px var(--border-strong)',
                  cursor: 'pointer',
                  border: 0,
                }}
              >
                {tag} · {count}
              </button>
              <button
                type="button"
                onClick={() => onEvaluate({ tags: [tag] })}
                disabled={running}
                aria-label={`evaluate tag ${tag}`}
                className="inline-flex items-center justify-center"
                style={{
                  width: 20,
                  height: 20,
                  marginLeft: 2,
                  border: 0,
                  borderRadius: 999,
                  background: 'transparent',
                  color: 'var(--text-4)',
                  cursor: running ? 'wait' : 'pointer',
                }}
              >
                <Play size={9} strokeWidth={1.8} />
              </button>
            </div>
          ))}
        </div>
      )}

      {visible.length > 0 && (
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => setExpanded(new Set(visible.map(({ i }) => i)))}
            style={{
              padding: '5px 10px',
              border: 0,
              borderRadius: 999,
              background: 'transparent',
              boxShadow: 'inset 0 0 0 1px var(--border-strong)',
              color: 'var(--text-3)',
              fontSize: 10.5,
              fontWeight: 400,
              cursor: 'pointer',
            }}
          >
            Expand all
          </button>
          <button
            type="button"
            onClick={() => setExpanded(new Set())}
            style={{
              padding: '5px 10px',
              border: 0,
              borderRadius: 999,
              background: 'transparent',
              boxShadow: 'inset 0 0 0 1px var(--border-strong)',
              color: 'var(--text-3)',
              fontSize: 10.5,
              fontWeight: 400,
              cursor: 'pointer',
            }}
          >
            Collapse all
          </button>
        </div>
      )}

      <div className="flex flex-col gap-2">
        {visible.map(({ tc, i }) => (
          <TestCaseCard
            key={i}
            index={i}
            testCase={tc}
            result={resultByIndex.get(i)}
            open={expanded.has(i)}
            onOpenChange={(open) => {
              setExpanded((prev) => {
                const next = new Set(prev);
                if (open) next.add(i); else next.delete(i);
                return next;
              });
            }}
            onEvaluate={(idx) => onEvaluate({ indices: [idx] })}
            running={running}
          />
        ))}
      </div>
    </div>
  );
}

function Tick({
  color,
  label,
  count,
}: {
  color: string;
  label: string;
  count: number;
}) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span
        style={{
          width: 6,
          height: 6,
          borderRadius: 999,
          background: color,
          display: 'inline-block',
        }}
      />
      <span
        className="mono"
        style={{ fontSize: 11, color: 'var(--text-2)' }}
      >
        {count} {label}
      </span>
    </span>
  );
}
