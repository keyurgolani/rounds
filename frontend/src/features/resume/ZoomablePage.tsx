// Reusable zoomable A4 page viewer. Owns the scroll container, the
// CSS-transform scaler, and a toolbar with zoom (−/%/+) + Fit. Used by
//
//   - studio/PreviewDialog — full-screen preview modal in the editor
//   - pages/PublicResume — read-only viewer for /r/:token share links
//
// so both views share zoom + fit + pagination behaviour. Callers own
// the outer chrome (modal backdrop, page header, etc.); this component
// stops at the scroll edge.
//
// Zoom mechanics:
//   • Buttons (−, %, +, Fit) and keyboard shortcuts (+/=, −, 0, F)
//   • Ctrl/Cmd + wheel zooms; plain wheel scrolls
//   • The page is wrapped in a transform-scaled inner div so the
//     scroll container reports correct overflow at every zoom level —
//     the user can pan a zoomed page by scrolling normally.
//   • An outer placeholder mirrors the scaled inner's footprint so the
//     scroll math works (scaled content otherwise overflows invisibly).

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { Maximize2, Minus, Plus } from 'lucide-react';
import type { ResumeData, TemplateConfig } from './types';
import { templateById } from './templates/registry';
import { ResumePageStyles } from './templates/parts';
import PaginatedFrame from './studio/PaginatedFrame';

const MIN_ZOOM = 0.4;
const MAX_ZOOM = 3;
const ZOOM_STEP = 0.1;

// Natural rendered width of an A4 page at 96 CSS-DPI. Used by the Fit
// calculation so we can pick a zoom that snugly fills the scroll area.
const PAGE_WIDTH_PX = (210 * 96) / 25.4;

const clampZoom = (z: number) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z));

type Props = {
  data: ResumeData;
  templateId: string;
  design: TemplateConfig;
  /** Eyebrow text on the left of the toolbar. Defaults to "Preview". */
  toolbarLabel?: string;
  /** Extra actions on the right side of the toolbar (e.g. a Close
   *  button when the parent is a modal). */
  toolbarActions?: ReactNode;
  /** Called on Esc keypress. Modals usually wire this to onClose. */
  onEscape?: () => void;
  /** Lock document body scroll while mounted (modal mode). */
  lockBodyScroll?: boolean;
};

export default function ZoomablePage({
  data,
  templateId,
  design,
  toolbarLabel = 'Preview',
  toolbarActions,
  onEscape,
  lockBodyScroll,
}: Props) {
  const Template = templateById(templateId).component;
  const scrollRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  // Measured natural size of the rendered page wrapper at scale 1. We
  // mirror this onto the outer placeholder so the scroll container
  // reports the right overflow when the inner is CSS-scaled.
  const [naturalSize, setNaturalSize] = useState({ w: 0, h: 0 });

  // Apply hidden-section filters identically to PreviewPane so the
  // viewer never shows content the export wouldn't. Memoised because
  // it appears in effect deps below; without memo every render
  // produced a new reference and re-fired the measurement effect,
  // causing an infinite render loop on object-literal identity.
  const renderData = useMemo<ResumeData>(
    () => ({
      ...data,
      experience: data.hiddenSections?.includes('experience') ? [] : data.experience,
      education: data.hiddenSections?.includes('education') ? [] : data.education,
      skills: data.hiddenSections?.includes('skills') ? [] : data.skills,
      projects: data.hiddenSections?.includes('projects') ? [] : data.projects,
      publications: data.hiddenSections?.includes('publications')
        ? []
        : data.publications,
      profiles: data.hiddenSections?.includes('profiles') ? [] : data.profiles,
    }),
    [data],
  );

  // Fit-to-width helper. Reads the live scroll-container width so it
  // stays accurate after browser resizes.
  const fitZoom = useCallback(() => {
    const container = scrollRef.current;
    if (!container) return;
    // 32px gutter on either side so the page doesn't kiss the edge.
    const available = container.clientWidth - 64;
    if (available <= 0) return;
    setZoom(clampZoom(available / PAGE_WIDTH_PX));
  }, []);

  // Default to "Fit" on mount so a long resume opens with the whole
  // width visible regardless of viewport.
  useEffect(() => {
    const id = requestAnimationFrame(fitZoom);
    return () => cancelAnimationFrame(id);
  }, [fitZoom]);

  useEffect(() => {
    if (!lockBodyScroll) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [lockBodyScroll]);

  // Track the rendered page's natural size so we can size the outer
  // placeholder. Re-measures on content changes (template swap, edits,
  // font load) via ResizeObserver. setState is functional + bails when
  // w/h are unchanged so equal measurements don't re-render.
  useLayoutEffect(() => {
    const el = innerRef.current;
    if (!el) return;
    const measure = () => {
      const w = el.offsetWidth;
      const h = el.offsetHeight;
      setNaturalSize((prev) => (prev.w === w && prev.h === h ? prev : { w, h }));
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Keyboard shortcuts: Esc → onEscape, +/=/− zoom, 0 → 100%, F → fit.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && onEscape) {
        onEscape();
        return;
      }
      // Don't hijack zoom while the user is typing.
      const target = e.target as HTMLElement | null;
      if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA')) {
        return;
      }
      if (e.key === '+' || e.key === '=') {
        e.preventDefault();
        setZoom((z) => clampZoom(z + ZOOM_STEP));
      } else if (e.key === '-' || e.key === '_') {
        e.preventDefault();
        setZoom((z) => clampZoom(z - ZOOM_STEP));
      } else if (e.key === '0') {
        e.preventDefault();
        setZoom(1);
      } else if (e.key === 'f' || e.key === 'F') {
        e.preventDefault();
        fitZoom();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onEscape, fitZoom]);

  // Ctrl/Cmd + wheel zooms. Plain wheel scrolls so a long zoomed-in
  // page can be reviewed top-to-bottom naturally.
  const onWheel = useCallback((e: React.WheelEvent<HTMLDivElement>) => {
    if (!(e.ctrlKey || e.metaKey)) return;
    e.preventDefault();
    const dir = e.deltaY < 0 ? 1 : -1;
    setZoom((z) => clampZoom(z + dir * ZOOM_STEP));
  }, []);

  return (
    <>
      <ResumePageStyles />
      <Toolbar
        label={toolbarLabel}
        zoom={zoom}
        onZoomIn={() => setZoom((z) => clampZoom(z + ZOOM_STEP))}
        onZoomOut={() => setZoom((z) => clampZoom(z - ZOOM_STEP))}
        onZoomReset={() => setZoom(1)}
        onZoomFit={fitZoom}
        actions={toolbarActions}
      />
      <div
        ref={scrollRef}
        onWheel={onWheel}
        style={{
          flex: 1,
          minHeight: 0,
          overflow: 'auto',
          padding: 32,
          background: 'var(--bg-sunken)',
        }}
      >
        <div
          style={{
            // Outer placeholder mirrors the scaled inner's footprint
            // so the scroll container reports correct overflow.
            // Centered horizontally when narrower than the viewport so
            // a fitted page sits centered, not pinned left.
            width: naturalSize.w ? naturalSize.w * zoom : 'auto',
            height: naturalSize.h ? naturalSize.h * zoom : 'auto',
            margin: '0 auto',
            position: 'relative',
          }}
        >
          <div
            ref={innerRef}
            style={{
              width: 'fit-content',
              transform: `scale(${zoom})`,
              transformOrigin: 'top left',
              position: 'absolute',
              top: 0,
              left: 0,
            }}
          >
            <PaginatedFrame>
              <Template data={renderData} design={design} />
            </PaginatedFrame>
          </div>
        </div>
      </div>
    </>
  );
}

function Toolbar({
  label,
  zoom,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  onZoomFit,
  actions,
}: {
  label: string;
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onZoomReset: () => void;
  onZoomFit: () => void;
  actions?: ReactNode;
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '10px 14px',
        background: 'var(--bg-elev)',
        borderBottom: '1px solid var(--border)',
        gap: 10,
      }}
    >
      <div className="eyebrow" style={{ fontSize: 9.5 }}>
        {label}
      </div>

      <div className="flex items-center gap-2">
        <div
          className="flex items-center"
          style={{
            background: 'var(--bg-sunken)',
            borderRadius: 8,
            boxShadow: 'inset 0 0 0 1px var(--border)',
            padding: 2,
            gap: 2,
          }}
        >
          <button
            type="button"
            onClick={onZoomOut}
            disabled={zoom <= MIN_ZOOM + 1e-3}
            aria-label="Zoom out"
            title="Zoom out  (−)"
            style={zoomBtn(zoom <= MIN_ZOOM + 1e-3)}
          >
            <Minus size={13} strokeWidth={1.9} />
          </button>
          <button
            type="button"
            onClick={onZoomReset}
            title="Reset to 100%  (0)"
            style={{
              ...zoomBtn(false),
              minWidth: 56,
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {Math.round(zoom * 100)}%
          </button>
          <button
            type="button"
            onClick={onZoomIn}
            disabled={zoom >= MAX_ZOOM - 1e-3}
            aria-label="Zoom in"
            title="Zoom in  (+)"
            style={zoomBtn(zoom >= MAX_ZOOM - 1e-3)}
          >
            <Plus size={13} strokeWidth={1.9} />
          </button>
        </div>

        <button
          type="button"
          onClick={onZoomFit}
          title="Fit to width  (F)"
          className="inline-flex items-center gap-1.5"
          style={{
            padding: '6px 12px',
            borderRadius: 8,
            background: 'transparent',
            color: 'var(--text-2)',
            boxShadow: 'inset 0 0 0 1px var(--border-strong)',
            border: 0,
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          <Maximize2 size={12} strokeWidth={1.8} />
          Fit
        </button>

        {actions}
      </div>
    </div>
  );
}

function zoomBtn(disabled: boolean): React.CSSProperties {
  return {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '5px 9px',
    minWidth: 30,
    background: 'transparent',
    color: disabled ? 'var(--text-3)' : 'var(--text-2)',
    border: 0,
    borderRadius: 6,
    fontSize: 12,
    fontWeight: 500,
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
  };
}
