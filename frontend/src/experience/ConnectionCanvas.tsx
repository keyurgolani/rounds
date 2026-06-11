// frontend/src/experience/ConnectionCanvas.tsx
//
// Shared wiring-board canvas: a 4-column grid of cards grouped by kind, with
// drag-to-link handles, animated connectors, and hover highlight/dim. Card
// bodies and group headers are supplied by the caller via render props.
//
// Consumers: ImportReview (review extracted items) and ArrangeBoard (live edit).
import {
  Fragment,
  useState, useCallback, useMemo, useRef, useEffect, useLayoutEffect, useReducer,
  type ReactNode, type PointerEvent as ReactPointerEvent,
} from 'react';
import { X } from 'lucide-react';
import { ConnectorOverlay, type Connector } from '../pages/behavioral/ConnectorOverlay';
import { LinkableCard } from '../pages/behavioral/LinkableCard';
import type { EntityKind } from './experienceApi';
import { canParent } from './connectionPair';
import { validChildKinds } from './connectionApi';

export interface CanvasItem {
  localId: string;
  kind: EntityKind;
  /** Optional board flag (e.g. an unfiled/no-parent card). */
  flag?: 'unfiled';
}

export interface CanvasConnection {
  parentLocalId: string;
  childLocalId: string;
  dashed?: boolean;
}

interface Props {
  items: CanvasItem[];
  connections: CanvasConnection[];
  /** Card body for a single item (the caller owns its content/affordances). */
  renderCardContent: (item: CanvasItem) => ReactNode;
  /** Column header; defaults to `KIND (count)` in the kind's accent color. */
  renderGroupHeader?: (kind: EntityKind, items: CanvasItem[]) => ReactNode;
  /** Fired when a drag links two cards. `alreadyLinked` lets the caller toggle. */
  onToggleLink: (parentLocalId: string, childLocalId: string, alreadyLinked: boolean) => void;
  /** When provided, an ✕ is rendered at each connector midpoint. */
  onDisconnect?: (parentLocalId: string, childLocalId: string) => void;
  /** When provided, clicking a card (not its drag handle) opens it. */
  onOpenItem?: (localId: string) => void;
  /** Each column scrolls independently within the canvas height (default off). */
  columnScroll?: boolean;
  /**
   * 'always' (default) draws every edge behind the cards with a midpoint ✕ —
   * legacy behavior used by ImportReview. 'focus' draws only the focused card's
   * edges on top, with the ✕ anchored to the linked (neighbor) card.
   */
  interaction?: 'always' | 'focus';
  /** Pinned card (controlled by the caller) — only used in focus mode. */
  selectedId?: string | null;
  /**
   * Fired in focus mode when a card is clicked (with its id — caller toggles the
   * pin) or when the empty canvas is clicked (with null — caller clears the pin).
   */
  onSelectItem?: (localId: string | null) => void;
}

export const TYPE_COLORS: Record<EntityKind, { bg: string; text: string }> = {
  job: { bg: 'var(--ink-soft)', text: 'var(--ink)' },
  project: { bg: 'var(--ochre-soft)', text: 'var(--ochre)' },
  anecdote: { bg: 'var(--accent-soft)', text: 'var(--accent)' },
  bullet: { bg: 'var(--forest-soft)', text: 'var(--forest)' },
};

export const TYPE_LABELS: Record<EntityKind, string> = {
  job: 'Jobs', project: 'Projects', anecdote: 'Anecdotes', bullet: 'Bullets',
};

const KINDS: EntityKind[] = ['job', 'project', 'anecdote', 'bullet'];

export default function ConnectionCanvas({
  items, connections, renderCardContent, renderGroupHeader,
  onToggleLink, onDisconnect, onOpenItem, columnScroll = false,
  interaction = 'always', selectedId = null, onSelectItem,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const columnRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [tickValue, tick] = useReducer((n: number) => n + 1, 0);
  const [drag, setDrag] = useState<{ fromId: string; fromX: number; fromY: number; x: number; y: number } | null>(null);
  const [dropTarget, setDropTarget] = useState<string | null>(null);
  const [xHoveredKey, setXHoveredKey] = useState<string | null>(null);
  const [hoveredLineKey, setHoveredLineKey] = useState<string | null>(null);

  const kindById = useMemo(() => {
    const m: Record<string, EntityKind> = {};
    for (const it of items) m[it.localId] = it.kind;
    return m;
  }, [items]);

  const grouped = useMemo(() => {
    const groups: Record<EntityKind, CanvasItem[]> = { job: [], project: [], anecdote: [], bullet: [] };
    for (const it of items) groups[it.kind].push(it);
    return groups;
  }, [items]);

  const connSet = useMemo(() => {
    const s = new Set<string>();
    for (const c of connections) s.add(`${c.parentLocalId}::${c.childLocalId}`);
    return s;
  }, [connections]);

  const isConnected = useCallback(
    (a: string, b: string) => connSet.has(`${a}::${b}`) || connSet.has(`${b}::${a}`),
    [connSet],
  );

  const focus = interaction === 'focus';
  // In focus mode the pinned card locks the focus; with nothing pinned, hovering
  // peeks. Pin-locking keeps the neighbor-anchored ✕ reachable — hovering a
  // neighbor no longer steals focus and hides the disconnect controls.
  const focusId = focus ? (selectedId ?? hoveredId) : hoveredId;
  // Disconnect controls show whenever a card is pinned (selectedId set). They are
  // NOT shown during a pure hover with no pin — so ✕ never appears on a transient
  // hover target when nothing is pinned.
  const pinnedFocus = focus && focusId != null && focusId === selectedId;

  const isActive = (id: string) => {
    if (!focusId) return false;
    return focusId === id || isConnected(focusId, id);
  };
  const isDimmed = (id: string) => Boolean(focusId) && !isActive(id);

  // Drag direction is meaningful: the dragged-from card must be allowed to parent
  // the dropped-on card. Reverse drags (e.g. bullet → job) are rejected.
  const linkFromDrag = useCallback((fromId: string, toId: string) => {
    const aKind = kindById[fromId];
    const bKind = kindById[toId];
    if (!aKind || !bKind) return;
    if (!canParent(aKind, bKind)) return;
    onToggleLink(fromId, toId, connSet.has(`${fromId}::${toId}`));
  }, [kindById, connSet, onToggleLink]);

  const beginDrag = useCallback((id: string, e: ReactPointerEvent<HTMLSpanElement>) => {
    e.preventDefault();
    e.stopPropagation();
    const el = cardRefs.current[id];
    if (!el || !containerRef.current) return;
    const rect = el.getBoundingClientRect();
    const cRect = containerRef.current.getBoundingClientRect();
    setDrag({
      fromId: id,
      fromX: rect.right - cRect.left,
      fromY: rect.top - cRect.top + rect.height / 2,
      x: e.clientX - cRect.left,
      y: e.clientY - cRect.top,
    });
  }, []);

  useEffect(() => {
    if (!drag) return;
    const handleMove = (e: PointerEvent) => {
      const cRect = containerRef.current?.getBoundingClientRect();
      if (!cRect) return;
      setDrag((d) => (d ? { ...d, x: e.clientX - cRect.left, y: e.clientY - cRect.top } : d));
      // Only highlight a card under the cursor when the drag's source can parent it
      // (one-way connections). The cursor is over at most one card at a time.
      const sourceKind = drag ? kindById[drag.fromId] : undefined;
      for (const [id, el] of Object.entries(cardRefs.current)) {
        if (!el) continue;
        const r = el.getBoundingClientRect();
        if (e.clientX >= r.left && e.clientX <= r.right && e.clientY >= r.top && e.clientY <= r.bottom) {
          const targetKind = kindById[id];
          if (id !== drag?.fromId && sourceKind && targetKind && canParent(sourceKind, targetKind)) {
            setDropTarget(id);
          } else {
            setDropTarget(null);
          }
          return;
        }
      }
      setDropTarget(null);
    };
    const handleUp = () => {
      if (drag && dropTarget && dropTarget !== drag.fromId) linkFromDrag(drag.fromId, dropTarget);
      setDrag(null);
      setDropTarget(null);
    };
    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup', handleUp);
    return () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup', handleUp);
    };
  }, [drag, dropTarget, linkFromDrag, kindById]);

  // Measure connector endpoints (and disconnect-button positions) from card refs.
  // In focus mode only edges incident to focusId are emitted, and the ✕ is placed
  // at the neighbor endpoint instead of the midpoint.
  const { connectors, disconnects } = useMemo(() => {
    const cRect = containerRef.current?.getBoundingClientRect();
    const lines: Connector[] = [];
    const buttons: Array<{ parentLocalId: string; childLocalId: string; key: string; x: number; y: number; active: boolean }> = [];
    if (!cRect) return { connectors: lines, disconnects: buttons };
    for (const c of connections) {
      const incident = c.parentLocalId === focusId || c.childLocalId === focusId;
      if (focus && !incident) continue;

      const pEl = cardRefs.current[c.parentLocalId];
      const cEl = cardRefs.current[c.childLocalId];
      if (!pEl || !cEl) continue;
      const pr = pEl.getBoundingClientRect();
      const cr = cEl.getBoundingClientRect();
      const from = { x: pr.right - cRect.left, y: pr.top - cRect.top + pr.height / 2 };
      const to = { x: cr.left - cRect.left, y: cr.top - cRect.top + cr.height / 2 };
      const key = `${c.parentLocalId}-${c.childLocalId}`;
      const active = focus ? true : (hoveredId === c.parentLocalId || hoveredId === c.childLocalId);
      lines.push({ key, from, to, active, dashed: c.dashed });

      // focus: anchor ✕ to the neighbor (the end that is NOT the focused card).
      // always: keep the legacy midpoint.
      const pos = focus
        ? (c.parentLocalId === focusId ? to : from)
        : { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 };
      buttons.push({
        parentLocalId: c.parentLocalId, childLocalId: c.childLocalId,
        key, active, x: pos.x, y: pos.y,
      });
    }
    return { connectors: lines, disconnects: buttons };
    // tickValue forces a re-measure once refs are attached / layout settles.
  }, [connections, hoveredId, tickValue, focus, focusId]);

  useLayoutEffect(() => { tick(); }, [items, connections]);

  // Reset hover state when the pin changes so a re-focused ✕ never renders with
  // a stale hover color.
  useEffect(() => {
    setHoveredLineKey(null);
    setXHoveredKey(null);
  }, [selectedId]);

  // When columns scroll independently, a card's bounding rect changes as the user
  // scrolls — connectors and ✕ midpoints must re-measure to track it.
  useEffect(() => {
    if (!columnScroll) return;
    const els = Object.values(columnRefs.current).filter(Boolean) as HTMLDivElement[];
    const onScroll = () => tick();
    for (const el of els) el.addEventListener('scroll', onScroll, { passive: true });
    return () => { for (const el of els) el.removeEventListener('scroll', onScroll); };
  }, [columnScroll, items]);

  // Re-measure when the canvas itself resizes — e.g. the inspector panel opens or
  // closes and reflows the board, the window resizes, or the sidebar collapses.
  // Without this the connector endpoints keep stale positions until the next tick.
  useEffect(() => {
    const el = containerRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(() => tick());
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const rootStyle = columnScroll
    ? { position: 'relative' as const, height: '100%', display: 'flex' as const, flexDirection: 'column' as const }
    : { position: 'relative' as const };
  const gridBase = { display: 'grid' as const, gridTemplateColumns: 'repeat(4, 1fr)', gap: 24, position: 'relative' as const, zIndex: 2 };
  const gridStyle = columnScroll
    ? { ...gridBase, flex: 1, minHeight: 0 }
    : gridBase;
  // overflow-y:auto makes the column clip on BOTH axes (overflow-x computes to
  // auto too), so symmetric padding is needed or the cards' outset decorations
  // get cut off: the right padding clears the drag handle (and its ring), and the
  // left/top/bottom padding clears each card's active accent ring and the dashed
  // "unfiled" outline.
  const columnStyle = columnScroll
    ? { display: 'flex' as const, flexDirection: 'column' as const, minHeight: 0, overflowY: 'auto' as const, padding: '0 18px 8px 6px' }
    : undefined;

  return (
    <div
      ref={containerRef}
      style={rootStyle}
      onClick={focus ? (e) => { if (e.target === e.currentTarget) onSelectItem?.(null); } : undefined}
    >
      <ConnectorOverlay connectors={connectors} drag={drag ?? undefined} hasDropTarget={!!dropTarget} onTop={focus} />

      {onDisconnect && disconnects.map((b) => {
        // focus: visible whenever a card is pinned. always: revealed by hovering
        // the line midpoint (legacy hit-zone), preserved for ImportReview.
        const visible = focus
          ? pinnedFocus
          : (hoveredLineKey === b.key || xHoveredKey === b.key);
        return (
          <Fragment key={b.key}>
            {!focus && (
              <div
                onMouseEnter={() => setHoveredLineKey(b.key)}
                onMouseLeave={() => setHoveredLineKey((k) => (k === b.key ? null : k))}
                style={{
                  position: 'absolute', left: b.x, top: b.y, transform: 'translate(-50%, -50%)',
                  width: 24, height: 24, borderRadius: 999, zIndex: 3,
                  cursor: 'pointer',
                }}
              />
            )}
            <button
              type="button"
              aria-label="Remove connection"
              title="Remove connection"
              onClick={() => onDisconnect(b.parentLocalId, b.childLocalId)}
              onMouseEnter={() => setXHoveredKey(b.key)}
              onMouseLeave={() => setXHoveredKey((k) => (k === b.key ? null : k))}
              style={{
                position: 'absolute', left: b.x, top: b.y, transform: 'translate(-50%, -50%)',
                width: 18, height: 18, borderRadius: 999, padding: 0, zIndex: focus ? 6 : 4,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'var(--bg-elev)',
                color: xHoveredKey === b.key ? 'var(--plum)' : 'var(--text-3)',
                boxShadow: '0 0 0 1px var(--border-strong), 0 1px 3px rgba(0,0,0,0.12)',
                cursor: 'pointer',
                opacity: visible ? 1 : 0,
                pointerEvents: visible ? 'auto' : 'none',
                transition: 'opacity 140ms, color 140ms',
              }}
            >
              <X size={11} strokeWidth={2.4} />
            </button>
          </Fragment>
        );
      })}

      <div style={gridStyle}>
        {KINDS.map((kind) => {
          const groupItems = grouped[kind];
          if (groupItems.length === 0) return null;
          const colors = TYPE_COLORS[kind];
          const headerStyle = columnScroll
            ? { marginBottom: 12, position: 'sticky' as const, top: 0, background: 'var(--bg)', paddingBottom: 6, zIndex: 1 }
            : { marginBottom: 12 };
          return (
            <div
              key={kind}
              ref={(el) => { columnRefs.current[kind] = el; }}
              style={columnStyle}
            >
              <div style={headerStyle}>
                {renderGroupHeader
                  ? renderGroupHeader(kind, groupItems)
                  : (
                    <span className="mono" style={{ fontSize: 11, letterSpacing: '0.08em', color: colors.text }}>
                      {TYPE_LABELS[kind].toUpperCase()} ({groupItems.length})
                    </span>
                  )}
              </div>
              <div className="flex flex-col gap-3" style={columnScroll ? { paddingBottom: 8 } : undefined}>
                {groupItems.map((item) => (
                  <LinkableCard
                    key={item.localId}
                    innerRef={(el) => { cardRefs.current[item.localId] = el; }}
                    onMouseEnter={() => setHoveredId(item.localId)}
                    onMouseLeave={() => setHoveredId(null)}
                    onOpen={
                      onSelectItem
                        ? () => onSelectItem(item.localId)
                        : (onOpenItem ? () => onOpenItem(item.localId) : undefined)
                    }
                    onBeginDrag={(e) => beginDrag(item.localId, e)}
                    active={isActive(item.localId)}
                    dimmed={isDimmed(item.localId)}
                    isDropTarget={dropTarget === item.localId}
                    isDragSource={drag?.fromId === item.localId}
                    side="right"
                    compact={kind === 'bullet' || kind === 'anecdote'}
                    draggable={validChildKinds(item.kind).length > 0}
                    flag={item.flag}
                  >
                    {renderCardContent(item)}
                  </LinkableCard>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
