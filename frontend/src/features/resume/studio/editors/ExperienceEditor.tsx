import { useState } from 'react';
import type { ResumeData } from '../../types';
import { moveItem, newExperience, patchById, removeById } from '../../utils';
import { emptyEntryLink, type EntryLink, type ResumeLinks } from '../../links/types';
import { jobHeader, jobHeaderBack } from '../../links/resolve';
import { reconcileHighlightLinks } from '../../links/maintain';
import type { LibraryData } from '../../links/library';
import { updateJob, updateBullet } from '../../../../experience/experienceApi';
import LibraryPicker from '../../links/LibraryPicker';
import ImproveButton, { ListImproveButton } from './ImproveButton';
import {
  AddButton,
  Field,
  GridTwo,
  ItemCard,
  StringList,
  TextArea,
  TextInput,
  ToggleCheckbox,
} from './parts';

// Library-backed header keys — changing any of these on a linked entry
// flips headerEdited so the "linked / edited" chip updates.
const HEADER_KEYS: Array<keyof ResumeData['experience'][number]> = [
  'company',
  'position',
  'location',
  'startDate',
  'endDate',
  'current',
  'description',
];

type Props = {
  data: ResumeData;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
  links: ResumeLinks;
  setLinks: (next: ResumeLinks | ((prev: ResumeLinks) => ResumeLinks)) => void;
  lib: LibraryData | null;
};

export default function ExperienceEditor({ data, setData, links, setLinks, lib }: Props) {
  const list = data.experience;

  // Tracks which (item + field) pairs are currently being AI-improved.
  // Keying by `${id}.${field}` so each row's description / highlights
  // can run an enhancement independently.
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

  // Library picker state
  const [pickerOpen, setPickerOpen] = useState(false);

  // --- link helpers -------------------------------------------------------

  const getLink = (id: string): EntryLink =>
    links.experience[id] ?? emptyEntryLink();

  const setEntryLink = (id: string, next: EntryLink) =>
    setLinks((prev) => ({
      ...prev,
      experience: { ...prev.experience, [id]: next },
    }));

  // --- CRUD helpers -------------------------------------------------------

  const add = () => {
    const entry = newExperience();
    setData((prev) => ({ ...prev, experience: [...prev.experience, entry] }));
    setEntryLink(entry.id, emptyEntryLink());
  };

  const addFromLibrary = (sel: { ref: string; bulletIds: string[]; bulletTitles: string[] }) => {
    if (!lib) return;
    const job = lib.jobs[sel.ref];
    if (!job) return;
    const entry = { ...newExperience(), ...jobHeader(job), highlights: sel.bulletTitles };
    setData((prev) => ({ ...prev, experience: [...prev.experience, entry] }));
    setEntryLink(entry.id, {
      ref: sel.ref,
      headerEdited: false,
      bulletRefs: [...sel.bulletIds],
      bulletEdited: sel.bulletIds.map(() => false),
    });
  };

  const update = (id: string, patch: Partial<ResumeData['experience'][number]>) => {
    setData((prev) => ({ ...prev, experience: patchById(prev.experience, id, patch) }));
    // If any library-backed header keys changed and the entry has a ref,
    // flip headerEdited.
    const link = getLink(id);
    if (link.ref !== null && !link.headerEdited) {
      const isHeaderChange = (Object.keys(patch) as Array<keyof typeof patch>).some((k) =>
        HEADER_KEYS.includes(k as keyof ResumeData['experience'][number]),
      );
      if (isHeaderChange) {
        setEntryLink(id, { ...link, headerEdited: true });
      }
    }
  };

  const remove = (id: string) => {
    setData((prev) => ({ ...prev, experience: removeById(prev.experience, id) }));
    setLinks((prev) => {
      const ex = { ...prev.experience };
      delete ex[id];
      return { ...prev, experience: ex };
    });
  };

  const move = (i: number, j: number) =>
    setData((prev) => ({ ...prev, experience: moveItem(prev.experience, i, j) }));

  return (
    <div className="flex flex-col gap-2">
      {list.map((e, i) => {
        const link = getLink(e.id);
        return (
          <ItemCard
            key={e.id}
            title={
              e.position && e.company
                ? `${e.position} · ${e.company}`
                : e.company || e.position || 'New role'
            }
            index={i}
            total={list.length}
            onMoveUp={() => move(i, i - 1)}
            onMoveDown={() => move(i, i + 1)}
            onRemove={() => remove(e.id)}
          >
            {/* Library link chip */}
            {link.ref !== null && (
              <HeaderLinkChip
                entryId={e.id}
                entry={e}
                link={link}
                lib={lib}
                setEntryLink={setEntryLink}
                update={update}
              />
            )}
            <GridTwo>
              <Field label="Position">
                <TextInput
                  value={e.position}
                  onChange={(v) => update(e.id, { position: v })}
                  placeholder="Senior Software Engineer"
                />
              </Field>
              <Field label="Company">
                <TextInput
                  value={e.company}
                  onChange={(v) => update(e.id, { company: v })}
                  placeholder="Acme Inc."
                />
              </Field>
              <Field label="Location">
                <TextInput
                  value={e.location ?? ''}
                  onChange={(v) => update(e.id, { location: v })}
                  placeholder="Remote / San Francisco"
                />
              </Field>
              <Field label="Current?">
                <ToggleCheckbox
                  checked={Boolean(e.current)}
                  onChange={(v) => update(e.id, { current: v, endDate: v ? '' : e.endDate })}
                  label="I still work here"
                />
              </Field>
              <Field label="Start (YYYY-MM)">
                <TextInput
                  type="month"
                  value={e.startDate ?? ''}
                  onChange={(v) => update(e.id, { startDate: v })}
                />
              </Field>
              <Field label="End (YYYY-MM)">
                <TextInput
                  type="month"
                  value={e.current ? '' : (e.endDate ?? '')}
                  onChange={(v) => update(e.id, { endDate: v })}
                  ariaLabel="End date"
                  disabled={Boolean(e.current)}
                />
              </Field>
            </GridTwo>
            <Field
              label="Description (optional)"
              loading={isEnh(`${e.id}.description`)}
              actions={
                <ImproveButton
                  text={e.description ?? ''}
                  context={{ position: e.position, company: e.company }}
                  field={`experience[${e.id}].description`}
                  onChange={(v) => update(e.id, { description: v })}
                  onStreamingChange={(b) => setEnh(`${e.id}.description`, b)}
                />
              }
            >
              <TextArea
                value={e.description ?? ''}
                onChange={(v) => update(e.id, { description: v })}
                placeholder="What the team did and your role in it."
                rows={2}
                disabled={isEnh(`${e.id}.description`)}
              />
            </Field>
            <Field
              label="Highlights / bullets"
              loading={isEnh(`${e.id}.highlights`)}
              actions={
                <ListImproveButton
                  values={e.highlights}
                  context={{ position: e.position, company: e.company }}
                  field={`experience[${e.id}].highlights`}
                  onChange={(next) => {
                    setData((prev) => ({ ...prev, experience: patchById(prev.experience, e.id, { highlights: next }) }));
                    setEntryLink(e.id, reconcileHighlightLinks(e.highlights, next, getLink(e.id)));
                  }}
                  onStreamingChange={(b) => setEnh(`${e.id}.highlights`, b)}
                />
              }
            >
              <StringList
                values={e.highlights}
                onChange={(next) => {
                  // Use setData directly to avoid triggering headerEdited for highlights changes
                  setData((prev) => ({ ...prev, experience: patchById(prev.experience, e.id, { highlights: next }) }));
                }}
                placeholder="Led migration of X to Y, cutting Z by 40%."
                multiline
                disabled={isEnh(`${e.id}.highlights`)}
                improveContext={{ position: e.position, company: e.company }}
                fieldBase={`experience[${e.id}].highlights`}
                linkRefs={link.bulletRefs}
                linkEdited={link.bulletEdited}
                onLinkChange={(refs, edited) =>
                  setEntryLink(e.id, { ...link, bulletRefs: refs, bulletEdited: edited })
                }
                renderRowAdornment={(idx) => (
                  <BulletAdornment
                    entryId={e.id}
                    bulletIndex={idx}
                    highlights={e.highlights}
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
        <AddButton onClick={add} label="Add experience" />
        <AddButton onClick={() => setPickerOpen(true)} label="Add from library" />
      </div>

      <LibraryPicker
        kind="job"
        open={pickerOpen}
        onClose={() => setPickerOpen(false)}
        onPick={addFromLibrary}
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
  entry: ResumeData['experience'][number];
  link: EntryLink;
  lib: LibraryData | null;
  setEntryLink: (id: string, next: EntryLink) => void;
  update: (id: string, patch: Partial<ResumeData['experience'][number]>) => void;
}) {
  const isEdited = link.headerEdited;

  const handleRelink = () => {
    if (!lib || !link.ref) return;
    const job = lib.jobs[link.ref];
    if (!job) return;
    // Reapply the library header without flipping headerEdited again.
    // We bypass `update()` to avoid the headerEdited side-effect.
    const patch = jobHeader(job);
    // Directly call the parent update but then immediately clear headerEdited
    update(entryId, patch as Partial<ResumeData['experience'][number]>);
    // Clear headerEdited after patching (update may have set it again,
    // so we schedule a state update to clear it)
    setEntryLink(entryId, { ...link, headerEdited: false, ref: link.ref });
  };

  const handlePush = async () => {
    if (!lib || !link.ref) return;
    await updateJob(link.ref, jobHeaderBack(entry));
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
      const exp = prev.experience.map((e) => {
        if (e.id !== entryId) return e;
        const next = e.highlights.slice();
        next[bulletIndex] = bullet.title;
        return { ...e, highlights: next };
      });
      return { ...prev, experience: exp };
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
