import { useState, useRef, useEffect, useCallback } from 'react';
import { Upload, FileText, Type, X } from 'lucide-react';
import { extractText } from '../features/resume/import/extract';
import { importExperienceFromText, type ExtractionResult } from './importApi';
import ImportReview from './ImportReview';

type Tab = 'upload' | 'paste';

interface Props {
  open: boolean;
  onClose: () => void;
  onImported: () => void;
}

export default function ImportModal({ open, onClose, onImported }: Props) {
  const [tab, setTab] = useState<Tab>('upload');
  const [pastedText, setPastedText] = useState('');
  // Staged progress label while work is in flight (null = idle). Drives the
  // running-glow border, matching resume import / ATS scoring.
  const [status, setStatus] = useState<string | null>(null);
  const loading = status !== null;
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Reset state when modal opens
  useEffect(() => {
    if (open) {
      setTab('upload');
      setPastedText('');
      setStatus(null);
      setError(null);
      setResult(null);
    }
  }, [open]);

  // Escape to close
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [open, onClose]);

  const sendToAI = useCallback(async (text: string) => {
    setStatus('Reading with AI…');
    setError(null);
    try {
      const res = await importExperienceFromText(text);
      setResult(res);
    } catch (e) {
      setError(String(e));
    } finally {
      setStatus(null);
    }
  }, []);

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setStatus('Extracting text…');
    setError(null);
    try {
      const { text } = await extractText(file);
      await sendToAI(text);
    } catch (e) {
      setError(String(e));
      setStatus(null);
    }
    // Reset file input so the same file can be re-selected
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function handlePasteSubmit() {
    const trimmed = pastedText.trim();
    if (!trimmed) return;
    await sendToAI(trimmed);
  }

  function handleReviewComplete() {
    onImported();
    onClose();
  }

  if (!open) return null;

  // ---- Review phase ----
  if (result) {
    return (
      <ImportReview
        result={result}
        onComplete={handleReviewComplete}
        onCancel={onClose}
      />
    );
  }

  // ---- Import phase ----
  const TABS: { key: Tab; label: string; icon: typeof Upload }[] = [
    { key: 'upload', label: 'Upload File', icon: Upload },
    { key: 'paste', label: 'Paste Text', icon: Type },
  ];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Import Experiences"
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
          width: 'min(600px, 100%)',
          maxHeight: 'calc(100vh - 48px)',
          background: 'var(--bg)',
          borderRadius: 'var(--radius-lg)',
          boxShadow: 'var(--shadow-elev)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          className="flex items-start gap-3"
          style={{
            padding: '16px 20px 12px',
            borderBottom: '1px solid var(--border)',
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <h2
              style={{
                fontSize: 22,
                lineHeight: 1.15,
                margin: 0,
                color: 'var(--text)',
                fontWeight: 600,
              }}
            >
              Import Experiences
            </h2>
            <p
              style={{
                margin: '4px 0 0',
                fontSize: 12.5,
                color: 'var(--text-3)',
                lineHeight: 1.45,
              }}
            >
              Upload a resume or paste text to extract experience items.
            </p>
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

        {/* Tab bar */}
        <div
          className="flex"
          style={{
            borderBottom: '1px solid var(--border)',
            padding: '0 20px',
          }}
        >
          {TABS.map((t) => {
            const Icon = t.icon;
            const isActive = tab === t.key;
            return (
              <button
                key={t.key}
                type="button"
                onClick={() => { setTab(t.key); setError(null); }}
                className="flex items-center gap-1.5"
                style={{
                  padding: '10px 14px',
                  border: 0,
                  borderBottom: isActive ? '2px solid var(--accent)' : '2px solid transparent',
                  background: 'transparent',
                  color: isActive ? 'var(--text)' : 'var(--text-3)',
                  fontSize: 13,
                  fontWeight: isActive ? 600 : 400,
                  cursor: 'pointer',
                  marginBottom: -1,
                }}
              >
                <Icon size={14} strokeWidth={isActive ? 2.2 : 1.8} />
                {t.label}
              </button>
            );
          })}
        </div>

        {/* Body */}
        <div style={{ padding: 20, flex: 1, overflow: 'auto', minHeight: 0 }}>
          {error && (
            <div
              style={{
                padding: '10px 14px',
                borderRadius: 'var(--radius)',
                background: 'var(--plum-soft, rgba(180, 60, 100, 0.08))',
                color: 'var(--plum)',
                fontSize: 13,
                marginBottom: 16,
              }}
            >
              {error}
            </div>
          )}

          {tab === 'upload' && (
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.txt,.md,.markdown"
                onChange={handleFileChange}
                style={{ display: 'none' }}
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={loading}
                data-ai-processing-glow={loading ? 'true' : undefined}
                className="flex flex-col items-center justify-center gap-3 w-full"
                style={{
                  padding: '40px 20px',
                  border: 0,
                  borderRadius: 'var(--radius)',
                  background: 'var(--bg-sunken)',
                  boxShadow: 'inset 0 0 0 1px var(--border)',
                  cursor: loading ? 'wait' : 'pointer',
                  color: loading ? 'var(--text-2)' : 'var(--text-3)',
                  fontSize: 13,
                }}
              >
                <FileText size={28} strokeWidth={1.8} style={{ color: loading ? 'var(--accent)' : undefined }} />
                {status ?? 'Click to upload PDF, DOCX, TXT, or Markdown'}
              </button>
            </div>
          )}

          {tab === 'paste' && (
            <div className="flex flex-col gap-3">
              <textarea
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                placeholder="Paste your resume or experience text here..."
                style={{
                  width: '100%',
                  minHeight: 200,
                  padding: '12px 14px',
                  border: 0,
                  borderRadius: 'var(--radius)',
                  background: 'var(--bg-sunken)',
                  boxShadow: 'inset 0 0 0 1px var(--border)',
                  color: 'var(--text)',
                  fontSize: 13,
                  lineHeight: 1.55,
                  resize: 'vertical',
                  outline: 'none',
                  fontFamily: 'inherit',
                }}
              />
              <button
                type="button"
                onClick={handlePasteSubmit}
                disabled={loading || !pastedText.trim()}
                data-ai-processing-glow={loading ? 'true' : undefined}
                className="inline-flex items-center justify-center gap-2 self-end"
                style={{
                  padding: '10px 18px',
                  border: 0,
                  borderRadius: 'var(--radius)',
                  background: 'var(--accent)',
                  color: 'var(--accent-fg, var(--paper))',
                  fontSize: 13,
                  fontWeight: 500,
                  cursor: loading ? 'wait' : !pastedText.trim() ? 'not-allowed' : 'pointer',
                  opacity: !loading && !pastedText.trim() ? 0.5 : 1,
                }}
              >
                <Upload size={14} strokeWidth={2} />
                {status ?? 'Import'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
