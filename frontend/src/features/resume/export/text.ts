// Plain-text export. Useful as the ATS-fallback companion file —
// recruiters' systems that mangle PDFs sometimes accept plain text
// reliably. Mirrors the section ordering on the rendered resume.

import type { ResumeData, SectionKey } from '../types';
import { sectionOrder, isSectionHidden, SECTION_LABELS } from '../utils';
import { downloadString } from './index';

export function buildText(data: ResumeData): string {
  const lines: string[] = [];
  const p = data.personalInfo;
  lines.push(p.fullName || 'Untitled');
  if (p.title) lines.push(p.title);
  const meta = [p.location, p.email, p.phone, p.website, p.linkedin, p.github]
    .filter(Boolean)
    .join('  ·  ');
  if (meta) lines.push(meta);
  lines.push('');

  for (const key of sectionOrder(data)) {
    if (key === 'personal') continue;
    if (isSectionHidden(data, key)) continue;
    const block = renderSection(data, key);
    if (block) {
      lines.push(SECTION_LABELS[key].toUpperCase());
      lines.push('-'.repeat(SECTION_LABELS[key].length));
      lines.push(block);
      lines.push('');
    }
  }

  return lines.join('\n').trimEnd() + '\n';
}

function renderSection(data: ResumeData, key: SectionKey): string {
  const lines: string[] = [];
  switch (key) {
    case 'experience':
      for (const e of data.experience) {
        const dates = dateRange(e.startDate, e.endDate, e.current);
        lines.push(`${e.position || ''}${e.company ? ` — ${e.company}` : ''}${e.location ? `, ${e.location}` : ''} ${dates ? `(${dates})` : ''}`.trim());
        if (e.description) lines.push(e.description);
        for (const h of e.highlights) lines.push(`- ${h}`);
        lines.push('');
      }
      break;
    case 'education':
      for (const ed of data.education) {
        const dates = dateRange(ed.startDate, ed.endDate);
        lines.push(`${ed.institution}${ed.location ? `, ${ed.location}` : ''} ${dates ? `(${dates})` : ''}`.trim());
        const second = [ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : ''].filter(Boolean).join(' — ');
        if (second) lines.push(second);
        if (ed.description) lines.push(ed.description);
        lines.push('');
      }
      break;
    case 'skills':
      for (const sk of data.skills) {
        lines.push(`${sk.category}: ${sk.items.join(', ')}`);
      }
      break;
    case 'projects':
      for (const pr of data.projects) {
        lines.push(`${pr.name}${pr.technologies.length ? ` [${pr.technologies.join(', ')}]` : ''}`);
        if (pr.description) lines.push(pr.description);
        for (const h of pr.highlights) lines.push(`- ${h}`);
        if (pr.url) lines.push(`URL: ${pr.url}`);
        if (pr.github) lines.push(`GitHub: ${pr.github}`);
        lines.push('');
      }
      break;
    case 'publications':
      for (const pb of data.publications) {
        lines.push(pb.title);
        const meta = [pb.publisher, pb.releaseDate].filter(Boolean).join(' — ');
        if (meta) lines.push(meta);
        if (pb.url) lines.push(pb.url);
        if (pb.summary) lines.push(pb.summary);
        lines.push('');
      }
      break;
    case 'profiles':
      for (const pf of data.profiles) {
        lines.push(`${pf.network}: ${pf.url || pf.username || ''}`);
      }
      break;
    case 'personal':
      break;
  }
  return lines.join('\n').trim();
}

function dateRange(start?: string, end?: string, current?: boolean): string {
  const fmt = (s?: string) => (s ? s.replace(/^(\d{4})-(\d{2}).*$/, '$1-$2') : '');
  const s = fmt(start);
  const e = current ? 'Present' : fmt(end);
  if (!s && !e) return '';
  if (!s) return e;
  if (!e) return s;
  return `${s} – ${e}`;
}

export function exportText(data: ResumeData, base: string): void {
  downloadString(buildText(data), `${base}.txt`, 'text/plain;charset=utf-8');
}
