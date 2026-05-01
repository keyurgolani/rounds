import { useMemo } from 'react';
import type { ArchitectureDiagramData } from './types';
import ArchitectureChart from './internal/ArchitectureChart';

interface ArchitectureDiagramProps {
  data: ArchitectureDiagramData;
  height?: number;
  className?: string;
}

export function ArchitectureDiagram({
  data,
  height = 360,
  className = '',
}: ArchitectureDiagramProps) {
  const isEmpty = useMemo(
    () => !data.nodes.length && !data.edges.length,
    [data],
  );

  if (isEmpty) return null;

  return (
    <div className={className} style={{ minHeight: height, overflow: 'hidden' }}>
      <ArchitectureChart data={data} />
    </div>
  );
}
