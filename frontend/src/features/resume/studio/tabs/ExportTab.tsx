// Export tab. Replaces the prior modal — exports always render the
// current resume, so a tab keeps the live preview visible alongside
// the format picker instead of covering it. One row per format with a
// short label, blurb, and per-action button. Server PDF + browser
// print sit next to each other so a renderer outage never blocks an
// export entirely.
//
// Errors surface inline per format (rather than as toasts) because
// the user is already looking at this surface; no need to bounce
// their attention elsewhere.

import { useState } from 'react';
import { Download, Printer } from 'lucide-react';
import type { Resume, ResumeData } from '../../types';
import { exportPdfServer, exportPdfPrint } from '../../export/pdf';
import { exportDocx } from '../../export/docx';
import { exportStandaloneHtml } from '../../export/html';
import { exportMarkdown } from '../../export/markdown';
import { exportText } from '../../export/text';
import { exportJsonResume } from '../../export/jsonResume';

type Props = {
  resume: Resume | null;
  data: ResumeData;
  // Push pending in-flight edits before any export so the rendered
  // copy reflects everything the user has typed. Provided by the
  // host (ResumeStudio) which owns the resume hook.
  onBeforeExport: () => Promise<void>;
};

type Slot = {
  key: string;
  label: string;
  blurb: string;
  action: 'server-pdf' | 'print' | 'docx' | 'html' | 'markdown' | 'text' | 'json';
  primary?: boolean;
};

const SLOTS: Slot[] = [
  {
    key: 'server-pdf',
    label: 'PDF (high-fidelity)',
    blurb:
      'Server-rendered via headless Chromium. Best match to the on-screen preview.',
    action: 'server-pdf',
    primary: true,
  },
  {
    key: 'print',
    label: 'Print to PDF (browser)',
    blurb:
      'Opens the system print dialog. Works offline; appearance varies by browser.',
    action: 'print',
  },
  {
    key: 'docx',
    label: 'Word (.docx)',
    blurb:
      "When a recruiter asks for the Word version. Clean, ATS-parseable, doesn't try to mimic the on-screen typography.",
    action: 'docx',
  },
  {
    key: 'html',
    label: 'Standalone HTML',
    blurb: 'Self-contained .html file. Email-attachable, prints nicely.',
    action: 'html',
  },
  {
    key: 'markdown',
    label: 'Markdown',
    blurb: 'Paste into a GitHub README or a blog post.',
    action: 'markdown',
  },
  {
    key: 'text',
    label: 'Plain text',
    blurb: 'For ATS systems that mangle PDFs. The "always works" companion file.',
    action: 'text',
  },
  {
    key: 'json',
    label: 'JSON Resume',
    blurb:
      'jsonresume.org schema. Portable across dozens of community themes outside Rounds.',
    action: 'json',
  },
];

export default function ExportTab({ resume, data, onBeforeExport }: Props) {
  const [busy, setBusy] = useState<string | null>(null);
  const [errors, setErrors] = useState<Record<string, string>>({});

  if (!resume) {
    return (
      <div style={{ fontSize: 12, color: 'var(--text-3)' }}>
        Loading resume…
      </div>
    );
  }

  const filenameBase = (resume.slug || resume.name || 'resume').replace(
    /[^a-z0-9._-]+/gi,
    '-',
  );

  const run = async (slot: Slot) => {
    setBusy(slot.key);
    setErrors((e) => {
      const next = { ...e };
      delete next[slot.key];
      return next;
    });
    try {
      // Flush pending edits so the export reflects the latest text.
      await onBeforeExport();
      switch (slot.action) {
        case 'server-pdf':
          await exportPdfServer(filenameBase, 0);
          break;
        case 'print':
          exportPdfPrint();
          break;
        case 'docx':
          await exportDocx(data, filenameBase);
          break;
        case 'html':
          if (!exportStandaloneHtml(filenameBase)) {
            throw new Error('No preview is currently rendered.');
          }
          break;
        case 'markdown':
          exportMarkdown(data, filenameBase);
          break;
        case 'text':
          exportText(data, filenameBase);
          break;
        case 'json':
          exportJsonResume(data, filenameBase);
          break;
      }
    } catch (err) {
      setErrors((e) => ({ ...e, [slot.key]: (err as Error).message }));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      {SLOTS.map((s) => (
        <div
          key={s.key}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            padding: 12,
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            background: s.primary ? 'var(--bg-elev)' : 'transparent',
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>{s.label}</div>
            <div
              style={{ fontSize: 11.5, color: 'var(--text-3)', lineHeight: 1.45 }}
            >
              {s.blurb}
            </div>
            {errors[s.key] && (
              <div
                style={{
                  marginTop: 4,
                  fontSize: 11,
                  color: 'var(--plum)',
                  lineHeight: 1.4,
                }}
              >
                {errors[s.key]}
              </div>
            )}
          </div>
          <button
            type="button"
            onClick={() => run(s)}
            disabled={busy !== null}
            className="inline-flex items-center gap-1.5"
            style={{
              padding: '7px 12px',
              borderRadius: 'var(--radius)',
              border: 0,
              background: s.primary ? 'var(--accent)' : 'transparent',
              color: s.primary ? 'var(--bg-elev)' : 'var(--text-2)',
              boxShadow: s.primary
                ? 'none'
                : 'inset 0 0 0 1px var(--border-strong)',
              fontSize: 12,
              fontWeight: 500,
              cursor: busy ? 'wait' : 'pointer',
              flexShrink: 0,
            }}
          >
            {s.action === 'print' ? (
              <Printer size={12} strokeWidth={1.8} />
            ) : (
              <Download size={12} strokeWidth={1.8} />
            )}
            {busy === s.key
              ? 'Working…'
              : s.action === 'print'
                ? 'Print'
                : 'Download'}
          </button>
        </div>
      ))}
    </div>
  );
}
