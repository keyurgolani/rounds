import { useState } from 'react';
import type { Project, ResumeData } from '../../types';
import { moveItem, newProject, patchById, removeById } from '../../utils';
import { emptyEntryLink, type EntryLink, type ResumeLinks } from '../../links/types';
import { projectHeader, projectHeaderBack } from '../../links/resolve';
import { reconcileHighlightLinks } from '../../links/maintain';
import type { LibraryData } from '../../links/library';
import { updateProject, updateBullet } from '../../../../experience/experienceApi';
import LibraryPicker from '../../links/LibraryPicker';
import GithubImportDialog from './GithubImportDialog';
import ImproveButton, { ListImproveButton } from './ImproveButton';
import {
  AddButton,
  Field,
  GridTwo,
  ItemCard,
  StringList,
  TextArea,
  TextInput,
} from './parts';

// Library-backed header keys — changing any of these on a linked entry
// flips headerEdited so the "linked / edited" chip updates.
// url/github are resume-only and never library-backed, so they're excluded.
const HEADER_KEYS: Array<keyof ResumeData['projects'][number]> = [
  'name',
  'description',
  'technologies',
  'startDate',
  'endDate',
];

type Props = {
  data: ResumeData;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
  links: ResumeLinks;
  setLinks: (next: ResumeLinks | ((prev: ResumeLinks) => ResumeLinks)) => void;
  lib: LibraryData | null;
};

export default function ProjectsEditor({ data, setData, links, setLinks, lib }: Props) {
  const list = data.projects;
  const [ghOpen, setGhOpen] = useState(false);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [enhKeys, setEnhKeys] = useState<Set<string>>(new Set());
  const isEnh = (k: string) => enhKeys.has(k);
  const setEnh = (k: string, on: boolean) => {
    setEnhKeys((prev) => {
      const next = new Set(prev);
      if (on) next.add(k);
      else next.delete(k);
      return next;
    });
  };

  // --- link helpers -------------------------------------------------------

  const getLink = (id: string): EntryLink =>
    links.projects[id] ?? emptyEntryLink();

  const setEntryLink = (id: string, next: EntryLink) =>
    setLinks((prev) => ({
      ...prev,
      projects: { ...prev.projects, [id]: next },
    }));

  // --- CRUD helpers -------------------------------------------------------

  const add = () => {
    const entry = newProject();
    setData((prev) => ({ ...prev, projects: [...prev.projects, entry] }));
    setEntryLink(entry.id, emptyEntryLink());
  };

  const addFromLibrary = (sel: { ref: string; bulletIds: string[]; bulletTitles: string[] }) => {
    if (!lib) return;
    const proj = lib.projects[sel.ref];
    if (!proj) return;
    const entry = { ...newProject(), ...projectHeader(proj), highlights: sel.bulletTitles };
    setData((prev) => ({ ...prev, projects: [...prev.projects, entry] }));
    setEntryLink(entry.id, {
      ref: sel.ref,
      headerEdited: false,
      bulletRefs: [...sel.bulletIds],
      bulletEdited: sel.bulletIds.map(() => false),
    });
  };

  const update = (id: string, patch: Partial<ResumeData['projects'][number]>) => {
    setData((prev) => ({ ...prev, projects: patchById(prev.projects, id, patch) }));
    // If any library-backed header keys changed and the entry has a ref,
    // flip headerEdited.
    const link = getLink(id);
    if (link.ref !== null && !link.headerEdited) {
      const isHeaderChange = (Object.keys(patch) as Array<keyof typeof patch>).some((k) =>
        HEADER_KEYS.includes(k as keyof ResumeData['projects'][number]),
      );
      if (isHeaderChange) {
        setEntryLink(id, { ...link, headerEdited: true });
      }
    }
  };

  const remove = (id: string) => {
    setData((prev) => ({ ...prev, projects: removeById(prev.projects, id) }));
    setLinks((prev) => {
      const projs = { ...prev.projects };
      delete projs[id];
      return { ...prev, projects: projs };
    });
  };

  const move = (i: number, j: number) =>
    setData((prev) => ({ ...prev, projects: moveItem(prev.projects, i, j) }));

  const importGithub = (projects: Project[]) =>
    setData((prev) => ({ ...prev, projects: [...prev.projects, ...projects] }));

  return (
    <div className="flex flex-col gap-2">
      {list.map((pr, i) => {
        const link = getLink(pr.id);
        return (
          <ItemCard
            key={pr.id}
            title={pr.name || `Project ${i + 1}`}
            index={i}
            total={list.length}
            onMoveUp={() => move(i, i - 1)}
            onMoveDown={() => move(i, i + 1)}
            onRemove={() => remove(pr.id)}
          >
            {/* Library link chip */}
            {link.ref !== null && (
              <HeaderLinkChip
                entryId={pr.id}
                entry={pr}
                link={link}
                lib={lib}
                setEntryLink={setEntryLink}
                update={update}
              />
            )}
            <GridTwo>
              <Field label="Name" span={2}>
                <TextInput
                  value={pr.name}
                  onChange={(v) => update(pr.id, { name: v })}
                  placeholder="Open-source CLI for X"
                />
              </Field>
              <Field label="URL">
                <TextInput
                  type="url"
                  value={pr.url ?? ''}
                  onChange={(v) => update(pr.id, { url: v })}
                  placeholder="https://example.dev"
                />
              </Field>
              <Field label="GitHub">
                <TextInput
                  value={pr.github ?? ''}
                  onChange={(v) => update(pr.id, { github: v })}
                  placeholder="github.com/you/project"
                />
              </Field>
              <Field label="Start (YYYY-MM)">
                <TextInput
                  type="month"
                  value={pr.startDate ?? ''}
                  onChange={(v) => update(pr.id, { startDate: v })}
                />
              </Field>
              <Field label="End (YYYY-MM)">
                <TextInput
                  type="month"
                  value={pr.endDate ?? ''}
                  onChange={(v) => update(pr.id, { endDate: v })}
                />
              </Field>
            </GridTwo>
            <Field label="Tech stack">
              <StringList
                values={pr.technologies}
                onChange={(next) => update(pr.id, { technologies: next })}
                placeholder="Rust"
              />
            </Field>
            <Field
              label="Description"
              loading={isEnh(`${pr.id}.description`)}
              actions={
                <ImproveButton
                  text={pr.description ?? ''}
                  context={{ position: pr.name, company: '' }}
                  field={`projects[${pr.id}].description`}
                  onChange={(v) => update(pr.id, { description: v })}
                  onStreamingChange={(b) => setEnh(`${pr.id}.description`, b)}
                />
              }
            >
              <TextArea
                value={pr.description ?? ''}
                onChange={(v) => update(pr.id, { description: v })}
                placeholder="A one-line description that doubles as a tagline."
                rows={2}
                disabled={isEnh(`${pr.id}.description`)}
              />
            </Field>
            <Field
              label="Highlights"
              loading={isEnh(`${pr.id}.highlights`)}
              actions={
                <ListImproveButton
                  values={pr.highlights}
                  context={{ position: pr.name, company: '' }}
                  field={`projects[${pr.id}].highlights`}
                  onChange={(next) => {
                    setData((prev) => ({ ...prev, projects: patchById(prev.projects, pr.id, { highlights: next }) }));
                    setEntryLink(pr.id, reconcileHighlightLinks(pr.highlights, next, getLink(pr.id)));
                  }}
                  onStreamingChange={(b) => setEnh(`${pr.id}.highlights`, b)}
                />
              }
            >
              <StringList
                values={pr.highlights}
                onChange={(next) => {
                  // Use setData directly to avoid triggering headerEdited for highlights changes
                  setData((prev) => ({ ...prev, projects: patchById(prev.projects, pr.id, { highlights: next }) }));
                }}
                placeholder="Adopted by 2k+ users in the first 3 months."
                multiline
                disabled={isEnh(`${pr.id}.highlights`)}
                improveContext={{ position: pr.name, company: '' }}
                fieldBase={`projects[${pr.id}].highlights`}
                linkRefs={link.bulletRefs}
                linkEdited={link.bulletEdited}
                onLinkChange={(refs, edited) =>
                  setEntryLink(pr.id, { ...link, bulletRefs: refs, bulletEdited: edited })
                }
                renderRowAdornment={(idx) => (
                  <BulletAdornment
                    entryId={pr.id}
                    bulletIndex={idx}
                    highlights={pr.highlights}
                    link={link}
                    lib={lib}
                    setEntryLink={setEntryLink}
                    setData={setData}
                  />
                )}
              />
            </Field>
          </ItemCard>
        );
      })}

      {/* Add buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        <AddButton onClick={add} label="Add project" />
        <AddButton onClick={() => setPickerOpen(true)} label="Add from library" />
        <button
          type="button"
          onClick={() => setGhOpen(true)}
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
          title="Import public repos as project entries"
        >
          <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z" />
          </svg>
          Import from GitHub
        </button>
      </div>

      <LibraryPicker
        kind="project"
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onPick={addFromLibrary}
      />

      <GithubImportDialog
        open={ghOpen}
        onClose={() => setGhOpen(false)}
        onImport={importGithub}
      />
    </div>
  );
}

// ---------------------------------------------------------------------------
// HeaderLinkChip — shown inside each ItemCard when the entry has a library ref
// ---------------------------------------------------------------------------

function HeaderLinkChip({
  entryId,
  entry,
  link,
  lib,
  setEntryLink,
  update,
}: {
  entryId: string;
  entry: ResumeData['projects'][number];
  link: EntryLink;
  lib: LibraryData | null;
  setEntryLink: (id: string, next: EntryLink) => void;
  update: (id: string, patch: Partial<ResumeData['projects'][number]>) => void;
}) {
  const isEdited = link.headerEdited;

  const handleRelink = () => {
    if (!lib || !link.ref) return;
    const proj = lib.projects[link.ref];
    if (!proj) return;
    // Reapply the library header without flipping headerEdited again.
    // We bypass `update()` to avoid the headerEdited side-effect.
    const patch = projectHeader(proj);
    update(entryId, patch as Partial<ResumeData['projects'][number]>);
    // Clear headerEdited after patching
    setEntryLink(entryId, { ...link, headerEdited: false, ref: link.ref });
  };

  const handlePush = async () => {
    if (!lib || !link.ref) return;
    await updateProject(link.ref, projectHeaderBack(entry));
    setEntryLink(entryId, { ...link, headerEdited: false });
  };

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 6,
        fontSize: 11,
        fontFamily: 'var(--font-mono, monospace)',
        color: isEdited ? 'var(--accent)' : 'var(--text-3)',
        flexWrap: 'wrap',
      }}
    >
      <span title={isEdited ? 'Header diverged from library' : 'Linked to library'}>
        {isEdited ? 'header edited' : 'linked'}
      </span>
      {isEdited && lib && (
        <>
          <InlineBtn onClick={handleRelink} title="Relink header from library">
            Relink
          </InlineBtn>
          <InlineBtn onClick={() => void handlePush()} title="Push header changes to library">
            Push
          </InlineBtn>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// BulletAdornment — per-row decoration in the highlights StringList
// ---------------------------------------------------------------------------

function BulletAdornment({
  entryId,
  bulletIndex,
  highlights,
  link,
  lib,
  setEntryLink,
  setData,
}: {
  entryId: string;
  bulletIndex: number;
  highlights: string[];
  link: EntryLink;
  lib: LibraryData | null;
  setEntryLink: (id: string, next: EntryLink) => void;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
}) {
  const ref = link.bulletRefs[bulletIndex] ?? null;
  const edited = link.bulletEdited[bulletIndex] ?? false;

  if (ref === null) return null;

  if (!edited) {
    return (
      <span
        title="Linked to library"
        style={{
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: 'var(--text-4)',
          display: 'inline-block',
          flexShrink: 0,
        }}
      />
    );
  }

  // Edited state
  const handleRelink = () => {
    if (!lib) return;
    const bullet = lib.bullets[ref];
    if (!bullet) return;
    // Restore highlight text from library
    setData((prev) => {
      const projs = prev.projects.map((p) => {
        if (p.id !== entryId) return p;
        const next = p.highlights.slice();
        next[bulletIndex] = bullet.title;
        return { ...p, highlights: next };
      });
      return { ...prev, projects: projs };
    });
    // Clear edited flag
    const newEdited = link.bulletEdited.slice();
    newEdited[bulletIndex] = false;
    setEntryLink(entryId, { ...link, bulletEdited: newEdited });
  };

  const handlePush = async () => {
    if (!lib) return;
    const currentText = highlights[bulletIndex] ?? '';
    await updateBullet(ref, { title: currentText });
    const newEdited = link.bulletEdited.slice();
    newEdited[bulletIndex] = false;
    setEntryLink(entryId, { ...link, bulletEdited: newEdited });
  };

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 4,
        fontSize: 10,
        fontFamily: 'var(--font-mono, monospace)',
        color: 'var(--accent)',
        flexShrink: 0,
      }}
    >
      <span>edited</span>
      {lib && (
        <>
          <InlineBtn onClick={handleRelink} title="Restore from library">
            Relink
          </InlineBtn>
          <InlineBtn onClick={() => void handlePush()} title="Push to library">
            Push
          </InlineBtn>
        </>
      )}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Tiny inline text button
// ---------------------------------------------------------------------------

function InlineBtn({
  children,
  onClick,
  title,
}: {
  children: React.ReactNode;
  onClick: () => void;
  title?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      style={{
        padding: '1px 5px',
        background: 'transparent',
        border: 0,
        boxShadow: 'inset 0 0 0 1px var(--border)',
        borderRadius: 4,
        fontSize: 10,
        fontFamily: 'inherit',
        color: 'var(--accent)',
        cursor: 'pointer',
        lineHeight: 1.4,
      }}
    >
      {children}
    </button>
  );
}
