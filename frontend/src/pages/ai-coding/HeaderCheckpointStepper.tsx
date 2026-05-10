import { useEffect, useRef, useState } from 'react';
import { Check, RotateCcw } from 'lucide-react';
import BlockMarkdown from '../../components/shell/BlockMarkdown';

type Checkpoint = {
  label: string;
  prompt: string;
  ai_allowed: boolean;
};

type Props = {
  checkpoints: Checkpoint[];
  currentIndex: number;
  passed: boolean[];
  /** Reset the passed-state of a specific checkpoint. Optional — when
   *  omitted, the reset affordance is hidden. */
  onResetCheckpoint?: (idx: number) => void;
};

/**
 * Header-mounted stepper that morphs in place. Closed: a compact row
 * of numbered/checkmarked dots connected by horizontal lines. Click
 * anywhere on it and the SAME element transforms into the larger
 * stepper plus a description card — anchored at the closed state's
 * top-right so the dots visually grow from where they were rather
 * than a separate popover appearing.
 *
 * Layout trick: when expanded, an invisible spacer reserves the
 * closed stepper's footprint in the header chrome, while the actual
 * panel takes itself out of flow (`position: absolute`) anchored to
 * the same corner. The expanded panel's first row is itself a
 * stepper, just bigger — so the user reads it as the same control
 * growing.
 */
export default function HeaderCheckpointStepper({
  checkpoints,
  currentIndex,
  passed,
  onResetCheckpoint,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const [focusIdx, setFocusIdx] = useState(currentIndex);
  const wrapRef = useRef<HTMLDivElement>(null);
  const closedRef = useRef<HTMLButtonElement>(null);
  const [closedSize, setClosedSize] = useState<{ w: number; h: number } | null>(
    null,
  );

  // Sync focused step when the outer active changes (e.g. via the CTA).
  useEffect(() => {
    setFocusIdx(currentIndex);
  }, [currentIndex]);

  // Close on outside click / Escape.
  useEffect(() => {
    if (!expanded) return;
    const onClick = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setExpanded(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setExpanded(false);
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [expanded]);

  if (!checkpoints || checkpoints.length === 0) return null;

  function stepStatus(i: number): 'passed' | 'active' | 'todo' {
    if (passed[i]) return 'passed';
    if (i === currentIndex) return 'active';
    return 'todo';
  }

  function handleOpen() {
    if (closedRef.current) {
      const r = closedRef.current.getBoundingClientRect();
      setClosedSize({ w: r.width, h: r.height });
    }
    setExpanded(true);
  }

  return (
    <div
      ref={wrapRef}
      style={{
        position: 'relative',
        display: 'inline-block',
      }}
    >
      {/* When expanded, this invisible spacer holds the closed footprint
          so surrounding header chrome doesn't reflow. */}
      {expanded && closedSize && (
        <span
          aria-hidden="true"
          style={{
            display: 'inline-block',
            width: closedSize.w,
            height: closedSize.h,
            visibility: 'hidden',
          }}
        />
      )}

      {/* The morph target. Either renders the inline closed button or,
          when expanded, an absolutely-positioned panel anchored to the
          same top-right corner. The closed button is always mounted
          (just hidden when expanded) so its measured size feeds the
          spacer above. */}
      <button
        ref={closedRef}
        type="button"
        onClick={handleOpen}
        aria-label="Show checkpoint details"
        aria-expanded={expanded}
        title="Checkpoints"
        style={{
          height: 24,
          padding: '0 8px',
          border: 0,
          borderRadius: 6,
          background: 'var(--bg-sunken)',
          boxShadow: 'inset 0 0 0 1px var(--border)',
          cursor: 'pointer',
          display: expanded ? 'none' : 'inline-flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        <span
          className="mono"
          style={{
            fontSize: 9.5,
            color: 'var(--text-4)',
            letterSpacing: '0.1em',
          }}
        >
          CHECKPOINTS
        </span>
        <CompactStepper
          checkpoints={checkpoints}
          stepStatus={stepStatus}
        />
      </button>

      {expanded && (
        <div
          role="dialog"
          aria-label="Checkpoint details"
          style={{
            position: 'absolute',
            top: 0,
            right: 0,
            zIndex: 40,
            width: 540,
            maxWidth: 'calc(100vw - 32px)',
            background: 'var(--bg)',
            borderRadius: 'var(--radius-lg)',
            boxShadow: 'var(--shadow-elev)',
            border: '1px solid var(--border)',
            padding: 16,
            display: 'flex',
            flexDirection: 'column',
            gap: 0,
            transformOrigin: 'top right',
            animation: 'rounds-cp-stepper-grow 160ms cubic-bezier(0.22, 0.8, 0.36, 1)',
          }}
        >
          <ExpandedStepper
            checkpoints={checkpoints}
            stepStatus={stepStatus}
            focusIdx={focusIdx}
            onPick={setFocusIdx}
          />
          <Connector focusIdx={focusIdx} count={checkpoints.length} />
          <CheckpointDetail
            checkpoint={checkpoints[focusIdx]}
            index={focusIdx}
            isCurrent={focusIdx === currentIndex}
            isPassed={passed[focusIdx]}
            onReset={
              onResetCheckpoint && passed[focusIdx]
                ? () => onResetCheckpoint(focusIdx)
                : undefined
            }
          />
        </div>
      )}
      <style>{`
        @keyframes rounds-cp-stepper-grow {
          from { transform: scale(0.92); opacity: 0; }
          to   { transform: scale(1);    opacity: 1; }
        }
      `}</style>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Compact stepper used in the closed state — fits in the header chrome.
// ---------------------------------------------------------------------------

function CompactStepper({
  checkpoints,
  stepStatus,
}: {
  checkpoints: Checkpoint[];
  stepStatus: (i: number) => 'passed' | 'active' | 'todo';
}) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
      }}
    >
      {checkpoints.map((_cp, i) => {
        const s = stepStatus(i);
        const last = i === checkpoints.length - 1;
        return (
          <span
            key={i}
            style={{ display: 'inline-flex', alignItems: 'center' }}
          >
            <CompactDot status={s} index={i} />
            {!last && (
              <span
                aria-hidden="true"
                style={{
                  width: 14,
                  height: 2,
                  background:
                    stepStatus(i) === 'passed'
                      ? 'var(--forest)'
                      : 'var(--border-strong)',
                  margin: '0 2px',
                  borderRadius: 1,
                }}
              />
            )}
          </span>
        );
      })}
    </span>
  );
}

function CompactDot({
  status,
  index,
}: {
  status: 'passed' | 'active' | 'todo';
  index: number;
}) {
  const bg =
    status === 'passed'
      ? 'var(--forest)'
      : status === 'active'
        ? 'var(--accent)'
        : 'transparent';
  const fg =
    status === 'passed' || status === 'active' ? 'var(--bg)' : 'var(--text-3)';
  const ring =
    status === 'todo' ? 'inset 0 0 0 1px var(--border-strong)' : 'none';
  return (
    <span
      style={{
        width: 16,
        height: 16,
        borderRadius: 999,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: bg,
        color: fg,
        boxShadow: ring,
        fontSize: 9,
        fontWeight: 600,
        fontFamily: 'var(--font-mono)',
        lineHeight: 1,
      }}
    >
      {status === 'passed' ? <Check size={9} strokeWidth={3} /> : index + 1}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Expanded stepper — same step semantics but larger, labelled, clickable
// to focus a step (does NOT navigate the editor).
// ---------------------------------------------------------------------------

function ExpandedStepper({
  checkpoints,
  stepStatus,
  focusIdx,
  onPick,
}: {
  checkpoints: Checkpoint[];
  stepStatus: (i: number) => 'passed' | 'active' | 'todo';
  focusIdx: number;
  onPick: (i: number) => void;
}) {
  return (
    <div
      role="list"
      aria-label="Checkpoint stepper"
      style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${checkpoints.length}, 1fr)`,
        alignItems: 'start',
        gap: 0,
      }}
    >
      {checkpoints.map((cp, i) => {
        const s = stepStatus(i);
        const isFocused = i === focusIdx;
        const isLast = i === checkpoints.length - 1;
        return (
          <button
            key={i}
            type="button"
            role="listitem"
            aria-current={isFocused ? 'step' : undefined}
            onClick={() => onPick(i)}
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '4px 6px 8px',
              border: 0,
              background: 'transparent',
              cursor: 'pointer',
              gap: 6,
              textAlign: 'center',
              minWidth: 0,
              position: 'relative',
            }}
            title={cp.label}
          >
            <span style={{ display: 'flex', alignItems: 'center', width: '100%' }}>
              {/* Left connector — only for steps after the first. */}
              <span
                aria-hidden="true"
                style={{
                  flex: 1,
                  height: 2,
                  background:
                    i > 0 && stepStatus(i - 1) === 'passed'
                      ? 'var(--forest)'
                      : i > 0
                        ? 'var(--border-strong)'
                        : 'transparent',
                  borderRadius: 1,
                }}
              />
              <ExpandedDot
                status={s}
                index={i}
                focused={isFocused}
              />
              {/* Right connector — only for steps before the last. */}
              <span
                aria-hidden="true"
                style={{
                  flex: 1,
                  height: 2,
                  background:
                    !isLast && s === 'passed'
                      ? 'var(--forest)'
                      : !isLast
                        ? 'var(--border-strong)'
                        : 'transparent',
                  borderRadius: 1,
                }}
              />
            </span>
            <span
              style={{
                fontSize: 11.5,
                color: isFocused
                  ? 'var(--text)'
                  : s === 'passed'
                    ? 'var(--forest)'
                    : 'var(--text-3)',
                fontWeight: isFocused ? 600 : 400,
                lineHeight: 1.3,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                maxWidth: '100%',
              }}
            >
              {cp.label}
            </span>
            <span
              className="mono"
              style={{
                fontSize: 9.5,
                color: 'var(--text-4)',
                letterSpacing: '0.08em',
              }}
            >
              {s === 'passed' ? 'PASSED' : s === 'active' ? 'ACTIVE' : 'TODO'}
            </span>
          </button>
        );
      })}
    </div>
  );
}

function ExpandedDot({
  status,
  index,
  focused,
}: {
  status: 'passed' | 'active' | 'todo';
  index: number;
  focused: boolean;
}) {
  const bg =
    status === 'passed'
      ? 'var(--forest)'
      : status === 'active'
        ? 'var(--accent)'
        : 'var(--bg)';
  const fg =
    status === 'passed' || status === 'active' ? 'var(--bg)' : 'var(--text-3)';
  const ring = focused
    ? `0 0 0 2px var(--bg), 0 0 0 4px var(${
        status === 'passed' ? '--forest' : '--accent'
      })`
    : status === 'todo'
      ? 'inset 0 0 0 1.5px var(--border-strong)'
      : 'none';
  return (
    <span
      style={{
        flexShrink: 0,
        width: 24,
        height: 24,
        borderRadius: 999,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: bg,
        color: fg,
        boxShadow: ring,
        fontSize: 11,
        fontWeight: 600,
        fontFamily: 'var(--font-mono)',
        margin: '0 4px',
        transition: 'box-shadow 120ms ease',
      }}
    >
      {status === 'passed' ? (
        <Check size={12} strokeWidth={2.5} />
      ) : (
        index + 1
      )}
    </span>
  );
}

function Connector({ focusIdx, count }: { focusIdx: number; count: number }) {
  const leftPct = ((focusIdx + 0.5) / count) * 100;
  return (
    <div
      aria-hidden="true"
      style={{
        position: 'relative',
        height: 14,
        marginTop: 2,
      }}
    >
      <span
        style={{
          position: 'absolute',
          left: `${leftPct}%`,
          top: 0,
          bottom: 0,
          width: 2,
          marginLeft: -1,
          borderRadius: 1,
          background: 'var(--accent)',
        }}
      />
    </div>
  );
}

function CheckpointDetail({
  checkpoint,
  index,
  isCurrent,
  isPassed,
  onReset,
}: {
  checkpoint: Checkpoint;
  index: number;
  isCurrent: boolean;
  isPassed: boolean;
  onReset?: () => void;
}) {
  return (
    <div
      style={{
        background: 'var(--bg-sunken)',
        borderRadius: 'var(--radius)',
        padding: 14,
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
    >
      <div className="flex items-center" style={{ gap: 8 }}>
        <span
          className="mono"
          style={{
            fontSize: 10.5,
            color: 'var(--text-4)',
            letterSpacing: '0.1em',
          }}
        >
          CP {index + 1}
        </span>
        <span
          style={{
            fontSize: 13.5,
            color: 'var(--text)',
            fontWeight: 500,
          }}
        >
          {checkpoint.label}
        </span>
        {isPassed && (
          <span
            className="pill"
            style={{
              background: 'var(--forest-soft)',
              color: 'var(--forest)',
            }}
          >
            passed
          </span>
        )}
        {!checkpoint.ai_allowed && (
          <span
            className="pill"
            style={{
              background: 'transparent',
              color: 'var(--text-4)',
              boxShadow: 'inset 0 0 0 1px var(--border)',
            }}
          >
            solo
          </span>
        )}
        {onReset && (
          <button
            type="button"
            onClick={onReset}
            title="Reset this checkpoint"
            aria-label={`Reset checkpoint ${index + 1}`}
            className="inline-flex items-center gap-1"
            style={{
              marginLeft: 'auto',
              padding: '2px 8px',
              fontSize: 10.5,
              letterSpacing: '0.08em',
              border: 0,
              borderRadius: 999,
              background: 'transparent',
              color: 'var(--text-3)',
              boxShadow: 'inset 0 0 0 1px var(--border)',
              cursor: 'pointer',
            }}
          >
            <RotateCcw size={9} strokeWidth={2} />
            RESET
          </button>
        )}
      </div>
      <div
        style={{
          fontSize: 13,
          color: 'var(--text-2)',
          lineHeight: 1.55,
          maxHeight: 220,
          overflow: 'auto',
        }}
      >
        <BlockMarkdown text={checkpoint.prompt} />
      </div>
      <div className="flex items-center gap-2">
        <span
          className="mono"
          style={{
            fontSize: 10.5,
            color: isCurrent ? 'var(--accent)' : 'var(--text-4)',
            letterSpacing: '0.08em',
          }}
        >
          {isCurrent
            ? 'CURRENTLY ACTIVE'
            : 'SWITCH IN THE CHECKPOINTS RAIL TAB →'}
        </span>
      </div>
    </div>
  );
}
