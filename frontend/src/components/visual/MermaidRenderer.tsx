import { useEffect, useRef, useState } from 'react';
import { Skeleton } from './Skeleton';

interface MermaidRendererProps {
  chart: string;
  className?: string;
}

let mermaidPromise: Promise<typeof import('mermaid').default> | null = null;
function loadMermaid() {
  if (!mermaidPromise) {
    mermaidPromise = import('mermaid').then((m) => {
      m.default.initialize({
        startOnLoad: false,
        theme: 'neutral',
        fontFamily: "'Inter', system-ui, sans-serif",
        securityLevel: 'strict',
      });
      return m.default;
    });
  }
  return mermaidPromise;
}

let renderId = 0;

export function MermaidRenderer({ chart, className = '' }: MermaidRendererProps) {
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    setSvg(null);
    setError(null);

    loadMermaid()
      .then((mermaid) => mermaid.render(`mmd-${++renderId}`, chart))
      .then(({ svg }) => {
        if (!cancelled) setSvg(svg);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });

    return () => {
      cancelled = true;
    };
  }, [chart]);

  if (error) {
    return (
      <div className={`text-xs text-red-500 font-mono p-2 ${className}`}>
        Diagram error: {error}
      </div>
    );
  }

  if (!svg) {
    return (
      <div data-testid="mermaid-loading" className={className}>
        <Skeleton height={180} />
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      data-testid="mermaid"
      className={`overflow-x-auto ${className}`}
      // SVG already sanitized by Mermaid securityLevel='strict'
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}
