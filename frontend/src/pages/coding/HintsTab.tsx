import { ArrowRight } from 'lucide-react';
import InlineMarkdown from '../../components/shell/InlineMarkdown';

interface HintsTabProps {
  hints: string[];
  tips: string[];
  thoughtProcess: string[];
}

export function HintsTab({ hints, tips, thoughtProcess }: HintsTabProps) {
  if (hints.length === 0 && tips.length === 0 && thoughtProcess.length === 0) {
    return (
      <div
        className="flex items-center justify-center"
        style={{ height: '100%', color: 'var(--text-4)', fontSize: 12 }}
      >
        No hints for this problem.
      </div>
    );
  }
  return (
    <div className="space-y-3">
      {hints.map((hint, i) => (
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
      {tips.length > 0 && (
        <>
          <div className="pt-2" style={{ borderTop: '1px solid var(--border)' }}>
            <span className="eyebrow">Tips</span>
          </div>
          {tips.map((tip, i) => (
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
      {thoughtProcess.length > 0 && (
        <>
          <div className="pt-2" style={{ borderTop: '1px solid var(--border)' }}>
            <span className="eyebrow">Thought process</span>
          </div>
          {thoughtProcess.map((step, i) => (
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
  );
}
