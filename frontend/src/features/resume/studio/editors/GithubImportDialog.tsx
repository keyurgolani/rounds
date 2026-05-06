// "Import from GitHub" — pulls a candidate's public repos and turns
// the ones they pick into Project entries.
//
// Uses GitHub's unauthenticated REST API
// (`https://api.github.com/users/<u>/repos`). That gets us name,
// description, primary language, html_url, stars, and date — enough
// to seed a project entry the user can polish in-place.
//
// "Pinned repos" require GitHub's GraphQL API which mandates auth, so
// we approximate by sorting all repos by star count then recency.
// Forks are filtered out by default; the user can flip the toggle.

import { useEffect, useMemo, useState } from 'react';
import { ExternalLink, Sparkles, Star, X } from 'lucide-react';
import type { Project } from '../../types';
import { uid } from '../../utils';
import { enhanceProjects } from '../../ai/client';

type Repo = {
  id: number;
  name: string;
  full_name: string;
  description: string | null;
  html_url: string;
  homepage: string | null;
  language: string | null;
  topics: string[];
  fork: boolean;
  stargazers_count: number;
  pushed_at: string;
};

type Props = {
  open: boolean;
  onClose: () => void;
  onImport: (projects: Project[]) => void;
};

const MAX_REPOS = 100;

export default function GithubImportDialog({ open, onClose, onImport }: Props) {
  const [username, setUsername] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [repos, setRepos] = useState<Repo[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [includeForks, setIncludeForks] = useState(false);
  const [aiEnhance, setAiEnhance] = useState(true);
  const [importing, setImporting] = useState(false);

  // Reset state on close so the next open feels fresh.
  useEffect(() => {
    if (!open) {
      setUsername('');
      setRepos([]);
      setSelected(new Set());
      setError(null);
      setLoading(false);
      setImporting(false);
    }
  }, [open]);

  // Esc closes.
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  async function fetchRepos() {
    if (!username.trim()) return;
    setLoading(true);
    setError(null);
    setRepos([]);
    setSelected(new Set());
    try {
      const res = await fetch(
        `https://api.github.com/users/${encodeURIComponent(username.trim())}/repos?per_page=${MAX_REPOS}&sort=updated`,
        { headers: { Accept: 'application/vnd.github+json' } },
      );
      if (res.status === 404) {
        throw new Error(`No GitHub user "${username.trim()}" found.`);
      }
      if (!res.ok) {
        const detail = await res.text().catch(() => res.statusText);
        throw new Error(`GitHub ${res.status}: ${detail.slice(0, 160)}`);
      }
      const data = (await res.json()) as Repo[];
      setRepos(data);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  const visible = useMemo(() => {
    const list = repos.filter((r) => includeForks || !r.fork);
    // Stars first; ties broken by recency.
    return list.sort((a, b) => {
      if (b.stargazers_count !== a.stargazers_count) {
        return b.stargazers_count - a.stargazers_count;
      }
      return (b.pushed_at || '').localeCompare(a.pushed_at || '');
    });
  }, [repos, includeForks]);

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function doImport() {
    const picked = visible.filter((r) => selected.has(r.id));
    if (picked.length === 0) {
      onClose();
      return;
    }
    const baseProjects: Project[] = picked.map((r) => ({
      id: uid(),
      name: r.name,
      description: r.description ?? '',
      technologies: techsFor(r),
      url: r.homepage || r.html_url,
      github: r.html_url,
      startDate: '',
      endDate: dateOnly(r.pushed_at),
      highlights:
        r.stargazers_count > 0
          ? [`⭐ ${r.stargazers_count} stargazers on GitHub`]
          : [],
    }));

    if (!aiEnhance) {
      onImport(baseProjects);
      onClose();
      return;
    }

    // Run AI enhancement before handing the projects up. If the call
    // fails we fall back to the raw projects so the import still
    // completes — the dialog surfaces the error inline.
    setImporting(true);
    setError(null);
    try {
      const enhanced = await enhanceProjects(
        picked.map((r) => ({
          name: r.name,
          full_name: r.full_name,
          description: r.description ?? '',
          language: r.language,
          topics: r.topics ?? [],
          stargazers: r.stargazers_count,
          url: r.homepage || r.html_url,
          homepage: r.homepage,
        })),
      );
      const merged = baseProjects.map((p, i) => {
        const e = enhanced[i];
        if (!e) return p;
        return {
          ...p,
          description: e.description?.trim() || p.description,
          highlights: [
            ...(e.highlights ?? []),
            // keep the auto stargazers note at the tail if present
            ...p.highlights.filter((h) => h.startsWith('⭐')),
          ].slice(0, 6),
        };
      });
      onImport(merged);
      onClose();
    } catch (err) {
      setError(`AI enhancement failed: ${(err as Error).message}`);
      // Don't auto-fall-back; let the user retry or untick the toggle.
    } finally {
      setImporting(false);
    }
  }

  if (!open) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Import from GitHub"
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
          maxWidth: 640,
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
          <div className="flex items-center gap-2">
            <GithubGlyph size={14} />
            <div>
              <div className="eyebrow" style={{ fontSize: 9.5 }}>
                Projects
              </div>
              <div style={{ fontSize: 13, fontWeight: 500 }}>Import from GitHub</div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            style={iconBtn}
          >
            <X size={14} strokeWidth={1.8} />
          </button>
        </div>

        <div
          style={{
            padding: 14,
            display: 'flex',
            flexDirection: 'column',
            gap: 10,
          }}
        >
          <label className="flex flex-col gap-1.5">
            <span className="eyebrow" style={{ fontSize: 9.5 }}>
              GitHub username
            </span>
            <div className="flex items-center gap-2">
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    void fetchRepos();
                  }
                }}
                placeholder="e.g. octocat"
                style={inputStyle}
                autoFocus
              />
              <button
                type="button"
                onClick={fetchRepos}
                disabled={!username.trim() || loading}
                style={{
                  padding: '8px 14px',
                  borderRadius: 'var(--radius)',
                  border: 0,
                  background: 'var(--accent)',
                  color: 'var(--bg-elev)',
                  fontSize: 12.5,
                  fontWeight: 500,
                  cursor: !username.trim() || loading ? 'not-allowed' : 'pointer',
                  opacity: !username.trim() || loading ? 0.6 : 1,
                  flexShrink: 0,
                }}
              >
                {loading ? 'Loading…' : 'Fetch repos'}
              </button>
            </div>
          </label>

          {error && (
            <div role="alert" style={{ fontSize: 11.5, color: 'var(--plum)' }}>
              {error}
            </div>
          )}

          {repos.length > 0 && (
            <>
              <div className="flex items-center gap-4 flex-wrap">
                <label
                  className="flex items-center gap-2"
                  style={{ fontSize: 11.5, color: 'var(--text-3)' }}
                >
                  <input
                    type="checkbox"
                    checked={includeForks}
                    onChange={(e) => setIncludeForks(e.target.checked)}
                  />
                  Include forks
                </label>
                <label
                  className="flex items-center gap-2"
                  style={{ fontSize: 11.5, color: 'var(--text-3)' }}
                  title={
                    'Pulls each project’s markdown docs (README, ARCHITECTURE, ' +
                    'docs/**) and runs a per-doc + aggregator agent pipeline to ' +
                    'extract niche, achievements, vision, architecture, and ' +
                    'engineering highlights. Slower but produces stronger output.'
                  }
                >
                  <input
                    type="checkbox"
                    checked={aiEnhance}
                    onChange={(e) => setAiEnhance(e.target.checked)}
                  />
                  <span className="inline-flex items-center gap-1">
                    <Sparkles
                      size={11}
                      strokeWidth={1.7}
                      style={{ color: 'var(--accent)' }}
                    />
                    AI Enhancement
                  </span>
                </label>
              </div>

              <div
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 6,
                  maxHeight: '52vh',
                  overflowY: 'auto',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  padding: 6,
                }}
              >
                {visible.map((r) => {
                  const checked = selected.has(r.id);
                  return (
                    <label
                      key={r.id}
                      style={{
                        display: 'flex',
                        gap: 10,
                        padding: '8px 10px',
                        borderRadius: 'var(--radius)',
                        background: checked ? 'var(--bg-elev)' : 'transparent',
                        boxShadow: checked
                          ? 'inset 0 0 0 1px var(--accent)'
                          : 'inset 0 0 0 1px var(--border)',
                        cursor: 'pointer',
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggle(r.id)}
                        style={{ marginTop: 2, flexShrink: 0 }}
                      />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span style={{ fontSize: 12.5, fontWeight: 500 }}>{r.name}</span>
                          {r.fork && (
                            <span
                              className="mono"
                              style={{
                                fontSize: 9,
                                padding: '1px 6px',
                                borderRadius: 999,
                                color: 'var(--text-4)',
                                boxShadow: 'inset 0 0 0 1px var(--border)',
                              }}
                            >
                              fork
                            </span>
                          )}
                          {r.stargazers_count > 0 && (
                            <span
                              className="mono"
                              style={{
                                fontSize: 10,
                                color: 'var(--ochre)',
                                display: 'inline-flex',
                                alignItems: 'center',
                                gap: 2,
                              }}
                            >
                              <Star size={10} strokeWidth={1.7} fill="currentColor" />{' '}
                              {r.stargazers_count}
                            </span>
                          )}
                          {r.language && (
                            <span
                              className="mono"
                              style={{
                                fontSize: 10,
                                color: 'var(--text-3)',
                                background: 'var(--bg-sunken)',
                                padding: '1px 6px',
                                borderRadius: 999,
                              }}
                            >
                              {r.language}
                            </span>
                          )}
                          <a
                            href={r.html_url}
                            target="_blank"
                            rel="noreferrer"
                            onClick={(e) => e.stopPropagation()}
                            style={{
                              marginLeft: 'auto',
                              fontSize: 10,
                              color: 'var(--text-4)',
                              textDecoration: 'none',
                              display: 'inline-flex',
                              alignItems: 'center',
                              gap: 3,
                            }}
                          >
                            <ExternalLink size={10} strokeWidth={1.7} />
                          </a>
                        </div>
                        {r.description && (
                          <div
                            style={{
                              fontSize: 11.5,
                              color: 'var(--text-3)',
                              lineHeight: 1.45,
                              marginTop: 2,
                            }}
                          >
                            {r.description}
                          </div>
                        )}
                      </div>
                    </label>
                  );
                })}
              </div>
            </>
          )}

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => void doImport()}
              disabled={selected.size === 0 || importing}
              style={{
                padding: '8px 14px',
                borderRadius: 'var(--radius)',
                border: 0,
                background: 'var(--accent)',
                color: 'var(--bg-elev)',
                fontSize: 12.5,
                fontWeight: 500,
                cursor:
                  selected.size === 0 || importing ? 'not-allowed' : 'pointer',
                opacity: selected.size === 0 || importing ? 0.5 : 1,
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              {importing && aiEnhance ? (
                <>
                  <Sparkles size={11} strokeWidth={1.8} />
                  Reading docs…
                </>
              ) : (
                <>
                  Import {selected.size || ''} project
                  {selected.size === 1 ? '' : 's'}
                </>
              )}
            </button>
            <button
              type="button"
              onClick={onClose}
              style={{
                padding: '8px 12px',
                background: 'transparent',
                border: 0,
                color: 'var(--text-3)',
                fontSize: 12,
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// Tiny GitHub mark — saves an icon-set dependency for one button.
function GithubGlyph({ size = 14 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 16 16"
      fill="currentColor"
      aria-hidden="true"
    >
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
    </svg>
  );
}

function techsFor(r: Repo): string[] {
  // Prefer `topics` (curated by the repo owner); fall back to language.
  if (r.topics && r.topics.length > 0) return r.topics.slice(0, 8);
  if (r.language) return [r.language];
  return [];
}

function dateOnly(iso: string | null | undefined): string {
  if (!iso) return '';
  const m = iso.match(/^(\d{4})-(\d{2})/);
  return m ? `${m[1]}-${m[2]}` : '';
}

const inputStyle: React.CSSProperties = {
  flex: 1,
  padding: '8px 10px',
  background: 'var(--bg-elev)',
  boxShadow: 'inset 0 0 0 1px var(--border-strong)',
  borderRadius: 'var(--radius)',
  border: 0,
  fontSize: 12.5,
  color: 'var(--text)',
  outline: 'none',
};

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
