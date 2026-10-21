// The Legacy Artifact Snapshot materializer against the Studio preview
// (ROUNDS-00A-L04).
//
// This file sits outside src/ so `tsc`, which builds the frontend image
// from frontend/ alone, never resolves its imports from backend/ and
// contracts/. It runs the materializer's own core
// (backend/materializer/src/core.mjs) with this package's React 18.3.1, the
// version the materializer pins, and compares each template's snapshot with
// PreviewPane rendered on the server. PaginatedFrame pushes entries down in a
// layout effect, which server rendering never runs, so this is the preview's
// [data-resume-page] before its push-downs, byte for byte.

import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest';

import {
  BODY_SIZE,
  BULLET_STYLES,
  createMaterializer,
  FONT_IDS,
  FONT_STACKS,
  HEX_COLOR,
  MARGIN_MM,
  normalizeDesign,
} from '../../backend/materializer/src/core.mjs';
import { DESIGN, HIDDEN, RICH } from '../../backend/materializer/test/fixtures.mjs';
import contract from '../../contracts/definitions/artifact-renderer.v1.schema.json';
import { wrapStandaloneHtml } from '../src/features/resume/export/shell';
import PreviewPane from '../src/features/resume/studio/PreviewPane';
import { TEMPLATES } from '../src/features/resume/templates/registry';
import type { ResumeData, TemplateConfig } from '../src/features/resume/types';
import { emptyResumeData } from '../src/features/resume/types';

const materialize = createMaterializer({
  createElement,
  renderToStaticMarkup,
  templates: TEMPLATES,
  wrapStandaloneHtml,
  emptyResumeData,
});

// The one [data-resume-page] article in server-rendered markup.
function previewArticle(html: string): string {
  const open = '<article data-resume-page';
  const start = html.indexOf(open);
  expect(start).toBeGreaterThan(-1);
  expect(html.indexOf(open, start + 1)).toBe(-1);
  const tags = /<(\/?)article\b/g;
  tags.lastIndex = start;
  let depth = 0;
  for (let m = tags.exec(html); m; m = tags.exec(html)) {
    depth += m[1] ? -1 : 1;
    if (depth === 0) return html.slice(start, html.indexOf('>', m.index) + 1);
  }
  throw new Error('the article never closes');
}

function preview(data: ResumeData, templateId: string, design: TemplateConfig): string {
  return previewArticle(renderToStaticMarkup(createElement(PreviewPane, { data, templateId, design })));
}

describe('materializer: preview parity', () => {
  // React 18 warns that useLayoutEffect does nothing on the server.
  let quiet: ReturnType<typeof vi.spyOn>;
  beforeAll(() => {
    quiet = vi.spyOn(console, 'error').mockImplementation(() => {});
  });
  afterAll(() => quiet.mockRestore());

  const fixtures: [string, ResumeData][] = [
    ['all six hideable sections hidden', HIDDEN as unknown as ResumeData],
    ['every section shown', RICH as unknown as ResumeData],
  ];
  for (const template of TEMPLATES) {
    for (const [name, data] of fixtures) {
      it(`gives ${template.id} with ${name} the preview's article in the export shell`, () => {
        const design = structuredClone(DESIGN) as TemplateConfig;
        const snapshot = materialize({ template_id: template.id, design, data: structuredClone(data) });
        expect(snapshot.status).toBe('ok');
        expect(snapshot.markup).toBe(wrapStandaloneHtml(preview(structuredClone(data), template.id, design)));
      });
    }
  }
});

describe('materializer: the Artifact Renderer Contract', () => {
  const overrides = contract.properties.overrides.properties;

  it('validates the same grammar the contract states', () => {
    expect([...FONT_IDS]).toEqual(contract.$defs.font_id.enum);
    expect([...BULLET_STYLES]).toEqual(overrides.bulletStyle.enum);
    expect(MARGIN_MM).toEqual({ min: overrides.spacing.properties.margin.minimum, max: overrides.spacing.properties.margin.maximum });
    const size = overrides.typography.properties.body.properties.size;
    expect(BODY_SIZE).toEqual({ min: size.minimum, max: size.maximum });
    expect(HEX_COLOR.source).toBe(overrides.colors.properties.primary.pattern);
    expect(TEMPLATES.map((t) => t.id)).toEqual(contract.properties.template_id.enum);
  });

  it('keeps only paths the contract has', () => {
    const full = normalizeDesign({
      spacing: { margin: 30, padding: 1 },
      typography: { body: { size: 9, family: 'inter', weight: 4 }, heading: { family: 'cmu-serif', size: 20 } },
      colors: { primary: '#000000', secondary: '#ffffff' },
      bulletStyle: 'none',
      layout: 'two-column',
    });
    expect(full.ok).toBe(true);
    const keys = (value: object) => Object.keys(value).sort();
    const { design } = full as { design: Record<string, Record<string, Record<string, unknown>>> };
    expect(keys(design)).toEqual(keys(overrides).sort());
    expect(keys(design.spacing)).toEqual(keys(overrides.spacing.properties));
    expect(keys(design.colors)).toEqual(keys(overrides.colors.properties));
    expect(keys(design.typography)).toEqual(keys(overrides.typography.properties));
    expect(keys(design.typography.body)).toEqual(keys(overrides.typography.properties.body.properties));
    expect(keys(design.typography.heading)).toEqual(keys(overrides.typography.properties.heading.properties));
  });

  it('renders every font id through a stack that names it first', () => {
    for (const id of FONT_IDS) {
      const snapshot = materialize({ template_id: 'modern', design: { typography: { body: { family: id } } }, data: RICH });
      expect(snapshot.status).toBe('ok');
      expect(snapshot.font_families).toContain(id);
      expect(FONT_STACKS[id]).toMatch(/^'[^']+'/);
    }
  });
});
