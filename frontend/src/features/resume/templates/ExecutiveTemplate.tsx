// Single-column, dark serif headings, restrained palette. Heading
// dominance does the hierarchy work — body type stays compact so
// senior candidates fit a 2-page narrative without it feeling thin.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

export default function ExecutiveTemplate({ data, design }: Props) {
  const fontFamily =
    design?.typography?.body?.family ?? "'Source Sans Pro', 'Helvetica Neue', system-ui, sans-serif";
  const headFamily =
    design?.typography?.heading?.family ?? "'Playfair Display', 'Georgia', serif";
  const fontSize = design?.typography?.body?.size ?? 10;
  const marginMm = (design?.spacing?.margin ?? 14) | 0;
  const accent = design?.colors?.primary ?? '#0f172a';

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
      <header style={{ marginBottom: 14 }}>
        <div
          style={{
            fontFamily: headFamily,
            fontSize: 30,
            fontWeight: 600,
            letterSpacing: '0.005em',
            color: accent,
            lineHeight: 1.05,
          }}
        >
          {p.fullName || 'Your name'}
        </div>
        {p.title && (
          <div
            style={{
              fontSize: 12.5,
              color: '#374151',
              marginTop: 4,
              letterSpacing: '0.06em',
              textTransform: 'uppercase',
            }}
          >
            {p.title}
          </div>
        )}
        {meta && (
          <div style={{ fontSize: 9.5, color: '#374151', marginTop: 6 }}>{meta}</div>
        )}
      </header>

      {p.summary && (
        <Section title="Profile" accent={accent} headFamily={headFamily}>
          <p style={{ margin: 0, textAlign: 'justify' }}>{p.summary}</p>
        </Section>
      )}

      {data.experience.length > 0 && (
        <Section title="Experience" accent={accent} headFamily={headFamily}>
          {data.experience.map((e) => (
            <div key={e.id} data-page-block style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ fontWeight: 600, fontSize: 11.5 }}>{e.position || '—'}</div>
                <div style={{ fontSize: 9.5, color: '#374151' }}>
                  {formatDateRange(e.startDate, e.endDate, e.current)}
                </div>
              </div>
              <div style={{ fontSize: 10.5, color: '#374151', marginTop: 1 }}>
                {joinNonEmpty([e.company, e.location])}
              </div>
              {e.description && (
                <div style={{ marginTop: 4 }}>{e.description}</div>
              )}
              {e.highlights.length > 0 && (
                <ul style={{ margin: '4px 0 0 18px', padding: 0 }}>
                  {e.highlights.map((h, i) => (
                    <li key={i} style={{ marginBottom: 2 }}>
                      {h}
                    </li>
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
            <div key={ed.id} data-page-block style={{ marginBottom: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ fontWeight: 600 }}>{ed.institution}</div>
                <div style={{ fontSize: 9.5, color: '#374151' }}>
                  {formatDateRange(ed.startDate, ed.endDate)}
                </div>
              </div>
              <div style={{ fontSize: 10.5, color: '#374151' }}>
                {joinNonEmpty([ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : undefined])}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.projects.length > 0 && (
        <Section title="Selected Work" accent={accent} headFamily={headFamily}>
          {data.projects.map((pr) => (
            <div key={pr.id} data-page-block style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: 600 }}>{pr.name}</div>
              {pr.technologies.length > 0 && (
                <div style={{ fontSize: 10.5, color: '#374151' }}>
                  {pr.technologies.join(' · ')}
                </div>
              )}
              {pr.description && (
                <div style={{ fontSize: 10.5, marginTop: 2 }}>{pr.description}</div>
              )}
            </div>
          ))}
        </Section>
      )}

      {data.skills.length > 0 && (
        <Section title="Capabilities" accent={accent} headFamily={headFamily}>
          {data.skills.map((sk) => (
            <div key={sk.id} style={{ marginBottom: 3 }}>
              <span style={{ fontWeight: 600 }}>{sk.category}:</span>{' '}
              <span>{sk.items.join(', ')}</span>
            </div>
          ))}
        </Section>
      )}

      {data.publications.length > 0 && (
        <Section title="Publications" accent={accent} headFamily={headFamily}>
          {data.publications.map((pb) => (
            <div key={pb.id} data-page-block style={{ marginBottom: 4 }}>
              <div style={{ fontWeight: 600 }}>{pb.title}</div>
              <div style={{ fontSize: 10.5, color: '#374151' }}>
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
              <span style={{ fontWeight: 600 }}>{pf.network}:</span>{' '}
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
          fontSize: 13,
          fontWeight: 600,
          color: accent,
          margin: '0 0 6px 0',
          borderBottom: `1px solid ${accent}55`,
          paddingBottom: 3,
        }}
      >
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
