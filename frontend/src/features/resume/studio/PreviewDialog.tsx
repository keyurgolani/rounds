// Full-screen preview modal — renders the same A4 page the editor's
// PreviewPane shows, but on its own backdrop with a toolbar and
// user-controlled zoom so the resume can be inspected in detail
// without the editor chrome competing for room.
//
// The zoomable scroll/scale machinery lives in `ZoomablePage`, which
// is also reused by `pages/PublicResume` so the share-link viewer
// looks and feels the same as the studio preview.

import { X } from 'lucide-react';
import { useEffect } from 'react';
import type { ResumeData, TemplateConfig } from '../types';
import ZoomablePage from '../ZoomablePage';

type Props = {
  open: boolean;
  onClose: () => void;
  data: ResumeData;
  templateId: string;
  design: TemplateConfig;
};

export default function PreviewDialog({
  open,
  onClose,
  data,
  templateId,
  design,
}: Props) {
  // Body scroll-lock is handled by ZoomablePage when `lockBodyScroll`
  // is true; nothing else to do per-mount here.
  useEffect(() => {
    // No-op effect kept so future modal-only side effects have a hook.
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
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          flex: 1,
          minHeight: 0,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <ZoomablePage
          data={data}
          templateId={templateId}
          design={design}
          toolbarLabel="Preview"
          onEscape={onClose}
          lockBodyScroll
          toolbarActions={
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
          }
        />
      </div>
    </div>
  );
}
