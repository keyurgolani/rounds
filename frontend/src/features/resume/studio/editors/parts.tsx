// Form primitives shared by every section editor. Mirrors the look of
// existing Rounds forms (AnecdoteEditorPage / NewApplication) so the
// Studio doesn't introduce a competing visual language.

import {
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
} from 'react';
import {
  ArrowDown,
  ArrowUp,
  GripVertical,
  Plus,
  Trash2,
  X,
} from 'lucide-react';
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
import type { ImproveContext } from '../../ai/client';
import ImproveButton from './ImproveButton';

export function Field({
  label,
  children,
  hint,
  span = 1,
  actions,
  loading,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
  span?: 1 | 2;
  actions?: ReactNode;
  // When true, an accent running-glow border traces the input
  // wrapper. Used while an AI improve call for this field is in
  // flight.
  loading?: boolean;
}) {
  // When `actions` is supplied, render a label-row flex container with
  // the eyebrow on the left and the action node (typically an
  // <ImproveButton/>) flush right. The wrapper switches from <label>
  // to <div> in that case so interactive children inside `actions`
  // don't get associated as click targets for the field.
  const Tag = actions ? 'div' : 'label';
  return (
    <Tag
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 4,
        gridColumn: `span ${span}`,
      }}
    >
      <div
        className="flex items-center"
        style={{ gap: 6, minHeight: actions ? 22 : undefined }}
      >
        <span className="eyebrow" style={{ fontSize: 9.5, flex: 1 }}>
          {label}
        </span>
        {actions}
      </div>
      <div
        data-ai-processing-glow={loading ? 'true' : undefined}
        style={{
          borderRadius: 'var(--radius)',
          // The glow lives on a wrapper so the underlying input keeps
          // its own border + interactions; the wrapper is only
          // visually present when loading.
        }}
      >
        {children}
      </div>
      {hint && (
        <span style={{ fontSize: 11, color: 'var(--text-4)', lineHeight: 1.4 }}>{hint}</span>
      )}
    </Tag>
  );
}

const BASE_INPUT: CSSProperties = {
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

export function TextInput(props: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  type?: 'text' | 'email' | 'tel' | 'url' | 'month';
  ariaLabel?: string;
  disabled?: boolean;
}) {
  return (
    <input
      type={props.type ?? 'text'}
      value={props.value}
      onChange={(e) => props.onChange(e.target.value)}
      placeholder={props.placeholder}
      aria-label={props.ariaLabel}
      disabled={props.disabled}
      style={{
        ...BASE_INPUT,
        cursor: props.disabled ? 'not-allowed' : 'text',
        opacity: props.disabled ? 0.55 : 1,
      }}
    />
  );
}

export function TextArea(props: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  rows?: number;
  ariaLabel?: string;
  disabled?: boolean;
}) {
  return (
    <textarea
      value={props.value}
      onChange={(e) => props.onChange(e.target.value)}
      placeholder={props.placeholder}
      aria-label={props.ariaLabel}
      rows={props.rows ?? 3}
      disabled={props.disabled}
      style={{
        ...BASE_INPUT,
        resize: 'vertical',
        fontFamily: 'inherit',
        lineHeight: 1.45,
        cursor: props.disabled ? 'not-allowed' : 'text',
        opacity: props.disabled ? 0.55 : 1,
      }}
    />
  );
}

export function ToggleCheckbox(props: {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
}) {
  return (
    <label style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
      <input
        type="checkbox"
        checked={props.checked}
        onChange={(e) => props.onChange(e.target.checked)}
      />
      <span>{props.label}</span>
    </label>
  );
}

// Card wrapper for a single repeated item (one experience entry, one
// project, etc.) — consistent header chrome with up/down/remove.
export function ItemCard({
  title,
  index,
  total,
  onMoveUp,
  onMoveDown,
  onRemove,
  children,
}: {
  title?: string;
  index: number;
  total: number;
  onMoveUp: () => void;
  onMoveDown: () => void;
  onRemove: () => void;
  children: ReactNode;
}) {
  return (
    <div
      className="card"
      style={{
        padding: 12,
        marginBottom: 10,
        display: 'flex',
        flexDirection: 'column',
        gap: 8,
      }}
    >
      <div className="flex items-center justify-between">
        <div className="eyebrow" style={{ fontSize: 9.5, color: 'var(--text-3)' }}>
          {title || `Item ${index + 1}`}
        </div>
        <div className="flex items-center gap-1">
          <IconBtn onClick={onMoveUp} disabled={index === 0} ariaLabel="Move up">
            <ArrowUp size={12} strokeWidth={1.8} />
          </IconBtn>
          <IconBtn
            onClick={onMoveDown}
            disabled={index === total - 1}
            ariaLabel="Move down"
          >
            <ArrowDown size={12} strokeWidth={1.8} />
          </IconBtn>
          <IconBtn onClick={onRemove} ariaLabel="Remove" danger>
            <X size={12} strokeWidth={1.8} />
          </IconBtn>
        </div>
      </div>
      {children}
    </div>
  );
}

export function IconBtn({
  children,
  onClick,
  disabled,
  ariaLabel,
  danger,
}: {
  children: ReactNode;
  onClick: () => void;
  disabled?: boolean;
  ariaLabel: string;
  danger?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      title={ariaLabel}
      style={{
        height: 24,
        width: 24,
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'transparent',
        border: 0,
        borderRadius: 6,
        boxShadow: 'inset 0 0 0 1px var(--border)',
        color: danger ? 'var(--plum)' : 'var(--text-2)',
        cursor: disabled ? 'not-allowed' : 'pointer',
        opacity: disabled ? 0.4 : 1,
      }}
    >
      {children}
    </button>
  );
}

export function AddButton({
  onClick,
  label,
}: {
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1.5"
      style={{
        padding: '8px 12px',
        background: 'transparent',
        boxShadow: 'inset 0 0 0 1px var(--border-strong)',
        borderRadius: 'var(--radius)',
        border: 0,
        color: 'var(--text-2)',
        fontSize: 12,
        fontWeight: 500,
        cursor: 'pointer',
      }}
    >
      <Plus size={12} strokeWidth={1.8} />
      {label}
    </button>
  );
}

export function GridTwo({ children }: { children: ReactNode }) {
  return (
    <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
      {children}
    </div>
  );
}

// Lightweight sub-list editor: bullets, skill items, technologies. The
// caller passes the array + a write-back; this component handles add /
// remove / drag-reorder / inline edit. Each row uses a textarea that
// starts at one line and auto-grows as content wraps.
//
// Per-row AI improvement: when the caller passes `improveContext`,
// each row gets its own AI button on the right. Field-level
// AI buttons (passed via `Field actions={…}`) still operate on the
// whole list at once, independent of these per-row affordances.
//
// Optional link-state props (`linkRefs`, `linkEdited`, `onLinkChange`):
// callers that maintain parallel arrays of library-reference metadata
// can pass these to keep them aligned with add/remove/reorder/edit ops.
// All three must be supplied together; passing none is perfectly fine.
//
// `renderRowAdornment`: optional render-prop called with the row index;
// the returned node is rendered inside the right-side action cluster,
// before the trash button, so callers can inject per-row UI (e.g. a
// link indicator).
export function StringList({
  values,
  onChange,
  placeholder,
  multiline = false,
  disabled = false,
  improveContext,
  fieldBase,
  linkRefs,
  linkEdited,
  onLinkChange,
  renderRowAdornment,
}: {
  values: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  multiline?: boolean;
  disabled?: boolean;
  // When provided, each row renders its own ImproveButton bound to
  // just that row's text. The button forwards the same studio-wide
  // resume + ATS context as field-level buttons.
  improveContext?: ImproveContext;
  // Stable base path for the field — row index is appended.
  fieldBase?: string;
  // Optional parallel arrays kept in sync with the values array.
  // All three should be supplied together or not at all.
  linkRefs?: (string | null)[];
  linkEdited?: boolean[];
  onLinkChange?: (refs: (string | null)[], edited: boolean[]) => void;
  // Optional per-row adornment rendered before the trash button.
  renderRowAdornment?: (index: number) => ReactNode;
}) {
  // Stable per-row IDs for dnd-kit. Synced to `values.length` on
  // append/remove from outside; reorders apply the same arrayMove to
  // both arrays so they stay aligned.
  const idsRef = useRef<string[]>([]);
  if (idsRef.current.length < values.length) {
    while (idsRef.current.length < values.length) {
      idsRef.current.push(`row-${Math.random().toString(36).slice(2, 10)}`);
    }
  } else if (idsRef.current.length > values.length) {
    idsRef.current = idsRef.current.slice(0, values.length);
  }
  const ids = idsRef.current;

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 4 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  const setAt = (i: number, v: string) => {
    const next = values.slice();
    next[i] = v;
    onChange(next);
    if (onLinkChange) {
      const refs = linkRefs ?? [];
      const edited = linkEdited ?? [];
      // Mark row as edited only when it had a linked ref and hasn't been
      // manually edited before — so the link badge can show "stale".
      if (refs[i] != null && !edited[i]) {
        onLinkChange(refs, edited.map((e, j) => (j === i ? true : e)));
      }
    }
  };
  const remove = (i: number) => {
    onChange(values.filter((_, j) => j !== i));
    idsRef.current = idsRef.current.filter((_, j) => j !== i);
    if (onLinkChange) {
      const refs = linkRefs ?? [];
      const edited = linkEdited ?? [];
      onLinkChange(refs.filter((_, j) => j !== i), edited.filter((_, j) => j !== i));
    }
  };
  const handleDragEnd = (e: DragEndEvent) => {
    const { active, over } = e;
    if (!over || active.id === over.id) return;
    const oldIdx = ids.indexOf(active.id as string);
    const newIdx = ids.indexOf(over.id as string);
    if (oldIdx < 0 || newIdx < 0) return;
    onChange(arrayMove(values, oldIdx, newIdx));
    idsRef.current = arrayMove(ids, oldIdx, newIdx);
    if (onLinkChange) {
      const refs = linkRefs ?? [];
      const edited = linkEdited ?? [];
      onLinkChange(arrayMove(refs, oldIdx, newIdx), arrayMove(edited, oldIdx, newIdx));
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      <DndContext
        sensors={sensors}
        collisionDetection={closestCenter}
        onDragEnd={handleDragEnd}
      >
        <SortableContext items={ids} strategy={verticalListSortingStrategy}>
          {values.map((v, i) => (
            <SortableListRow
              key={ids[i]}
              id={ids[i]}
              value={v}
              placeholder={placeholder}
              multiline={multiline}
              disabled={disabled}
              improveContext={improveContext}
              field={fieldBase ? `${fieldBase}[${i}]` : undefined}
              onChange={(next) => setAt(i, next)}
              onRemove={() => remove(i)}
              adornment={renderRowAdornment?.(i)}
            />
          ))}
        </SortableContext>
      </DndContext>
      <div className="flex items-center gap-1.5 self-start flex-wrap">
        <button
          type="button"
          onClick={() => {
            onChange([...values, '']);
            if (onLinkChange) {
              const refs = linkRefs ?? [];
              const edited = linkEdited ?? [];
              onLinkChange([...refs, null], [...edited, false]);
            }
          }}
          className="inline-flex items-center gap-1"
          style={{
            padding: '5px 9px',
            background: 'transparent',
            boxShadow: 'inset 0 0 0 1px var(--border)',
            borderRadius: 'var(--radius)',
            border: 0,
            color: 'var(--text-3)',
            fontSize: 11,
            cursor: 'pointer',
          }}
        >
          <Plus size={11} strokeWidth={1.8} /> Add
        </button>
      </div>
    </div>
  );
}

// One row of a StringList. Layout left-to-right:
//   [grip]   spans the row's full height with no chrome — just the
//            icon. Click-and-drag from anywhere along it.
//   [input]  auto-growing textarea. Wrapped in a glow div so an AI
//            improve in flight on this row gets the same accent
//            border the score cards use.
//   [AI]     per-row improve button (when improveContext is supplied).
//   [trash]  delete the row.
//
// The right-side cluster is anchored to the top so it doesn't
// stretch when the input grows to multiple lines.
function SortableListRow({
  id,
  value,
  placeholder,
  multiline,
  disabled,
  improveContext,
  field,
  onChange,
  onRemove,
  adornment,
}: {
  id: string;
  value: string;
  placeholder?: string;
  multiline: boolean;
  disabled?: boolean;
  improveContext?: ImproveContext;
  field?: string;
  onChange: (v: string) => void;
  onRemove: () => void;
  adornment?: ReactNode;
}) {
  const [enhancing, setEnhancing] = useState(false);
  const effectiveDisabled = Boolean(disabled || enhancing);
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } =
    useSortable({ id, disabled: effectiveDisabled });

  return (
    <div
      ref={setNodeRef}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        opacity: isDragging ? 0.6 : 1,
        position: 'relative',
        zIndex: isDragging ? 5 : 'auto',
        display: 'flex',
        // align-stretch so the grip handle on the left grows with
        // the input. The right action cluster overrides this with
        // align-self: flex-start so it stays anchored to the top.
        alignItems: 'stretch',
        gap: 4,
      }}
    >
      <button
        type="button"
        aria-label="Drag to reorder"
        title="Drag to reorder"
        {...attributes}
        {...listeners}
        disabled={effectiveDisabled}
        style={{
          background: 'transparent',
          border: 0,
          padding: 0,
          margin: 0,
          width: 16,
          color: 'var(--text-4)',
          cursor: effectiveDisabled
            ? 'not-allowed'
            : isDragging
              ? 'grabbing'
              : 'grab',
          touchAction: 'none',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          opacity: effectiveDisabled ? 0.4 : 1,
        }}
      >
        <GripVertical size={12} strokeWidth={1.6} />
      </button>

      <div
        data-ai-processing-glow={enhancing ? 'true' : undefined}
        style={{
          flex: 1,
          minWidth: 0,
          borderRadius: 'var(--radius)',
        }}
      >
        <AutoGrowInput
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          // For non-multiline rows (skills, technologies) Enter shouldn't
          // create a newline inside the cell — that just looks broken.
          // Suppress it; the user can use Add to make a new row.
          suppressEnter={!multiline}
          disabled={effectiveDisabled}
        />
      </div>

      <div
        className="flex items-center gap-1"
        style={{
          height: 36,
          flexShrink: 0,
          alignSelf: 'flex-start',
        }}
      >
        {improveContext && (
          <ImproveButton
            text={value}
            context={improveContext}
            field={field}
            onChange={onChange}
            onStreamingChange={setEnhancing}
          />
        )}
        {adornment}
        <IconBtn
          onClick={onRemove}
          ariaLabel="Delete"
          danger
          disabled={effectiveDisabled}
        >
          <Trash2 size={11} strokeWidth={1.8} />
        </IconBtn>
      </div>
    </div>
  );
}

// Textarea that mimics a one-line input until content wraps, then
// grows to fit. Resync height every render so it tracks `value` even
// when the parent rewrites it (e.g., during AI streaming).
function AutoGrowInput({
  value,
  onChange,
  placeholder,
  suppressEnter,
  disabled,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  suppressEnter?: boolean;
  disabled?: boolean;
}) {
  const ref = useRef<HTMLTextAreaElement>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
  }, [value]);

  return (
    <textarea
      ref={ref}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onKeyDown={(e) => {
        if (suppressEnter && e.key === 'Enter' && !e.shiftKey) {
          e.preventDefault();
          (e.currentTarget as HTMLTextAreaElement).blur();
        }
      }}
      placeholder={placeholder}
      rows={1}
      disabled={disabled}
      style={{
        ...BASE_INPUT,
        boxSizing: 'border-box',
        resize: 'none',
        overflow: 'hidden',
        fontFamily: 'inherit',
        lineHeight: 1.45,
        // Match the height of a one-line <input> so empty rows look
        // identical to a regular text input.
        minHeight: 36,
        cursor: disabled ? 'not-allowed' : 'text',
        opacity: disabled ? 0.55 : 1,
      }}
    />
  );
}
