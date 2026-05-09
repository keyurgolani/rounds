// Pan/zoom SVG viewport — shared by Tree/Graph/Chain canvases.
//
// Why this exists: each canvas computes a "natural" content size from its
// data (a 30-node tree gets very wide; a circular graph gets tall). When
// that size exceeds the side panel width the previous behavior was to
// fall back on browser scrollbars, which felt clumsy. This wrapper keeps
// the SVG sized to its container and moves the content via a transform,
// so pan/zoom feel like Figma/Miro instead of like an iframe.
//
// Interaction model (desktop-first):
//   - Mouse drag on empty space → pan
//   - Wheel → pan (vertical + horizontal via deltaX)
//   - Ctrl/Cmd + wheel → zoom around cursor
//   - Toolbar: Zoom in / Zoom out / Fit to width
//
// Touch (pinch + drag) is intentionally not implemented yet — the mobile
// dock has its own scroll and is rarely used to author trees/graphs.
//
// The background <rect> handles drag start so clicks on real content
// (nodes, slots, X handles) propagate to their own onClick handlers
// untouched (we check `e.target === e.currentTarget` to disambiguate).

import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';

interface PanZoomSvgProps {
  /** Natural width of the rendered content (no zoom applied). */
  contentWidth: number;
  /** Natural height of the rendered content. */
  contentHeight: number;
  /** Display height of the SVG viewport. Width is always 100% of the
      container so the viewport flexes with the side panel. */
  displayHeight: number;
  /** Optional cap so a 30-deep tree doesn't make the canvas absurdly
      tall. Defaults to displayHeight. */
  maxDisplayHeight?: number;
  children: ReactNode;
}

const MIN_ZOOM = 0.25;
const MAX_ZOOM = 4;

export function PanZoomSvg({
  contentWidth,
  contentHeight,
  displayHeight,
  maxDisplayHeight,
  children,
}: PanZoomSvgProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const svgRef = useRef<SVGSVGElement | null>(null);
  const [containerWidth, setContainerWidth] = useState(0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [grabbing, setGrabbing] = useState(false);

  // ResizeObserver to track the container width — needed both for the
  // initial fit-to-width and for any subsequent panel resize so the
  // canvas re-fits cleanly.
  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === 'undefined') {
      // jsdom has no ResizeObserver — fall back to a sensible default.
      setContainerWidth(el?.clientWidth ?? 360);
      return;
    }
    const ro = new ResizeObserver((entries) => {
      const cw = entries[0]?.contentRect.width ?? 0;
      setContainerWidth(cw);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const effectiveDisplayHeight = Math.min(
    maxDisplayHeight ?? displayHeight,
    Math.max(displayHeight, contentHeight),
  );

  // Auto-fit on first measurement and whenever the natural content
  // dimensions change (e.g. user added a node and the layout regrew).
  // Two distinct phases: (1) wait for ResizeObserver to populate
  // containerWidth; (2) compute scale + center.
  const lastFitKey = useRef<string>('');
  useEffect(() => {
    if (containerWidth === 0) return;
    const key = `${contentWidth}:${contentHeight}:${containerWidth}:${effectiveDisplayHeight}`;
    if (lastFitKey.current === key) return;
    lastFitKey.current = key;
    fitToView();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [contentWidth, contentHeight, containerWidth, effectiveDisplayHeight]);

  function fitToView() {
    if (containerWidth === 0) return;
    const sx = containerWidth / contentWidth;
    const sy = effectiveDisplayHeight / contentHeight;
    const target = Math.min(sx, sy, 1);
    setZoom(target);
    setPan({
      x: (containerWidth - contentWidth * target) / 2,
      y: (effectiveDisplayHeight - contentHeight * target) / 2,
    });
  }

  function clampZoom(z: number) {
    return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, z));
  }

  function zoomBy(factor: number, center?: { x: number; y: number }) {
    const next = clampZoom(zoom * factor);
    if (next === zoom) return;
    const cx = center?.x ?? containerWidth / 2;
    const cy = center?.y ?? effectiveDisplayHeight / 2;
    // Pin the on-screen point under (cx, cy) so zoom feels anchored
    // rather than re-centering on every step.
    setPan((p) => ({
      x: cx - (cx - p.x) * (next / zoom),
      y: cy - (cy - p.y) * (next / zoom),
    }));
    setZoom(next);
  }

  function onWheel(e: React.WheelEvent<SVGSVGElement>) {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const rect = svgRef.current?.getBoundingClientRect();
      if (!rect) return;
      const factor = e.deltaY < 0 ? 1.1 : 1 / 1.1;
      zoomBy(factor, { x: e.clientX - rect.left, y: e.clientY - rect.top });
    } else {
      // Don't preventDefault here — let the browser still scroll the
      // outer panel if the user has reached the canvas edge. Pan only
      // when the canvas is genuinely overflowing so wheel feels natural.
      const overflowX = contentWidth * zoom > containerWidth;
      const overflowY = contentHeight * zoom > effectiveDisplayHeight;
      if (!overflowX && !overflowY) return;
      e.preventDefault();
      setPan((p) => ({
        x: overflowX ? p.x - e.deltaX : p.x,
        y: overflowY ? p.y - e.deltaY : p.y,
      }));
    }
  }

  function onMouseDownBg(e: React.MouseEvent<SVGRectElement>) {
    // Only initiate drag on an actual background hit — clicks that
    // bubbled up from a node/slot/handle have a different target and
    // must keep their own behavior.
    if (e.target !== e.currentTarget) return;
    e.preventDefault();
    const startX = e.clientX;
    const startY = e.clientY;
    const startPan = pan;
    setGrabbing(true);
    function onMove(ev: MouseEvent) {
      setPan({
        x: startPan.x + (ev.clientX - startX),
        y: startPan.y + (ev.clientY - startY),
      });
    }
    function onUp() {
      setGrabbing(false);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    }
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }

  const transform = useMemo(
    () => `translate(${pan.x} ${pan.y}) scale(${zoom})`,
    [pan.x, pan.y, zoom],
  );

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        background: 'var(--bg-sunken)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        overflow: 'hidden',
      }}
    >
      <svg
        ref={svgRef}
        width="100%"
        height={effectiveDisplayHeight}
        onWheel={onWheel}
        style={{
          display: 'block',
          cursor: grabbing ? 'grabbing' : 'grab',
          touchAction: 'none',
        }}
        data-testid="panzoom-svg"
      >
        {/* Background hit-rect — pure pan affordance, ignored by content
            click handlers via the e.target === e.currentTarget gate. */}
        <rect
          width="100%"
          height={effectiveDisplayHeight}
          fill="transparent"
          onMouseDown={onMouseDownBg}
        />
        <g transform={transform}>{children}</g>
      </svg>
      <ZoomToolbar
        zoom={zoom}
        onZoomIn={() => zoomBy(1.2)}
        onZoomOut={() => zoomBy(1 / 1.2)}
        onFit={fitToView}
      />
    </div>
  );
}

function ZoomToolbar({
  zoom,
  onZoomIn,
  onZoomOut,
  onFit,
}: {
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFit: () => void;
}) {
  return (
    <div
      className="flex items-center gap-1"
      style={{
        position: 'absolute',
        right: 6,
        bottom: 6,
        padding: 3,
        background: 'var(--bg)',
        border: '1px solid var(--border)',
        borderRadius: 6,
        boxShadow: '0 2px 6px rgba(0,0,0,0.06)',
      }}
    >
      <ZoomIconButton icon={ZoomOut} label="Zoom out" onClick={onZoomOut} />
      <button
        type="button"
        onClick={onFit}
        title="Fit to view"
        className="mono"
        style={{
          padding: '2px 6px',
          fontSize: 10,
          background: 'transparent',
          color: 'var(--text-3)',
          border: 0,
          borderRadius: 3,
          cursor: 'pointer',
          minWidth: 36,
          textAlign: 'center',
        }}
      >
        {Math.round(zoom * 100)}%
      </button>
      <ZoomIconButton icon={ZoomIn} label="Zoom in" onClick={onZoomIn} />
      <ZoomIconButton icon={Maximize2} label="Fit to view" onClick={onFit} />
    </div>
  );
}

function ZoomIconButton({
  icon: Icon,
  label,
  onClick,
}: {
  icon: typeof ZoomIn;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={label}
      aria-label={label}
      style={{
        width: 22,
        height: 22,
        padding: 0,
        background: 'transparent',
        color: 'var(--text-3)',
        border: 0,
        borderRadius: 3,
        cursor: 'pointer',
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Icon size={12} strokeWidth={1.8} />
    </button>
  );
}
