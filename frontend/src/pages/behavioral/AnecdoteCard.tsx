import type { Anecdote, BehavioralCategoryLite } from './types';

interface AnecdoteCardProps {
  anecdote: Anecdote;
  categories: BehavioralCategoryLite[];
  onEdit: (anecdote: Anecdote) => void;
  onDelete?: (id: string) => void;
}

function categoryName(categories: BehavioralCategoryLite[], id: string): string {
  return categories.find((c) => c.id === id)?.name || '';
}

function categoryColor(categories: BehavioralCategoryLite[], id: string): string {
  return categories.find((c) => c.id === id)?.color || '#808080';
}

export function AnecdoteCard({
  anecdote,
  categories,
  onEdit,
  onDelete,
}: AnecdoteCardProps) {
  const linkedCount = anecdote.linked_question_ids.length;
  return (
    <div className="card-hover h-full">
      <button
        type="button"
        onClick={() => onEdit(anecdote)}
        aria-label={anecdote.title}
        className="w-full text-left p-4 flex flex-col gap-2"
      >
        <h3 className="text-sm font-medium text-gray-900 leading-snug">
          {anecdote.title}
        </h3>
        {anecdote.situation && (
          <p className="text-xs text-gray-500 line-clamp-3">
            {anecdote.situation}
          </p>
        )}
        {anecdote.category_ids.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mt-1">
            {anecdote.category_ids.map((cid) => (
              <span
                key={cid}
                className="pill"
                style={{
                  backgroundColor: `${categoryColor(categories, cid)}15`,
                  color: categoryColor(categories, cid),
                }}
              >
                {categoryName(categories, cid)}
              </span>
            ))}
          </div>
        )}
        <div className="flex items-center justify-between mt-auto pt-1">
          <span className="text-xs text-gray-400">
            Linked to {linkedCount} {linkedCount === 1 ? 'question' : 'questions'}
          </span>
          {onDelete && (
            <span
              role="button"
              aria-label="delete anecdote"
              tabIndex={0}
              onClick={(e) => {
                e.stopPropagation();
                onDelete(anecdote.id);
              }}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.stopPropagation();
                  onDelete(anecdote.id);
                }
              }}
              className="text-xs text-gray-400 hover:text-red-500 transition-colors px-1.5 py-0.5"
            >
              ✕
            </span>
          )}
        </div>
      </button>
    </div>
  );
}
