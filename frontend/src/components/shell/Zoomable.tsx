import { useEffect, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { Expand, X } from 'lucide-react';

interface ZoomableProps {
  children: ReactNode;
  className?: string;
  style?: React.CSSProperties;
  label?: string; // optional context label shown in the modal header
}

export default function Zoomable({ children, className = '', style, label }: ZoomableProps) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = prev;
      window.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const modal = open ? (
    <div
      onClick={() => setOpen(false)}
      role="dialog"
      aria-modal="true"
      aria-label={label ?? 'Zoomed view'}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.6)',
        backdropFilter: 'blur(2px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 32,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="card"
        style={{
          position: 'relative',
          width: '100%',
          maxWidth: 1400,
          maxHeight: '92vh',
          overflow: 'auto',
          padding: 28,
          background: 'var(--bg-elev)',
        }}
      >
        <button
          type="button"
          onClick={() => setOpen(false)}
          aria-label="Close zoomed view"
          style={{
            position: 'absolute',
            top: 12,
            right: 12,
            width: 32,
            height: 32,
            border: 0,
            borderRadius: 6,
            background: 'var(--bg-sunken)',
            boxShadow: 'inset 0 0 0 1px var(--border-strong)',
            color: 'var(--text-2)',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1,
          }}
        >
          <X size={14} strokeWidth={1.8} />
        </button>
        {label && (
          <div className="eyebrow mb-4" style={{ fontSize: 10.5 }}>
            {label}
          </div>
        )}
        {children}
      </div>
    </div>
  ) : null;

  return (
    <>
      <div
        className={className}
        style={{ position: 'relative', cursor: 'zoom-in', ...style }}
        onClick={(e) => {
          // Don't trigger if the click hit an interactive control inside (but not the wrapper itself)
          const target = e.target as HTMLElement;
          const interactive = target.closest('button, a, input, textarea, select, [role="button"]');
          if (interactive && interactive !== e.currentTarget) return;
          setOpen(true);
        }}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            setOpen(true);
          }
        }}
        aria-label={label ? `Expand ${label}` : 'Expand'}
      >
        {children}
        <div
          style={{
            position: 'absolute',
            top: 8,
            right: 8,
            width: 28,
            height: 28,
            borderRadius: 6,
            background: 'var(--bg-elev)',
            boxShadow: 'inset 0 0 0 1px var(--border-strong)',
            color: 'var(--text-3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            pointerEvents: 'none',
            opacity: 0.85,
          }}
          aria-hidden="true"
        >
          <Expand size={14} strokeWidth={1.8} />
        </div>
      </div>

      {modal && typeof document !== 'undefined'
        ? createPortal(modal, document.body)
        : null}
    </>
  );
}
