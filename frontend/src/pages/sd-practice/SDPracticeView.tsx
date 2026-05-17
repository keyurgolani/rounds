import { lazy, Suspense, useState } from 'react';
import type { CanvasDriver } from './canvasTools';
import SDPracticeChatPanel from './SDPracticeChatPanel';

const ExcalidrawCanvas = lazy(() => import('./ExcalidrawCanvas'));

type Props = {
  questionSlug: string;
  questionPrompt: string;
};

export default function SDPracticeView({ questionSlug, questionPrompt }: Props) {
  const [driver, setDriver] = useState<CanvasDriver | null>(null);

  return (
    <div
      style={{
        display: 'flex',
        height: '100%',
        minHeight: 0,
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        overflow: 'hidden',
        background: 'var(--bg)',
      }}
    >
      <div style={{ flex: 1, minWidth: 0, position: 'relative' }}>
        <Suspense
          fallback={
            <div
              style={{
                position: 'absolute',
                inset: 0,
                display: 'grid',
                placeItems: 'center',
                color: 'var(--text-3)',
                fontSize: 13,
              }}
            >
              Loading canvas…
            </div>
          }
        >
          <ExcalidrawCanvas onDriverReady={setDriver} />
        </Suspense>
      </div>
      <div
        style={{
          width: 400,
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          minWidth: 0,
        }}
      >
        <SDPracticeChatPanel
          questionSlug={questionSlug}
          questionPrompt={questionPrompt}
          driver={driver}
        />
      </div>
    </div>
  );
}
