import { useState } from 'react';
import type { ResumeData } from '../../types';
import ImproveButton from './ImproveButton';
import { Field, GridTwo, TextArea, TextInput } from './parts';

type Props = {
  data: ResumeData;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
};

export default function PersonalInfoEditor({ data, setData }: Props) {
  const p = data.personalInfo;
  const [summaryEnh, setSummaryEnh] = useState(false);
  const set = <K extends keyof ResumeData['personalInfo']>(key: K, value: ResumeData['personalInfo'][K]) => {
    setData((prev) => ({ ...prev, personalInfo: { ...prev.personalInfo, [key]: value } }));
  };

  return (
    <div className="flex flex-col gap-3">
      <GridTwo>
        <Field label="Full name">
          <TextInput value={p.fullName} onChange={(v) => set('fullName', v)} placeholder="Jane Doe" />
        </Field>
        <Field label="Headline / title">
          <TextInput
            value={p.title ?? ''}
            onChange={(v) => set('title', v)}
            placeholder="Senior Software Engineer"
          />
        </Field>
        <Field label="Email">
          <TextInput
            type="email"
            value={p.email ?? ''}
            onChange={(v) => set('email', v)}
            placeholder="jane@example.com"
          />
        </Field>
        <Field label="Phone">
          <TextInput
            type="tel"
            value={p.phone ?? ''}
            onChange={(v) => set('phone', v)}
            placeholder="+1 (555) 123-4567"
          />
        </Field>
        <Field label="Location">
          <TextInput
            value={p.location ?? ''}
            onChange={(v) => set('location', v)}
            placeholder="San Francisco, CA"
          />
        </Field>
        <Field label="Website">
          <TextInput
            type="url"
            value={p.website ?? ''}
            onChange={(v) => set('website', v)}
            placeholder="https://janedoe.dev"
          />
        </Field>
        <Field label="LinkedIn">
          <TextInput
            value={p.linkedin ?? ''}
            onChange={(v) => set('linkedin', v)}
            placeholder="linkedin.com/in/janedoe"
          />
        </Field>
        <Field label="GitHub">
          <TextInput
            value={p.github ?? ''}
            onChange={(v) => set('github', v)}
            placeholder="github.com/janedoe"
          />
        </Field>
      </GridTwo>
      <Field
        label="Summary"
        hint="2–3 sentences. Lead with what you do, who you do it for, and a measurable outcome."
        loading={summaryEnh}
        actions={
          <ImproveButton
            text={p.summary ?? ''}
            field="personalInfo.summary"
            onChange={(v) => set('summary', v)}
            onStreamingChange={setSummaryEnh}
          />
        }
      >
        <TextArea
          value={p.summary ?? ''}
          onChange={(v) => set('summary', v)}
          placeholder="Senior backend engineer with 8 years scaling API platforms…"
          rows={4}
          disabled={summaryEnh}
        />
      </Field>
    </div>
  );
}
