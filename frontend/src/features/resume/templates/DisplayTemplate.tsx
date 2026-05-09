// Bold — display. The name is the page: an oversized italic
// display-serif headline, set tight against the left edge so it
// reads almost like a magazine cover. Body underneath is a tight,
// dense serif. The type is the design — minimal other ornaments.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

export default function DisplayTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#7c3a4e';
  const fontFamily =
    design?.typography?.body?.family ??
    "'Source Serif Pro', 'Georgia', 'Times New Roman', serif";
  const headFamily =
    design?.typography?.heading?.family ?? "'Playfair Display', 'Georgia', serif";
  const fontSize = design?.typography?.body?.size ?? 10;
  const marginMm = (design?.spacing?.margin ?? 18) | 0;

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
      <header style={{ marginBottom: 22 }}>
        <div
          style={{
            fontFamily: headFamily,
            fontStyle: 'italic',
            fontSize: 64,
            fontWeight: 400,
            color: accent,
            lineHeight: 0.9,
            letterSpacing: '-0.02em',
          }}
        >
          {p.fullName || 'Your name'}
        </div>
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'baseline',
            gap: 12,
            marginTop: 12,
            paddingTop: 8,
            borderTop: `2px solid ${accent}`,
          }}
        >
          {p.title ? (
            <div
              style={{
                fontSize: 11,
                color: '#222',
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.18em',
              }}
            >
              {p.title}
            </div>
          ) : (
            <span />
          )}
          {meta && (
            <div style={{ fontSize: 9.5, color: '#555', textAlign: 'right' }}>{meta}</div>
          )}
        </div>
      </header>

      {p.summary && (
        <Section title="Summary" accent={accent} headFamily={headFamily}>
          <p style={{ margin: 0, lineHeight: 1.55 }}>{p.summary}</p>
        </Section>
      )}

      {data.experience.length > 0 && (
        <Section title="Experience" accent={accent} headFamily={headFamily}>
          {data.experience.map((e) => (
            <div key={e.id} data-page-block style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
                <div style={{ fontWeight: 700 }}>
                  {e.position || '—'}
                  {e.company && (
                    <span style={{ fontWeight: 400, fontStyle: 'italic', color: '#555' }}>
                      {' · '}{e.company}
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 10, color: '#666', fontStyle: 'italic', whiteSpace: 'nowrap' }}>
                  {formatDateRange(e.startDate, e.endDate, e.current)}
                </div>
              </div>
              {e.location && (
                <div style={{ fontSize: 10, color: '#777', fontStyle: 'italic' }}>{e.location}</div>
              )}
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
            <div key={pr.id} data-page-block style={{ marginBottom: 9 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
                <div style={{ fontWeight: 700 }}>{pr.name || '—'}</div>
                <div style={{ fontSize: 10, color: '#666', fontStyle: 'italic' }}>
                  {formatDateRange(pr.startDate, pr.endDate)}
                </div>
              </div>
              {pr.technologies.length > 0 && (
                <div style={{ fontSize: 10, color: '#777', fontStyle: 'italic' }}>
                  {pr.technologies.join(' · ')}
                </div>
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
            <div key={ed.id} data-page-block style={{ marginBottom: 7 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
                <div style={{ fontWeight: 700 }}>{ed.institution || '—'}</div>
                <div style={{ fontSize: 10, color: '#666', fontStyle: 'italic' }}>
                  {formatDateRange(ed.startDate, ed.endDate)}
                </div>
              </div>
              <div style={{ fontSize: 10, color: '#444', fontStyle: 'italic' }}>
                {joinNonEmpty([ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : undefined])}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.skills.length > 0 && (
        <Section title="Skills" accent={accent} headFamily={headFamily}>
          {data.skills.map((sk) => (
            <div key={sk.id} style={{ marginBottom: 3, fontSize: 10 }}>
              <span style={{ fontWeight: 700 }}>{sk.category}:</span>{' '}
              <span>{sk.items.join(', ')}</span>
            </div>
          ))}
        </Section>
      )}

      {data.publications.length > 0 && (
        <Section title="Publications" accent={accent} headFamily={headFamily}>
          {data.publications.map((pb) => (
            <div key={pb.id} data-page-block style={{ marginBottom: 5 }}>
              <div style={{ fontWeight: 700 }}>{pb.title}</div>
              <div style={{ fontSize: 10, color: '#666', fontStyle: 'italic' }}>
                {joinNonEmpty([pb.publisher, pb.releaseDate])}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.profiles.length > 0 && (
        <Section title="Profiles" accent={accent} headFamily={headFamily}>
          {data.profiles.map((pf) => (
            <div key={pf.id} style={{ marginBottom: 2, fontSize: 10 }}>
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
          fontStyle: 'italic',
          fontSize: 22,
          fontWeight: 400,
          color: accent,
          margin: '0 0 6px 0',
          letterSpacing: '-0.01em',
        }}
      >
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
