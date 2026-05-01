import { useMemo } from 'react';
import SequenceChart from './internal/SequenceChart';
import { parseSequence } from './internal/parseSequence';
import { MermaidRenderer } from './MermaidRenderer';

interface SequenceDiagramProps {
  source: string;
  className?: string;
}

export function SequenceDiagram({ source, className = '' }: SequenceDiagramProps) {
  const parsed = useMemo(() => parseSequence(source), [source]);
  if (!parsed) {
    return <MermaidRenderer chart={source} className={className} />;
  }
  return (
    <div className={className} data-testid="sequence-diagram">
      <SequenceChart data={parsed} />
    </div>
  );
}
