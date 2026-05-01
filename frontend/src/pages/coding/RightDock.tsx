import type { ReactNode } from 'react';
import { CasesTab } from './CasesTab';
import { ResultTab } from './ResultTab';
import { TestCasesTab } from './TestCasesTab';
import type {
  TestCase,
  CodeRunResult,
  CodeEvaluateResult,
  EvaluateFilter,
  Entry,
} from './types';

export type SideTab = 'tests' | 'run';

interface RightDockProps {
  activeTab: SideTab;
  onTabChange: (tab: SideTab) => void;
  entry: Entry;
  testCases: TestCase[];
  running: boolean;
  onRun: (input: unknown) => void;
  onEvaluate: (filter?: EvaluateFilter) => void;
  runResult?: CodeRunResult;
  runInput?: unknown;
  evalResult?: CodeEvaluateResult;
  /** Optional header slot rendered above the tab strip — used for the
      mobile sheet drag handle / close button injected by CodingDetail. */
  headerSlot?: ReactNode;
}

const TABS: { key: SideTab; label: string }[] = [
  { key: 'tests', label: 'Test Cases' },
  { key: 'run', label: 'Run' },
];

export function RightDock({
  activeTab,
  onTabChange,
  entry,
  testCases,
  running,
  onRun,
  onEvaluate,
  runResult,
  runInput,
  evalResult,
  headerSlot,
}: RightDockProps) {
  return (
    <div className="flex flex-col h-full" data-testid="right-dock">
      {headerSlot}
      <div
        role="tablist"
        aria-label="Run sidebar"
        className="flex"
        style={{
          borderBottom: '1px solid var(--border)',
          flexShrink: 0,
          background: 'var(--bg)',
        }}
      >
        {TABS.map(({ key, label }) => {
          const active = activeTab === key;
          return (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onTabChange(key)}
              style={{
                position: 'relative',
                padding: '10px 16px',
                fontSize: 12,
                fontWeight: active ? 600 : 500,
                background: 'transparent',
                color: active ? 'var(--text)' : 'var(--text-4)',
                border: 0,
                cursor: 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                transition: 'color 140ms',
              }}
            >
              {label}
              {key === 'tests' && evalResult && (
                <span
                  className="mono"
                  style={{
                    fontSize: 10,
                    color:
                      evalResult.failed === 0
                        ? 'var(--status-pass)'
                        : 'var(--status-fail)',
                  }}
                >
                  {evalResult.passed}/{evalResult.passed + evalResult.failed}
                </span>
              )}
              {active && (
                <span
                  aria-hidden="true"
                  style={{
                    position: 'absolute',
                    left: 12,
                    right: 12,
                    bottom: -1,
                    height: 2,
                    background: 'var(--accent)',
                    borderRadius: '2px 2px 0 0',
                  }}
                />
              )}
            </button>
          );
        })}
      </div>
      <div style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        {activeTab === 'tests' && (
          <div style={{ flex: 1, overflow: 'auto', padding: 12, minHeight: 0 }}>
            <TestCasesTab
              testCases={testCases}
              evalResult={evalResult}
              running={running}
              onEvaluate={onEvaluate}
            />
          </div>
        )}
        {activeTab === 'run' && (
          <RunSplit
            entry={entry}
            testCases={testCases}
            running={running}
            onRun={onRun}
            runResult={runResult}
            runInput={runInput}
          />
        )}
      </div>
    </div>
  );
}

interface RunSplitProps {
  entry: Entry;
  testCases: TestCase[];
  running: boolean;
  onRun: (input: unknown) => void;
  runResult?: CodeRunResult;
  runInput?: unknown;
}

// Run tab layout:
//   - No result yet → input section fills the whole sidebar.
//   - Result present → result section sizes to its content but caps at
//     50% of the sidebar; input takes the rest.
//
// Achieved purely via flexbox: input is the flexible child (`flex: 1`),
// result is auto-sized (`flex: 0 0 auto`) with `max-height: 50%` so a
// long result still scrolls inside instead of pushing the input
// off-screen.
function RunSplit({
  entry,
  testCases,
  running,
  onRun,
  runResult,
  runInput,
}: RunSplitProps) {
  return (
    <div className="flex flex-col" style={{ flex: 1, minHeight: 0 }}>
      <div
        style={{
          flex: '1 1 0',
          minHeight: 0,
          overflow: 'auto',
          padding: 12,
        }}
      >
        <CasesTab
          entry={entry}
          samples={testCases}
          running={running}
          onRun={onRun}
        />
      </div>
      {runResult && (
        <div
          style={{
            flex: '0 0 auto',
            maxHeight: '50%',
            overflow: 'auto',
            padding: 12,
            borderTop: '1px solid var(--border)',
            background: 'var(--bg-sunken)',
          }}
        >
          <div
            className="flex items-center justify-between"
            style={{ marginBottom: 8 }}
          >
            <span
              className="mono uppercase"
              style={{
                fontSize: 9.5,
                color: 'var(--text-4)',
                letterSpacing: '0.12em',
              }}
            >
              Result
            </span>
            <span className="mono" style={{ fontSize: 10, color: 'var(--text-4)' }}>
              {runResult.duration_ms}ms
            </span>
          </div>
          <ResultTab runResult={runResult} runInput={runInput} />
        </div>
      )}
    </div>
  );
}
