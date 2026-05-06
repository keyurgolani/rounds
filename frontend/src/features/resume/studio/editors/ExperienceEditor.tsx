import { useState } from 'react';
import type { ResumeData } from '../../types';
import { moveItem, newExperience, patchById, removeById } from '../../utils';
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

type Props = {
  data: ResumeData;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
};

export default function ExperienceEditor({ data, setData }: Props) {
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

  const add = () =>
    setData((prev) => ({ ...prev, experience: [...prev.experience, newExperience()] }));
  const update = (id: string, patch: Partial<ResumeData['experience'][number]>) =>
    setData((prev) => ({ ...prev, experience: patchById(prev.experience, id, patch) }));
  const remove = (id: string) =>
    setData((prev) => ({ ...prev, experience: removeById(prev.experience, id) }));
  const move = (i: number, j: number) =>
    setData((prev) => ({ ...prev, experience: moveItem(prev.experience, i, j) }));

  return (
    <div className="flex flex-col gap-2">
      {list.map((e, i) => (
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
                onChange={(next) => update(e.id, { highlights: next })}
                onStreamingChange={(b) => setEnh(`${e.id}.highlights`, b)}
              />
            }
          >
            <StringList
              values={e.highlights}
              onChange={(next) => update(e.id, { highlights: next })}
              placeholder="Led migration of X to Y, cutting Z by 40%."
              multiline
              library
              disabled={isEnh(`${e.id}.highlights`)}
              improveContext={{ position: e.position, company: e.company }}
              fieldBase={`experience[${e.id}].highlights`}
            />
          </Field>
        </ItemCard>
      ))}
      <AddButton onClick={add} label="Add experience" />
    </div>
  );
}
