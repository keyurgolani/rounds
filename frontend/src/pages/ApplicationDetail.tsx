import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Check, ChevronDown, Wand2 } from 'lucide-react';
import {
  getApplication,
  listRounds,
  updateApplication,
  updateApplicationField,
  type Application,
  type InterviewRound as Round,
} from '../applications/api';
import RoundsList from '../applications/RoundsList';
import InlineAddRound from '../applications/InlineAddRound';
import InlineEditField from '../applications/InlineEditField';
import AppHeader from '../components/shell/AppHeader';
import PageShell from '../components/shell/PageShell';
import BackLink from '../components/shell/BackLink';
import InlineMarkdown from '../components/shell/InlineMarkdown';
import OfferPanel, { type Offer } from '../components/shell/OfferPanel';
import { listResumes } from '../features/resume/api';

const STATUS_OPTIONS = ['Wishlist', 'Applied', 'Interviewing', 'Offer', 'Rejected'];

const STATUS_COLORS: Record<string, { bg: string; fg: string }> = {
  Wishlist: { bg: 'var(--paper-3)', fg: 'var(--text-3)' },
  Applied: { bg: 'var(--ochre-soft)', fg: 'var(--ochre)' },
  Interviewing: { bg: 'var(--accent-soft)', fg: 'var(--accent)' },
  Offer: { bg: 'var(--forest-soft)', fg: 'var(--forest)' },
  Rejected: { bg: 'var(--plum-soft)', fg: 'var(--plum)' },
};

export default function ApplicationDetail() {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const [app, setApp] = useState<Application | null>(null);
  const [rounds, setRounds] = useState<Round[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState('');

  // Mirror of the OfferPanel's last-seen offer, used to detect the
  // null → non-null transition (i.e. user just created an offer).
  // Without this ref, the auto-flip code can't tell the difference
  // between "offer was just created" and "offer was edited" and ends
  // up clobbering deliberate status changes.
  const offerRef = useRef<Offer | null>(null);
  const existingLoopLabels = useMemo(() => {
    const set = new Set<string>();
    for (const r of rounds) {
      if (r.loop_label) set.add(r.loop_label);
    }
    return Array.from(set).sort();
  }, [rounds]);

  useEffect(() => {
    if (!slug) return;
    setLoading(true);
    // Slug-or-id resolution happens in getApplication; we then load
    // rounds by the resolved id so we never fire listRounds against a
    // slug (which the previous code did, silently returning []).
    let cancelled = false;
    getApplication(slug)
      .then(async (a) => {
        if (cancelled) return;
        setApp(a);
        setStatus(a.status);
        const rs = await listRounds(a.id).catch(() => [] as Round[]);
        if (!cancelled) setRounds(rs);
      })
      .catch(() => {
        if (!cancelled) setApp(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (loading) {
    return (
      <div
        className="h-full flex items-center justify-center"
        style={{ color: 'var(--text-4)', fontSize: 13 }}
      >
        Loading…
      </div>
    );
  }

  if (!app) {
    return (
      <PageShell
        header={
          <AppHeader
            eyebrow={
              <span className="inline-flex items-center" style={{ gap: 6 }}>
                <BackLink to="/applications" label="All applications" />
                <span style={{ color: 'var(--text-4)' }}>·</span>
                <span>Not found</span>
              </span>
            }
            title="Application not found"
            description="The application you tried to open doesn't exist (or was deleted). Head back to the list to pick another."
          />
        }
      >
        <div
          className="flex items-center justify-center h-full"
          style={{ color: 'var(--text-3)', fontSize: 13 }}
        >
          We couldn't find that application.
        </div>
      </PageShell>
    );
  }

  async function updateStatus(next: string) {
    if (!app || next === app.status) return;
    setSaving(true);
    setStatus(next);
    try {
      const saved = await updateApplication(app.id, {
        company: app.company,
        role: app.role,
        status: next,
        applied_date: app.applied_date,
        notes: app.notes,
        resume_variant: app.resume_variant,
        url: app.url,
        job_description: app.job_description,
        campaign_id: app.campaign_id ?? '',
        last_activity_at: new Date().toISOString(),
      });
      setApp(saved);
    } catch {
      setStatus(app.status);
    } finally {
      setSaving(false);
    }
  }

  return (
    <PageShell
      header={
        <AppHeader
          eyebrow={
            <span className="inline-flex items-center" style={{ gap: 6 }}>
              <BackLink to="/applications" label="All applications" />
              <span style={{ color: 'var(--text-4)' }}>·</span>
              <span>{app.company}</span>
            </span>
          }
          title={app.role}
          description={`Everything you've captured about ${app.company} — role detail, rounds, notes, and offer terms once they land.`}
          chromeActions={
            <div className="flex items-center gap-1.5">
              <StatusSwitch
                status={status}
                saving={saving}
                onChange={(next) => void updateStatus(next)}
              />
              <TailorButton applicationId={String(app.id)} />
            </div>
          }
        />
      }
      footer={
        /*
          Offer dock — floating card pinned to the bottom of the
          viewport via PageShell's footer slot, so it stays put
          regardless of content height above. Wrapper has page-edge
          padding so the dock reads as a separate floating element
          rather than a flush bottom bar. Height is content-driven:
          collapsed when there's no offer, taller when recording /
          editing or when there's a long negotiation trail. Capped at
          60vh with internal scroll so it never swallows more than
          ~60% of the viewport.
        */
        <div className="px-5 sm:px-8 pb-4 pt-2">
          <div
            style={{
              maxHeight: '60vh',
              overflowY: 'auto',
              borderRadius: 'var(--radius)',
              boxShadow: '0 12px 28px rgba(0, 0, 0, 0.16)',
            }}
          >
            <OfferPanel
              applicationId={String(app.id)}
              onOfferChange={(o) => {
                // Sync application.status with offer presence on the
                // two edge transitions:
                //   null  → Offer    : recording a first offer flips to "Offer"
                //   Offer → null     : clearing the offer flips back to "Interviewing"
                // Mid-state edits (any non-null → non-null) don't
                // touch status — that would clobber deliberate status
                // changes the user made on the chrome pill.
                const prev = offerRef.current;
                offerRef.current = o;
                if (
                  o &&
                  !prev &&
                  app.status !== 'Offer' &&
                  app.status !== 'Rejected'
                ) {
                  updateStatus('Offer');
                } else if (!o && prev && app.status === 'Offer') {
                  updateStatus('Interviewing');
                }
              }}
            />
          </div>
        </div>
      }
    >
      <div className="px-5 sm:px-8 py-6 flex flex-col gap-5">
        <div
          className="grid gap-5"
          style={{
            gridTemplateColumns: 'minmax(0, 2fr) minmax(0, 1fr)',
          }}
        >
          <div className="card p-6">
            <div className="flex items-center justify-between mb-3 gap-3">
              <div className="eyebrow">Company</div>
              <Timestamps createdAt={app.created_at} updatedAt={app.updated_at} />
            </div>
            <InlineEditField
              kind="text"
              label="Company"
              value={app.company}
              onCommit={async (next) => {
                const saved = await updateApplicationField(app.id, {
                  company: next,
                });
                setApp(saved);
              }}
              placeholder="Company name"
              renderRead={(v) => (
                <span
                  className="display-italic"
                  style={{
                    fontSize: 30,
                    fontWeight: 400,
                    lineHeight: 1.05,
                    color: v ? 'var(--text)' : 'var(--text-4)',
                  }}
                >
                  {v || 'Untitled company'}
                </span>
              )}
            />

            <div
              className="grid gap-4 mt-5"
              style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}
            >
              <InlineEditField
                kind="text"
                label="Role"
                value={app.role}
                onCommit={async (next) => {
                  const saved = await updateApplicationField(app.id, {
                    role: next,
                  });
                  setApp(saved);
                }}
                placeholder="Software Engineer"
              />
              <InlineEditField
                kind="date-only"
                label="Applied"
                value={app.applied_date}
                onCommit={async (next) => {
                  const saved = await updateApplicationField(app.id, {
                    applied_date: next,
                  });
                  setApp(saved);
                }}
                placeholder="Set the applied date"
                renderRead={(v) => (
                  <span
                    className="mono"
                    style={{
                      fontSize: 13,
                      color: v ? 'var(--text)' : 'var(--text-4)',
                    }}
                  >
                    {v || '—'}
                  </span>
                )}
              />
              <InlineEditField
                kind="text"
                label="Resume variant"
                value={app.resume_variant}
                onCommit={async (next) => {
                  const saved = await updateApplicationField(app.id, {
                    resume_variant: next,
                  });
                  setApp(saved);
                }}
                placeholder="main / AI / staff …"
              />
              <InlineEditField
                kind="url"
                label="Posting"
                value={app.url}
                onCommit={async (next) => {
                  const saved = await updateApplicationField(app.id, {
                    url: next,
                  });
                  setApp(saved);
                }}
                placeholder="https://…"
                renderRead={(v) =>
                  v ? (
                    <a
                      href={v}
                      target="_blank"
                      rel="noreferrer"
                      className="mono truncate"
                      style={{
                        color: 'var(--accent)',
                        fontSize: 12,
                        textDecoration: 'none',
                        maxWidth: '100%',
                        display: 'inline-block',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      {prettyUrl(v)}
                    </a>
                  ) : (
                    <span
                      className="mono"
                      style={{
                        fontSize: 12,
                        color: 'var(--text-4)',
                        fontStyle: 'italic',
                      }}
                    >
                      No posting URL
                    </span>
                  )
                }
              />
            </div>
          </div>

          <div className="card p-6">
            <InlineEditField
              kind="multiline"
              label="Notes"
              value={app.notes}
              onCommit={async (next) => {
                const saved = await updateApplicationField(app.id, {
                  notes: next,
                });
                setApp(saved);
              }}
              placeholder="Anything you want to remember about this role."
              renderRead={(v) =>
                v.trim() ? (
                  <InlineMarkdown
                    as="div"
                    text={v}
                    style={{
                      fontSize: 13.5,
                      color: 'var(--text-2)',
                      lineHeight: 1.65,
                      whiteSpace: 'pre-wrap',
                    }}
                  />
                ) : (
                  <span
                    style={{
                      fontSize: 13,
                      color: 'var(--text-4)',
                      fontStyle: 'italic',
                    }}
                  >
                    Click to add notes.
                  </span>
                )
              }
            />
          </div>
        </div>

        <div className="card p-6">
          <InlineEditField
            kind="multiline"
            label="Job description"
            value={app.job_description}
            onCommit={async (next) => {
              const saved = await updateApplicationField(app.id, {
                job_description: next,
              });
              setApp(saved);
            }}
            placeholder="Paste the role description so prep anchors to the actual asks."
            renderRead={(v) =>
              v.trim() ? (
                <InlineMarkdown
                  as="div"
                  text={v}
                  style={{
                    fontSize: 14,
                    color: 'var(--text-2)',
                    lineHeight: 1.7,
                    whiteSpace: 'pre-wrap',
                  }}
                />
              ) : (
                <span
                  style={{
                    fontSize: 13,
                    color: 'var(--text-4)',
                    fontStyle: 'italic',
                  }}
                >
                  No job description on file. Click to add.
                </span>
              )
            }
          />
        </div>

          <div className="card p-6">
            <div className="eyebrow mb-3">Rounds &amp; loops</div>
            {rounds.length === 0 ? (
              <div
                style={{
                  fontSize: 13,
                  color: 'var(--text-4)',
                  lineHeight: 1.55,
                  fontStyle: 'italic',
                  marginBottom: 14,
                }}
              >
                No rounds tracked yet. Add the first one below.
              </div>
            ) : (
              <div style={{ marginBottom: 14 }}>
                <RoundsList
                  rounds={rounds}
                  onUpdated={(next) =>
                    setRounds((prev) =>
                      prev.map((r) => (r.id === next.id ? next : r)),
                    )
                  }
                  onDeleted={(id) =>
                    setRounds((prev) => prev.filter((r) => r.id !== id))
                  }
                />
              </div>
            )}
            <InlineAddRound
              applicationId={app.id}
              existingLoopLabels={existingLoopLabels}
              onCreated={(round) => setRounds((prev) => [...prev, round])}
            />
          </div>
      </div>
    </PageShell>
  );
}

/**
 * Compact status picker that sits in the header chrome next to the
 * Tailor button. Trigger is a colored pill matching the current
 * status; click drops the themed Select popover with all 5 options.
 * We compute the popover ourselves rather than reusing shell/Select
 * because the trigger has its own pill aesthetic — but we share the
 * same outside-click / Escape semantics.
 */
function StatusSwitch({
  status,
  saving,
  onChange,
}: {
  status: string;
  saving: boolean;
  onChange: (next: string) => void;
}) {
  const c = STATUS_COLORS[status] ?? STATUS_COLORS.Applied;
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function onDoc(e: MouseEvent) {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        e.preventDefault();
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onDoc);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDoc);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  return (
    <div ref={wrapRef} style={{ position: 'relative' }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        disabled={saving}
        aria-label="Application status"
        aria-haspopup="listbox"
        aria-expanded={open}
        className="inline-flex items-center"
        style={{
          gap: 6,
          padding: '6px 10px 6px 12px',
          borderRadius: 999,
          background: c.bg,
          color: c.fg,
          border: 0,
          fontSize: 12,
          fontWeight: 600,
          cursor: saving ? 'wait' : 'pointer',
          opacity: saving ? 0.7 : 1,
        }}
      >
        <span
          aria-hidden="true"
          style={{
            width: 6,
            height: 6,
            borderRadius: 999,
            background: 'currentColor',
          }}
        />
        <span style={{ minWidth: 60 }}>{status}</span>
        <ChevronDown size={12} strokeWidth={2} aria-hidden="true" />
      </button>
      {open && (
        <ul
          role="listbox"
          aria-label="Application status"
          style={{
            position: 'absolute',
            top: 'calc(100% + 6px)',
            right: 0,
            zIndex: 30,
            margin: 0,
            padding: 4,
            listStyle: 'none',
            background: 'var(--bg-elev)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            boxShadow: 'var(--shadow-elev)',
            minWidth: 160,
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
          }}
        >
          {STATUS_OPTIONS.map((opt) => {
            const oc = STATUS_COLORS[opt] ?? STATUS_COLORS.Applied;
            const active = opt === status;
            return (
              <li key={opt} role="option" aria-selected={active}>
                <button
                  type="button"
                  onClick={() => {
                    onChange(opt);
                    setOpen(false);
                  }}
                  className="flex items-center justify-between w-full"
                  style={{
                    padding: '6px 10px',
                    background: active ? 'var(--bg-sunken)' : 'transparent',
                    border: 0,
                    borderRadius: 'var(--radius)',
                    color: 'var(--text)',
                    fontSize: 12.5,
                    cursor: 'pointer',
                    gap: 8,
                  }}
                  onMouseEnter={(e) => {
                    if (!active) e.currentTarget.style.background = 'var(--bg-sunken)';
                  }}
                  onMouseLeave={(e) => {
                    if (!active) e.currentTarget.style.background = 'transparent';
                  }}
                >
                  <span className="inline-flex items-center" style={{ gap: 8 }}>
                    <span
                      aria-hidden="true"
                      style={{
                        width: 6,
                        height: 6,
                        borderRadius: 999,
                        background: oc.fg,
                      }}
                    />
                    {opt}
                  </span>
                  {active && (
                    <Check size={12} strokeWidth={2.2} color={oc.fg} aria-hidden="true" />
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// Tailor entry: hands the user off to the Studio with the picked
// master resume + this Application pre-anchored. We keep the picker
// inline (no modal) — most users have a small number of resumes, and
// a dropdown is faster than a multi-step dialog.
function TailorButton({ applicationId }: { applicationId: string }) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [resumes, setResumes] = useState<{ id: string; slug: string; name: string }[]>(
    [],
  );
  const [loading, setLoading] = useState(false);

  const onClick = async () => {
    if (!open) {
      setLoading(true);
      try {
        const items = await listResumes();
        if (items.length === 0) {
          // No master to tailor — drop them on the Resumes page so
          // they can create one.
          navigate('/resumes');
          return;
        }
        if (items.length === 1) {
          // Only one — skip the menu entirely.
          navigate(`/resumes/${items[0].slug}?app=${applicationId}&tab=tailor`);
          return;
        }
        setResumes(items.map((r) => ({ id: r.id, slug: r.slug, name: r.name })));
        setOpen(true);
      } finally {
        setLoading(false);
      }
    } else {
      setOpen(false);
    }
  };

  return (
    <div style={{ position: 'relative' }}>
      <button
        type="button"
        onClick={onClick}
        disabled={loading}
        className="inline-flex items-center gap-1.5"
        style={{
          padding: '8px 12px',
          borderRadius: 'var(--radius)',
          border: 0,
          background: 'transparent',
          boxShadow: 'inset 0 0 0 1px var(--border-strong)',
          color: 'var(--text-2)',
          fontSize: 12.5,
          fontWeight: 500,
          cursor: loading ? 'wait' : 'pointer',
        }}
        title="Rewrite a resume to match this job description"
      >
        <Wand2 size={13} strokeWidth={1.7} />
        Tailor resume
      </button>
      {open && (
        <div
          role="menu"
          onMouseLeave={() => setOpen(false)}
          className="card"
          style={{
            position: 'absolute',
            right: 0,
            top: 'calc(100% + 4px)',
            minWidth: 240,
            padding: 4,
            display: 'flex',
            flexDirection: 'column',
            gap: 2,
            zIndex: 10,
          }}
        >
          <div
            className="eyebrow"
            style={{ fontSize: 9, padding: '6px 10px 4px', color: 'var(--text-4)' }}
          >
            Pick a master resume
          </div>
          {resumes.map((r) => (
            <button
              key={r.id}
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                navigate(`/resumes/${r.slug}?app=${applicationId}&tab=tailor`);
              }}
              style={{
                textAlign: 'left',
                background: 'transparent',
                border: 0,
                padding: '7px 10px',
                borderRadius: 4,
                cursor: 'pointer',
                color: 'var(--text)',
                fontSize: 12.5,
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--bg-sunken)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
              }}
            >
              {r.name}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Discreet "Created · Updated" caption rendered next to the Company
 * eyebrow at the top-right of the card. Both timestamps used to live
 * in their own "Activity" card, which earned too much real estate for
 * what's essentially row-metadata.
 */
function Timestamps({
  createdAt,
  updatedAt,
}: {
  createdAt?: string;
  updatedAt?: string;
}) {
  const fmt = (iso?: string) =>
    iso
      ? new Date(iso).toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        })
      : null;
  const created = fmt(createdAt);
  const updated = fmt(updatedAt);
  if (!created && !updated) return null;
  return (
    <div
      className="mono"
      style={{
        fontSize: 10.5,
        color: 'var(--text-4)',
        letterSpacing: '0.04em',
        whiteSpace: 'nowrap',
        textAlign: 'right',
      }}
    >
      {created && <span>Created {created}</span>}
      {created && updated && (
        <span style={{ margin: '0 8px', color: 'var(--text-4)' }}>·</span>
      )}
      {updated && <span>Updated {updated}</span>}
    </div>
  );
}

function prettyUrl(url: string) {
  try {
    const u = new URL(url);
    return u.host + u.pathname.replace(/\/$/, '');
  } catch {
    return url;
  }
}
