import { FlowchartDiagram } from './FlowchartDiagram';
import { ERDiagram } from './ERDiagram';
import { SequenceDiagram } from './SequenceDiagram';
import { MermaidRenderer } from './MermaidRenderer';

interface SmartDiagramProps {
  source: string;
  className?: string;
}

// Inspect the first meaningful token of a Mermaid source and dispatch to
// the matching custom renderer. Unknown kinds fall through to Mermaid.
export function SmartDiagram({ source, className }: SmartDiagramProps) {
  const firstLine = source
    .split(/\r?\n/)
    .map((l) => l.trim())
    .find((l) => l.length > 0 && !l.startsWith('%%'));

  if (firstLine) {
    const head = firstLine.toLowerCase();
    if (head.startsWith('sequencediagram')) {
      return <SequenceDiagram source={source} className={className} />;
    }
    if (head.startsWith('erdiagram')) {
      return <ERDiagram source={source} className={className} />;
    }
    if (head.startsWith('graph ') || head.startsWith('flowchart ')) {
      return <FlowchartDiagram source={source} className={className} />;
    }
  }

  return <MermaidRenderer chart={source} className={className} />;
}
