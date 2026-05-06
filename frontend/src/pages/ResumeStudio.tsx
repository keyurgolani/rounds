import { useCallback, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ChevronLeft, Eye, Mail, Pencil, Share2, Trash2 } from 'lucide-react';
import AppHeader from '../components/shell/AppHeader';
import PageShell from '../components/shell/PageShell';
import StudioShell, {
  VALID_TABS,
  type ActiveKey,
} from '../features/resume/studio/StudioShell';
import CoverLetterDialog from '../features/resume/studio/CoverLetterDialog';
import PreviewDialog from '../features/resume/studio/PreviewDialog';
import ShareDialog from '../features/resume/share/ShareDialog';
import BulletLibraryDrawer from '../features/resume/bullets/BulletLibraryDrawer';
import { BulletLibraryProvider } from '../features/resume/bullets/BulletLibraryContext';
import { useResume } from '../features/resume/hooks/useResume';
import { deleteResume } from '../features/resume/api';

const DEFAULT_TAB: ActiveKey = 'personal';
const VALID_TAB_SET: Set<string> = new Set(VALID_TABS);

export default function ResumeStudio() {
  const { slug } = useParams<{ slug: string }>();
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const result = useResume(slug);
  const [renaming, setRenaming] = useState(false);
  const [draftName, setDraftName] = useState('');
  const [coverOpen, setCoverOpen] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // The studio's active tab is whatever `?tab=` says. Selecting a
  // different section/tool in the shell rewrites this param so the
  // URL is the single source of truth for tab state — bookmarkable,
  // shareable, survives reloads.
  const tabParam = searchParams.get('tab');
  const active: ActiveKey =
    tabParam && VALID_TAB_SET.has(tabParam)
      ? (tabParam as ActiveKey)
      : DEFAULT_TAB;
  const onTabChange = useCallback(
    (next: ActiveKey) => {
      setSearchParams(
        (prev) => {
          const params = new URLSearchParams(prev);
          if (next === DEFAULT_TAB) params.delete('tab');
          else params.set('tab', next);
          return params;
        },
        // Tab swaps shouldn't pile up in the back stack — the user
        // expects Back to take them out of the resume entirely, not
        // walk through every tab they clicked.
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const startRename = () => {
    if (!result.resume) return;
    setDraftName(result.resume.name);
    setRenaming(true);
  };
  const commitRename = async () => {
    setRenaming(false);
    const next = draftName.trim();
    if (!next || !result.resume || next === result.resume.name) return;
    const newSlug = await result.rename(next);
    // If the slug changed, swap the URL in place so reloads land on
    // the right resume. `replace: true` keeps the back button taking
    // the user wherever they came from rather than the stale slug.
    if (newSlug && newSlug !== slug) {
      navigate(`/resumes/${newSlug}`, { replace: true });
    }
  };

  const onDelete = async () => {
    if (!result.resume || deleting) return;
    const ok = window.confirm(
      `Delete "${result.resume.name}"? This removes the resume permanently. ` +
        `Variants and share links tied to it will be deleted too.`,
    );
    if (!ok) return;
    setDeleting(true);
    try {
      await deleteResume(result.resume.id);
      navigate('/resumes');
    } catch (err) {
      window.alert(`Couldn't delete: ${(err as Error).message}`);
      setDeleting(false);
    }
  };

  return (
    <BulletLibraryProvider>
      <PrintStyles />
      <PageShell
        header={
          <AppHeader
            eyebrow={
              <Link
                to="/resumes"
                className="inline-flex items-center gap-1"
                style={{ color: 'var(--text-3)', textDecoration: 'none', fontSize: 11.5 }}
              >
                <ChevronLeft size={12} strokeWidth={1.8} />
                Resumes
              </Link>
            }
            title={
              renaming ? (
                <input
                  autoFocus
                  value={draftName}
                  onChange={(e) => setDraftName(e.target.value)}
                  onBlur={commitRename}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') commitRename();
                    if (e.key === 'Escape') setRenaming(false);
                  }}
                  style={{
                    fontFamily: 'inherit',
                    fontSize: 'inherit',
                    fontWeight: 'inherit',
                    color: 'var(--text)',
                    background: 'var(--bg-elev)',
                    border: 0,
                    outline: 'none',
                    padding: '2px 6px',
                    borderRadius: 6,
                    boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                    minWidth: 240,
                  }}
                />
              ) : (
                <button
                  type="button"
                  onClick={startRename}
                  className="inline-flex items-center gap-2"
                  style={{
                    background: 'transparent',
                    border: 0,
                    color: 'inherit',
                    font: 'inherit',
                    padding: 0,
                    cursor: 'text',
                  }}
                  title="Rename"
                >
                  {result.resume?.name ?? (result.loading ? 'Loading…' : 'Resume')}
                  <Pencil size={11} strokeWidth={1.7} style={{ opacity: 0.5 }} />
                </button>
              )
            }
            description={
              result.resume
                ? `${result.resume.template_id} · ${formatSaveState(result)}`
                : undefined
            }
            chromeActions={
              <div className="flex items-center gap-1.5" data-no-print>
                <button
                  type="button"
                  onClick={onDelete}
                  disabled={!result.resume || deleting}
                  className="inline-flex items-center gap-1.5"
                  style={{
                    padding: '6px 10px',
                    borderRadius: 8,
                    background: 'transparent',
                    color: 'var(--text-3)',
                    boxShadow: 'inset 0 0 0 1px var(--border)',
                    border: 0,
                    fontSize: 12,
                    fontWeight: 500,
                    cursor:
                      !result.resume || deleting ? 'not-allowed' : 'pointer',
                    opacity: !result.resume || deleting ? 0.6 : 1,
                  }}
                  title="Delete this resume"
                  aria-label="Delete this resume"
                  onMouseEnter={(e) => {
                    if (result.resume && !deleting) {
                      e.currentTarget.style.color = 'var(--plum)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = 'var(--text-3)';
                  }}
                >
                  <Trash2 size={13} strokeWidth={1.8} />
                  {deleting ? 'Deleting…' : 'Delete'}
                </button>
                <button
                  type="button"
                  onClick={() => setShareOpen(true)}
                  disabled={!result.resume}
                  className="inline-flex items-center gap-1.5"
                  style={{
                    padding: '6px 12px',
                    borderRadius: 8,
                    background: 'transparent',
                    color: 'var(--text-2)',
                    boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                    border: 0,
                    fontSize: 12,
                    fontWeight: 500,
                    cursor: result.resume ? 'pointer' : 'not-allowed',
                  }}
                  title="Create a public share link"
                >
                  <Share2 size={13} strokeWidth={1.8} />
                  Share
                </button>
                <button
                  type="button"
                  onClick={() => setCoverOpen(true)}
                  disabled={!result.resume}
                  className="inline-flex items-center gap-1.5"
                  style={{
                    padding: '6px 12px',
                    borderRadius: 8,
                    background: 'transparent',
                    color: 'var(--text-2)',
                    boxShadow: 'inset 0 0 0 1px var(--border-strong)',
                    border: 0,
                    fontSize: 12,
                    fontWeight: 500,
                    cursor: result.resume ? 'pointer' : 'not-allowed',
                  }}
                  title="Generate a cover letter from this resume"
                >
                  <Mail size={13} strokeWidth={1.8} />
                  Cover letter
                </button>
                <button
                  type="button"
                  onClick={() => setPreviewOpen(true)}
                  disabled={!result.resume}
                  className="inline-flex items-center gap-1.5"
                  style={{
                    padding: '6px 12px',
                    borderRadius: 8,
                    background: 'var(--accent)',
                    color: 'var(--bg-elev)',
                    border: 0,
                    fontSize: 12,
                    fontWeight: 500,
                    cursor: result.resume ? 'pointer' : 'not-allowed',
                  }}
                  title="Inspect the resume full screen"
                >
                  <Eye size={13} strokeWidth={1.8} />
                  Preview
                </button>
              </div>
            }
          />
        }
      >
        <div
          className="h-full px-5 sm:px-8 py-5 flex flex-col min-h-0"
          data-resume-studio-body
        >
          {result.error ? (
            <div className="card p-8 text-center" style={{ color: 'var(--plum)' }}>
              {result.error}
            </div>
          ) : result.loading || !result.resume ? (
            <div className="card p-8 text-center" style={{ color: 'var(--text-3)' }}>
              Loading…
            </div>
          ) : (
            <StudioShell
              result={result}
              active={active}
              onActiveChange={onTabChange}
            />
          )}
        </div>
      </PageShell>
      {result.resume && (
        <CoverLetterDialog
          open={coverOpen}
          onClose={() => setCoverOpen(false)}
          data={result.data}
          filenameBase={(result.resume.slug || result.resume.name || 'resume').replace(
            /[^a-z0-9._-]+/gi,
            '-',
          )}
        />
      )}
      {result.resume && (
        <ShareDialog
          open={shareOpen}
          onClose={() => setShareOpen(false)}
          resumeId={result.resume.id}
        />
      )}
      {result.resume && (
        <PreviewDialog
          open={previewOpen}
          onClose={() => setPreviewOpen(false)}
          data={result.data}
          templateId={result.templateId}
          design={result.design}
        />
      )}
      <BulletLibraryDrawer />
    </BulletLibraryProvider>
  );
}

function formatSaveState(r: ReturnType<typeof useResume>): string {
  if (r.saveState === 'saving') return 'Saving…';
  if (r.saveState === 'saved') return 'Saved';
  if (r.saveState === 'error') return 'Save failed — retrying';
  if (r.lastSavedAt) {
    const t = new Date(r.lastSavedAt);
    if (!Number.isNaN(t.getTime())) {
      return `Last saved ${t.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`;
    }
  }
  return 'All changes saved';
}

// Print styles dropped via a single tag so the studio owns its own
// print rules without polluting the global stylesheet. When the user
// hits Print, everything except the rendered A4 page collapses out
// and the page background goes white.
function PrintStyles() {
  return (
    <style>{`
      @media print {
        @page {
          size: A4;
          margin: 0;
        }
        html, body {
          background: #fff !important;
        }
        /* Hide app chrome */
        aside, nav, header, [role="navigation"], [data-no-print] {
          display: none !important;
        }
        /* Hide every studio pane except the preview */
        [data-studio-pane="sections"],
        [data-studio-pane="form"] {
          display: none !important;
        }
        /* Let the preview fill the page */
        [data-resume-studio-body] {
          padding: 0 !important;
        }
        [data-studio-pane="preview"] {
          position: static !important;
          height: auto !important;
        }
        [data-resume-preview] {
          padding: 0 !important;
          background: #fff !important;
          border-radius: 0 !important;
          /* The preview card scrolls inside its column on screen, but
             print needs the entire content rendered, not clipped to
             the visible viewport. */
          height: auto !important;
          overflow: visible !important;
        }
        [data-resume-page] {
          box-shadow: none !important;
          margin: 0 !important;
          width: 100% !important;
          min-height: 100% !important;
        }
        /* Visual page-break markers belong to the editor only — never
           to the printed output. */
        [data-page-overlay] {
          display: none !important;
        }
      }
    `}</style>
  );
}
