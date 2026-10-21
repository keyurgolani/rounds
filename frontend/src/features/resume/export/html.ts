// Standalone HTML export. Captures the live preview's DOM (which already
// has all the inline styles the templates produce) and wraps it in the
// minimal <html> shell from `shell.ts`. The result is portable: open in
// any browser, print, or attach to an email.

import { downloadString } from './index';
import { wrapStandaloneHtml } from './shell';

export function buildStandaloneHtml(): string | null {
  const node = document.querySelector<HTMLElement>('[data-resume-page]');
  if (!node) return null;
  return wrapStandaloneHtml(node.outerHTML);
}

export function exportStandaloneHtml(base: string): boolean {
  const html = buildStandaloneHtml();
  if (!html) return false;
  downloadString(html, `${base}.html`, 'text/html;charset=utf-8');
  return true;
}
