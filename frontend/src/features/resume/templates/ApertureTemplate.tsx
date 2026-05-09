// Designer — aperture. Photography portfolio aesthetic: oversized
// typographic name, mono-typed metadata sitting on a precise grid,
// generous whitespace. The name is the hero; everything else is a
// quiet caption beneath. Works best for senior candidates who can
// hold the page with substance.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

export default function ApertureTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#111';
  const fontFamily =
    design?.typography?.body?.family ?? "'Inter', 'Helvetica Neue', system-ui, sans-serif";
  const fontSize = design?.typography?.body?.size ?? 10.5;
  const marginMm = (design?.spacing?.margin ?? 18) | 0;

  const p = data.personalInfo;

  return (
    <A4Page marginMm={marginMm} fontFamily={fontFamily} fontSize={fontSize} bulletStyle={design?.bulletStyle}>
      <header style={{ marginBottom: 22 }}>
        <div
          style={{
            fontSize: 44,
            fontWeight: 700,
            letterSpacing: '-0.04em',
            color: '#111',
            lineHeight: 0.95,
          }}
        >
          {p.fullName || 'Your name'}
        </div>
        {p.title && (
          <div
            style={{
              fontSize: 11,
              color: accent,
              marginTop: 8,
              textTransform: 'uppercase',
              letterSpacing: '0.18em',
              fontWeight: 600,
            }}
          >
            {p.title}
          </div>
        )}
        {p.subtitle && (
          <div
            style={{
              fontSize: 10,
              color: '#555',
              marginTop: 3,
              textTransform: 'uppercase',
              letterSpacing: '0.16em',
              fontWeight: 500,
            }}
          >
            {p.subtitle}
          </div>
        )}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
            gap: '4px 24px',
            marginTop: 14,
            fontFamily: "'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace",
            fontSize: 9,
            color: '#444',
          }}
        >
          {p.location && <Pair label="LOC" value={p.location} />}
          {p.email && <Pair label="EML" value={p.email} />}
          {p.phone && <Pair label="TEL" value={p.phone} />}
          {p.website && <Pair label="WEB" value={p.website} />}
          {p.linkedin && <Pair label="LIN" value={p.linkedin} />}
          {p.github && <Pair label="GIT" value={p.github} />}
        </div>
      </header>

      {p.summary && (
        <Section title="Summary" accent={accent}>
          <p style={{ margin: 0, lineHeight: 1.6 }}>{p.summary}</p>
        </Section>
      )}

      {data.experience.length > 0 && (
        <Section title="Experience" accent={accent}>
          {data.experience.map((e) => (
            <div key={e.id} data-page-block style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
                <div style={{ fontWeight: 700, fontSize: 12 }}>{e.position || '—'}</div>
                <div
                  style={{
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                    fontSize: 9,
                    color: '#666',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {formatDateRange(e.startDate, e.endDate, e.current)}
                </div>
              </div>
              <div style={{ fontSize: 10.5, color: accent }}>
                {joinNonEmpty([e.company, e.location])}
              </div>
              {e.description && (
                <div style={{ fontSize: 10.5, marginTop: 4 }}>{e.description}</div>
              )}
              {e.highlights.length > 0 && (
                <ul style={{ margin: '4px 0 0 18px', padding: 0 }}>
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
        <Section title="Projects" accent={accent}>
          {data.projects.map((pr) => (
            <div key={pr.id} data-page-block style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
                <div style={{ fontWeight: 700, fontSize: 12 }}>{pr.name || '—'}</div>
                <div style={{ fontFamily: "'JetBrains Mono', ui-monospace, monospace", fontSize: 9, color: '#666' }}>
                  {formatDateRange(pr.startDate, pr.endDate)}
                </div>
              </div>
              {pr.technologies.length > 0 && (
                <div style={{ fontSize: 10, color: '#666' }}>{pr.technologies.join(' · ')}</div>
              )}
              {pr.description && (
                <div style={{ fontSize: 10.5, marginTop: 3 }}>{pr.description}</div>
              )}
              {pr.highlights.length > 0 && (
                <ul style={{ margin: '4px 0 0 18px', padding: 0 }}>
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
        <Section title="Education" accent={accent}>
          {data.education.map((ed) => (
            <div key={ed.id} data-page-block style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
                <div style={{ fontWeight: 700 }}>{ed.institution || '—'}</div>
                <div style={{ fontFamily: "'JetBrains Mono', ui-monospace, monospace", fontSize: 9, color: '#666' }}>
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

      {data.skills.length > 0 && (
        <Section title="Skills" accent={accent}>
          {data.skills.map((sk) => (
            <div key={sk.id} style={{ marginBottom: 4 }}>
              <span style={{ fontWeight: 700 }}>{sk.category}</span>
              {' — '}
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
              <div style={{ fontSize: 10, color: '#666' }}>
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
              <span style={{ fontWeight: 700 }}>{pf.network}</span>
              {' — '}
              <span>{pf.url || pf.username || '—'}</span>
            </div>
          ))}
        </Section>
      )}
    </A4Page>
  );
}

function Pair({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', gap: 8, minWidth: 0 }}>
      <span style={{ color: '#999', flexShrink: 0 }}>{label}</span>
      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {value}
      </span>
    </div>
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
    <section style={{ marginBottom: 14 }}>
      <h2
        style={{
          fontFamily: "'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace",
          fontSize: 9,
          fontWeight: 600,
          letterSpacing: '0.24em',
          textTransform: 'uppercase',
          color: accent,
          margin: '0 0 8px 0',
        }}
      >
        — {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
