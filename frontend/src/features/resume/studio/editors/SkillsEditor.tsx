import type { ResumeData } from '../../types';
import { moveItem, newSkillGroup, patchById, removeById } from '../../utils';
import { AddButton, Field, ItemCard, StringList, TextInput } from './parts';

type Props = {
  data: ResumeData;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
};

export default function SkillsEditor({ data, setData }: Props) {
  const list = data.skills;
  const add = (category = '') =>
    setData((prev) => ({ ...prev, skills: [...prev.skills, newSkillGroup(category)] }));
  const update = (id: string, patch: Partial<ResumeData['skills'][number]>) =>
    setData((prev) => ({ ...prev, skills: patchById(prev.skills, id, patch) }));
  const remove = (id: string) =>
    setData((prev) => ({ ...prev, skills: removeById(prev.skills, id) }));
  const move = (i: number, j: number) =>
    setData((prev) => ({ ...prev, skills: moveItem(prev.skills, i, j) }));

  const hasAtsCategory = list.some((sk) => /^\s*ats\s*keywords\s*$/i.test(sk.category));

  return (
    <div className="flex flex-col gap-2">
      {list.map((sk, i) => (
        <ItemCard
          key={sk.id}
          title={sk.category || `Group ${i + 1}`}
          index={i}
          total={list.length}
          onMoveUp={() => move(i, i - 1)}
          onMoveDown={() => move(i, i + 1)}
          onRemove={() => remove(sk.id)}
        >
          <Field label="Category">
            <TextInput
              value={sk.category}
              onChange={(v) => update(sk.id, { category: v })}
              placeholder="Languages / Frameworks / Cloud / Tools"
            />
          </Field>
          <Field label="Items">
            <StringList
              values={sk.items}
              onChange={(next) => update(sk.id, { items: next })}
              placeholder="Python"
            />
          </Field>
        </ItemCard>
      ))}
      <div className="flex flex-wrap gap-2">
        <AddButton onClick={() => add()} label="Add skill group" />
        {!hasAtsCategory && (
          <AddButton onClick={() => add('ATS Keywords')} label="Add ATS Keywords" />
        )}
      </div>
    </div>
  );
}
