import { useState } from 'react';
import type { Project, ResumeData } from '../../types';
import { moveItem, newProject, patchById, removeById } from '../../utils';
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

type Props = {
  data: ResumeData;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
};

export default function ProjectsEditor({ data, setData }: Props) {
  const list = data.projects;
  const [ghOpen, setGhOpen] = useState(false);
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
  const add = () => setData((prev) => ({ ...prev, projects: [...prev.projects, newProject()] }));
  const update = (id: string, patch: Partial<ResumeData['projects'][number]>) =>
    setData((prev) => ({ ...prev, projects: patchById(prev.projects, id, patch) }));
  const remove = (id: string) =>
    setData((prev) => ({ ...prev, projects: removeById(prev.projects, id) }));
  const move = (i: number, j: number) =>
    setData((prev) => ({ ...prev, projects: moveItem(prev.projects, i, j) }));
  const importGithub = (projects: Project[]) =>
    setData((prev) => ({ ...prev, projects: [...prev.projects, ...projects] }));

  return (
    <div className="flex flex-col gap-2">
      {list.map((pr, i) => (
        <ItemCard
          key={pr.id}
          title={pr.name || `Project ${i + 1}`}
          index={i}
          total={list.length}
          onMoveUp={() => move(i, i - 1)}
          onMoveDown={() => move(i, i + 1)}
          onRemove={() => remove(pr.id)}
        >
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
                onChange={(next) => update(pr.id, { highlights: next })}
                onStreamingChange={(b) => setEnh(`${pr.id}.highlights`, b)}
              />
            }
          >
            <StringList
              values={pr.highlights}
              onChange={(next) => update(pr.id, { highlights: next })}
              placeholder="Adopted by 2k+ users in the first 3 months."
              multiline
              library
              disabled={isEnh(`${pr.id}.highlights`)}
              improveContext={{ position: pr.name, company: '' }}
              fieldBase={`projects[${pr.id}].highlights`}
            />
          </Field>
        </ItemCard>
      ))}
      <div className="flex items-center gap-2 flex-wrap">
        <AddButton onClick={add} label="Add project" />
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
      <GithubImportDialog
        open={ghOpen}
        onClose={() => setGhOpen(false)}
        onImport={importGithub}
      />
    </div>
  );
}
