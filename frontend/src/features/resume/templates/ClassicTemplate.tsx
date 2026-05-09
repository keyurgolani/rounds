// Single-column serif. Centered name + contact block, subtle small-caps
// section heads, simple horizontal rules. Good when the recipient is
// likely to read on paper or expects a "real resume" look.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

export default function ClassicTemplate({ data, design }: Props) {
  const fontFamily =
    design?.typography?.body?.family ?? "'Source Serif Pro', 'Georgia', 'Times New Roman', serif";
  const fontSize = design?.typography?.body?.size ?? 10.5;
  const marginMm = (design?.spacing?.margin ?? 16) | 0;
  const accent = design?.colors?.primary ?? '#111';

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
      <header style={{ textAlign: 'center', marginBottom: 12 }}>
        <div style={{ fontSize: 22, fontWeight: 600, letterSpacing: '0.02em' }}>
          {p.fullName || 'Your name'}
        </div>
        {p.title && (
          <div style={{ fontSize: 12, fontStyle: 'italic', color: '#333', marginTop: 2 }}>
            {p.title}
          </div>
        )}
        {meta && (
          <div style={{ fontSize: 10, color: '#444', marginTop: 4 }}>{meta}</div>
        )}
      </header>

      {p.summary && (
        <Section title="Summary" accent={accent}>
          <p style={{ margin: 0, textAlign: 'justify' }}>{p.summary}</p>
        </Section>
      )}

      {data.experience.length > 0 && (
        <Section title="Experience" accent={accent}>
          {data.experience.map((e) => (
            <div key={e.id} data-page-block style={{ marginBottom: 9 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ fontWeight: 600 }}>
                  {e.company}
                  {e.position && <span style={{ fontWeight: 400 }}>, {e.position}</span>}
                </div>
                <div style={{ fontStyle: 'italic', color: '#444', fontSize: 10 }}>
                  {formatDateRange(e.startDate, e.endDate, e.current)}
                </div>
              </div>
              {e.location && (
                <div style={{ fontSize: 10.5, color: '#444', fontStyle: 'italic' }}>
                  {e.location}
                </div>
              )}
              {e.description && (
                <div style={{ fontSize: 10.5, marginTop: 3 }}>{e.description}</div>
              )}
              {e.highlights.length > 0 && (
                <ul style={{ margin: '3px 0 0 18px', padding: 0 }}>
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
        <Section title="Education" accent={accent}>
          {data.education.map((ed) => (
            <div key={ed.id} data-page-block style={{ marginBottom: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ fontWeight: 600 }}>{ed.institution}</div>
                <div style={{ fontStyle: 'italic', color: '#444', fontSize: 10 }}>
                  {formatDateRange(ed.startDate, ed.endDate)}
                </div>
              </div>
              <div style={{ fontSize: 10.5, color: '#333' }}>
                {joinNonEmpty([ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : undefined])}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.projects.length > 0 && (
        <Section title="Projects" accent={accent}>
          {data.projects.map((pr) => (
            <div key={pr.id} data-page-block style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: 600 }}>{pr.name}</div>
              {pr.technologies.length > 0 && (
                <div style={{ fontSize: 10.5, color: '#444', fontStyle: 'italic' }}>
                  {pr.technologies.join(', ')}
                </div>
              )}
              {pr.description && (
                <div style={{ fontSize: 10.5, marginTop: 2 }}>{pr.description}</div>
              )}
              {pr.highlights.length > 0 && (
                <ul style={{ margin: '2px 0 0 18px', padding: 0 }}>
                  {pr.highlights.map((h, i) => (
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

      {data.skills.length > 0 && (
        <Section title="Skills" accent={accent}>
          {data.skills.map((sk) => (
            <div key={sk.id} style={{ marginBottom: 3 }}>
              <span style={{ fontWeight: 600 }}>{sk.category}:</span>{' '}
              <span>{sk.items.join(', ')}</span>
            </div>
          ))}
        </Section>
      )}

      {data.publications.length > 0 && (
        <Section title="Publications" accent={accent}>
          {data.publications.map((pb) => (
            <div key={pb.id} data-page-block style={{ marginBottom: 5 }}>
              <div style={{ fontWeight: 600 }}>{pb.title}</div>
              <div style={{ fontSize: 10.5, color: '#444', fontStyle: 'italic' }}>
                {joinNonEmpty([pb.publisher, pb.releaseDate])}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.profiles.length > 0 && (
        <Section title="Profiles" accent={accent}>
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
          fontSize: 10.5,
          fontWeight: 700,
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: accent,
          margin: '0 0 4px 0',
          borderBottom: `0.5px solid ${accent}`,
          paddingBottom: 2,
        }}
      >
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
