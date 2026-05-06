// "Improve" button for a resume field. Sits next to the field's
// label (passed via Field's `actions` slot). When clicked it streams
// a rewrite from /api/ai/improve, but the field's content is NOT
// cleared during streaming — chunks are buffered locally and the
// parent only receives `onChange(final)` once the stream completes.
// This way the field stays readable (and visibly disabled with a
// running glow) until the new value is ready to swap in.
//
// After a successful enhancement we keep both versions around — the
// pre-AI text (`original`) and the AI output (`aiVersion`) — so the
// user can hop between them with Undo/Redo. The visible affordance
// flips based on which side the field's current text matches:
//
//   text === aiVersion  →  Undo (back to original)
//   text === original   →  Redo (forward to AI version)
//   anything else       →  user has manually edited; both hide
//
// As soon as the user types into the field, both buttons disappear
// because neither version matches the live value anymore.
//
// Resume + ATS context (rule + AI) are pulled from the studio-wide
// EnhancementContext and forwarded to /api/ai/improve so a
// single-field rewrite stays consistent with the rest of the
// resume.

import { useEffect, useRef, useState } from 'react';
import { Redo2, Sparkles, Undo2 } from 'lucide-react';
import {
  improveStream,
  type ImproveContext,
  type ImproveStyle,
} from '../../ai/client';
import { useEnhancementContext } from '../EnhancementContext';

type Props = {
  text: string;
  context?: ImproveContext;
  field?: string;
  onChange: (next: string) => void;
  onStreamingChange?: (streaming: boolean) => void;
};

export default function ImproveButton({
  text,
  context,
  field,
  onChange,
  onStreamingChange,
}: Props) {
  const [style, setStyle] = useState<ImproveStyle>('improve');
  const [open, setOpen] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [original, setOriginal] = useState<string | null>(null);
  const [aiVersion, setAiVersion] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const enhancement = useEnhancementContext();

  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const setStreamingBoth = (next: boolean) => {
    setStreaming(next);
    onStreamingChange?.(next);
  };

  const run = async (s: ImproveStyle) => {
    if (!text.trim()) return;
    setOpen(false);
    setStyle(s);
    setError(null);
    setStreamingBoth(true);
    // New run: this becomes the new "original" baseline; clear any
    // prior AI version until this one settles.
    setOriginal(text);
    setAiVersion(null);
    abortRef.current?.abort();
    abortRef.current = new AbortController();

    let acc = '';
    await improveStream(
      {
        text,
        style: s,
        context,
        field,
        resume: enhancement.resume ?? undefined,
        ats: enhancement.ats ?? undefined,
      },
      {
        onDelta: (chunk) => {
          acc += chunk;
        },
        onError: (err) => {
          setError(err.message);
          setStreamingBoth(false);
        },
        onDone: () => {
          const finalText = acc.replace(/^\s+|\s+$/g, '');
          if (finalText && finalText !== text) {
            onChange(finalText);
            setAiVersion(finalText);
          }
          setStreamingBoth(false);
        },
        signal: abortRef.current.signal,
      },
    );
  };

  const onUndo = () => {
    if (original !== null) onChange(original);
  };
  const onRedo = () => {
    if (aiVersion !== null) onChange(aiVersion);
  };

  // History toggle visibility: only show one of the two, and only
  // when the field's live value still matches a known version. Once
  // the user types into the field the live value diverges from both
  // and both buttons hide.
  const hasHistory =
    original !== null && aiVersion !== null && original !== aiVersion;
  const showUndo = !streaming && hasHistory && text === aiVersion;
  const showRedo = !streaming && hasHistory && text === original;

  return (
    <div
      style={{
        position: 'relative',
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
      }}
    >
      {showUndo && (
        <button
          type="button"
          onClick={onUndo}
          title="Undo AI enhancement"
          aria-label="Undo AI enhancement"
          style={historyBtnStyle}
        >
          <Undo2 size={11} strokeWidth={1.7} />
        </button>
      )}
      {showRedo && (
        <button
          type="button"
          onClick={onRedo}
          title="Redo AI enhancement"
          aria-label="Redo AI enhancement"
          style={historyBtnStyle}
        >
          <Redo2 size={11} strokeWidth={1.7} />
        </button>
      )}

      <button
        type="button"
        onClick={() => {
          if (streaming) {
            abortRef.current?.abort();
            setStreamingBoth(false);
            return;
          }
          setOpen((o) => !o);
        }}
        title={streaming ? 'Stop' : 'AI improve'}
        aria-label={streaming ? 'Stop streaming' : 'AI improve field'}
        style={{
          height: 24,
          padding: '0 6px',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 4,
          background: streaming ? 'var(--accent)' : 'transparent',
          color: streaming ? 'var(--bg-elev)' : 'var(--text-2)',
          border: 0,
          borderRadius: 6,
          boxShadow: streaming ? 'none' : 'inset 0 0 0 1px var(--border)',
          fontSize: 10,
          fontWeight: 500,
          cursor: 'pointer',
        }}
      >
        <Sparkles size={11} strokeWidth={1.8} />
        {streaming ? 'Stop' : 'AI'}
      </button>
      {open && !streaming && (
        <div
          className="card"
          role="menu"
          style={{
            position: 'absolute',
            right: 0,
            top: 'calc(100% + 4px)',
            padding: 4,
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
            zIndex: 5,
            minWidth: 140,
          }}
        >
          <MenuItem onClick={() => run('improve')} label="Improve" hint="Rewrite for impact" />
          <MenuItem onClick={() => run('fix')} label="Fix" hint="Grammar & clarity only" />
          <MenuItem onClick={() => run('shorten')} label="Shorten" hint="Tighten under 180 chars" />
        </div>
      )}
      {error && (
        <div
          role="alert"
          style={{
            position: 'absolute',
            right: 0,
            top: 'calc(100% + 4px)',
            padding: '6px 8px',
            background: 'var(--bg-elev)',
            border: '1px solid var(--plum)',
            borderRadius: 6,
            fontSize: 11,
            color: 'var(--plum)',
            maxWidth: 240,
            zIndex: 6,
          }}
        >
          {error}
        </div>
      )}
      {/* keep style as a dependency hint for tooling; not visually rendered */}
      <span hidden>{style}</span>
    </div>
  );
}

// Field-level Optimize button for a list of bullet rows. Joins the
// bullets with newlines (the /improve system prompt knows to treat
// each non-empty line as its own bullet and preserve the line count),
// then splits the streamed reply back into the array. Useful when a
// Field's `actions` slot wants to optimize a whole list at once.
export function ListImproveButton({
  values,
  context,
  field,
  onChange,
  onStreamingChange,
}: {
  values: string[];
  context?: ImproveContext;
  field?: string;
  onChange: (next: string[]) => void;
  onStreamingChange?: (streaming: boolean) => void;
}) {
  const joined = values.filter((v) => v.trim()).join('\n');
  return (
    <ImproveButton
      text={joined}
      context={context}
      field={field}
      onStreamingChange={onStreamingChange}
      onChange={(next) => {
        const lines = next
          .split('\n')
          .map((line) => line.replace(/^\s*[-•*]\s+/, '').trim())
          .filter((line) => line.length > 0);
        onChange(lines);
      }}
    />
  );
}

const historyBtnStyle: React.CSSProperties = {
  height: 24,
  width: 24,
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  background: 'transparent',
  color: 'var(--text-3)',
  border: 0,
  borderRadius: 6,
  boxShadow: 'inset 0 0 0 1px var(--border)',
  cursor: 'pointer',
};

function MenuItem({
  label,
  hint,
  onClick,
}: {
  label: string;
  hint: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      role="menuitem"
      style={{
        textAlign: 'left',
        background: 'transparent',
        border: 0,
        padding: '6px 8px',
        borderRadius: 4,
        cursor: 'pointer',
        color: 'var(--text)',
        display: 'flex',
        flexDirection: 'column',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'var(--bg-sunken)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'transparent';
      }}
    >
      <span style={{ fontSize: 12, fontWeight: 500 }}>{label}</span>
      <span style={{ fontSize: 10.5, color: 'var(--text-3)' }}>{hint}</span>
    </button>
  );
}
