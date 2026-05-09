import type { ComponentType } from 'react';
import type { ResumeData, TemplateConfig } from '../types';
import ModernTemplate from './ModernTemplate';
import ClassicTemplate from './ClassicTemplate';
import ExecutiveTemplate from './ExecutiveTemplate';
import SWELatexTemplate from './SWELatexTemplate';
import CompactTemplate from './CompactTemplate';
import TimelineTemplate from './TimelineTemplate';
import EditorialTemplate from './EditorialTemplate';
import BrutalistMonoTemplate from './BrutalistMonoTemplate';
import NotionTemplate from './NotionTemplate';
import GeometricTemplate from './GeometricTemplate';
import SplitTemplate from './SplitTemplate';
import ConfettiTemplate from './ConfettiTemplate';
import ApertureTemplate from './ApertureTemplate';
import TypewriterTemplate from './TypewriterTemplate';
import LinearTemplate from './LinearTemplate';
import InvertedTemplate from './InvertedTemplate';
import BannerTemplate from './BannerTemplate';
import DisplayTemplate from './DisplayTemplate';

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
  {
    id: 'compact',
    label: 'Compact',
    blurb:
      'Two-column dense layout. Deedy-inspired, fits ~25% more text per page — best for senior engineers.',
    component: CompactTemplate,
  },
  {
    id: 'timeline',
    label: 'Timeline',
    blurb:
      'Date rail on the left, content right of a vertical rule. Reads like a changelog — scannable career arc.',
    component: TimelineTemplate,
  },
  {
    id: 'editorial',
    label: 'Editorial',
    blurb:
      'Magazine-style display-serif italic heads, two-column footer. Senior IC voice.',
    component: EditorialTemplate,
  },
  {
    id: 'brutalist-mono',
    label: 'Brutalist Mono',
    blurb:
      'All monospace, ALL-CAPS heads, heavy black rules. Distinctive for indie and infra-dev candidates.',
    component: BrutalistMonoTemplate,
  },
  {
    id: 'notion',
    label: 'Notion',
    blurb:
      'Document-style with pill-tagged tech stacks and gray dividers. Modern startup aesthetic.',
    component: NotionTemplate,
  },

  // Creative
  {
    id: 'geometric',
    label: 'Geometric',
    blurb:
      'Diagonal accent wedge in the upper-left corner. Modern artsy header, clean sans-serif body.',
    component: GeometricTemplate,
  },
  {
    id: 'split',
    label: 'Split',
    blurb:
      'Vertical accent band runs the full page height. Section heads tick out toward the band.',
    component: SplitTemplate,
  },
  {
    id: 'confetti',
    label: 'Confetti',
    blurb:
      'Decorative accent flecks across the header strip. Playful but professional.',
    component: ConfettiTemplate,
  },

  // Designer
  {
    id: 'aperture',
    label: 'Aperture',
    blurb:
      'Photography-portfolio aesthetic. Oversized typographic name, mono metadata grid.',
    component: ApertureTemplate,
  },
  {
    id: 'typewriter',
    label: 'Typewriter',
    blurb:
      'Monospace body, italic display-serif name. Vintage-modern hybrid with em-dash chapter heads.',
    component: TypewriterTemplate,
  },
  {
    id: 'linear',
    label: 'Linear',
    blurb:
      'Linear/Vercel-inspired micro-typography. Lowercase labels, mono metadata, the lightest possible dividers.',
    component: LinearTemplate,
  },

  // Bold
  {
    id: 'inverted',
    label: 'Inverted',
    blurb:
      'Dark accent header band with light text; body in normal print mode for readability.',
    component: InvertedTemplate,
  },
  {
    id: 'banner',
    label: 'Banner',
    blurb:
      'Full-width accent banner with the name in white display caps. Section heads on accent blocks.',
    component: BannerTemplate,
  },
  {
    id: 'display',
    label: 'Display',
    blurb:
      'Mega italic display-serif name as the page hero. Tight serif body, type as the design.',
    component: DisplayTemplate,
  },
];

export function templateById(id: string | undefined): TemplateMeta {
  return TEMPLATES.find((t) => t.id === id) ?? TEMPLATES[0];
}
