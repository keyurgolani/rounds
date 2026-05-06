import type { ResumeData } from '../../types';
import { moveItem, newProfile, patchById, removeById } from '../../utils';
import { AddButton, Field, GridTwo, ItemCard, TextInput } from './parts';

type Props = {
  data: ResumeData;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
};

export default function ProfilesEditor({ data, setData }: Props) {
  const list = data.profiles;
  const add = () => setData((prev) => ({ ...prev, profiles: [...prev.profiles, newProfile()] }));
  const update = (id: string, patch: Partial<ResumeData['profiles'][number]>) =>
    setData((prev) => ({ ...prev, profiles: patchById(prev.profiles, id, patch) }));
  const remove = (id: string) =>
    setData((prev) => ({ ...prev, profiles: removeById(prev.profiles, id) }));
  const move = (i: number, j: number) =>
    setData((prev) => ({ ...prev, profiles: moveItem(prev.profiles, i, j) }));

  return (
    <div className="flex flex-col gap-2">
      {list.map((pf, i) => (
        <ItemCard
          key={pf.id}
          title={pf.network || `Profile ${i + 1}`}
          index={i}
          total={list.length}
          onMoveUp={() => move(i, i - 1)}
          onMoveDown={() => move(i, i + 1)}
          onRemove={() => remove(pf.id)}
        >
          <GridTwo>
            <Field label="Network">
              <TextInput
                value={pf.network}
                onChange={(v) => update(pf.id, { network: v })}
                placeholder="LinkedIn / Stack Overflow / Twitter"
              />
            </Field>
            <Field label="Username">
              <TextInput
                value={pf.username ?? ''}
                onChange={(v) => update(pf.id, { username: v })}
                placeholder="janedoe"
              />
            </Field>
            <Field label="URL" span={2}>
              <TextInput
                type="url"
                value={pf.url ?? ''}
                onChange={(v) => update(pf.id, { url: v })}
                placeholder="https://…"
              />
            </Field>
          </GridTwo>
        </ItemCard>
      ))}
      <AddButton onClick={add} label="Add profile" />
    </div>
  );
}
