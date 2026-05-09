// Single-column, generous whitespace, sans-serif. The accent color
// (default: warm steel-blue) drives section headings and the name
// bar. Sober enough for FAANG-style hiring; airy enough not to feel
// like a Word doc.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

export default function ModernTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#1f3b56';
  const fontFamily =
    design?.typography?.body?.family ?? "'Inter', 'Helvetica Neue', system-ui, sans-serif";
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
      <header style={{ marginBottom: 14, borderBottom: `2px solid ${accent}`, paddingBottom: 8 }}>
        <div
          style={{
            fontSize: 26,
            fontWeight: 600,
            letterSpacing: '-0.01em',
            color: accent,
          }}
        >
          {p.fullName || 'Your name'}
        </div>
        {p.title && (
          <div style={{ fontSize: 13, color: '#444', marginTop: 2 }}>{p.title}</div>
        )}
        {meta && (
          <div style={{ fontSize: 10, color: '#555', marginTop: 4 }}>{meta}</div>
        )}
      </header>

      {p.summary && (
        <Section title="Summary" accent={accent}>
          <p style={{ margin: 0 }}>{p.summary}</p>
        </Section>
      )}

      {data.experience.length > 0 && (
        <Section title="Experience" accent={accent}>
          {data.experience.map((e) => (
            <div key={e.id} data-page-block style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ fontWeight: 600 }}>{e.position || '—'}</div>
                <div style={{ fontSize: 10, color: '#555' }}>
                  {formatDateRange(e.startDate, e.endDate, e.current)}
                </div>
              </div>
              <div style={{ fontSize: 10.5, color: '#444' }}>
                {joinNonEmpty([e.company, e.location])}
              </div>
              {e.description && (
                <div style={{ fontSize: 10.5, marginTop: 4 }}>{e.description}</div>
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

      {data.projects.length > 0 && (
        <Section title="Projects" accent={accent}>
          {data.projects.map((pr) => (
            <div key={pr.id} data-page-block style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ fontWeight: 600 }}>{pr.name || '—'}</div>
                <div style={{ fontSize: 10, color: '#555' }}>
                  {formatDateRange(pr.startDate, pr.endDate)}
                </div>
              </div>
              {pr.technologies.length > 0 && (
                <div style={{ fontSize: 10.5, color: '#444' }}>{pr.technologies.join(' · ')}</div>
              )}
              {pr.description && (
                <div style={{ fontSize: 10.5, marginTop: 4 }}>{pr.description}</div>
              )}
              {pr.highlights.length > 0 && (
                <ul style={{ margin: '4px 0 0 18px', padding: 0 }}>
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

      {data.education.length > 0 && (
        <Section title="Education" accent={accent}>
          {data.education.map((ed) => (
            <div key={ed.id} data-page-block style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ fontWeight: 600 }}>{ed.institution || '—'}</div>
                <div style={{ fontSize: 10, color: '#555' }}>
                  {formatDateRange(ed.startDate, ed.endDate)}
                </div>
              </div>
              <div style={{ fontSize: 10.5, color: '#444' }}>
                {joinNonEmpty([ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : undefined])}
              </div>
              {ed.description && (
                <div style={{ fontSize: 10.5, marginTop: 2 }}>{ed.description}</div>
              )}
            </div>
          ))}
        </Section>
      )}

      {data.skills.length > 0 && (
        <Section title="Skills" accent={accent}>
          {data.skills.map((sk) => (
            <div key={sk.id} style={{ marginBottom: 4 }}>
              <span style={{ fontWeight: 600 }}>{sk.category}:</span>{' '}
              <span>{sk.items.join(', ')}</span>
            </div>
          ))}
        </Section>
      )}

      {data.publications.length > 0 && (
        <Section title="Publications" accent={accent}>
          {data.publications.map((pb) => (
            <div key={pb.id} data-page-block style={{ marginBottom: 6 }}>
              <div style={{ fontWeight: 600 }}>{pb.title}</div>
              <div style={{ fontSize: 10.5, color: '#555' }}>
                {joinNonEmpty([pb.publisher, pb.releaseDate])}
              </div>
              {pb.summary && (
                <div style={{ fontSize: 10.5, marginTop: 2 }}>{pb.summary}</div>
              )}
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
    <section style={{ marginBottom: 12 }}>
      <h2
        style={{
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: '0.16em',
          textTransform: 'uppercase',
          color: accent,
          margin: '0 0 6px 0',
          borderBottom: `1px solid ${accent}33`,
          paddingBottom: 2,
        }}
      >
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
