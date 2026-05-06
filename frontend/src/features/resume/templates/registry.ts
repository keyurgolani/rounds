import type { ComponentType } from 'react';
import type { ResumeData, TemplateConfig } from '../types';
import ModernTemplate from './ModernTemplate';
import ClassicTemplate from './ClassicTemplate';
import ExecutiveTemplate from './ExecutiveTemplate';
import SWELatexTemplate from './SWELatexTemplate';

export type TemplateProps = { data: ResumeData; design?: TemplateConfig };

export type TemplateMeta = {
  id: string;
  label: string;
  blurb: string;
  component: ComponentType<TemplateProps>;
};

export const TEMPLATES: TemplateMeta[] = [
  {
    id: 'modern',
    label: 'Modern',
    blurb: 'Sans-serif single column. Accent-colored heads, breathable spacing.',
    component: ModernTemplate,
  },
  {
    id: 'classic',
    label: 'Classic',
    blurb: 'Serif single column with a centered header. Conservative, print-first.',
    component: ClassicTemplate,
  },
  {
    id: 'executive',
    label: 'Executive',
    blurb: 'Display-serif headings, restrained body. Built to carry a 2-page narrative.',
    component: ExecutiveTemplate,
  },
  {
    id: 'swe-latex',
    label: 'SWE LaTeX',
    blurb: 'Computer-Modern serif, ATS-safe single column. Jake-style for engineers.',
    component: SWELatexTemplate,
  },
];

export function templateById(id: string | undefined): TemplateMeta {
  return TEMPLATES.find((t) => t.id === id) ?? TEMPLATES[0];
}
