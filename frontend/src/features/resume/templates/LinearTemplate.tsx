// Designer — linear. Inspired by Linear / Vercel design language:
// micro-typographic precision, lowercase labels, monospaced metadata,
// the lightest possible dividers. Pristine and quiet — most readers
// will not consciously notice the design at all, which is the goal.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

export default function LinearTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#5b6cff';
  const fontFamily =
    design?.typography?.body?.family ?? "'Inter', 'Helvetica Neue', system-ui, sans-serif";
  const fontSize = design?.typography?.body?.size ?? 10.5;
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
      <header style={{ marginBottom: 18 }}>
        <div
          style={{
            fontSize: 22,
            fontWeight: 600,
            letterSpacing: '-0.02em',
            color: '#0a0a0a',
            lineHeight: 1.1,
          }}
        >
          {p.fullName || 'Your name'}
        </div>
        {p.title && (
          <div style={{ fontSize: 11, color: '#666', marginTop: 3, fontWeight: 500 }}>
            {p.title}
          </div>
        )}
        {meta && (
          <div
            style={{
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
              fontSize: 9,
              color: '#888',
              marginTop: 8,
              letterSpacing: '-0.01em',
            }}
          >
            {meta}
          </div>
        )}
      </header>

      {p.summary && (
        <Section title="summary" accent={accent}>
          <p style={{ margin: 0, color: '#222', lineHeight: 1.6 }}>{p.summary}</p>
        </Section>
      )}

      {data.experience.length > 0 && (
        <Section title="experience" accent={accent}>
          {data.experience.map((e) => (
            <div key={e.id} data-page-block style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
                <div style={{ fontWeight: 600, fontSize: 12, color: '#0a0a0a' }}>
                  {e.position || '—'}
                </div>
                <div
                  style={{
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                    fontSize: 9,
                    color: '#888',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {formatDateRange(e.startDate, e.endDate, e.current)}
                </div>
              </div>
              <div style={{ fontSize: 10.5, color: accent, fontWeight: 500 }}>
                {joinNonEmpty([e.company, e.location])}
              </div>
              {e.description && (
                <div style={{ fontSize: 10.5, color: '#333', marginTop: 4, lineHeight: 1.55 }}>
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
                    <li key={i} style={{ marginBottom: 2 }}>{h}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </Section>
      )}

      {data.projects.length > 0 && (
        <Section title="projects" accent={accent}>
          {data.projects.map((pr) => (
            <div key={pr.id} data-page-block style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
                <div style={{ fontWeight: 600, fontSize: 12, color: '#0a0a0a' }}>
                  {pr.name || '—'}
                </div>
                <div
                  style={{
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                    fontSize: 9,
                    color: '#888',
                  }}
                >
                  {formatDateRange(pr.startDate, pr.endDate)}
                </div>
              </div>
              {pr.technologies.length > 0 && (
                <div
                  style={{
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                    fontSize: 9,
                    color: '#888',
                  }}
                >
                  {pr.technologies.join(' · ')}
                </div>
              )}
              {pr.description && (
                <div style={{ fontSize: 10.5, color: '#333', marginTop: 3 }}>{pr.description}</div>
              )}
              {pr.highlights.length > 0 && (
                <ul style={{ margin: '4px 0 0 18px', padding: 0, color: '#333' }}>
                  {pr.highlights.map((h, i) => (
                    <li key={i} style={{ marginBottom: 2 }}>{h}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </Section>
      )}

      {data.skills.length > 0 && (
        <Section title="skills" accent={accent}>
          {data.skills.map((sk) => (
            <div key={sk.id} style={{ marginBottom: 4 }}>
              <span style={{ color: '#888', fontSize: 10 }}>{sk.category.toLowerCase()}</span>
              <br />
              <span>{sk.items.join(', ')}</span>
            </div>
          ))}
        </Section>
      )}

      {data.education.length > 0 && (
        <Section title="education" accent={accent}>
          {data.education.map((ed) => (
            <div key={ed.id} data-page-block style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
                <div style={{ fontWeight: 600, color: '#0a0a0a' }}>{ed.institution || '—'}</div>
                <div
                  style={{
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                    fontSize: 9,
                    color: '#888',
                  }}
                >
                  {formatDateRange(ed.startDate, ed.endDate)}
                </div>
              </div>
              <div style={{ fontSize: 10.5, color: '#444' }}>
                {joinNonEmpty([ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : undefined])}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.publications.length > 0 && (
        <Section title="publications" accent={accent}>
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
        <Section title="profiles" accent={accent}>
          {data.profiles.map((pf) => (
            <div key={pf.id} style={{ marginBottom: 2 }}>
              <span style={{ color: '#888' }}>{pf.network.toLowerCase()}</span>
              {' '}
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
    <section style={{ marginBottom: 16 }}>
      <h2
        style={{
          fontSize: 9.5,
          fontWeight: 600,
          color: accent,
          margin: '0 0 6px 0',
          letterSpacing: '0.05em',
        }}
      >
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
