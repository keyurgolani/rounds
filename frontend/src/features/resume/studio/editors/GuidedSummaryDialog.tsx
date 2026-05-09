// Guided summary modal — three structured inputs (years, top skills,
// signature accomplishment) that drive a 3-part-formula professional
// summary via /api/ai/improve with style='guided-summary'. The
// backend's _GUIDED_SUMMARY_SYSTEM prompt instructs the model to
// preserve the user's literal numbers and skills verbatim, so the
// output is grounded in real input rather than fabrication.

import { useEffect, useRef, useState } from 'react';
import { Ruler, Sparkles, X } from 'lucide-react';
import { improveStream } from '../../ai/client';

type Props = {
  open: boolean;
  onClose: () => void;
  onApply: (summary: string) => void;
  currentSummary?: string;
};

export default function GuidedSummaryDialog({
  open,
  onClose,
  onApply,
  currentSummary,
}: Props) {
  const [years, setYears] = useState('');
  const [topSkills, setTopSkills] = useState('');
  const [accomplishment, setAccomplishment] = useState('');
  const [output, setOutput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') doClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  function doClose() {
    abortRef.current?.abort();
    setStreaming(false);
    onClose();
  }

  function reset() {
    setYears('');
    setTopSkills('');
    setAccomplishment('');
    setOutput('');
    setError(null);
  }

  const yearsNum = Number(years.trim());
  const skillList = topSkills
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean);
  const canGenerate =
    !streaming &&
    Number.isFinite(yearsNum) &&
    yearsNum > 0 &&
    skillList.length > 0 &&
    accomplishment.trim().length > 0;

  async function generate() {
    if (!canGenerate) return;
    abortRef.current?.abort();
    abortRef.current = new AbortController();
    setOutput('');
    setError(null);
    setStreaming(true);

    let acc = '';
    await improveStream(
      {
        text: currentSummary?.trim() || '(write a fresh 3-part-formula summary)',
        style: 'guided-summary',
        field: 'personalInfo.summary',
        context: {
          years: yearsNum,
          top_skills: skillList,
          signature_accomplishment: accomplishment.trim(),
        },
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

  function applyAndClose() {
    const trimmed = output.replace(/^\s+|\s+$/g, '');
    if (!trimmed) return;
    onApply(trimmed);
    reset();
    onClose();
  }

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Guided summary"
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
          maxWidth: 600,
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
            <Ruler size={14} strokeWidth={1.7} style={{ color: 'var(--accent)' }} />
            <div>
              <div className="eyebrow" style={{ fontSize: 9.5 }}>
                AI assistant
              </div>
              <div style={{ fontSize: 13, fontWeight: 500 }}>Guided summary (3-part formula)</div>
            </div>
          </div>
          <button type="button" onClick={doClose} aria-label="Close" style={iconBtn}>
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
          <p style={{ fontSize: 11.5, color: 'var(--text-3)', margin: 0 }}>
            Years of experience + best-fit skills + a signature accomplishment with
            hard numbers. The model is instructed to preserve every number you
            enter exactly.
          </p>

          <Field label="Years of experience">
            <input
              type="number"
              min={1}
              value={years}
              onChange={(e) => setYears(e.target.value)}
              placeholder="8"
              style={inputStyle}
            />
          </Field>

          <Field label="Top 3 skills (comma-separated)">
            <input
              type="text"
              value={topSkills}
              onChange={(e) => setTopSkills(e.target.value)}
              placeholder="Brand strategy, P&L, Team leadership"
              style={inputStyle}
            />
          </Field>

          <Field label="Signature accomplishment (with hard numbers)">
            <textarea
              value={accomplishment}
              onChange={(e) => setAccomplishment(e.target.value)}
              rows={3}
              placeholder="Grew U.S. revenue 47% to $112M in 18 months by launching 2 viral campaigns on a $300K budget."
              style={{ ...inputStyle, fontFamily: 'inherit', resize: 'vertical' }}
            />
          </Field>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={generate}
              disabled={!canGenerate}
              style={{
                padding: '8px 14px',
                borderRadius: 'var(--radius)',
                border: 0,
                background: 'var(--accent)',
                color: 'var(--bg-elev)',
                fontSize: 12.5,
                fontWeight: 500,
                cursor: canGenerate ? 'pointer' : 'not-allowed',
                opacity: canGenerate ? 1 : 0.6,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <Sparkles size={13} strokeWidth={1.7} />
              {streaming ? 'Streaming…' : output ? 'Regenerate' : 'Generate'}
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
            <Field label="Generated summary">
              <textarea
                value={output}
                onChange={(e) => setOutput(e.target.value)}
                rows={5}
                placeholder={error ? '' : 'The streamed summary will appear here…'}
                style={{
                  ...inputStyle,
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

          {output && !error && !streaming && (
            <div className="flex items-center gap-2">
              <button type="button" onClick={applyAndClose} style={primaryBtn}>
                Use this summary
              </button>
              <button type="button" onClick={() => setOutput('')} style={ghostBtn}>
                Discard
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="eyebrow" style={{ fontSize: 9.5 }}>
        {label}
      </span>
      {children}
    </label>
  );
}

const inputStyle: React.CSSProperties = {
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

const ghostBtn: React.CSSProperties = {
  padding: '8px 12px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'transparent',
  boxShadow: 'inset 0 0 0 1px var(--border)',
  color: 'var(--text-2)',
  fontSize: 12,
  fontWeight: 500,
  cursor: 'pointer',
};

const primaryBtn: React.CSSProperties = {
  padding: '8px 14px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'var(--accent)',
  color: 'var(--bg-elev)',
  fontSize: 12.5,
  fontWeight: 500,
  cursor: 'pointer',
};
