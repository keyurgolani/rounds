import { afterEach, describe, expect, it } from 'vitest';

import { RESUME_PAGE_CSS } from '../../templates/parts';
import { buildStandaloneHtml } from '../html';
import { wrapStandaloneHtml } from '../shell';

// The client HTML export and the Legacy Artifact Snapshot materializer
// (ROUNDS-00A-L04) share wrapStandaloneHtml, so a snapshot's shell is the
// export's.
describe('standalone HTML shell', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('wraps the live preview article in the shared shell', () => {
    document.body.innerHTML = '<div><article data-resume-page="true" style="width: 210mm;"><p>Ada &amp; co</p></article></div>';
    const node = document.querySelector('[data-resume-page]') as HTMLElement;
    expect(buildStandaloneHtml()).toBe(wrapStandaloneHtml(node.outerHTML));
  });

  it('returns null when no preview is rendered', () => {
    expect(buildStandaloneHtml()).toBeNull();
  });

  it('is one A4 document carrying the page CSS and the article once', () => {
    const inner = '<article data-resume-page="true"></article>';
    const html = wrapStandaloneHtml(inner);
    expect(html.startsWith('<!DOCTYPE html>\n<html lang="en">\n<head>')).toBe(true);
    expect(html.endsWith(`<body>\n${inner}\n</body>\n</html>`)).toBe(true);
    expect(html).toContain('@page { size: A4; margin: 0; }');
    expect(html).toContain(RESUME_PAGE_CSS);
    expect(html.split(inner)).toHaveLength(2);
  });
});
