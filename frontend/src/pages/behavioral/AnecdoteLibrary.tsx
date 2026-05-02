import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../../api/client';
import { AnecdoteCard } from './AnecdoteCard';
import { CategoryIcon } from '../../components/shell/CategoryIcon';
import { Skeleton } from '../../components/visual/Skeleton';
import type { Anecdote, BehavioralCategoryLite, BehavioralQuestionLite } from './types';

interface AnecdoteLibraryProps {
  categories: BehavioralCategoryLite[];
  questions: BehavioralQuestionLite[];
}

export function AnecdoteLibrary({ categories, questions: _questions }: AnecdoteLibraryProps) {
  const navigate = useNavigate();
  const [anecdotes, setAnecdotes] = useState<Anecdote[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedCat, setSelectedCat] = useState<string | null>(null);

  useEffect(() => {
    api.get<Anecdote[]>('/api/anecdotes')
      .then(setAnecdotes)
      .finally(() => setLoading(false));
  }, []);

  const visible = useMemo(() => {
    if (selectedCat === null) return anecdotes;
    return anecdotes.filter((a) => a.category_ids.includes(selectedCat));
  }, [anecdotes, selectedCat]);

  const handleCardDelete = async (id: string) => {
    if (!confirm('Delete this anecdote? This cannot be undone.')) return;
    try {
      await api.del(`/api/anecdotes/${id}`);
      setAnecdotes((prev) => prev.filter((a) => a.id !== id));
    } catch (e) {
      alert(String(e));
    }
  };

  return (
    <>
      <div className="flex items-center justify-between mb-3">
        <button
          type="button"
          onClick={() => navigate('/behavioral/anecdotes/new')}
          className="px-3 py-1.5 rounded-md text-xs font-medium bg-gray-900 text-white hover:bg-gray-700"
        >
          + New anecdote
        </button>
        <span className="text-xs text-gray-400">
          {anecdotes.length} {anecdotes.length === 1 ? 'anecdote' : 'anecdotes'}
        </span>
      </div>

      {!loading && anecdotes.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-4">
          <button
            type="button"
            onClick={() => setSelectedCat(null)}
            className={`pill transition-colors ${
              selectedCat === null
                ? 'bg-gray-900 text-white'
                : 'bg-gray-50 text-gray-600 hover:bg-gray-100'
            }`}
          >
            All
          </button>
          {categories.map((c) => (
            <button
              key={c.id}
              type="button"
              aria-label={c.name}
              onClick={() => setSelectedCat(selectedCat === c.id ? null : c.id)}
              className="pill transition-colors"
              style={{
                backgroundColor: selectedCat === c.id ? c.color : `${c.color}15`,
                color: selectedCat === c.id ? '#fff' : c.color,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
              }}
            >
              <CategoryIcon name={c.icon} size={12} strokeWidth={1.8} />
              {c.name}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} height={140} className="rounded-lg" />
          ))}
        </div>
      ) : visible.length === 0 ? (
        <div className="card p-6 text-center text-sm text-gray-500">
          {anecdotes.length === 0
            ? 'No anecdotes yet. Click "+ New anecdote" to add your first STAR story.'
            : 'No anecdotes match this category.'}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3">
          {visible.map((a) => (
            <AnecdoteCard
              key={a.id}
              anecdote={a}
              categories={categories}
              onEdit={(anecdote) => navigate(`/behavioral/anecdotes/${anecdote.id}/edit`)}
              onDelete={handleCardDelete}
            />
          ))}
        </div>
      )}
    </>
  );
}
