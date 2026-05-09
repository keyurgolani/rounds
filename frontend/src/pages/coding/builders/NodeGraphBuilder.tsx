// Layout dispatcher for node-shaped inputs (linked list, tree, graph).
// Delegates to the SVG canvases; kept as a thin wrapper so callers
// (CasesTab) only need to know which Layout to ask for.

import type { NodeTemplate } from '../types';
import { formatValue } from '../format';
import {
  type VerboseGraph,
  fromVerboseChain,
  fromVerboseLevelOrder,
} from './shorthand';
import { ChainCanvas } from './ChainCanvas';
import { TreeCanvas } from './TreeCanvas';
import { GraphCanvas } from './GraphCanvas';

export type Layout = 'chain' | 'tree' | 'general';

interface NodeGraphBuilderProps {
  template: NodeTemplate;
  layout: Layout;
  value: VerboseGraph;
  onChange: (next: VerboseGraph) => void;
}

export function NodeGraphBuilder(props: NodeGraphBuilderProps) {
  if (props.layout === 'chain') {
    return <ChainCanvas template={props.template} value={props.value} onChange={props.onChange} />;
  }
  if (props.layout === 'tree') {
    return <TreeCanvas template={props.template} value={props.value} onChange={props.onChange} />;
  }
  if (props.layout === 'general') {
    return <GraphCanvas template={props.template} value={props.value} onChange={props.onChange} />;
  }
  return (
    <pre className="mono" style={{ fontSize: 11, color: 'var(--text-4)', margin: 0 }}>
      {formatValue(props.value)}
    </pre>
  );
}

// Re-export verbose helpers for callers that build NodeGraphBuilder values from shorthand.
export { fromVerboseChain, fromVerboseLevelOrder };
