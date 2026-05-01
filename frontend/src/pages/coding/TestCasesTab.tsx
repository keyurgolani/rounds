import { useState, useMemo } from 'react';
import { Play, ChevronRight, ChevronDown } from 'lucide-react';
import type {
  TestCase,
  CodeEvaluateResult,
  EvaluateCaseResult,
  EvaluateFilter,
} from './types';
import { ResultCard, type ResultStatus } from './ResultCard';
import { formatValue } from './format';

interface TestCasesTabProps {
  testCases: TestCase[];
  evalResult?: CodeEvaluateResult;
  running: boolean;
  onEvaluate: (filter?: EvaluateFilter) => void;
}

function groupByTag(cases: TestCase[]): { tag: string; indices: number[] }[] {
  const m = new Map<string, number[]>();
  cases.forEach((tc, idx) => {
    const tag = tc.tags && tc.tags.length > 0 ? tc.tags[0] : 'general';
    const arr = m.get(tag) ?? [];
    arr.push(idx);
    m.set(tag, arr);
  });
  return Array.from(m.entries()).map(([tag, indices]) => ({ tag, indices }));
}

function statusFor(r?: EvaluateCaseResult): ResultStatus {
  if (!r) return 'pending';
  if (r.error?.startsWith('Time limit')) return 'timeout';
  if (r.error) return 'error';
  return r.passed ? 'pass' : 'fail';
}

export function TestCasesTab({
  testCases,
  evalResult,
  running,
  onEvaluate,
}: TestCasesTabProps) {
  const groups = useMemo(() => groupByTag(testCases), [testCases]);
  const resultByIndex = useMemo(() => {
    const m = new Map<number, EvaluateCaseResult>();
    evalResult?.results.forEach((r) => m.set(r.index, r));
    return m;
  }, [evalResult]);

  const total = testCases.length;
  const passed = evalResult?.passed ?? 0;
  const failed = evalResult?.failed ?? 0;

  return (
    <div className="flex flex-col gap-2.5 h-full">
      <div className="flex items-center justify-between flex-shrink-0">
        <button
          type="button"
          onClick={() => onEvaluate()}
          disabled={running || total === 0}
          className="inline-flex items-center gap-1.5"
          style={{
            padding: '5px 12px',
            fontSize: 11,
            fontWeight: 500,
            background: 'var(--ink)',
            color: 'var(--paper)',
            border: 0,
            borderRadius: 999,
            cursor: running ? 'wait' : 'pointer',
            opacity: running ? 0.6 : 1,
          }}
        >
          <Play size={10} strokeWidth={1.9} />
          {running ? 'Running…' : `Run all (${total})`}
        </button>
        {evalResult && (
          <span
            className="mono"
            style={{
              fontSize: 10.5,
              color: failed === 0 ? 'var(--status-pass)' : 'var(--status-fail)',
            }}
          >
            {passed} / {passed + failed} passed
          </span>
        )}
      </div>

      <div className="flex flex-col gap-3 overflow-auto" style={{ flex: 1, minHeight: 0 }}>
        {groups.map(({ tag, indices }) => (
          <CategoryGroup
            key={tag}
            tag={tag}
            indices={indices}
            testCases={testCases}
            resultByIndex={resultByIndex}
            running={running}
            onRunGroup={() => onEvaluate({ tags: [tag] })}
            onRunCase={(idx) => onEvaluate({ indices: [idx] })}
          />
        ))}
      </div>
    </div>
  );
}

function CategoryGroup({
  tag,
  indices,
  testCases,
  resultByIndex,
  running,
  onRunGroup,
  onRunCase,
}: {
  tag: string;
  indices: number[];
  testCases: TestCase[];
  resultByIndex: Map<number, EvaluateCaseResult>;
  running: boolean;
  onRunGroup: () => void;
  onRunCase: (idx: number) => void;
}) {
  const [open, setOpen] = useState(true);
  const groupResults = indices.map((i) => resultByIndex.get(i));
  const hasResults = groupResults.some((r) => r !== undefined);
  const groupPassed = groupResults.filter((r) => r?.passed).length;
  const groupRan = groupResults.filter((r) => r !== undefined).length;

  return (
    <div className="flex flex-col" style={{ gap: 4 }}>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setOpen(!open)}
          aria-expanded={open}
          aria-label={`${open ? 'Collapse' : 'Expand'} ${tag} group`}
          className="inline-flex items-center gap-1"
          style={{
            background: 'transparent',
            border: 0,
            padding: 0,
            cursor: 'pointer',
            color: 'var(--text-3)',
          }}
        >
          {open ? (
            <ChevronDown size={12} strokeWidth={1.8} />
          ) : (
            <ChevronRight size={12} strokeWidth={1.8} />
          )}
        </button>
        <span
          className="mono uppercase"
          style={{
            fontSize: 9.5,
            color: 'var(--text-3)',
            letterSpacing: '0.12em',
            fontWeight: 500,
          }}
        >
          {tag}
        </span>
        <span className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)' }}>
          {hasResults ? `${groupPassed}/${groupRan}` : `${indices.length}`}
        </span>
        <button
          type="button"
          onClick={onRunGroup}
          disabled={running}
          aria-label={`Run ${tag} group`}
          className="inline-flex items-center gap-1 ml-auto mono"
          style={{
            fontSize: 10.5,
            padding: '2px 8px',
            background: 'transparent',
            color: 'var(--text-3)',
            border: 0,
            boxShadow: 'inset 0 0 0 1px var(--border-strong)',
            borderRadius: 999,
            cursor: running ? 'wait' : 'pointer',
            opacity: running ? 0.5 : 1,
          }}
        >
          <Play size={9} strokeWidth={1.9} />
          run group
        </button>
      </div>

      {open && (
        <div
          className="flex flex-col"
          style={{
            gap: 3,
            paddingLeft: 16,
            borderLeft: '1px dashed var(--border)',
            marginLeft: 5,
          }}
        >
          {indices.map((idx) => (
            <CaseRow
              key={idx}
              index={idx}
              testCase={testCases[idx]}
              result={resultByIndex.get(idx)}
              running={running}
              onRun={() => onRunCase(idx)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function CaseRow({
  index,
  testCase,
  result,
  running,
  onRun,
}: {
  index: number;
  testCase: TestCase;
  result?: EvaluateCaseResult;
  running: boolean;
  onRun: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const status = statusFor(result);
  const label = testCase.description || `Case ${index + 1}`;
  const inputPreview = useMemo(() => {
    try {
      const s = formatValue(testCase.input);
      return s.length > 60 ? s.slice(0, 57) + '…' : s;
    } catch {
      return '';
    }
  }, [testCase.input]);

  return (
    <div className="flex flex-col" style={{ gap: 4 }}>
      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-2 flex-1 min-w-0 text-left"
          style={{
            background: 'transparent',
            border: 0,
            padding: '4px 0',
            cursor: 'pointer',
          }}
        >
          <StatusDot status={status} />
          <span style={{ fontSize: 11.5, color: 'var(--text-2)', whiteSpace: 'nowrap' }}>
            {label}
          </span>
          <span
            className="mono"
            style={{
              fontSize: 10.5,
              color: 'var(--text-4)',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {inputPreview}
          </span>
        </button>
        {result?.duration_ms !== undefined && (
          <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>
            {result.duration_ms}ms
          </span>
        )}
        <button
          type="button"
          onClick={onRun}
          disabled={running}
          aria-label={`Run case ${index + 1}`}
          className="inline-flex items-center"
          style={{
            background: 'transparent',
            border: 0,
            padding: 3,
            color: 'var(--text-3)',
            cursor: running ? 'wait' : 'pointer',
            opacity: running ? 0.5 : 1,
            borderRadius: 4,
          }}
        >
          <Play size={11} strokeWidth={1.8} />
        </button>
      </div>

      {expanded && (
        <div style={{ marginLeft: 16, marginBottom: 4 }}>
          <ResultCard
            status={status}
            description={label}
            input={testCase.input}
            output={result?.error ? undefined : result?.output}
            expected={testCase.expected}
            reason={result?.error}
            durationMs={result?.duration_ms}
          />
        </div>
      )}
    </div>
  );
}

function StatusDot({ status }: { status: ResultStatus }) {
  const color =
    status === 'pass'
      ? 'var(--status-pass)'
      : status === 'timeout'
        ? 'var(--status-warn)'
        : status === 'fail' || status === 'error'
          ? 'var(--status-fail)'
          : 'var(--border-strong)';
  return (
    <span
      aria-hidden="true"
      style={{
        width: 7,
        height: 7,
        borderRadius: 999,
        background: color,
        flexShrink: 0,
        display: 'inline-block',
      }}
    />
  );
}
