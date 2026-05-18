import { GripVertical } from 'lucide-react';

type Props = {
  onMouseDown: (e: React.MouseEvent) => void;
  /** Which edge of the parent panel this handle sits on. The handle
   *  is absolutely positioned and overhangs that edge by 3px so it's
   *  easy to grab without visual noise at rest. */
  edge: 'left' | 'right';
};

/**
 * 6-px-wide absolute-positioned drag handle. Pair with the
 * `useResizableWidth` hook on the parent panel — bind this handle's
 * `onMouseDown` to the hook's `onResizeStart` and apply the returned
 * width to the panel itself.
 *
 * A faint vertical grip icon fades in on hover so the affordance is
 * discoverable; otherwise the handle is visually invisible at rest.
 *
 * The parent panel MUST have `position: relative` (or any non-static
 * position) for absolute positioning to anchor correctly.
 */
export default function ResizeHandle({ onMouseDown, edge }: Props) {
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label="Resize panel"
      onMouseDown={onMouseDown}
      style={{
        position: 'absolute',
        top: 0,
        bottom: 0,
        width: 6,
        cursor: 'col-resize',
        zIndex: 5,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        ...(edge === 'right' ? { right: -3 } : { left: -3 }),
      }}
    >
      <span
        aria-hidden="true"
        style={{ opacity: 0, color: 'var(--text-4)', transition: 'opacity 120ms' }}
        className="rounds-resize-grip"
      >
        <GripVertical size={12} strokeWidth={1.8} />
      </span>
      <style>{`
        .rounds-resize-grip { opacity: 0; }
        [role="separator"]:hover .rounds-resize-grip { opacity: 0.6; }
      `}</style>
    </div>
  );
}
