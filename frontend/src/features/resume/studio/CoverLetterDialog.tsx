// Cover-letter generator. Opens from the Studio header. Drives the
// AI text model with the current resume + a JD + tone, streams the
// letter into a text area, and lets the user copy or download it
// (Markdown or plain text).
//
// Anchoring to a tracked Application is optional but lifts the JD off
// the Application card automatically — the same trick TailorTab and
// ATSTab use.

import { useEffect, useMemo, useRef, useState } from 'react';
import { Copy, Download, Mail, Wand2, X } from 'lucide-react';
import { api } from '../../../api/client';
import { coverLetterStream } from '../ai/client';
import { downloadString } from '../export/index';
import type { ResumeData } from '../types';

type AppRow = {
  id: string;
  company: string;
  role: string;
  job_description?: string;
};

type Props = {
  open: boolean;
  onClose: () => void;
  data: ResumeData;
  filenameBase: string;
};

const TONES = [
  { id: 'professional', label: 'Professional' },
  { id: 'concise', label: 'Concise' },
  { id: 'warm', label: 'Warm' },
  { id: 'technical', label: 'Technical' },
];

export default function CoverLetterDialog({
  open,
  onClose,
  data,
  filenameBase,
}: Props) {
  const [apps, setApps] = useState<AppRow[]>([]);
  const [appId, setAppId] = useState<string | null>(null);
  const [jd, setJd] = useState('');
  const [tone, setTone] = useState('professional');
  const [output, setOutput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!open) return;
    api
      .get<AppRow[]>('/api/applications')
      .then(setApps)
      .catch(() => setApps([]));
  }, [open]);

  // Esc closes (cancels stream).
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') doClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const selectedApp = useMemo(
    () => apps.find((a) => a.id === appId) ?? null,
    [apps, appId],
  );

  function doClose() {
    abortRef.current?.abort();
    setStreaming(false);
    onClose();
  }

  function pickApp(id: string | null) {
    setAppId(id);
    if (!id) return;
    const a = apps.find((x) => x.id === id);
    if (a?.job_description && !jd.trim()) setJd(a.job_description);
  }

  async function generate() {
    if (!jd.trim()) return;
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setOutput('');
    setError(null);
    setCopied(false);
    setStreaming(true);
    let acc = '';
    await coverLetterStream(
      {
        data,
        job_description: jd,
        tone,
        target_company: selectedApp?.company,
        job_title: selectedApp?.role,
      },
      {
        onDelta: (chunk) => {
          acc += chunk;
          setOutput(acc);
        },
        onDone: () => setStreaming(false),
        onError: (err) => {
          setError(err.message);
          setStreaming(false);
        },
        signal: abortRef.current.signal,
      },
    );
  }

  async function copyText() {
    if (!output) return;
    try {
      await navigator.clipboard.writeText(output);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  }

  function download(kind: 'md' | 'txt') {
    if (!output) return;
    const ext = kind === 'md' ? 'md' : 'txt';
    const mime = kind === 'md' ? 'text/markdown;charset=utf-8' : 'text/plain;charset=utf-8';
    const company = selectedApp?.company
      ? `-${selectedApp.company.replace(/[^a-z0-9]+/gi, '-').toLowerCase()}`
      : '';
    downloadString(output, `${filenameBase}-cover${company}.${ext}`, mime);
  }

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Cover letter"
      onClick={doClose}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.45)',
        zIndex: 60,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 16,
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="card"
        style={{
          width: '100%',
          maxWidth: 720,
          maxHeight: '90vh',
          padding: 0,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          className="flex items-center justify-between"
          style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}
        >
          <div className="flex items-center gap-2">
            <Mail size={14} strokeWidth={1.7} style={{ color: 'var(--accent)' }} />
            <div>
              <div className="eyebrow" style={{ fontSize: 9.5 }}>
                AI assistant
              </div>
              <div style={{ fontSize: 13, fontWeight: 500 }}>Cover letter</div>
            </div>
          </div>
          <button
            type="button"
            onClick={doClose}
            aria-label="Close"
            style={iconBtn}
          >
            <X size={14} strokeWidth={1.8} />
          </button>
        </div>

        <div
          style={{
            padding: 14,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
            overflow: 'auto',
          }}
        >
          <Field label="Anchor to a tracked application (optional)">
            <select
              value={appId ?? ''}
              onChange={(e) => pickApp(e.target.value || null)}
              style={selectStyle}
            >
              <option value="">— No application —</option>
              {apps.map((a) => (
                <option key={a.id} value={a.id}>
                  {a.company} — {a.role}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Target JD">
            <textarea
              value={jd}
              onChange={(e) => setJd(e.target.value)}
              rows={5}
              placeholder="Paste the job description here."
              style={{ ...selectStyle, fontFamily: 'inherit', resize: 'vertical' }}
            />
          </Field>

          <Field label="Tone">
            <div className="flex flex-wrap gap-1.5">
              {TONES.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTone(t.id)}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 'var(--radius)',
                    border: 0,
                    background: tone === t.id ? 'var(--accent)' : 'var(--bg-sunken)',
                    color: tone === t.id ? 'var(--bg-elev)' : 'var(--text-2)',
                    boxShadow:
                      tone === t.id ? 'none' : 'inset 0 0 0 1px var(--border)',
                    fontSize: 11.5,
                    fontWeight: 500,
                    cursor: 'pointer',
                  }}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </Field>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={generate}
              disabled={streaming || !jd.trim()}
              style={{
                padding: '8px 14px',
                borderRadius: 'var(--radius)',
                border: 0,
                background: 'var(--accent)',
                color: 'var(--bg-elev)',
                fontSize: 12.5,
                fontWeight: 500,
                cursor: streaming || !jd.trim() ? 'not-allowed' : 'pointer',
                opacity: streaming || !jd.trim() ? 0.6 : 1,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <Wand2 size={13} strokeWidth={1.7} />
              {streaming ? 'Streaming…' : output ? 'Regenerate' : 'Generate cover letter'}
            </button>
            {streaming && (
              <button
                type="button"
                onClick={() => abortRef.current?.abort()}
                style={ghostBtn}
              >
                Stop
              </button>
            )}
          </div>

          {(output || error) && (
            <Field label="Letter">
              <textarea
                value={output}
                onChange={(e) => setOutput(e.target.value)}
                rows={12}
                placeholder={error ? '' : 'The streamed letter will appear here…'}
                style={{
                  ...selectStyle,
                  fontFamily: 'inherit',
                  resize: 'vertical',
                  lineHeight: 1.55,
                }}
              />
              {error && (
                <span style={{ fontSize: 11.5, color: 'var(--plum)' }}>{error}</span>
              )}
            </Field>
          )}

          {output && !error && (
            <div className="flex items-center gap-2 flex-wrap">
              <button type="button" onClick={copyText} style={outlineBtn}>
                <Copy size={12} strokeWidth={1.7} /> {copied ? 'Copied' : 'Copy'}
              </button>
              <button type="button" onClick={() => download('md')} style={outlineBtn}>
                <Download size={12} strokeWidth={1.7} /> .md
              </button>
              <button type="button" onClick={() => download('txt')} style={outlineBtn}>
                <Download size={12} strokeWidth={1.7} /> .txt
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="eyebrow" style={{ fontSize: 9.5 }}>
        {label}
      </span>
      {children}
    </label>
  );
}

const selectStyle: React.CSSProperties = {
  padding: '8px 10px',
  background: 'var(--bg-elev)',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
  borderRadius: 'var(--radius)',
  border: 0,
  fontSize: 12.5,
  color: 'var(--text)',
  outline: 'none',
  width: '100%',
};

const iconBtn: React.CSSProperties = {
  background: 'transparent',
  border: 0,
  padding: 4,
  borderRadius: 6,
  boxShadow: 'inset 0 0 0 1px var(--border)',
  color: 'var(--text-2)',
  cursor: 'pointer',
  display: 'inline-flex',
};

const outlineBtn: React.CSSProperties = {
  padding: '6px 10px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'transparent',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
  color: 'var(--text-2)',
  fontSize: 11.5,
  fontWeight: 500,
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 5,
};

const ghostBtn: React.CSSProperties = {
  padding: '6px 10px',
  background: 'transparent',
  border: 0,
  color: 'var(--text-3)',
  fontSize: 11.5,
  cursor: 'pointer',
};
