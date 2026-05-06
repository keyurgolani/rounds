// Right pane — pure live A4 preview with visible page-break markers.
//
// Tabs (Design / Tailor / ATS / History) used to live here, but their
// inputs all change resume data the user wants to see updated in the
// preview. Putting them on top of the preview meant flipping a tab
// hid the very thing they're driving. They've moved to the left rail
// in StudioShell; this pane is now exclusively the rendered template
// so any edit anywhere immediately shows up here.
//
// PaginatedFrame draws subtle dashed page boundaries every 297 mm so
// the user can see where the printed PDF will break. `ResumePageStyles`
// injects the `break-inside: avoid` / `break-after: avoid` rules that
// browsers and Puppeteer use to keep entries on the same page.

import type { ResumeData, TemplateConfig } from '../types';
import { templateById } from '../templates/registry';
import { ResumePageStyles } from '../templates/parts';
import PaginatedFrame from './PaginatedFrame';

type Props = {
  data: ResumeData;
  templateId: string;
  design: TemplateConfig;
};

export default function PreviewPane({ data, templateId, design }: Props) {
  const Template = templateById(templateId).component;

  // Strip hidden sections so the preview matches the export — same as
  // the production renderer.
  const renderData: ResumeData = {
    ...data,
    experience: data.hiddenSections?.includes('experience') ? [] : data.experience,
    education: data.hiddenSections?.includes('education') ? [] : data.education,
    skills: data.hiddenSections?.includes('skills') ? [] : data.skills,
    projects: data.hiddenSections?.includes('projects') ? [] : data.projects,
    publications: data.hiddenSections?.includes('publications') ? [] : data.publications,
    profiles: data.hiddenSections?.includes('profiles') ? [] : data.profiles,
  };

  return (
    <>
      <ResumePageStyles />
      <div
        data-resume-preview
        style={{
          padding: 16,
          background: 'var(--bg-sunken)',
          borderRadius: 'var(--radius)',
          // Fill the studio's preview column and let the resume scroll
          // *inside* the shaded surround instead of letting the surround
          // grow past the fold. On narrow stacked layouts the parent's
          // height is `auto` so this collapses to content height — the
          // card stays the natural size and the page scrolls normally.
          height: '100%',
          overflow: 'auto',
        }}
      >
        <PaginatedFrame>
          <Template data={renderData} design={design} />
        </PaginatedFrame>
      </div>
    </>
  );
}
