// LaTeX-grade single-column for software engineering candidates. Models
// itself on Jake Gutierrez's resume / Awesome-CV: Computer Modern stack
// (or system-fallback serif) for body, no colors, no icons, generous
// kerning on section heads, tight-but-readable bullets. ATS-safe by
// construction — no two-column layouts, no table-based positioning, no
// images, no boxed components.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

export default function SWELatexTemplate({ data, design }: Props) {
  // CMU Serif if installed; otherwise the system serif. Either way
  // ATS parsers see plain text — typography is for human readers.
  const fontFamily =
    design?.typography?.body?.family ??
    "'CMU Serif', 'Latin Modern Roman', 'Source Serif Pro', 'Georgia', 'Times New Roman', serif";
  const fontSize = design?.typography?.body?.size ?? 10.5;
  const marginMm = (design?.spacing?.margin ?? 12) | 0;
  // Default is pure black (LaTeX look). User-picked accent tints
  // section heads + the rule beneath them; everything else stays b/w.
  const accent = design?.colors?.primary ?? '#000';

  const p = data.personalInfo;
  const meta = joinNonEmpty([
    p.location,
    p.email,
    p.phone,
    p.website,
    p.linkedin,
    p.github,
  ]);

  return (
    <A4Page marginMm={marginMm} fontFamily={fontFamily} fontSize={fontSize} color="#000" bulletStyle={design?.bulletStyle}>
      <header style={{ textAlign: 'center', marginBottom: 8 }}>
        <div
          style={{
            fontSize: 22,
            fontWeight: 600,
            letterSpacing: '0.01em',
            lineHeight: 1.05,
          }}
        >
          {p.fullName || 'Your Name'}
        </div>
        {meta && (
          <div style={{ fontSize: 10, marginTop: 4 }}>{meta}</div>
        )}
        {p.title && (
          <div style={{ fontSize: 10.5, fontStyle: 'italic', marginTop: 2 }}>{p.title}</div>
        )}
      </header>

      {p.summary && (
        <Section title="Summary" accent={accent}>
          <p style={{ margin: 0, textAlign: 'justify' }}>{p.summary}</p>
        </Section>
      )}

      {data.education.length > 0 && (
        <Section title="Education" accent={accent}>
          {data.education.map((ed) => (
            <Entry
              key={ed.id}
              left={ed.institution}
              right={ed.location}
              subLeft={joinNonEmpty([ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : undefined])}
              subRight={formatDateRange(ed.startDate, ed.endDate)}
              body={ed.description}
            />
          ))}
        </Section>
      )}

      {data.experience.length > 0 && (
        <Section title="Experience" accent={accent}>
          {data.experience.map((e) => (
            <Entry
              key={e.id}
              left={e.company}
              right={e.location}
              subLeft={e.position}
              subRight={formatDateRange(e.startDate, e.endDate, e.current)}
              body={e.description}
              bullets={e.highlights}
            />
          ))}
        </Section>
      )}

      {data.projects.length > 0 && (
        <Section title="Projects" accent={accent}>
          {data.projects.map((pr) => (
            <Entry
              key={pr.id}
              left={
                <span>
                  <span style={{ fontWeight: 700 }}>{pr.name}</span>
                  {pr.technologies.length > 0 && (
                    <span style={{ fontStyle: 'italic' }}> | {pr.technologies.join(', ')}</span>
                  )}
                </span>
              }
              subRight={formatDateRange(pr.startDate, pr.endDate)}
              body={pr.description}
              bullets={pr.highlights}
            />
          ))}
        </Section>
      )}

      {data.skills.length > 0 && (
        <Section title="Technical Skills" accent={accent}>
          {data.skills.map((sk) => (
            <div key={sk.id} style={{ marginBottom: 2 }}>
              <span style={{ fontWeight: 700 }}>{sk.category}:</span>{' '}
              <span>{sk.items.join(', ')}</span>
            </div>
          ))}
        </Section>
      )}

      {data.publications.length > 0 && (
        <Section title="Publications" accent={accent}>
          {data.publications.map((pb) => (
            <div key={pb.id} style={{ marginBottom: 4 }}>
              <div style={{ fontWeight: 700 }}>{pb.title}</div>
              <div style={{ fontSize: 10, fontStyle: 'italic' }}>
                {joinNonEmpty([pb.publisher, pb.releaseDate])}
              </div>
              {pb.summary && <div style={{ fontSize: 10.5, marginTop: 1 }}>{pb.summary}</div>}
            </div>
          ))}
        </Section>
      )}

      {data.profiles.length > 0 && (
        <Section title="Profiles" accent={accent}>
          {data.profiles.map((pf) => (
            <div key={pf.id} style={{ marginBottom: 2 }}>
              <span style={{ fontWeight: 700 }}>{pf.network}:</span>{' '}
              <span>{pf.url || pf.username || '—'}</span>
            </div>
          ))}
        </Section>
      )}
    </A4Page>
  );
}

function Section({
  title,
  accent,
  children,
}: {
  title: string;
  accent: string;
  children: React.ReactNode;
}) {
  return (
    <section style={{ marginBottom: 10 }}>
      <h2
        style={{
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: accent,
          margin: '0 0 3px 0',
          paddingBottom: 1,
          borderBottom: `0.6px solid ${accent}`,
        }}
      >
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}

function Entry({
  left,
  right,
  subLeft,
  subRight,
  body,
  bullets,
}: {
  left: React.ReactNode;
  right?: React.ReactNode;
  subLeft?: React.ReactNode;
  subRight?: React.ReactNode;
  body?: string;
  bullets?: string[];
}) {
  return (
    <div data-page-block style={{ marginBottom: 7 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
        <div style={{ fontWeight: 700 }}>{left}</div>
        {right && <div style={{ fontSize: 10 }}>{right}</div>}
      </div>
      {(subLeft || subRight) && (
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
          {subLeft && <div style={{ fontStyle: 'italic' }}>{subLeft}</div>}
          {subRight && <div style={{ fontStyle: 'italic', fontSize: 10 }}>{subRight}</div>}
        </div>
      )}
      {body && <div style={{ marginTop: 2 }}>{body}</div>}
      {bullets && bullets.length > 0 && (
        <ul style={{ margin: '2px 0 0 16px', padding: 0 }}>
          {bullets.map((h, i) => (
            <li key={i} style={{ marginBottom: 1 }}>
              {h}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
