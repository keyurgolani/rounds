// Document-first style inspired by Notion / Linear / modern startup
// tooling. Light gray dividers, sans-serif, pill-shaped tech tags,
// regular-weight section heads (no SHOUTING small-caps). Reads more
// like a polished doc than a traditional resume — fits the aesthetic
// of recruiters at modern infra/dev-tools companies.
//
// Single-column for ATS safety. Tech tags are real text (not images),
// so parsers see "Python, Rust, Postgres" the same as a comma-list.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

export default function NotionTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#3b82a8';
  const fontFamily =
    design?.typography?.body?.family ??
    "'Inter', 'Helvetica Neue', system-ui, sans-serif";
  const fontSize = design?.typography?.body?.size ?? 10.5;
  const marginMm = (design?.spacing?.margin ?? 14) | 0;

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
      <header style={{ marginBottom: 16 }}>
        <div
          style={{
            fontSize: 24,
            fontWeight: 600,
            letterSpacing: '-0.015em',
            color: '#1a1a1a',
            lineHeight: 1.1,
          }}
        >
          {p.fullName || 'Your name'}
        </div>
        {p.title && (
          <div style={{ fontSize: 12.5, color: '#555', marginTop: 4 }}>{p.title}</div>
        )}
        {meta && (
          <div style={{ fontSize: 10, color: '#777', marginTop: 8 }}>{meta}</div>
        )}
      </header>

      {p.summary && (
        <Section title="About" accent={accent}>
          <p style={{ margin: 0, color: '#333', lineHeight: 1.6 }}>{p.summary}</p>
        </Section>
      )}

      {data.experience.length > 0 && (
        <Section title="Experience" accent={accent}>
          {data.experience.map((e) => (
            <div key={e.id} data-page-block style={{ marginBottom: 12 }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 8,
                  alignItems: 'baseline',
                }}
              >
                <div style={{ fontSize: 12.5, fontWeight: 600, color: '#1a1a1a' }}>
                  {e.position || '—'}
                </div>
                <div style={{ fontSize: 10, color: '#888', whiteSpace: 'nowrap' }}>
                  {formatDateRange(e.startDate, e.endDate, e.current)}
                </div>
              </div>
              <div style={{ fontSize: 11, color: accent, fontWeight: 500 }}>
                {joinNonEmpty([e.company, e.location], ' · ')}
              </div>
              {e.description && (
                <div style={{ fontSize: 10.5, color: '#444', marginTop: 4, lineHeight: 1.55 }}>
                  {e.description}
                </div>
              )}
              {e.highlights.length > 0 && (
                <ul
                  style={{
                    margin: '4px 0 0 18px',
                    padding: 0,
                    color: '#333',
                    lineHeight: 1.55,
                  }}
                >
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

      {data.projects.length > 0 && (
        <Section title="Projects" accent={accent}>
          {data.projects.map((pr) => (
            <div key={pr.id} data-page-block style={{ marginBottom: 12 }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 8,
                  alignItems: 'baseline',
                }}
              >
                <div style={{ fontSize: 12.5, fontWeight: 600, color: '#1a1a1a' }}>
                  {pr.name || '—'}
                </div>
                <div style={{ fontSize: 10, color: '#888', whiteSpace: 'nowrap' }}>
                  {formatDateRange(pr.startDate, pr.endDate)}
                </div>
              </div>
              {pr.technologies.length > 0 && (
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
                  {pr.technologies.map((t, i) => (
                    <Pill key={i} accent={accent}>
                      {t}
                    </Pill>
                  ))}
                </div>
              )}
              {pr.description && (
                <div style={{ fontSize: 10.5, color: '#444', marginTop: 5, lineHeight: 1.55 }}>
                  {pr.description}
                </div>
              )}
              {pr.highlights.length > 0 && (
                <ul
                  style={{
                    margin: '4px 0 0 18px',
                    padding: 0,
                    color: '#333',
                    lineHeight: 1.55,
                  }}
                >
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
            <div key={sk.id} style={{ marginBottom: 6 }}>
              <div style={{ fontSize: 10.5, fontWeight: 600, color: '#444', marginBottom: 3 }}>
                {sk.category}
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {sk.items.map((item, i) => (
                  <Pill key={i} accent={accent}>
                    {item}
                  </Pill>
                ))}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.education.length > 0 && (
        <Section title="Education" accent={accent}>
          {data.education.map((ed) => (
            <div key={ed.id} data-page-block style={{ marginBottom: 8 }}>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 8,
                  alignItems: 'baseline',
                }}
              >
                <div style={{ fontWeight: 600, color: '#1a1a1a' }}>{ed.institution || '—'}</div>
                <div style={{ fontSize: 10, color: '#888', whiteSpace: 'nowrap' }}>
                  {formatDateRange(ed.startDate, ed.endDate)}
                </div>
              </div>
              <div style={{ fontSize: 10.5, color: '#555' }}>
                {joinNonEmpty([ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : undefined])}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.publications.length > 0 && (
        <Section title="Publications" accent={accent}>
          {data.publications.map((pb) => (
            <div key={pb.id} data-page-block style={{ marginBottom: 6 }}>
              <div style={{ fontWeight: 600 }}>{pb.title}</div>
              <div style={{ fontSize: 10, color: '#777' }}>
                {joinNonEmpty([pb.publisher, pb.releaseDate])}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.profiles.length > 0 && (
        <Section title="Profiles" accent={accent}>
          {data.profiles.map((pf) => (
            <div key={pf.id} style={{ marginBottom: 2, fontSize: 10.5 }}>
              <span style={{ color: '#777' }}>{pf.network}</span>
              {' → '}
              <span style={{ color: accent }}>{pf.url || pf.username || '—'}</span>
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
    <section style={{ marginBottom: 16 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          margin: '0 0 8px 0',
        }}
      >
        <h2
          style={{
            fontSize: 12.5,
            fontWeight: 600,
            color: '#1a1a1a',
            margin: 0,
          }}
        >
          {title}
        </h2>
        <div style={{ flex: 1, height: 1, background: `${accent}33` }} />
      </div>
      <div>{children}</div>
    </section>
  );
}

function Pill({ accent, children }: { accent: string; children: React.ReactNode }) {
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 8px',
        borderRadius: 999,
        background: `${accent}15`,
        color: accent,
        fontSize: 9.5,
        fontWeight: 500,
        lineHeight: 1.4,
      }}
    >
      {children}
    </span>
  );
}
