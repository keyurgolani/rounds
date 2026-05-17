import { useCallback, useMemo, useState } from 'react';
import { Excalidraw } from '@excalidraw/excalidraw';
import '@excalidraw/excalidraw/index.css';
import type { ExcalidrawImperativeAPI } from '@excalidraw/excalidraw/types';
import { createExcalidrawDriver } from './excalidrawDriver';
import { buildSystemDesignLibrary } from './excalidrawLibrary';
import type { CanvasDriver } from './canvasTools';

type Props = {
  onDriverReady: (driver: CanvasDriver) => void;
};

export default function ExcalidrawCanvas({ onDriverReady }: Props) {
  const [, setApi] = useState<ExcalidrawImperativeAPI | null>(null);

  const handleApiRef = useCallback(
    (api: ExcalidrawImperativeAPI | null) => {
      setApi(api);
      if (api) {
        onDriverReady(createExcalidrawDriver(api));
      }
    },
    [onDriverReady],
  );

  // Build the pre-installed library once per mount. Memoised so the
  // Excalidraw component doesn't see a new reference on every render
  // (would otherwise re-init the library each time).
  const initialData = useMemo(
    () => ({ libraryItems: buildSystemDesignLibrary() }),
    [],
  );

  return (
    <div style={{ width: '100%', height: '100%' }}>
      <Excalidraw excalidrawAPI={handleApiRef} initialData={initialData} />
    </div>
  );
}
