import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, Plus, Trash2, Upload } from 'lucide-react';
import AppHeader from '../components/shell/AppHeader';
import PageShell from '../components/shell/PageShell';
import EmptyState from '../components/shell/EmptyState';
import { usePersistedState } from '../hooks/usePersistedState';
import { useButtonFileDrop } from '../hooks/useButtonFileDrop';
import { listResumes, createResume, deleteResume } from '../features/resume/api';
import { importFromText } from '../features/resume/ai/client';
import { extractText } from '../features/resume/import/extract';
import type { Resume } from '../features/resume/types';
import { titleCaseFromSlug } from '../lib/slug';

type SortKey = 'recent-desc' | 'recent-asc' | 'name-asc' | 'name-desc';

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: 'recent-desc', label: 'Recently updated' },
  { value: 'recent-asc', label: 'Least recent first' },
  { value: 'name-asc', label: 'Name (A–Z)' },
  { value: 'name-desc', label: 'Name (Z–A)' },
];

export default function ResumesList() {
  const navigate = useNavigate();
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [importing, setImporting] = useState<string | null>(null);
  const [importError, setImportError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [sort, setSort] = usePersistedState<SortKey>('rounds.resumes.sort', 'recent-desc');

  useEffect(() => {
    listResumes()
      .then(setResumes)
      .finally(() => setLoading(false));
  }, []);

  const filtered = useMemo(() => {
    const matches = resumes.filter((r) => {
      if (!query.trim()) return true;
      const s = query.trim().toLowerCase();
      return r.name.toLowerCase().includes(s);
    });
    const sorted = [...matches];
    sorted.sort((a, b) => {
      switch (sort) {
        case 'recent-asc':
          return a.updated_at.localeCompare(b.updated_at);
        case 'name-asc':
          return a.name.localeCompare(b.name);
        case 'name-desc':
          return b.name.localeCompare(a.name);
        case 'recent-desc':
        default:
          return b.updated_at.localeCompare(a.updated_at);
      }
    });
    return sorted;
  }, [resumes, query, sort]);

  async function onCreate() {
    if (creating) return;
    setCreating(true);
    try {
      const name = `Untitled resume ${resumes.length + 1}`;
      const created = await createResume({ name });
      navigate(`/resumes/${created.slug}`);
    } finally {
      setCreating(false);
    }
  }

  async function onDelete(target: Resume) {
    const ok = window.confirm(
      `Delete "${target.name}"? This removes the resume permanently. Variants ` +
        `and share links tied to it will be deleted too.`,
    );
    if (!ok) return;
    setDeleteError(null);
    // Optimistic — restore on failure.
    const before = resumes;
    setResumes((prev) => prev.filter((r) => r.id !== target.id));
    try {
      await deleteResume(target.id);
    } catch (err) {
      setResumes(before);
      setDeleteError(`Couldn't delete "${target.name}": ${(err as Error).message}`);
    }
  }

  async function onImport(file: File) {
    setImportError(null);
    setImporting('Extracting text…');
    try {
      const { text } = await extractText(file);
      setImporting('Parsing with AI…');
      const { data } = await importFromText(text);
      setImporting('Saving resume…');
      const stripped = file.name.replace(/\.[^.]+$/, '');
      const baseName = titleCaseFromSlug(stripped) || 'Imported resume';
      const created = await createResume({ name: baseName, data });
      navigate(`/resumes/${created.slug}`);
    } catch (err) {
      setImportError((err as Error).message);
    } finally {
      setImporting(null);
      if (fileRef.current) fileRef.current.value = '';
    }
  }

  const { dropProps, isOver: importDropOver } = useButtonFileDrop({
    onFile: onImport,
    disabled: importing !== null,
  });

  const hasData = resumes.length > 0;

  return (
    <PageShell
      header={
        <>
          <AppHeader
            eyebrow="Track · Resume Studio"
            title="Resumes"
            description="Master resumes and tailored variants for every application. Edit, customize, and export to any format."
            chromeActions={
              <div className="flex items-center gap-1.5">
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.docx,.md,.markdown,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) void onImport(f);
                  }}
                />
                <button
                  type="button"
                  onClick={() => fileRef.current?.click()}
                  disabled={importing !== null}
                  data-ai-processing-glow={importing ? 'true' : undefined}
                  className="inline-flex items-center gap-1.5"
                  {...dropProps}
                  style={{
                    padding: '6px 12px',
                    borderRadius: 8,
                    background: importDropOver ? 'var(--accent-soft)' : 'transparent',
                    color: importDropOver ? 'var(--accent)' : 'var(--text-2)',
                    boxShadow: importDropOver
                      ? 'inset 0 0 0 1.5px var(--accent)'
                      : 'inset 0 0 0 1px var(--border-strong)',
                    border: 0,
                    fontSize: 12,
                    fontWeight: 500,
                    cursor: importing ? 'wait' : 'pointer',
                    transition: 'background 120ms, box-shadow 120ms, color 120ms',
                  }}
                  title="Import from PDF / DOCX / Markdown / Text — or drop a file here"
                >
                  <Upload size={13} strokeWidth={1.8} />
                  {importing ?? 'Import'}
                </button>
                <button
                  type="button"
                  onClick={onCreate}
                  disabled={creating || importing !== null}
                  className="inline-flex items-center gap-1.5"
                  style={{ ...primaryBtn, padding: '6px 14px', borderRadius: 8 }}
                >
                  <Plus size={13} strokeWidth={1.8} />
                  New resume
                </button>
              </div>
            }
          />
          {hasData && (
            <div
              className="flex-shrink-0 px-5 sm:px-8 pt-4 pb-2"
              style={{ background: 'var(--bg)' }}
            >
              <div className="flex flex-wrap gap-2 items-center">
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search resume name…"
                  className="mono"
                  style={{
                    flex: '1 1 240px',
                    padding: '9px 12px',
                    background: 'var(--bg-elev)',
                    boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                    borderRadius: 'var(--radius)',
                    border: 0,
                    fontSize: 12.5,
                    color: 'var(--text)',
                    outline: 'none',
                  }}
                />
                <div style={{ minWidth: 200 }}>
                  <select
                    value={sort}
                    onChange={(e) => setSort(e.target.value as SortKey)}
                    aria-label="Sort"
                    style={{
                      padding: '9px 12px',
                      background: 'var(--bg-elev)',
                      boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                      borderRadius: 'var(--radius)',
                      border: 0,
                      fontSize: 12.5,
                      color: 'var(--text)',
                      outline: 'none',
                      width: '100%',
                    }}
                  >
                    {SORT_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                </div>
                <span
                  className="mono ml-auto"
                  style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}
                >
                  {filtered.length} OF {resumes.length} RESUMES
                </span>
              </div>
            </div>
          )}
        </>
      }
    >
      <div className="px-5 sm:px-8 py-5">
        {importError && (
          <div
            className="card"
            role="alert"
            style={{
              padding: '10px 14px',
              marginBottom: 12,
              borderColor: 'var(--plum)',
              background: 'var(--bg-elev)',
              color: 'var(--plum)',
              fontSize: 12.5,
            }}
          >
            Import failed: {importError}
          </div>
        )}
        {deleteError && (
          <div
            className="card"
            role="alert"
            style={{
              padding: '10px 14px',
              marginBottom: 12,
              borderColor: 'var(--plum)',
              background: 'var(--bg-elev)',
              color: 'var(--plum)',
              fontSize: 12.5,
            }}
          >
            {deleteError}
          </div>
        )}
        {loading ? (
          <div className="card p-8 text-center" style={{ color: 'var(--text-3)' }}>
            Loading…
          </div>
        ) : hasData ? (
          filtered.length === 0 ? (
            <div
              className="card p-8 text-center"
              style={{ color: 'var(--text-4)', fontSize: 13 }}
            >
              No resumes match that search.
            </div>
          ) : (
            <div className="card overflow-hidden">
              {filtered.map((r, i) => (
                <ResumeRow
                  key={r.id}
                  resume={r}
                  last={i === filtered.length - 1}
                  onDelete={() => void onDelete(r)}
                />
              ))}
            </div>
          )
        ) : (
          <EmptyState
            illustration={<ResumeStackIllustration />}
            title="No resumes yet"
            body="Start with a blank resume, or import a PDF you already have. Each resume can spawn job-tailored variants linked to applications you're tracking."
            primary={{ label: creating ? 'Creating…' : 'New resume', onClick: onCreate }}
            tip="Import a PDF in Studio to skip retyping everything"
          />
        )}
      </div>
    </PageShell>
  );
}

function ResumeRow({
  resume,
  last,
  onDelete,
}: {
  resume: Resume;
  last: boolean;
  onDelete: () => void;
}) {
  // The body is a navigating <Link>; the delete button is a sibling
  // so clicking it doesn't bubble through to the link. The wrapping
  // <div> owns the hover background and the bottom border, so the
  // row still reads as one continuous surface.
  return (
    <div
      className="flex items-stretch gap-1"
      style={{
        borderBottom: last ? 'none' : '1px solid var(--border)',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = 'var(--bg-sunken)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = 'transparent';
      }}
    >
      <Link
        to={`/resumes/${resume.slug}`}
        className="flex md:grid items-start md:items-center gap-2 md:gap-3 flex-col md:flex-row"
        style={{
          flex: 1,
          minWidth: 0,
          gridTemplateColumns: '1fr 160px 90px auto',
          padding: '14px 16px',
          textDecoration: 'none',
          color: 'var(--text)',
        }}
      >
        <div className="min-w-0">
          <div style={{ fontSize: 14, fontWeight: 500 }}>{resume.name}</div>
          <div style={{ fontSize: 12, color: 'var(--text-3)' }}>
            {resume.template_id ? `Template: ${resume.template_id}` : '—'}
          </div>
        </div>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-3)' }}>
          Updated {formatDate(resume.updated_at)}
        </span>
        <span className="mono" style={{ fontSize: 11, color: 'var(--text-4)' }}>
          {resume.slug}
        </span>
        <span style={{ color: 'var(--text-4)', display: 'inline-flex' }}>
          <ArrowRight size={13} strokeWidth={1.7} />
        </span>
      </Link>
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        title={`Delete ${resume.name}`}
        aria-label={`Delete ${resume.name}`}
        style={{
          alignSelf: 'center',
          marginRight: 12,
          height: 28,
          width: 28,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'transparent',
          border: 0,
          borderRadius: 6,
          color: 'var(--text-3)',
          cursor: 'pointer',
          flexShrink: 0,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'var(--bg-elev)';
          e.currentTarget.style.color = 'var(--plum)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'transparent';
          e.currentTarget.style.color = 'var(--text-3)';
        }}
      >
        <Trash2 size={13} strokeWidth={1.7} />
      </button>
    </div>
  );
}

function formatDate(iso: string): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso.slice(0, 10);
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function ResumeStackIllustration() {
  return (
    <svg viewBox="0 0 120 84" width="120" height="84" fill="none" aria-hidden="true">
      <rect
        x="20"
        y="22"
        width="50"
        height="58"
        rx="3"
        fill="var(--bg-sunken)"
        stroke="var(--border-strong)"
        strokeWidth="1"
        transform="rotate(-5 45 51)"
      />
      <rect
        x="40"
        y="14"
        width="50"
        height="58"
        rx="3"
        fill="var(--bg-elev)"
        stroke="var(--border-strong)"
        strokeWidth="1"
        transform="rotate(4 65 43)"
      />
      <rect
        x="36"
        y="18"
        width="50"
        height="58"
        rx="3"
        fill="var(--bg-elev)"
        stroke="var(--border-strong)"
        strokeWidth="1"
      />
      <line x1="44" y1="30" x2="78" y2="30" stroke="var(--text-2)" strokeWidth="1.6" strokeLinecap="round" />
      <line x1="44" y1="38" x2="72" y2="38" stroke="var(--text-4)" strokeWidth="1.4" strokeLinecap="round" opacity="0.7" />
      <line x1="44" y1="46" x2="78" y2="46" stroke="var(--text-4)" strokeWidth="1.4" strokeLinecap="round" opacity="0.6" />
      <line x1="44" y1="54" x2="68" y2="54" stroke="var(--text-4)" strokeWidth="1.4" strokeLinecap="round" opacity="0.5" />
      <line x1="44" y1="62" x2="76" y2="62" stroke="var(--text-4)" strokeWidth="1.4" strokeLinecap="round" opacity="0.4" />
    </svg>
  );
}

const primaryBtn: React.CSSProperties = {
  padding: '8px 14px',
  borderRadius: 6,
  border: 0,
  background: 'var(--accent)',
  color: 'var(--bg-elev)',
  fontSize: 12.5,
  fontWeight: 500,
  cursor: 'pointer',
};
