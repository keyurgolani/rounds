// DOCX export. Maps ResumeData straight to a Word document via the
// `docx` library. We don't try to perfectly mirror the on-screen
// template — DOCX rendering rules are different enough that fighting
// for pixel parity isn't worth it. Goal: a clean, ATS-parseable Word
// doc that recruiters who ask for "the Word version" can open without
// surprises.

import {
  AlignmentType,
  BorderStyle,
  Document,
  HeadingLevel,
  Packer,
  Paragraph,
  TextRun,
  type ParagraphChild,
} from 'docx';
import type { ResumeData, SectionKey } from '../types';
import { sectionOrder, isSectionHidden, SECTION_LABELS } from '../utils';
import { downloadBlob } from './index';

export async function exportDocx(data: ResumeData, base: string): Promise<void> {
  const blob = await buildDocx(data);
  downloadBlob(blob, `${base}.docx`);
}

async function buildDocx(data: ResumeData): Promise<Blob> {
  const p = data.personalInfo;
  const children: Paragraph[] = [];

  // Header
  children.push(
    new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({ text: p.fullName || 'Untitled', bold: true, size: 36 }),
      ],
    }),
  );
  if (p.title) {
    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: p.title, italics: true, size: 24 })],
      }),
    );
  }
  const meta = [p.location, p.email, p.phone, p.website, p.linkedin, p.github]
    .filter(Boolean)
    .join('  ·  ');
  if (meta) {
    children.push(
      new Paragraph({
        alignment: AlignmentType.CENTER,
        children: [new TextRun({ text: meta, size: 20 })],
      }),
    );
  }

  if (p.summary) {
    children.push(sectionHeading('Summary'));
    children.push(new Paragraph({ children: [new TextRun({ text: p.summary, size: 22 })] }));
  }

  for (const key of sectionOrder(data)) {
    if (key === 'personal') continue;
    if (isSectionHidden(data, key)) continue;
    const block = renderSection(data, key);
    if (block.length > 0) {
      children.push(sectionHeading(SECTION_LABELS[key]));
      children.push(...block);
    }
  }

  const doc = new Document({
    creator: 'Rounds',
    styles: {
      default: {
        document: {
          run: {
            font: 'Calibri',
            size: 22,
          },
        },
      },
    },
    sections: [
      {
        properties: {
          page: {
            margin: {
              top: 720, // 0.5"
              right: 720,
              bottom: 720,
              left: 720,
            },
          },
        },
        children,
      },
    ],
  });

  // Packer.toBlob is browser-friendly.
  return Packer.toBlob(doc);
}

function sectionHeading(label: string): Paragraph {
  return new Paragraph({
    heading: HeadingLevel.HEADING_2,
    spacing: { before: 240, after: 100 },
    border: {
      bottom: { color: '999999', style: BorderStyle.SINGLE, size: 6, space: 1 },
    },
    children: [
      new TextRun({
        text: label.toUpperCase(),
        bold: true,
        size: 22,
        characterSpacing: 30,
      }),
    ],
  });
}

function renderSection(data: ResumeData, key: SectionKey): Paragraph[] {
  switch (key) {
    case 'experience':
      return data.experience.flatMap((e) => {
        const dates = dateRange(e.startDate, e.endDate, e.current);
        const entries: Paragraph[] = [];
        entries.push(
          headerRow(
            [{ text: e.position || '', bold: true }, { text: e.company ? ` — ${e.company}` : '' }, { text: e.location ? `, ${e.location}` : '', italics: true }],
            dates,
          ),
        );
        if (e.description) {
          entries.push(new Paragraph({ children: [new TextRun({ text: e.description })] }));
        }
        for (const h of e.highlights) {
          entries.push(bullet(h));
        }
        entries.push(spacer());
        return entries;
      });
    case 'education':
      return data.education.flatMap((ed) => {
        const dates = dateRange(ed.startDate, ed.endDate);
        const entries: Paragraph[] = [];
        entries.push(
          headerRow(
            [
              { text: ed.institution, bold: true },
              { text: ed.location ? `, ${ed.location}` : '', italics: true },
            ],
            dates,
          ),
        );
        const second = [ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : ''].filter(Boolean).join(' — ');
        if (second) entries.push(new Paragraph({ children: [new TextRun({ text: second })] }));
        if (ed.description) entries.push(new Paragraph({ children: [new TextRun({ text: ed.description })] }));
        entries.push(spacer());
        return entries;
      });
    case 'skills':
      return data.skills.map(
        (sk) =>
          new Paragraph({
            children: [
              new TextRun({ text: `${sk.category}: `, bold: true }),
              new TextRun({ text: sk.items.join(', ') }),
            ],
          }),
      );
    case 'projects':
      return data.projects.flatMap((pr) => {
        const entries: Paragraph[] = [];
        const techs = pr.technologies.length ? ` — ${pr.technologies.join(', ')}` : '';
        entries.push(
          new Paragraph({
            children: [
              new TextRun({ text: pr.name, bold: true }),
              new TextRun({ text: techs, italics: true }),
            ],
          }),
        );
        if (pr.description) entries.push(new Paragraph({ children: [new TextRun({ text: pr.description })] }));
        for (const h of pr.highlights) entries.push(bullet(h));
        if (pr.url) entries.push(new Paragraph({ children: [new TextRun({ text: pr.url, italics: true })] }));
        if (pr.github) entries.push(new Paragraph({ children: [new TextRun({ text: `GitHub: ${pr.github}`, italics: true })] }));
        entries.push(spacer());
        return entries;
      });
    case 'publications':
      return data.publications.flatMap((pb) => {
        const entries: Paragraph[] = [];
        entries.push(new Paragraph({ children: [new TextRun({ text: pb.title, bold: true })] }));
        const meta = [pb.publisher, pb.releaseDate].filter(Boolean).join(' — ');
        if (meta) entries.push(new Paragraph({ children: [new TextRun({ text: meta, italics: true })] }));
        if (pb.summary) entries.push(new Paragraph({ children: [new TextRun({ text: pb.summary })] }));
        if (pb.url) entries.push(new Paragraph({ children: [new TextRun({ text: pb.url, italics: true })] }));
        entries.push(spacer());
        return entries;
      });
    case 'profiles':
      return data.profiles.map(
        (pf) =>
          new Paragraph({
            children: [
              new TextRun({ text: `${pf.network}: `, bold: true }),
              new TextRun({ text: pf.url || pf.username || '' }),
            ],
          }),
      );
    case 'personal':
      return [];
  }
}

function headerRow(
  parts: Array<{ text: string; bold?: boolean; italics?: boolean }>,
  trailing?: string,
): Paragraph {
  // docx doesn't have a built-in flex layout; split with a tab so the
  // trailing text right-aligns when a tab stop is set. For now we keep
  // it simple: header on one line, dates on the next.
  const children: ParagraphChild[] = parts.map(
    (p) => new TextRun({ text: p.text, bold: p.bold, italics: p.italics }),
  );
  if (trailing) {
    children.push(new TextRun({ text: `  (${trailing})`, italics: true }));
  }
  return new Paragraph({ children });
}

function bullet(text: string): Paragraph {
  return new Paragraph({
    bullet: { level: 0 },
    children: [new TextRun({ text })],
  });
}

function spacer(): Paragraph {
  return new Paragraph({ children: [new TextRun({ text: '' })] });
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
