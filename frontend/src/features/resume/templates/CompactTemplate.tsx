// Two-column dense layout inspired by Debarghya "Deedy" Das's resume.
// Left column (experience + projects) gets ~62% of the page; the right
// column (skills, education, publications, profiles) carries the rest.
// Designed for senior candidates with enough material to fill both
// columns — a junior resume can look thin in this format.
//
// ATS note: the layout is true CSS grid, not table-based. Most modern
// parsers (Greenhouse, Workday, Lever, Ashby) handle it fine; older
// keyword scrapers may interleave columns. Use SWELatex if you're
// targeting a stack that's known to mis-read multi-column resumes.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

export default function CompactTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#2c3e50';
  const fontFamily =
    design?.typography?.body?.family ?? "'Inter', 'Helvetica Neue', system-ui, sans-serif";
  const fontSize = design?.typography?.body?.size ?? 9.5;
  const marginMm = (design?.spacing?.margin ?? 12) | 0;

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
      {/* Header spans both columns */}
      <header style={{ marginBottom: 12 }}>
        <div
          style={{
            fontSize: 24,
            fontWeight: 700,
            letterSpacing: '-0.01em',
            color: accent,
            lineHeight: 1.05,
          }}
        >
          {p.fullName || 'Your name'}
        </div>
        {p.title && (
          <div style={{ fontSize: 12, color: '#444', marginTop: 2 }}>{p.title}</div>
        )}
        {p.subtitle && (
          <div style={{ fontSize: 10.5, color: '#666', marginTop: 1 }}>{p.subtitle}</div>
        )}
        {meta && (
          <div style={{ fontSize: 9.5, color: '#555', marginTop: 4 }}>{meta}</div>
        )}
        <div style={{ height: 2, background: accent, marginTop: 8 }} />
      </header>

      {p.summary && (
        <Section title="Summary" accent={accent}>
          <p style={{ margin: 0 }}>{p.summary}</p>
        </Section>
      )}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.6fr) minmax(0, 1fr)',
          gap: 18,
          alignItems: 'start',
        }}
      >
        {/* Left column: Experience + Projects (the bulk) */}
        <div>
          {data.experience.length > 0 && (
            <Section title="Experience" accent={accent}>
              {data.experience.map((e) => (
                <div key={e.id} data-page-block style={{ marginBottom: 10 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6 }}>
                    <div style={{ fontWeight: 700 }}>{e.position || '—'}</div>
                    <div style={{ fontSize: 9, color: '#555', whiteSpace: 'nowrap' }}>
                      {formatDateRange(e.startDate, e.endDate, e.current)}
                    </div>
                  </div>
                  <div style={{ fontSize: 9.5, color: '#444', fontStyle: 'italic' }}>
                    {joinNonEmpty([e.company, e.location])}
                  </div>
                  {e.description && (
                    <div style={{ fontSize: 9.5, marginTop: 3 }}>{e.description}</div>
                  )}
                  {e.highlights.length > 0 && (
                    <ul style={{ margin: '3px 0 0 16px', padding: 0 }}>
                      {e.highlights.map((h, i) => (
                        <li key={i} style={{ marginBottom: 1.5 }}>
                          {h}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </Section>
          )}

          {data.projects.length > 0 && (
            <Section title="Projects" accent={accent}>
              {data.projects.map((pr) => (
                <div key={pr.id} data-page-block style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 6 }}>
                    <div style={{ fontWeight: 700 }}>{pr.name || '—'}</div>
                    <div style={{ fontSize: 9, color: '#555', whiteSpace: 'nowrap' }}>
                      {formatDateRange(pr.startDate, pr.endDate)}
                    </div>
                  </div>
                  {pr.technologies.length > 0 && (
                    <div style={{ fontSize: 9.5, color: '#444' }}>{pr.technologies.join(' · ')}</div>
                  )}
                  {pr.description && (
                    <div style={{ fontSize: 9.5, marginTop: 3 }}>{pr.description}</div>
                  )}
                  {pr.highlights.length > 0 && (
                    <ul style={{ margin: '3px 0 0 16px', padding: 0 }}>
                      {pr.highlights.map((h, i) => (
                        <li key={i} style={{ marginBottom: 1.5 }}>
                          {h}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ))}
            </Section>
          )}
        </div>

        {/* Right column: Skills, Education, Publications, Profiles */}
        <div>
          {data.skills.length > 0 && (
            <Section title="Skills" accent={accent}>
              {data.skills.map((sk) => (
                <div key={sk.id} style={{ marginBottom: 5 }}>
                  <div style={{ fontWeight: 700, fontSize: 9.5 }}>{sk.category}</div>
                  <div style={{ fontSize: 9.5, color: '#333', lineHeight: 1.45 }}>
                    {sk.items.join(', ')}
                  </div>
                </div>
              ))}
            </Section>
          )}

          {data.education.length > 0 && (
            <Section title="Education" accent={accent}>
              {data.education.map((ed) => (
                <div key={ed.id} data-page-block style={{ marginBottom: 7 }}>
                  <div style={{ fontWeight: 700 }}>{ed.institution || '—'}</div>
                  <div style={{ fontSize: 9.5, color: '#444' }}>
                    {joinNonEmpty([ed.degree, ed.field])}
                  </div>
                  <div style={{ fontSize: 9, color: '#555', marginTop: 1 }}>
                    {formatDateRange(ed.startDate, ed.endDate)}
                    {ed.gpa && ` · GPA ${ed.gpa}`}
                  </div>
                </div>
              ))}
            </Section>
          )}

          {data.publications.length > 0 && (
            <Section title="Publications" accent={accent}>
              {data.publications.map((pb) => (
                <div key={pb.id} data-page-block style={{ marginBottom: 6 }}>
                  <div style={{ fontWeight: 700, fontSize: 9.5 }}>{pb.title}</div>
                  <div style={{ fontSize: 9, color: '#555' }}>
                    {joinNonEmpty([pb.publisher, pb.releaseDate])}
                  </div>
                </div>
              ))}
            </Section>
          )}

          {data.profiles.length > 0 && (
            <Section title="Profiles" accent={accent}>
              {data.profiles.map((pf) => (
                <div key={pf.id} style={{ marginBottom: 2, fontSize: 9.5 }}>
                  <span style={{ fontWeight: 700 }}>{pf.network}:</span>{' '}
                  <span>{pf.url || pf.username || '—'}</span>
                </div>
              ))}
            </Section>
          )}
        </div>
      </div>
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
          fontSize: 10,
          fontWeight: 700,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: accent,
          margin: '0 0 4px 0',
          paddingBottom: 1,
          borderBottom: `1px solid ${accent}55`,
        }}
      >
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
