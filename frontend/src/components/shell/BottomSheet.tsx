import { useEffect, useRef } from 'react';
import { X } from 'lucide-react';

type Props = {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
};

/**
 * Mobile-only bottom sheet. Viewport-fixed, slides up from the bottom
 * with a drag-handle header that supports drag-to-dismiss (past an
 * 80px threshold). Escape key and backdrop taps also close. Hidden on
 * desktop (lg+).
 *
 * Consumers give it children — the sheet supplies the chrome
 * (backdrop, rounded top, drag handle, close button, scroll area).
 */
export default function BottomSheet({ open, onClose, title, children }: Props) {
  const sheetRef = useRef<HTMLElement | null>(null);
  const startYRef = useRef<number | null>(null);
  const DISMISS_THRESHOLD = 80;

  // Escape key closes the sheet — standard modal behavior.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  const setSheetTranslate = (px: number | null) => {
    const el = sheetRef.current;
    if (!el) return;
    if (px === null) {
      el.style.transform = '';
      el.style.transition = '';
    } else {
      el.style.transition = 'none';
      el.style.transform = `translateY(${Math.max(0, px)}px)`;
    }
  };

  const onTouchStart = (e: React.TouchEvent<HTMLDivElement>) => {
    startYRef.current = e.touches[0].clientY;
    setSheetTranslate(0);
  };
  const onTouchMove = (e: React.TouchEvent<HTMLDivElement>) => {
    if (startYRef.current === null) return;
    setSheetTranslate(e.touches[0].clientY - startYRef.current);
  };
  const onTouchEnd = (e: React.TouchEvent<HTMLDivElement>) => {
    if (startYRef.current === null) return;
    const endY = e.changedTouches[0]?.clientY ?? startYRef.current;
    const delta = endY - startYRef.current;
    setSheetTranslate(null);
    if (delta > DISMISS_THRESHOLD) onClose();
    startYRef.current = null;
  };

  return (
    <>
      <div
        className="bottom-sheet-backdrop lg:hidden"
        data-open={open ? 'true' : 'false'}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        ref={sheetRef}
        className="bottom-sheet lg:hidden flex flex-col"
        data-open={open ? 'true' : 'false'}
        role="dialog"
        aria-modal="true"
        aria-hidden={!open}
      >
        <div
          className="flex-shrink-0 relative flex items-center px-4 pt-3 pb-2"
          style={{
            borderBottom: '1px solid var(--border)',
            touchAction: 'none',
            cursor: 'grab',
            userSelect: 'none',
          }}
          onTouchStart={onTouchStart}
          onTouchMove={onTouchMove}
          onTouchEnd={onTouchEnd}
          onTouchCancel={onTouchEnd}
        >
          <span
            aria-hidden="true"
            style={{
              position: 'absolute',
              left: '50%',
              top: 6,
              transform: 'translateX(-50%)',
              width: 36,
              height: 4,
              borderRadius: 999,
              background: 'var(--border-strong)',
            }}
          />
          <span
            className="mono uppercase"
            style={{
              fontSize: 10.5,
              color: 'var(--text-3)',
              letterSpacing: '0.14em',
              marginTop: 8,
            }}
          >
            {title}
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close sheet"
            className="ml-auto inline-flex items-center justify-center"
            style={{
              marginTop: 8,
              width: 28,
              height: 28,
              borderRadius: 999,
              border: 0,
              background: 'var(--bg-sunken)',
              color: 'var(--text-3)',
              boxShadow: 'inset 0 0 0 1px var(--border)',
              cursor: 'pointer',
            }}
          >
            <X size={13} strokeWidth={2} />
          </button>
        </div>
        <div
          className="flex-1 min-h-0 overflow-y-auto p-4 sm:p-5 space-y-4"
          style={{ overscrollBehavior: 'contain' }}
        >
          {children}
        </div>
      </aside>
    </>
  );
}
