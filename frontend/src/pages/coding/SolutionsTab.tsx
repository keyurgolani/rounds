import { useState } from 'react';
import { ChevronDown, ChevronUp, Download } from 'lucide-react';
import InlineMarkdown from '../../components/shell/InlineMarkdown';

export interface SolutionEntry {
  title: string;
  time_complexity: string;
  space_complexity: string;
  description: string;
  code: Record<string, string>;
}

interface SolutionsTabProps {
  solutions: SolutionEntry[];
  language: string;
  /** Called when the user clicks Load on a solution. The parent owns the
      "is editor dirty?" check and the actual setCode. */
  onLoadIntoEditor: (code: string) => void;
}

export function SolutionsTab({ solutions, language, onLoadIntoEditor }: SolutionsTabProps) {
  const [expanded, setExpanded] = useState<number>(-1);

  if (solutions.length === 0) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ height: '100%', color: 'var(--text-4)', fontSize: 12 }}
      >
        No reference solutions for this problem.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {solutions.map((sol, i) => {
        const hasCodeForLang = Boolean(sol.code[language]);
        const open = expanded === i;
        return (
          <div key={i} className="card overflow-hidden">
            <div
              className="p-3 flex items-center justify-between gap-2"
              style={{ background: 'transparent' }}
            >
              <button
                type="button"
                onClick={() => setExpanded(open ? -1 : i)}
                className="flex-1 min-w-0 text-left"
                style={{ background: 'transparent', border: 0, cursor: 'pointer', padding: 0 }}
              >
                <div style={{ fontSize: 13, fontWeight: 500 }}>{sol.title}</div>
                <div
                  className="mono"
                  style={{ fontSize: 11, color: 'var(--text-4)', marginTop: 2 }}
                >
                  {sol.time_complexity} · {sol.space_complexity}
                </div>
              </button>
              <div className="flex items-center gap-1 flex-shrink-0">
                {hasCodeForLang && (
                  <button
                    type="button"
                    title={`Load into editor (${language})`}
                    aria-label={`Load solution into editor in ${language}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onLoadIntoEditor(sol.code[language]);
                    }}
                    className="inline-flex items-center gap-1"
                    style={{
                      padding: '5px 10px',
                      borderRadius: 999,
                      border: 0,
                      background: 'var(--accent-soft)',
                      color: 'var(--accent)',
                      fontSize: 11,
                      fontWeight: 500,
                      cursor: 'pointer',
                    }}
                  >
                    <Download size={11} strokeWidth={1.9} />
                    Load
                  </button>
                )}
                <button
                  type="button"
                  aria-label={open ? 'Collapse solution' : 'Expand solution'}
                  onClick={() => setExpanded(open ? -1 : i)}
                  style={{
                    padding: 4,
                    border: 0,
                    background: 'transparent',
                    color: 'var(--text-3)',
                    cursor: 'pointer',
                    display: 'inline-flex',
                  }}
                >
                  {open ? (
                    <ChevronUp size={14} strokeWidth={1.7} />
                  ) : (
                    <ChevronDown size={14} strokeWidth={1.7} />
                  )}
                </button>
              </div>
            </div>
            {open && (
              <div className="px-3 pb-3 space-y-2">
                <InlineMarkdown
                  as="p"
                  text={sol.description}
                  style={{ fontSize: 12, color: 'var(--text-3)', margin: 0 }}
                />
                {sol.code[language] && (
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
                    {sol.code[language]}
                  </pre>
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
