// All-monospace, opinionated, indie-dev distinctive. JetBrains Mono /
// IBM Plex Mono with a system fallback. Heavy black horizontal rules,
// ALL-CAPS section heads with mono kerning, no accent color (pure
// b/w by default — accent is honored if the user sets one).
//
// Reads almost like a terminal log. Eye-catching for hiring managers
// who scroll fast; less ATS-friendly than Modern/SWE-LaTeX because of
// the unusual visual hierarchy, but the structural HTML is normal.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

export default function BrutalistMonoTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#000';
  const fontFamily =
    design?.typography?.body?.family ??
    "'JetBrains Mono', 'IBM Plex Mono', 'Fira Code', 'Menlo', ui-monospace, monospace";
  const fontSize = design?.typography?.body?.size ?? 9.5;
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
      <header style={{ marginBottom: 14, borderBottom: `3px solid ${accent}`, paddingBottom: 8 }}>
        <div
          style={{
            fontSize: 22,
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.02em',
            color: accent,
            lineHeight: 1.0,
          }}
        >
          {(p.fullName || 'YOUR NAME').toUpperCase()}
        </div>
        {p.title && (
          <div
            style={{
              fontSize: 11,
              color: '#222',
              marginTop: 6,
              textTransform: 'uppercase',
              letterSpacing: '0.16em',
            }}
          >
            // {p.title}
          </div>
        )}
        {p.subtitle && (
          <div
            style={{
              fontSize: 10,
              color: '#444',
              marginTop: 2,
              textTransform: 'uppercase',
              letterSpacing: '0.14em',
            }}
          >
            // {p.subtitle}
          </div>
        )}
        {meta && (
          <div style={{ fontSize: 9.5, color: '#333', marginTop: 6 }}>{meta}</div>
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
                <div style={{ fontWeight: 700 }}>
                  {(e.position || '—').toUpperCase()}
                </div>
                <div style={{ fontSize: 9, color: '#333', whiteSpace: 'nowrap' }}>
                  [{formatDateRange(e.startDate, e.endDate, e.current)}]
                </div>
              </div>
              <div style={{ fontSize: 10, color: '#333' }}>
                {joinNonEmpty([e.company, e.location], ' / ')}
              </div>
              {e.description && (
                <div style={{ fontSize: 9.5, marginTop: 3 }}>{e.description}</div>
              )}
              {e.highlights.length > 0 && (
                <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
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
                <div style={{ fontWeight: 700 }}>{(pr.name || '—').toUpperCase()}</div>
                <div style={{ fontSize: 9, color: '#333', whiteSpace: 'nowrap' }}>
                  [{formatDateRange(pr.startDate, pr.endDate)}]
                </div>
              </div>
              {pr.technologies.length > 0 && (
                <div style={{ fontSize: 10, color: '#333' }}>
                  {pr.technologies.map((t) => `[${t}]`).join(' ')}
                </div>
              )}
              {pr.description && (
                <div style={{ fontSize: 9.5, marginTop: 3 }}>{pr.description}</div>
              )}
              {pr.highlights.length > 0 && (
                <ul style={{ margin: '4px 0 0 16px', padding: 0 }}>
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
            <div key={ed.id} data-page-block style={{ marginBottom: 7 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <div style={{ fontWeight: 700 }}>{(ed.institution || '—').toUpperCase()}</div>
                <div style={{ fontSize: 9, color: '#333', whiteSpace: 'nowrap' }}>
                  [{formatDateRange(ed.startDate, ed.endDate)}]
                </div>
              </div>
              <div style={{ fontSize: 9.5, color: '#333' }}>
                {joinNonEmpty([ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : undefined], ' / ')}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.skills.length > 0 && (
        <Section title="Skills" accent={accent}>
          {data.skills.map((sk) => (
            <div key={sk.id} style={{ marginBottom: 4 }}>
              <span style={{ fontWeight: 700 }}>{sk.category.toUpperCase()}: </span>
              <span>{sk.items.join(', ')}</span>
            </div>
          ))}
        </Section>
      )}

      {data.publications.length > 0 && (
        <Section title="Publications" accent={accent}>
          {data.publications.map((pb) => (
            <div key={pb.id} data-page-block style={{ marginBottom: 6 }}>
              <div style={{ fontWeight: 700 }}>{pb.title}</div>
              <div style={{ fontSize: 9.5, color: '#333' }}>
                {joinNonEmpty([pb.publisher, pb.releaseDate], ' / ')}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.profiles.length > 0 && (
        <Section title="Profiles" accent={accent}>
          {data.profiles.map((pf) => (
            <div key={pf.id} style={{ marginBottom: 2 }}>
              <span style={{ fontWeight: 700 }}>{pf.network.toUpperCase()}: </span>
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
          letterSpacing: '0.22em',
          textTransform: 'uppercase',
          color: accent,
          margin: '0 0 6px 0',
          paddingBottom: 4,
          borderBottom: `2px solid ${accent}`,
        }}
      >
        ## {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
