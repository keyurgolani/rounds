import { useMemo } from 'react';
import FlowchartChart from './internal/FlowchartChart';
import { parseFlowchart } from './internal/parseFlowchart';
import { MermaidRenderer } from './MermaidRenderer';

interface FlowchartDiagramProps {
  source: string;
  className?: string;
}

export function FlowchartDiagram({ source, className = '' }: FlowchartDiagramProps) {
  const parsed = useMemo(() => parseFlowchart(source), [source]);
  if (!parsed) {
    // Unsupported Mermaid features — fall back to the generic renderer so
    // we never show a broken diagram.
    return <MermaidRenderer chart={source} className={className} />;
  }
  return (
    <div className={className} data-testid="flowchart-diagram">
      <FlowchartChart data={parsed} />
    </div>
  );
}
