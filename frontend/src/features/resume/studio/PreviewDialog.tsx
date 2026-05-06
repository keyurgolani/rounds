// Full-screen preview modal — renders the same A4 page the editor's
// PreviewPane shows, but on its own backdrop with a toolbar and a
// user-controlled zoom level so the resume can be inspected in detail
// without the editor chrome competing for room.
//
// Zoom mechanics:
//   • Buttons (−, 100%, +, Fit) and keyboard shortcuts (+, −, 0, F)
//   • Ctrl/Cmd + wheel zooms; plain wheel scrolls
//   • The page is wrapped in a CSS-transform scaler so the scroll
//     container reports correct overflow at every zoom level — the
//     user can pan a zoomed page by scrolling normally.
//
// Pagination markers from PaginatedFrame are kept; they're useful for
// the "inspect" use-case (the user can see exactly where pages break)
// and hidden via existing print rules whenever this dialog is printed.

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import { Maximize2, Minus, Plus, X } from 'lucide-react';
import type { ResumeData, TemplateConfig } from '../types';
import { templateById } from '../templates/registry';
import { ResumePageStyles } from '../templates/parts';
import PaginatedFrame from './PaginatedFrame';

type Props = {
  open: boolean;
  onClose: () => void;
  data: ResumeData;
  templateId: string;
  design: TemplateConfig;
};

const MIN_ZOOM = 0.4;
const MAX_ZOOM = 3;
const ZOOM_STEP = 0.1;

// The natural rendered width of an A4 page at 96 CSS-DPI. Used as the
// reference width for the "Fit" calculation so we can pick a zoom
// that snugly fills the available scroll container.
const PAGE_WIDTH_PX = (210 * 96) / 25.4;

const clampZoom = (z: number) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z));

export default function PreviewDialog({
  open,
  onClose,
  data,
  templateId,
  design,
}: Props) {
  const Template = templateById(templateId).component;
  const scrollRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  // Measured natural size of the rendered page wrapper at scale 1.
  // We mirror this onto the outer placeholder so the scroll container
  // reports the right overflow when the inner is CSS-scaled.
  const [naturalSize, setNaturalSize] = useState({ w: 0, h: 0 });

  // Apply hidden-section filters identically to PreviewPane so the
  // dialog never shows content the export wouldn't. Memoised because
  // it appears in effect deps below; without memo, every render
  // produced a new reference and re-fired the measurement effect,
  // which then called setNaturalSize with a fresh object literal and
  // pushed React into an infinite render loop (the dialog would mount
  // blank because the loop never settled).
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
    // Leave a 32px gutter on either side so the page doesn't kiss the
    // scroll container edges.
    const available = container.clientWidth - 64;
    if (available <= 0) return;
    setZoom(clampZoom(available / PAGE_WIDTH_PX));
  }, []);

  // Reset to a sensible default on each open. We pick "Fit" so a long
  // resume opens with the whole width visible regardless of viewport.
  useEffect(() => {
    if (!open) return;
    // Defer one frame so the scroll container has its measured width
    // before fitZoom reads it.
    const id = requestAnimationFrame(fitZoom);
    return () => cancelAnimationFrame(id);
  }, [open, fitZoom]);

  // Body scroll-lock while the dialog is open — otherwise scrolling
  // the page below shows through the backdrop on some browsers.
  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prev;
    };
  }, [open]);

  // Track the rendered page's natural size so we can size the outer
  // placeholder. The inner re-measures on content changes (template
  // swap, edits, font load) via ResizeObserver — no need to keep
  // those values in the dep array. setState is functional + bails
  // when w/h are unchanged so equal measurements don't re-render.
  useLayoutEffect(() => {
    if (!open) return;
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
  }, [open]);

  // Keyboard shortcuts: Esc closes, +/=/− zoom, 0 → 100%, F → fit.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      // Don't hijack zoom while the user is typing somewhere — the
      // dialog has no inputs today, but this keeps the rule honest if
      // one is added later.
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
  }, [open, onClose, fitZoom]);

  // Ctrl/Cmd + wheel zooms around the cursor. Plain wheel scrolls so
  // a long zoomed-in page can be reviewed top-to-bottom naturally.
  const onWheel = useCallback((e: React.WheelEvent<HTMLDivElement>) => {
    if (!(e.ctrlKey || e.metaKey)) return;
    e.preventDefault();
    // Negative deltaY = scroll up = zoom in. Use a small linear step
    // per wheel notch instead of multiplying by deltaY so the zoom
    // feels predictable across mice and trackpads.
    const dir = e.deltaY < 0 ? 1 : -1;
    setZoom((z) => clampZoom(z + dir * ZOOM_STEP));
  }, []);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Resume preview"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.72)',
        zIndex: 80,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      <ResumePageStyles />

      <Toolbar
        zoom={zoom}
        onZoomIn={() => setZoom((z) => clampZoom(z + ZOOM_STEP))}
        onZoomOut={() => setZoom((z) => clampZoom(z - ZOOM_STEP))}
        onZoomReset={() => setZoom(1)}
        onZoomFit={fitZoom}
        onClose={onClose}
      />

      <div
        ref={scrollRef}
        onClick={(e) => e.stopPropagation()}
        onWheel={onWheel}
        style={{
          flex: 1,
          minHeight: 0,
          overflow: 'auto',
          padding: 32,
          // Match the editor preview's sunken backdrop so the page
          // material reads the same way it does in the studio.
          background: 'var(--bg-sunken)',
        }}
      >
        <div
          style={{
            // Outer placeholder mirrors the scaled inner's footprint
            // so the scroll container reports correct overflow. We
            // also center it horizontally when narrower than the
            // viewport so a fitted page sits centered, not pinned left.
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
    </div>
  );
}

function Toolbar({
  zoom,
  onZoomIn,
  onZoomOut,
  onZoomReset,
  onZoomFit,
  onClose,
}: {
  zoom: number;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onZoomReset: () => void;
  onZoomFit: () => void;
  onClose: () => void;
}) {
  return (
    <div
      onClick={(e) => e.stopPropagation()}
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
        Preview
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

        <button
          type="button"
          onClick={onClose}
          aria-label="Close preview"
          title="Close  (Esc)"
          className="inline-flex items-center gap-1.5"
          style={{
            padding: '6px 12px',
            borderRadius: 8,
            background: 'var(--accent)',
            color: 'var(--bg-elev)',
            border: 0,
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
          }}
        >
          <X size={13} strokeWidth={1.8} />
          Close
        </button>
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
