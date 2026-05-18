import { lazy, Suspense, useState } from 'react';
import type { CanvasDriver } from './canvasTools';
import SDPracticeChatPanel from './SDPracticeChatPanel';
import { useResizableWidth } from '../../hooks/useResizableWidth';
import ResizeHandle from '../../components/layout/ResizeHandle';

const ExcalidrawCanvas = lazy(() => import('./ExcalidrawCanvas'));

const CHAT_RAIL_KEY = 'rounds.sd-practice.chatRailWidth';
const CHAT_RAIL_DEFAULT = 400;
const CHAT_RAIL_MIN = 280;
const CHAT_RAIL_MAX = 720;

type Props = {
  questionSlug: string;
  questionPrompt: string;
};

export default function SDPracticeView({ questionSlug, questionPrompt }: Props) {
  const [driver, setDriver] = useState<CanvasDriver | null>(null);
  const { width: railWidth, onResizeStart } = useResizableWidth({
    storageKey: CHAT_RAIL_KEY,
    defaultWidth: CHAT_RAIL_DEFAULT,
    min: CHAT_RAIL_MIN,
    max: CHAT_RAIL_MAX,
    edge: 'left',
  });

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
      <aside
        style={{
          width: railWidth,
          flexShrink: 0,
          display: 'flex',
          flexDirection: 'column',
          minWidth: 0,
          position: 'relative',
        }}
      >
        <ResizeHandle onMouseDown={onResizeStart} edge="left" />
        <SDPracticeChatPanel
          questionSlug={questionSlug}
          questionPrompt={questionPrompt}
          driver={driver}
        />
      </aside>
    </div>
  );
}
