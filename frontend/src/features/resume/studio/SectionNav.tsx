// Left pane of the Studio — the user picks which section to edit, can
// hide a section from the rendered resume, and can drag to reorder
// (the order is what the templates render). DnD via @dnd-kit so we
// share the lift/drop motion language with future bullet-library
// drawers.

import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core';
import {
  SortableContext,
  arrayMove,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Eye, EyeOff, GripVertical } from 'lucide-react';
import type { ResumeData, SectionKey } from '../types';
import { DEFAULT_SECTION_ORDER, SECTION_LABELS, sectionOrder, isSectionHidden } from '../utils';

type Props = {
  data: ResumeData;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
  // null means a non-section view is active — no row gets highlighted.
  active: SectionKey | null;
  onSelect: (key: SectionKey) => void;
};

export default function SectionNav({ data, setData, active, onSelect }: Props) {
  const order = sectionOrder(data);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const handleDragEnd = (e: DragEndEvent) => {
    const { active: a, over } = e;
    if (!over || a.id === over.id) return;
    const oldIdx = order.indexOf(a.id as SectionKey);
    const newIdx = order.indexOf(over.id as SectionKey);
    if (oldIdx < 0 || newIdx < 0) return;
    const next = arrayMove(order, oldIdx, newIdx);
    setData((prev) => ({ ...prev, sectionOrder: next }));
  };

  const toggleHide = (key: SectionKey) => {
    setData((prev) => {
      const hidden = new Set(prev.hiddenSections ?? []);
      if (hidden.has(key)) hidden.delete(key);
      else hidden.add(key);
      return { ...prev, hiddenSections: Array.from(hidden) };
    });
  };

  const reset = () => {
    setData((prev) => ({
      ...prev,
      sectionOrder: DEFAULT_SECTION_ORDER,
      hiddenSections: [],
    }));
  };

  const itemCount = (key: SectionKey): number => {
    if (key === 'personal') return data.personalInfo.fullName ? 1 : 0;
    return (data[key] as Array<unknown>).length;
  };

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between px-1">
        <div className="eyebrow" style={{ fontSize: 9.5 }}>
          Sections
        </div>
        <button
          type="button"
          onClick={reset}
          style={{
            background: 'transparent',
            border: 0,
            color: 'var(--text-4)',
            fontSize: 10.5,
            cursor: 'pointer',
            letterSpacing: '0.06em',
            textTransform: 'uppercase',
          }}
          title="Reset section order"
        >
          Reset
        </button>
      </div>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={order} strategy={verticalListSortingStrategy}>
          <div className="flex flex-col gap-1">
            {order.map((key, i) => (
              <SortableRow
                key={key}
                id={key}
                index={i}
                active={key === active}
                hidden={isSectionHidden(data, key)}
                count={itemCount(key)}
                onSelect={() => onSelect(key)}
                onToggleHide={() => toggleHide(key)}
              />
            ))}
          </div>
        </SortableContext>
      </DndContext>
    </div>
  );
}

function SortableRow({
  id,
  index,
  active,
  hidden,
  count,
  onSelect,
  onToggleHide,
}: {
  id: SectionKey;
  index: number;
  active: boolean;
  hidden: boolean;
  count: number;
  onSelect: () => void;
  onToggleHide: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id });

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        background: active ? 'var(--accent)' : 'var(--bg-elev)',
        color: active ? 'var(--bg-elev)' : 'var(--text)',
        borderRadius: 'var(--radius)',
        boxShadow: active ? 'none' : 'inset 0 0 0 1px var(--border)',
        padding: '7px 8px',
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        opacity: isDragging ? 0.6 : 1,
      }}
    >
      <button
        type="button"
        {...attributes}
        {...listeners}
        aria-label="Drag to reorder"
        style={{
          cursor: 'grab',
          background: 'transparent',
          border: 0,
          padding: 2,
          color: active ? 'var(--bg-elev)' : 'var(--text-4)',
          display: 'inline-flex',
        }}
      >
        <GripVertical size={13} strokeWidth={1.7} />
      </button>
      <button
        type="button"
        onClick={onSelect}
        style={{
          flex: 1,
          textAlign: 'left',
          background: 'transparent',
          border: 0,
          color: 'inherit',
          cursor: 'pointer',
          padding: 0,
          display: 'flex',
          alignItems: 'center',
          gap: 8,
        }}
      >
        <span
          className="mono"
          style={{
            fontSize: 9.5,
            opacity: 0.6,
            width: 12,
            textAlign: 'right',
          }}
        >
          {index + 1}
        </span>
        <span style={{ fontSize: 13, fontWeight: 500, textDecoration: hidden ? 'line-through' : 'none' }}>
          {SECTION_LABELS[id]}
        </span>
        {count > 0 && (
          <span
            className="mono"
            style={{
              fontSize: 9.5,
              opacity: 0.7,
              padding: '1px 5px',
              borderRadius: 999,
              boxShadow: active ? 'inset 0 0 0 1px rgba(255,255,255,0.4)' : 'inset 0 0 0 1px var(--border)',
            }}
          >
            {count}
          </span>
        )}
      </button>
      <button
        type="button"
        onClick={onToggleHide}
        aria-label={hidden ? 'Show section' : 'Hide section'}
        title={hidden ? 'Show section' : 'Hide section'}
        style={{
          background: 'transparent',
          border: 0,
          padding: 2,
          color: 'inherit',
          opacity: hidden ? 0.5 : 0.8,
          cursor: 'pointer',
          display: 'inline-flex',
        }}
      >
        {hidden ? <EyeOff size={12} strokeWidth={1.7} /> : <Eye size={12} strokeWidth={1.7} />}
      </button>
    </div>
  );
}
