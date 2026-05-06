// Visualises and enforces A4 page breaks on the live preview.
//
// Two jobs:
//
//   1. Measure each `[data-page-block]` element and, when one would
//      straddle a 297 mm boundary, set `margin-top` on it equal to
//      the gap to the next page. Effectively: blocks that don't fit
//      on the current page move *whole* to the next page, leaving
//      whitespace at the bottom of the previous page — same behaviour
//      browsers and Puppeteer apply during real pagination, but here
//      we replicate it on screen so the editor preview matches the
//      printed output exactly.
//
//   2. Draw a dashed page-break line + "PAGE N" pill at every 297 mm
//      boundary so the user can see where pages divide.
//
// The push-down is applied as inline `style.marginTop` on the entries
// themselves, which means the same DOM is what gets serialized into
// HTML / PDF / print exports — no parallel mode where preview disagrees
// with output.

import { useLayoutEffect, useRef, useState, type ReactNode } from 'react';

// 1 mm @ 96-CSS-DPI = 96/25.4 px. A4 page = 297 mm tall.
const PAGE_HEIGHT_PX = (297 * 96) / 25.4;
// Tiny safety margin so a block that ends exactly at a page boundary
// (within sub-pixel rounding) doesn't get punted to the next page.
const BOUNDARY_TOLERANCE = 1;

type Props = { children: ReactNode };

export default function PaginatedFrame({ children }: Props) {
  const wrapperRef = useRef<HTMLDivElement>(null);
  const [pageCount, setPageCount] = useState(1);

  useLayoutEffect(() => {
    const article = wrapperRef.current?.querySelector(
      '[data-resume-page]',
    ) as HTMLElement | null;
    if (!article) return;

    let raf = 0;

    const adjust = () => {
      const blocks = Array.from(
        article.querySelectorAll<HTMLElement>('[data-page-block]'),
      );

      // 1) Reset previous push-downs so we measure the natural layout.
      for (const b of blocks) b.style.marginTop = '';
      // Force a layout flush so subsequent reads see the reset state.
      void article.offsetHeight;

      // 2) Forward pass: any block whose [top, bottom] crosses a page
      // boundary gets pushed down to land at the start of the next
      // page. Subsequent blocks reflow naturally.
      const articleTop = article.getBoundingClientRect().top;
      for (const block of blocks) {
        const rect = block.getBoundingClientRect();
        const offsetTop = rect.top - articleTop;
        const height = rect.height;
        // Skip blocks too tall to fit on any single page — the print
        // layer will break them anyway; pushing helps no one.
        if (height < 1 || height >= PAGE_HEIGHT_PX - BOUNDARY_TOLERANCE) continue;
        const offsetBottom = offsetTop + height;
        const pageStart = Math.floor(offsetTop / PAGE_HEIGHT_PX);
        const pageEnd = Math.floor(
          (offsetBottom - BOUNDARY_TOLERANCE) / PAGE_HEIGHT_PX,
        );
        if (pageStart !== pageEnd) {
          const nextPageStart = (pageStart + 1) * PAGE_HEIGHT_PX;
          const pushDown = nextPageStart - offsetTop;
          // +0.5 nudges past sub-pixel rounding without being visible.
          block.style.marginTop = `${pushDown + 0.5}px`;
        }
      }

      // 3) Page count comes from the new (possibly taller) article height.
      setPageCount(
        Math.max(1, Math.ceil(article.offsetHeight / PAGE_HEIGHT_PX)),
      );
    };

    // Run synchronously now so the first paint already shows pagination.
    adjust();

    // Re-run when the article resizes — covers content edits, font
    // loads, design-slider tweaks, and template switches. Coalesce
    // bursts into the next animation frame so multiple tiny mutations
    // don't trigger N adjustments.
    const ro = new ResizeObserver(() => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(adjust);
    });
    ro.observe(article);

    return () => {
      cancelAnimationFrame(raf);
      ro.disconnect();
    };
  });

  return (
    <div
      ref={wrapperRef}
      style={{
        position: 'relative',
        display: 'flex',
        justifyContent: 'center',
      }}
    >
      {children}
      {pageCount > 1 && (
        <div
          data-page-overlay
          aria-hidden
          style={{
            position: 'absolute',
            top: 0,
            left: '50%',
            transform: 'translateX(-50%)',
            width: '210mm',
            height: '100%',
            pointerEvents: 'none',
          }}
        >
          {Array.from({ length: pageCount - 1 }).map((_, i) => (
            <div
              key={i}
              style={{
                position: 'absolute',
                top: `${(i + 1) * PAGE_HEIGHT_PX}px`,
                left: 0,
                right: 0,
                borderTop: '2px dashed var(--accent)',
                opacity: 0.55,
              }}
            >
              <span
                className="mono"
                style={{
                  position: 'absolute',
                  top: -10,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  background: 'var(--bg-elev)',
                  padding: '2px 10px',
                  borderRadius: 999,
                  fontSize: 9.5,
                  color: 'var(--text-3)',
                  boxShadow:
                    '0 1px 4px rgba(0,0,0,0.15), inset 0 0 0 1px var(--border-strong)',
                  letterSpacing: '0.12em',
                  whiteSpace: 'nowrap',
                }}
              >
                PAGE {i + 2}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
