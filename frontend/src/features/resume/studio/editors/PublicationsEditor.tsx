import { useState } from 'react';
import type { ResumeData } from '../../types';
import { moveItem, newPublication, patchById, removeById } from '../../utils';
import ImproveButton from './ImproveButton';
import { AddButton, Field, GridTwo, ItemCard, TextArea, TextInput } from './parts';

type Props = {
  data: ResumeData;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
};

export default function PublicationsEditor({ data, setData }: Props) {
  const list = data.publications;
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
    setData((prev) => ({ ...prev, publications: [...prev.publications, newPublication()] }));
  const update = (id: string, patch: Partial<ResumeData['publications'][number]>) =>
    setData((prev) => ({ ...prev, publications: patchById(prev.publications, id, patch) }));
  const remove = (id: string) =>
    setData((prev) => ({ ...prev, publications: removeById(prev.publications, id) }));
  const move = (i: number, j: number) =>
    setData((prev) => ({ ...prev, publications: moveItem(prev.publications, i, j) }));

  return (
    <div className="flex flex-col gap-2">
      {list.map((pb, i) => (
        <ItemCard
          key={pb.id}
          title={pb.title || `Publication ${i + 1}`}
          index={i}
          total={list.length}
          onMoveUp={() => move(i, i - 1)}
          onMoveDown={() => move(i, i + 1)}
          onRemove={() => remove(pb.id)}
        >
          <Field label="Title">
            <TextInput
              value={pb.title}
              onChange={(v) => update(pb.id, { title: v })}
              placeholder="On distributed consensus, again"
            />
          </Field>
          <GridTwo>
            <Field label="Publisher / venue">
              <TextInput
                value={pb.publisher ?? ''}
                onChange={(v) => update(pb.id, { publisher: v })}
                placeholder="OSDI '24"
              />
            </Field>
            <Field label="Date">
              <TextInput
                type="month"
                value={pb.releaseDate ?? ''}
                onChange={(v) => update(pb.id, { releaseDate: v })}
              />
            </Field>
            <Field label="URL" span={2}>
              <TextInput
                type="url"
                value={pb.url ?? ''}
                onChange={(v) => update(pb.id, { url: v })}
                placeholder="https://example.com/paper"
              />
            </Field>
          </GridTwo>
          <Field
            label="Summary"
            loading={isEnh(`${pb.id}.summary`)}
            actions={
              <ImproveButton
                text={pb.summary ?? ''}
                context={{
                  position: pb.title,
                  company: pb.publisher,
                  // The backend will follow this URL and feed the paper
                  // text (HTML or PDF) into the rewrite prompt.
                  paper_url: pb.url,
                }}
                field={`publications[${pb.id}].summary`}
                onChange={(v) => update(pb.id, { summary: v })}
                onStreamingChange={(b) => setEnh(`${pb.id}.summary`, b)}
              />
            }
          >
            <TextArea
              value={pb.summary ?? ''}
              onChange={(v) => update(pb.id, { summary: v })}
              placeholder="One sentence on what's interesting about it."
              rows={2}
              disabled={isEnh(`${pb.id}.summary`)}
            />
          </Field>
        </ItemCard>
      ))}
      <AddButton onClick={add} label="Add publication" />
    </div>
  );
}
