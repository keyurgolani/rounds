import { useState } from 'react';
import { Ruler } from 'lucide-react';
import type { ResumeData } from '../../types';
import GuidedSummaryDialog from './GuidedSummaryDialog';
import ImproveButton from './ImproveButton';
import { Field, GridTwo, TextArea, TextInput } from './parts';

type Props = {
  data: ResumeData;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
};

export default function PersonalInfoEditor({ data, setData }: Props) {
  const p = data.personalInfo;
  const [summaryEnh, setSummaryEnh] = useState(false);
  const [guidedOpen, setGuidedOpen] = useState(false);
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
        <Field
          label="Subtitle"
          hint="Optional second title. The Langstaff template renders this as a dual-title row: 'Title • Subtitle'."
        >
          <TextInput
            value={p.subtitle ?? ''}
            onChange={(v) => set('subtitle', v)}
            placeholder="CPG Industry Expert"
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
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <button
              type="button"
              onClick={() => setGuidedOpen(true)}
              title="Guided 3-part formula summary"
              aria-label="Guided summary"
              style={{
                height: 24,
                padding: '0 8px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 4,
                background: 'transparent',
                color: 'var(--text-2)',
                border: 0,
                borderRadius: 6,
                boxShadow: 'inset 0 0 0 1px var(--border)',
                fontSize: 10,
                fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              <Ruler size={11} strokeWidth={1.8} />
              Guided
            </button>
            <ImproveButton
              text={p.summary ?? ''}
              field="personalInfo.summary"
              onChange={(v) => set('summary', v)}
              onStreamingChange={setSummaryEnh}
            />
          </div>
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
      <GuidedSummaryDialog
        open={guidedOpen}
        onClose={() => setGuidedOpen(false)}
        onApply={(s) => set('summary', s)}
        currentSummary={p.summary}
      />
    </div>
  );
}
