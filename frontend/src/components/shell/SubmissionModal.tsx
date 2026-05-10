import { useEffect, type ReactNode } from 'react';
import { X } from 'lucide-react';

type Props = {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
};

/**
 * Centered modal used by the AI Coding and Builder Problems detail pages
 * to surface a submission report. Closes on backdrop click or Escape.
 * The parent owns whether the modal is open and what the last result was;
 * this component is only chrome.
 */
export default function SubmissionModal({
  open,
  onClose,
  title,
  subtitle,
  children,
}: Props) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    // Prevent background scroll while modal is open.
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 50,
        background: 'rgba(0, 0, 0, 0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          width: 'min(880px, 100%)',
          maxHeight: 'calc(100vh - 48px)',
          background: 'var(--bg)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-elev)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <div
          className="flex items-start gap-3"
          style={{
            padding: '16px 20px 12px',
            borderBottom: '1px solid var(--border)',
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <h2
              className="display-italic"
              style={{
                fontSize: 22,
                lineHeight: 1.15,
                margin: 0,
                color: 'var(--text)',
              }}
            >
              {title}
            </h2>
            {subtitle && (
              <p
                style={{
                  margin: '4px 0 0',
                  fontSize: 12.5,
                  color: 'var(--text-3)',
                  lineHeight: 1.45,
                }}
              >
                {subtitle}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            title="Close (Esc)"
            style={{
              width: 28,
              height: 28,
              border: 0,
              borderRadius: 6,
              background: 'var(--bg-sunken)',
              color: 'var(--text-2)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              boxShadow: 'inset 0 0 0 1px var(--border)',
            }}
          >
            <X size={14} strokeWidth={2} />
          </button>
        </div>
        <div
          style={{
            flex: 1,
            overflow: 'auto',
            padding: 20,
            minHeight: 0,
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
