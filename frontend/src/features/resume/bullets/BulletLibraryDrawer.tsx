// The drawer itself: a right-side slide-out panel that lists every
// bullet the user has saved, supports search across text + tags, and
// either lets the user manage entries (edit / delete / add) or picks
// one for insertion into the active editor row.
//
// The drawer is mounted once near the Studio root and listens to the
// shared `BulletLibraryContext` for its open/close mode.

import { useEffect, useMemo, useState } from 'react';
import {
  Plus,
  Search,
  Trash2,
  X,
} from 'lucide-react';
import {
  createBullet,
  deleteBullet,
  listBullets,
  updateBullet,
} from '../api';
import type { Bullet } from '../types';
import { useBulletLibrary } from './BulletLibraryContext';

export default function BulletLibraryDrawer() {
  const { mode, resolve, close } = useBulletLibrary();
  const open = mode !== 'closed';
  const isPicker = mode === 'picker';

  const [bullets, setBullets] = useState<Bullet[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [draftText, setDraftText] = useState('');
  const [draftTags, setDraftTags] = useState('');
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    listBullets()
      .then(setBullets)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [open]);

  // Esc closes the drawer (and cancels any in-flight pick).
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') close();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, close]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return bullets;
    return bullets.filter((b) => {
      if (b.text.toLowerCase().includes(q)) return true;
      return b.tags.some((t) => t.toLowerCase().includes(q));
    });
  }, [bullets, query]);

  const onAdd = async () => {
    const text = draftText.trim();
    if (!text) return;
    setAdding(true);
    try {
      const tags = parseTags(draftTags);
      const created = await createBullet({ text, tags });
      setBullets((prev) => [created, ...prev]);
      setDraftText('');
      setDraftTags('');
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setAdding(false);
    }
  };

  const onEditSave = async (id: string, text: string, tagsRaw: string) => {
    try {
      const updated = await updateBullet(id, { text, tags: parseTags(tagsRaw) });
      setBullets((prev) => prev.map((b) => (b.id === id ? updated : b)));
      setEditingId(null);
    } catch (err) {
      setError((err as Error).message);
    }
  };

  const onDelete = async (id: string) => {
    if (!window.confirm('Delete this bullet?')) return;
    try {
      await deleteBullet(id);
      setBullets((prev) => prev.filter((b) => b.id !== id));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Bullet library"
      onClick={close}
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.45)',
        zIndex: 60,
        display: 'flex',
        justifyContent: 'flex-end',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="card"
        style={{
          width: 'min(520px, 100vw)',
          height: '100%',
          padding: 0,
          display: 'flex',
          flexDirection: 'column',
          borderRadius: 0,
        }}
      >
        <div
          className="flex items-center justify-between"
          style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}
        >
          <div className="flex flex-col">
            <div className="eyebrow" style={{ fontSize: 9.5 }}>
              Bullet library
            </div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>
              {isPicker ? 'Pick a bullet to insert' : `${bullets.length} bullet${bullets.length === 1 ? '' : 's'}`}
            </div>
          </div>
          <button
            type="button"
            onClick={close}
            aria-label="Close"
            style={{
              background: 'transparent',
              border: 0,
              padding: 4,
              borderRadius: 6,
              boxShadow: 'inset 0 0 0 1px var(--border)',
              color: 'var(--text-2)',
              cursor: 'pointer',
              display: 'inline-flex',
            }}
          >
            <X size={14} strokeWidth={1.8} />
          </button>
        </div>

        <div
          style={{
            padding: '10px 16px',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}
        >
          <div
            className="flex items-center gap-2"
            style={{
              padding: '8px 10px',
              background: 'var(--bg-elev)',
              borderRadius: 'var(--radius)',
              boxShadow: 'inset 0 0 0 1px var(--border-strong)',
            }}
          >
            <Search size={13} strokeWidth={1.7} style={{ color: 'var(--text-3)' }} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search by text or tag…"
              style={{
                flex: 1,
                background: 'transparent',
                border: 0,
                outline: 'none',
                fontSize: 12.5,
                color: 'var(--text)',
              }}
            />
          </div>

          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: 6,
              padding: '8px 10px',
              border: '1px dashed var(--border)',
              borderRadius: 'var(--radius)',
              background: 'var(--bg-sunken)',
            }}
          >
            <textarea
              value={draftText}
              onChange={(e) => setDraftText(e.target.value)}
              placeholder="Add a new bullet — e.g. Cut p99 latency 40% by sharding the order pipeline."
              rows={2}
              style={{
                background: 'var(--bg-elev)',
                boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                borderRadius: 'var(--radius)',
                border: 0,
                padding: '8px 10px',
                fontSize: 12.5,
                color: 'var(--text)',
                outline: 'none',
                fontFamily: 'inherit',
                lineHeight: 1.45,
                resize: 'vertical',
              }}
            />
            <div className="flex items-center gap-2">
              <input
                value={draftTags}
                onChange={(e) => setDraftTags(e.target.value)}
                placeholder="tags (comma-separated)"
                style={{
                  flex: 1,
                  background: 'var(--bg-elev)',
                  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                  borderRadius: 'var(--radius)',
                  border: 0,
                  padding: '7px 10px',
                  fontSize: 11.5,
                  color: 'var(--text)',
                  outline: 'none',
                }}
              />
              <button
                type="button"
                onClick={onAdd}
                disabled={!draftText.trim() || adding}
                className="inline-flex items-center gap-1.5"
                style={{
                  padding: '7px 12px',
                  borderRadius: 'var(--radius)',
                  border: 0,
                  background: 'var(--accent)',
                  color: 'var(--bg-elev)',
                  fontSize: 12,
                  fontWeight: 500,
                  cursor: !draftText.trim() || adding ? 'not-allowed' : 'pointer',
                  opacity: !draftText.trim() || adding ? 0.6 : 1,
                }}
              >
                <Plus size={12} strokeWidth={1.8} />
                {adding ? 'Saving…' : 'Add'}
              </button>
            </div>
          </div>
        </div>

        <div style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: '10px 16px' }}>
          {error && (
            <div
              role="alert"
              style={{
                padding: '8px 10px',
                fontSize: 12,
                color: 'var(--plum)',
                marginBottom: 10,
              }}
            >
              {error}
            </div>
          )}
          {loading ? (
            <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Loading…</div>
          ) : filtered.length === 0 ? (
            <EmptyState query={query} />
          ) : (
            <div className="flex flex-col gap-2">
              {filtered.map((b) => (
                <BulletRow
                  key={b.id}
                  bullet={b}
                  isPicker={isPicker}
                  isEditing={editingId === b.id}
                  onPick={() => resolve(b)}
                  onStartEdit={() => setEditingId(b.id)}
                  onCancelEdit={() => setEditingId(null)}
                  onSaveEdit={(text, tags) => onEditSave(b.id, text, tags)}
                  onDelete={() => onDelete(b.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------

function BulletRow({
  bullet,
  isPicker,
  isEditing,
  onPick,
  onStartEdit,
  onCancelEdit,
  onSaveEdit,
  onDelete,
}: {
  bullet: Bullet;
  isPicker: boolean;
  isEditing: boolean;
  onPick: () => void;
  onStartEdit: () => void;
  onCancelEdit: () => void;
  onSaveEdit: (text: string, tags: string) => void;
  onDelete: () => void;
}) {
  const [text, setText] = useState(bullet.text);
  const [tagsRaw, setTagsRaw] = useState(bullet.tags.join(', '));

  // Reset draft when entering edit mode.
  useEffect(() => {
    if (isEditing) {
      setText(bullet.text);
      setTagsRaw(bullet.tags.join(', '));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isEditing]);

  if (isEditing) {
    return (
      <div
        className="card"
        style={{
          padding: 10,
          display: 'flex',
          flexDirection: 'column',
          gap: 6,
          boxShadow: 'inset 0 0 0 1px var(--accent)',
        }}
      >
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={3}
          style={{
            padding: '8px 10px',
            background: 'var(--bg-elev)',
            boxShadow: 'inset 0 0 0 1px var(--border-strong)',
            borderRadius: 'var(--radius)',
            border: 0,
            fontSize: 12.5,
            color: 'var(--text)',
            outline: 'none',
            fontFamily: 'inherit',
            lineHeight: 1.45,
            resize: 'vertical',
          }}
        />
        <input
          value={tagsRaw}
          onChange={(e) => setTagsRaw(e.target.value)}
          placeholder="tags (comma-separated)"
          style={{
            padding: '7px 10px',
            background: 'var(--bg-elev)',
            boxShadow: 'inset 0 0 0 1px var(--border-strong)',
            borderRadius: 'var(--radius)',
            border: 0,
            fontSize: 11.5,
            color: 'var(--text)',
            outline: 'none',
          }}
        />
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={() => onSaveEdit(text.trim(), tagsRaw)}
            disabled={!text.trim()}
            style={{
              padding: '6px 12px',
              borderRadius: 'var(--radius)',
              border: 0,
              background: 'var(--accent)',
              color: 'var(--bg-elev)',
              fontSize: 11.5,
              fontWeight: 500,
              cursor: 'pointer',
            }}
          >
            Save
          </button>
          <button
            type="button"
            onClick={onCancelEdit}
            style={{
              padding: '6px 10px',
              background: 'transparent',
              border: 0,
              color: 'var(--text-3)',
              fontSize: 11.5,
              cursor: 'pointer',
            }}
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="card"
      style={{
        padding: 10,
        display: 'flex',
        flexDirection: 'column',
        gap: 6,
      }}
    >
      <div style={{ fontSize: 12.5, color: 'var(--text)', lineHeight: 1.5 }}>
        {bullet.text}
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        {bullet.tags.map((t) => (
          <span
            key={t}
            className="mono"
            style={{
              padding: '1px 7px',
              borderRadius: 999,
              fontSize: 9.5,
              background: 'var(--bg-sunken)',
              color: 'var(--text-3)',
              boxShadow: 'inset 0 0 0 1px var(--border)',
            }}
          >
            {t}
          </span>
        ))}
      </div>
      <div className="flex items-center gap-1.5">
        {isPicker && (
          <button
            type="button"
            onClick={onPick}
            style={{
              padding: '5px 10px',
              borderRadius: 'var(--radius)',
              border: 0,
              background: 'var(--accent)',
              color: 'var(--bg-elev)',
              fontSize: 11,
              fontWeight: 500,
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
            }}
          >
            <Plus size={11} strokeWidth={1.8} /> Insert
          </button>
        )}
        <button
          type="button"
          onClick={onStartEdit}
          style={{
            padding: '5px 8px',
            background: 'transparent',
            border: 0,
            color: 'var(--text-3)',
            fontSize: 11,
            cursor: 'pointer',
          }}
        >
          Edit
        </button>
        <button
          type="button"
          onClick={onDelete}
          aria-label="Delete bullet"
          style={{
            padding: '5px 8px',
            background: 'transparent',
            border: 0,
            color: 'var(--plum)',
            fontSize: 11,
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            gap: 3,
            marginLeft: 'auto',
          }}
        >
          <Trash2 size={11} strokeWidth={1.7} />
        </button>
      </div>
    </div>
  );
}

function EmptyState({ query }: { query: string }) {
  if (query.trim()) {
    return (
      <div
        className="card text-center"
        style={{
          padding: 24,
          color: 'var(--text-3)',
          fontSize: 12.5,
        }}
      >
        No bullets match “{query}”.
      </div>
    );
  }
  return (
    <div
      className="card text-center"
      style={{
        padding: 24,
        color: 'var(--text-3)',
        fontSize: 12.5,
        lineHeight: 1.55,
      }}
    >
      No bullets in your library yet. Add ones you reuse a lot — or save them
      from a Behavioral anecdote with the “Save as bullet” button.
    </div>
  );
}

function parseTags(raw: string): string[] {
  return raw
    .split(',')
    .map((t) => t.trim().toLowerCase())
    .filter(Boolean);
}
