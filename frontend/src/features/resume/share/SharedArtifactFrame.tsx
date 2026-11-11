// A resolved Share Capability's markup, read-only (ROUNDS-00B-L03 stage 2).
//
// The markup is a Legacy Artifact Snapshot's document, which passed #4's
// output checks when it was stored. It goes into a sandboxed frame as
// srcdoc and nowhere else, never into this page's DOM. The sandbox grants
// no scripts and no same-origin access, so the frame runs nothing and
// reaches nothing of this page; its links open a new window, which may
// leave the sandbox. The frame also inherits the share page's CSP. Nothing
// here cleans the markup again: #4's checks decide what a snapshot holds,
// and the sandbox contains it.
//
// A sandboxed frame has an opaque origin, so this page can't measure its
// document. The frame gets the snapshot's page width (A4 plus the
// document's 16px padding) and the scroll area's height, zoom scales the
// whole frame, and the document scrolls inside it. Templates show their
// fallback fonts until #6.

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { clampZoom, Toolbar, ZOOM_STEP } from '../ZoomablePage';
import { ReadOnlyBadge, SHARE_TOOLBAR_LABEL } from './ReadOnlyBadge';

export const SHARED_FRAME_TITLE = 'Shared resume';
export const SHARED_FRAME_SANDBOX = 'allow-popups allow-popups-to-escape-sandbox';
// 210 mm at 96 CSS px per inch, plus the snapshot body's 16px padding on
// each side (export/shell.ts).
export const SHARED_FRAME_WIDTH_PX = Math.round((210 * 96) / 25.4) + 32;
const GUTTER_PX = 16;
const MIN_FRAME_HEIGHT_PX = 240;

export default function SharedArtifactFrame({ markup }: { markup: string }) {
  const areaRef = useRef<HTMLDivElement>(null);
  const [area, setArea] = useState({ w: 0, h: 0 });
  const [zoom, setZoom] = useState(1);
  // Fitted to the width until the reader picks a zoom; Fit goes back to it,
  // and a fitted page follows the width, a phone turned sideways included.
  const [fitted, setFitted] = useState(true);

  // The scroll area is this page's own element, so it can be measured.
  useLayoutEffect(() => {
    const el = areaRef.current;
    if (!el) return;
    const measure = () => {
      const w = el.clientWidth;
      const h = el.clientHeight;
      setArea((prev) => (prev.w === w && prev.h === h ? prev : { w, h }));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useLayoutEffect(() => {
    const available = area.w - GUTTER_PX * 2;
    if (fitted && available > 0) setZoom(clampZoom(available / SHARED_FRAME_WIDTH_PX));
  }, [fitted, area.w]);

  const zoomBy = useCallback((step: number) => {
    setFitted(false);
    setZoom((z) => clampZoom(z + step));
  }, []);
  const zoomReset = useCallback(() => {
    setFitted(false);
    setZoom(1);
  }, []);
  const zoomFit = useCallback(() => setFitted(true), []);

  // The same shortcuts as the other share page: +/= and − zoom, 0 resets,
  // F fits. They work while focus is on this page, not inside the frame.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        zoomBy(ZOOM_STEP);
      } else if (e.key === '-' || e.key === '_') {
        e.preventDefault();
        zoomBy(-ZOOM_STEP);
      } else if (e.key === '0') {
        e.preventDefault();
        zoomReset();
      } else if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        zoomFit();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [zoomBy, zoomReset, zoomFit]);

  // Scaled, the frame fills the scroll area's height; unscaled, it's that
  // height over the zoom, so the document scrolls inside it.
  const shownHeight = Math.max(MIN_FRAME_HEIGHT_PX, Math.floor(area.h - GUTTER_PX * 2));
  const frameHeight = Math.floor(shownHeight / zoom);

  return (
    <>
      <Toolbar
        label={SHARE_TOOLBAR_LABEL}
        zoom={zoom}
        onZoomIn={() => zoomBy(ZOOM_STEP)}
        onZoomOut={() => zoomBy(-ZOOM_STEP)}
        onZoomReset={zoomReset}
        onZoomFit={zoomFit}
        actions={<ReadOnlyBadge />}
      />
      <div
        ref={areaRef}
        style={{
          flex: 1,
          minHeight: 0,
          overflow: 'auto',
          padding: GUTTER_PX,
          background: 'var(--bg-sunken)',
        }}
      >
        <div
          style={{
            width: Math.ceil(SHARED_FRAME_WIDTH_PX * zoom),
            height: shownHeight,
            margin: '0 auto',
            position: 'relative',
          }}
        >
          <iframe
            title={SHARED_FRAME_TITLE}
            sandbox={SHARED_FRAME_SANDBOX}
            referrerPolicy="no-referrer"
            srcDoc={markup}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: SHARED_FRAME_WIDTH_PX,
              height: frameHeight,
              border: 0,
              background: '#fff',
              transform: `scale(${zoom})`,
              transformOrigin: 'top left',
              boxShadow: '0 1px 2px rgba(0, 0, 0, 0.08), 0 0 0 1px var(--border)',
            }}
          />
        </div>
      </div>
    </>
  );
}
