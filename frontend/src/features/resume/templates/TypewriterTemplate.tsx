// Designer — typewriter. Body in monospace; the name is a serif
// display script. Em-dash prefix on each section head reads like a
// chapter break in a typed manuscript. Vintage-modern hybrid; works
// well for candidates who want personality without screaming.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

export default function TypewriterTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#3a2a1a';
  const fontFamily =
    design?.typography?.body?.family ??
    "'Courier Prime', 'Courier New', 'IBM Plex Mono', ui-monospace, monospace";
  const headFamily =
    design?.typography?.heading?.family ?? "'Playfair Display', 'Georgia', serif";
  const fontSize = design?.typography?.body?.size ?? 10;
  const marginMm = (design?.spacing?.margin ?? 16) | 0;

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
    <A4Page marginMm={marginMm} fontFamily={fontFamily} fontSize={fontSize} bulletStyle={design?.bulletStyle}>
      <header style={{ marginBottom: 14, textAlign: 'center' }}>
        <div
          style={{
            fontFamily: headFamily,
            fontSize: 36,
            fontWeight: 400,
            color: accent,
            lineHeight: 1.0,
            letterSpacing: '-0.01em',
          }}
        >
          {p.fullName || 'Your name'}
        </div>
        {p.title && (
          <div style={{ fontSize: 10, color: '#444', marginTop: 6 }}>— {p.title} —</div>
        )}
        {meta && (
          <div style={{ fontSize: 9.5, color: '#555', marginTop: 6 }}>{meta}</div>
        )}
      </header>

      {p.summary && (
        <Section title="Summary" accent={accent} headFamily={headFamily}>
          <p style={{ margin: 0 }}>{p.summary}</p>
        </Section>
      )}

      {data.experience.length > 0 && (
        <Section title="Experience" accent={accent} headFamily={headFamily}>
          {data.experience.map((e) => (
            <div key={e.id} data-page-block style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ fontWeight: 700 }}>{e.position || '—'}</div>
                <div style={{ fontSize: 9, color: '#555' }}>
                  {formatDateRange(e.startDate, e.endDate, e.current)}
                </div>
              </div>
              <div style={{ fontSize: 10, color: '#444' }}>
                {joinNonEmpty([e.company, e.location])}
              </div>
              {e.description && (
                <div style={{ fontSize: 10, marginTop: 3 }}>{e.description}</div>
              )}
              {e.highlights.length > 0 && (
                <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                  {e.highlights.map((h, i) => (
                    <li key={i} style={{ marginBottom: 2 }}>{h}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </Section>
      )}

      {data.projects.length > 0 && (
        <Section title="Projects" accent={accent} headFamily={headFamily}>
          {data.projects.map((pr) => (
            <div key={pr.id} data-page-block style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ fontWeight: 700 }}>{pr.name || '—'}</div>
                <div style={{ fontSize: 9, color: '#555' }}>
                  {formatDateRange(pr.startDate, pr.endDate)}
                </div>
              </div>
              {pr.technologies.length > 0 && (
                <div style={{ fontSize: 10, color: '#444' }}>{pr.technologies.join(' · ')}</div>
              )}
              {pr.description && (
                <div style={{ fontSize: 10, marginTop: 3 }}>{pr.description}</div>
              )}
              {pr.highlights.length > 0 && (
                <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
                  {pr.highlights.map((h, i) => (
                    <li key={i} style={{ marginBottom: 2 }}>{h}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </Section>
      )}

      {data.education.length > 0 && (
        <Section title="Education" accent={accent} headFamily={headFamily}>
          {data.education.map((ed) => (
            <div key={ed.id} data-page-block style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ fontWeight: 700 }}>{ed.institution || '—'}</div>
                <div style={{ fontSize: 9, color: '#555' }}>
                  {formatDateRange(ed.startDate, ed.endDate)}
                </div>
              </div>
              <div style={{ fontSize: 10, color: '#444' }}>
                {joinNonEmpty([ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : undefined])}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.skills.length > 0 && (
        <Section title="Skills" accent={accent} headFamily={headFamily}>
          {data.skills.map((sk) => (
            <div key={sk.id} style={{ marginBottom: 4 }}>
              <span style={{ fontWeight: 700 }}>{sk.category}:</span>{' '}
              <span>{sk.items.join(', ')}</span>
            </div>
          ))}
        </Section>
      )}

      {data.publications.length > 0 && (
        <Section title="Publications" accent={accent} headFamily={headFamily}>
          {data.publications.map((pb) => (
            <div key={pb.id} data-page-block style={{ marginBottom: 6 }}>
              <div style={{ fontWeight: 700 }}>{pb.title}</div>
              <div style={{ fontSize: 10, color: '#555' }}>
                {joinNonEmpty([pb.publisher, pb.releaseDate])}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.profiles.length > 0 && (
        <Section title="Profiles" accent={accent} headFamily={headFamily}>
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
  headFamily,
  children,
}: {
  title: string;
  accent: string;
  headFamily: string;
  children: React.ReactNode;
}) {
  return (
    <section style={{ marginBottom: 12 }}>
      <h2
        style={{
          fontFamily: headFamily,
          fontSize: 14,
          fontWeight: 400,
          color: accent,
          margin: '0 0 5px 0',
          letterSpacing: '0.01em',
        }}
      >
        — {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
