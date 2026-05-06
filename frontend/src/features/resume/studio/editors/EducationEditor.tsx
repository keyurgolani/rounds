import { useState } from 'react';
import type { ResumeData } from '../../types';
import { moveItem, newEducation, patchById, removeById } from '../../utils';
import ImproveButton from './ImproveButton';
import { AddButton, Field, GridTwo, ItemCard, TextArea, TextInput } from './parts';

type Props = {
  data: ResumeData;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
};

export default function EducationEditor({ data, setData }: Props) {
  const list = data.education;
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
  const add = () => setData((prev) => ({ ...prev, education: [...prev.education, newEducation()] }));
  const update = (id: string, patch: Partial<ResumeData['education'][number]>) =>
    setData((prev) => ({ ...prev, education: patchById(prev.education, id, patch) }));
  const remove = (id: string) =>
    setData((prev) => ({ ...prev, education: removeById(prev.education, id) }));
  const move = (i: number, j: number) =>
    setData((prev) => ({ ...prev, education: moveItem(prev.education, i, j) }));

  return (
    <div className="flex flex-col gap-2">
      {list.map((ed, i) => (
        <ItemCard
          key={ed.id}
          title={ed.institution || `Education ${i + 1}`}
          index={i}
          total={list.length}
          onMoveUp={() => move(i, i - 1)}
          onMoveDown={() => move(i, i + 1)}
          onRemove={() => remove(ed.id)}
        >
          <GridTwo>
            <Field label="Institution">
              <TextInput
                value={ed.institution}
                onChange={(v) => update(ed.id, { institution: v })}
                placeholder="Stanford University"
              />
            </Field>
            <Field label="Location">
              <TextInput
                value={ed.location ?? ''}
                onChange={(v) => update(ed.id, { location: v })}
                placeholder="Stanford, CA"
              />
            </Field>
            <Field label="Degree">
              <TextInput
                value={ed.degree ?? ''}
                onChange={(v) => update(ed.id, { degree: v })}
                placeholder="B.S."
              />
            </Field>
            <Field label="Field">
              <TextInput
                value={ed.field ?? ''}
                onChange={(v) => update(ed.id, { field: v })}
                placeholder="Computer Science"
              />
            </Field>
            <Field label="GPA">
              <TextInput
                value={ed.gpa ?? ''}
                onChange={(v) => update(ed.id, { gpa: v })}
                placeholder="3.8 / 4.0"
              />
            </Field>
            <Field label=" ">
              <span style={{ fontSize: 11, color: 'var(--text-4)' }}>
                Use the right side for honors / coursework if relevant.
              </span>
            </Field>
            <Field label="Start (YYYY-MM)">
              <TextInput
                type="month"
                value={ed.startDate ?? ''}
                onChange={(v) => update(ed.id, { startDate: v })}
              />
            </Field>
            <Field label="End (YYYY-MM)">
              <TextInput
                type="month"
                value={ed.endDate ?? ''}
                onChange={(v) => update(ed.id, { endDate: v })}
              />
            </Field>
          </GridTwo>
          <Field
            label="Description / honors / coursework"
            loading={isEnh(`${ed.id}.description`)}
            actions={
              <ImproveButton
                text={ed.description ?? ''}
                context={{ position: ed.degree, company: ed.institution }}
                field={`education[${ed.id}].description`}
                onChange={(v) => update(ed.id, { description: v })}
                onStreamingChange={(b) => setEnh(`${ed.id}.description`, b)}
              />
            }
          >
            <TextArea
              value={ed.description ?? ''}
              onChange={(v) => update(ed.id, { description: v })}
              placeholder="Honors: Phi Beta Kappa. Coursework: Distributed Systems, ML…"
              rows={2}
              disabled={isEnh(`${ed.id}.description`)}
            />
          </Field>
        </ItemCard>
      ))}
      <AddButton onClick={add} label="Add education" />
    </div>
  );
}
