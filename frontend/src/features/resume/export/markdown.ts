// Markdown export. Convenient for pasting into a GitHub README or a
// blog. Headings hew to the visible section labels so the structure
// stays recognizable.

import type { ResumeData, SectionKey } from '../types';
import { sectionOrder, isSectionHidden, SECTION_LABELS } from '../utils';
import { downloadString } from './index';

export function buildMarkdown(data: ResumeData): string {
  const lines: string[] = [];
  const p = data.personalInfo;
  lines.push(`# ${p.fullName || 'Untitled'}`);
  if (p.title) lines.push(`**${p.title}**`);
  const meta = [p.location, p.email, p.phone, p.website, p.linkedin, p.github]
    .filter(Boolean)
    .join(' · ');
  if (meta) lines.push(`_${meta}_`);
  if (p.summary) {
    lines.push('');
    lines.push(p.summary);
  }
  lines.push('');

  for (const key of sectionOrder(data)) {
    if (key === 'personal') continue;
    if (isSectionHidden(data, key)) continue;
    const block = renderSection(data, key);
    if (block) {
      lines.push(`## ${SECTION_LABELS[key]}`);
      lines.push('');
      lines.push(block);
      lines.push('');
    }
  }

  return lines.join('\n').trim() + '\n';
}

function renderSection(data: ResumeData, key: SectionKey): string {
  const lines: string[] = [];
  switch (key) {
    case 'experience':
      for (const e of data.experience) {
        const dates = dateRange(e.startDate, e.endDate, e.current);
        const header = `### ${e.position || ''} — ${e.company || ''}${e.location ? `, ${e.location}` : ''}`;
        lines.push(header.replace(/—\s+,/g, '—'));
        if (dates) lines.push(`_${dates}_`);
        if (e.description) lines.push('', e.description);
        if (e.highlights.length) {
          lines.push('');
          for (const h of e.highlights) lines.push(`- ${h}`);
        }
        lines.push('');
      }
      break;
    case 'education':
      for (const ed of data.education) {
        const dates = dateRange(ed.startDate, ed.endDate);
        lines.push(`### ${ed.institution}${ed.location ? `, ${ed.location}` : ''}`);
        const second = [ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : ''].filter(Boolean).join(' — ');
        if (second) lines.push(second);
        if (dates) lines.push(`_${dates}_`);
        if (ed.description) lines.push('', ed.description);
        lines.push('');
      }
      break;
    case 'skills':
      for (const sk of data.skills) {
        lines.push(`- **${sk.category}:** ${sk.items.join(', ')}`);
      }
      break;
    case 'projects':
      for (const pr of data.projects) {
        const techs = pr.technologies.length ? ` _(${pr.technologies.join(', ')})_` : '';
        const link = pr.url ? `[${pr.name}](${pr.url})` : pr.name;
        lines.push(`### ${link}${techs}`);
        if (pr.description) lines.push(pr.description);
        if (pr.highlights.length) {
          lines.push('');
          for (const h of pr.highlights) lines.push(`- ${h}`);
        }
        if (pr.github) lines.push(`GitHub: ${pr.github}`);
        lines.push('');
      }
      break;
    case 'publications':
      for (const pb of data.publications) {
        const link = pb.url ? `[${pb.title}](${pb.url})` : pb.title;
        lines.push(`### ${link}`);
        const meta = [pb.publisher, pb.releaseDate].filter(Boolean).join(' — ');
        if (meta) lines.push(`_${meta}_`);
        if (pb.summary) lines.push('', pb.summary);
        lines.push('');
      }
      break;
    case 'profiles':
      for (const pf of data.profiles) {
        const target = pf.url || pf.username || '';
        lines.push(`- **${pf.network}:** ${pf.url ? `[${target}](${pf.url})` : target}`);
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

export function exportMarkdown(data: ResumeData, base: string): void {
  downloadString(buildMarkdown(data), `${base}.md`, 'text/markdown;charset=utf-8');
}
