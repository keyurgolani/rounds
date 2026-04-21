import { useMemo } from 'react';
import ERChart from './internal/ERChart';
import { parseER } from './internal/parseER';
import { MermaidRenderer } from './MermaidRenderer';

interface ERDiagramProps {
  source: string;
  className?: string;
}

export function ERDiagram({ source, className = '' }: ERDiagramProps) {
  const parsed = useMemo(() => parseER(source), [source]);
  if (!parsed) {
    return <MermaidRenderer chart={source} className={className} />;
  }
  return (
    <div className={className} data-testid="er-diagram">
      <ERChart data={parsed} />
    </div>
  );
}
