// Manage public share links for the active resume. Each link is a
// random token; the URL `/r/<token>` is publicly readable. The dialog
// lists existing links with their view counts, lets the user copy or
// delete them, and creates a new one with one click.

import { useEffect, useState } from 'react';
import { Copy, ExternalLink, Eye, Plus, Trash2, X } from 'lucide-react';
import {
  buildShareUrl,
  createShareLink,
  deleteShareLink,
  listShareLinks,
  type ShareLink,
} from './client';

type Props = {
  open: boolean;
  onClose: () => void;
  resumeId: string;
};

export default function ShareDialog({ open, onClose, resumeId }: Props) {
  const [links, setLinks] = useState<ShareLink[]>([]);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedToken, setCopiedToken] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    setError(null);
    listShareLinks()
      .then((all) => setLinks(all.filter((l) => l.resume_id === resumeId || l.variant_id)))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [open, resumeId]);

  // Esc closes.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  const onCreate = async () => {
    setCreating(true);
    setError(null);
    try {
      const link = await createShareLink({ resume_id: resumeId });
      setLinks((prev) => [link, ...prev]);
      // Auto-copy the new URL — most likely thing the user wants next.
      try {
        await navigator.clipboard.writeText(buildShareUrl(link.token));
        setCopiedToken(link.token);
        window.setTimeout(() => setCopiedToken(null), 1600);
      } catch {
        /* clipboard might be blocked on http; fine */
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setCreating(false);
    }
  };

  const onCopy = async (token: string) => {
    try {
      await navigator.clipboard.writeText(buildShareUrl(token));
      setCopiedToken(token);
      window.setTimeout(() => setCopiedToken(null), 1600);
    } catch {
      /* ignore */
    }
  };

  const onDelete = async (id: string) => {
    if (!window.confirm('Delete this share link? Anyone holding it will lose access.')) {
      return;
    }
    try {
      await deleteShareLink(id);
      setLinks((prev) => prev.filter((l) => l.id !== id));
    } catch (err) {
      setError((err as Error).message);
    }
  };

  // Filter links to those tied to the current resume id (or any of
  // its variants — we keep variant-tied links visible since they
  // share the same root resume).
  const linksForThis = links.filter((l) => l.resume_id === resumeId || l.variant_id);

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Share resume"
      onClick={onClose}
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
          maxWidth: 580,
          maxHeight: '88vh',
          padding: 0,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <div
          className="flex items-center justify-between"
          style={{ padding: '14px 16px', borderBottom: '1px solid var(--border)' }}
        >
          <div>
            <div className="eyebrow" style={{ fontSize: 9.5, marginBottom: 2 }}>
              Public share
            </div>
            <div style={{ fontSize: 13, fontWeight: 500 }}>Share this resume</div>
          </div>
          <button type="button" onClick={onClose} aria-label="Close" style={iconBtn}>
            <X size={14} strokeWidth={1.8} />
          </button>
        </div>

        <div style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--text-3)', lineHeight: 1.55 }}>
            Each link is a random URL anyone with the token can open. They render the resume
            read-only — no editor chrome, no auth required. View counts update as recipients
            open it.
          </p>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onCreate}
              disabled={creating}
              style={{
                padding: '8px 14px',
                borderRadius: 'var(--radius)',
                border: 0,
                background: 'var(--accent)',
                color: 'var(--bg-elev)',
                fontSize: 12.5,
                fontWeight: 500,
                cursor: creating ? 'wait' : 'pointer',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <Plus size={13} strokeWidth={1.8} />
              {creating ? 'Creating…' : 'Create share link'}
            </button>
          </div>

          {error && (
            <div role="alert" style={{ fontSize: 11.5, color: 'var(--plum)' }}>
              {error}
            </div>
          )}

          {loading ? (
            <div style={{ fontSize: 12, color: 'var(--text-3)' }}>Loading links…</div>
          ) : linksForThis.length === 0 ? (
            <div
              className="card"
              style={{
                padding: 16,
                fontSize: 12,
                color: 'var(--text-3)',
                textAlign: 'center',
                background: 'var(--bg-sunken)',
                border: '1px dashed var(--border)',
              }}
            >
              No share links yet.
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {linksForThis.map((l) => {
                const url = buildShareUrl(l.token);
                return (
                  <div
                    key={l.id}
                    className="card"
                    style={{
                      padding: 10,
                      display: 'flex',
                      flexDirection: 'column',
                      gap: 6,
                    }}
                  >
                    <div className="flex items-center gap-2 flex-wrap">
                      <span
                        className="mono"
                        style={{
                          flex: 1,
                          minWidth: 0,
                          fontSize: 11,
                          color: 'var(--text-2)',
                          wordBreak: 'break-all',
                        }}
                      >
                        {url}
                      </span>
                      <span
                        className="mono inline-flex items-center gap-1"
                        style={{
                          fontSize: 10,
                          color: 'var(--text-3)',
                          flexShrink: 0,
                        }}
                      >
                        <Eye size={10} strokeWidth={1.7} /> {l.view_count}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <button
                        type="button"
                        onClick={() => onCopy(l.token)}
                        style={outlineBtn}
                      >
                        <Copy size={11} strokeWidth={1.7} />
                        {copiedToken === l.token ? 'Copied' : 'Copy'}
                      </button>
                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        style={{ ...outlineBtn, textDecoration: 'none' }}
                      >
                        <ExternalLink size={11} strokeWidth={1.7} />
                        Open
                      </a>
                      <button
                        type="button"
                        onClick={() => onDelete(l.id)}
                        style={{ ...outlineBtn, color: 'var(--plum)' }}
                      >
                        <Trash2 size={11} strokeWidth={1.7} />
                      </button>
                      {l.variant_id && (
                        <span
                          className="mono"
                          style={{
                            fontSize: 9.5,
                            padding: '1px 6px',
                            borderRadius: 999,
                            background: 'var(--bg-sunken)',
                            color: 'var(--text-3)',
                            marginLeft: 'auto',
                          }}
                        >
                          variant
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

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

const outlineBtn: React.CSSProperties = {
  padding: '5px 9px',
  borderRadius: 'var(--radius)',
  border: 0,
  background: 'transparent',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
  color: 'var(--text-2)',
  fontSize: 11,
  fontWeight: 500,
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 4,
};
