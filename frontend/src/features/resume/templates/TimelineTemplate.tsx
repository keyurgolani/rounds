// Date-rail-on-left layout. Each entry's date range sits in a narrow
// monospace gutter on the left; the content sits right of a vertical
// rule, like a project changelog or git history. Distinctive visual
// rhythm, scannable at-a-glance — recruiters can run their eye down
// the rail and see ranges + titles together without reading bullets.
//
// Single-column overall (header spans full width); the date-rail
// is just a per-entry 90px-content grid, so ATS parsers see the
// content in normal reading order.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

export default function TimelineTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#3b6c8a';
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
      <header style={{ marginBottom: 14 }}>
        <div
          style={{
            fontSize: 28,
            fontWeight: 600,
            letterSpacing: '-0.01em',
            color: '#111',
            lineHeight: 1.05,
          }}
        >
          {p.fullName || 'Your name'}
        </div>
        {p.title && (
          <div style={{ fontSize: 13, color: accent, marginTop: 3, fontWeight: 500 }}>
            {p.title}
          </div>
        )}
        {p.subtitle && (
          <div style={{ fontSize: 11, color: '#555', marginTop: 1 }}>{p.subtitle}</div>
        )}
        {meta && (
          <div style={{ fontSize: 10, color: '#555', marginTop: 6 }}>{meta}</div>
        )}
      </header>

      {p.summary && (
        <SectionHead title="Summary" accent={accent} />
      )}
      {p.summary && (
        <div style={{ paddingLeft: 100, marginBottom: 14 }}>
          <p style={{ margin: 0 }}>{p.summary}</p>
        </div>
      )}

      {data.experience.length > 0 && (
        <>
          <SectionHead title="Experience" accent={accent} />
          {data.experience.map((e) => (
            <RailRow
              key={e.id}
              accent={accent}
              dateLabel={formatDateRange(e.startDate, e.endDate, e.current)}
            >
              <div style={{ fontWeight: 600, fontSize: 12 }}>{e.position || '—'}</div>
              <div style={{ fontSize: 10.5, color: accent }}>
                {joinNonEmpty([e.company, e.location])}
              </div>
              {e.description && (
                <div style={{ fontSize: 10.5, marginTop: 3 }}>{e.description}</div>
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
            </RailRow>
          ))}
        </>
      )}

      {data.projects.length > 0 && (
        <>
          <SectionHead title="Projects" accent={accent} />
          {data.projects.map((pr) => (
            <RailRow
              key={pr.id}
              accent={accent}
              dateLabel={formatDateRange(pr.startDate, pr.endDate)}
            >
              <div style={{ fontWeight: 600, fontSize: 12 }}>{pr.name || '—'}</div>
              {pr.technologies.length > 0 && (
                <div style={{ fontSize: 10.5, color: accent }}>{pr.technologies.join(' · ')}</div>
              )}
              {pr.description && (
                <div style={{ fontSize: 10.5, marginTop: 3 }}>{pr.description}</div>
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
            </RailRow>
          ))}
        </>
      )}

      {data.education.length > 0 && (
        <>
          <SectionHead title="Education" accent={accent} />
          {data.education.map((ed) => (
            <RailRow
              key={ed.id}
              accent={accent}
              dateLabel={formatDateRange(ed.startDate, ed.endDate)}
            >
              <div style={{ fontWeight: 600 }}>{ed.institution || '—'}</div>
              <div style={{ fontSize: 10.5, color: '#444' }}>
                {joinNonEmpty([ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : undefined])}
              </div>
              {ed.description && (
                <div style={{ fontSize: 10.5, marginTop: 2 }}>{ed.description}</div>
              )}
            </RailRow>
          ))}
        </>
      )}

      {data.skills.length > 0 && (
        <>
          <SectionHead title="Skills" accent={accent} />
          <div style={{ paddingLeft: 100, marginBottom: 14 }}>
            {data.skills.map((sk) => (
              <div key={sk.id} style={{ marginBottom: 4 }}>
                <span style={{ fontWeight: 600 }}>{sk.category}:</span>{' '}
                <span>{sk.items.join(', ')}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {data.publications.length > 0 && (
        <>
          <SectionHead title="Publications" accent={accent} />
          {data.publications.map((pb) => (
            <RailRow
              key={pb.id}
              accent={accent}
              dateLabel={pb.releaseDate ? pb.releaseDate.slice(0, 7) : ''}
            >
              <div style={{ fontWeight: 600 }}>{pb.title}</div>
              <div style={{ fontSize: 10.5, color: '#555' }}>{pb.publisher}</div>
              {pb.summary && (
                <div style={{ fontSize: 10.5, marginTop: 2 }}>{pb.summary}</div>
              )}
            </RailRow>
          ))}
        </>
      )}

      {data.profiles.length > 0 && (
        <>
          <SectionHead title="Profiles" accent={accent} />
          <div style={{ paddingLeft: 100, marginBottom: 4 }}>
            {data.profiles.map((pf) => (
              <div key={pf.id} style={{ marginBottom: 2 }}>
                <span style={{ fontWeight: 600 }}>{pf.network}:</span>{' '}
                <span>{pf.url || pf.username || '—'}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </A4Page>
  );
}

function SectionHead({ title, accent }: { title: string; accent: string }) {
  return (
    <h2
      style={{
        fontSize: 10.5,
        fontWeight: 700,
        letterSpacing: '0.18em',
        textTransform: 'uppercase',
        color: accent,
        margin: '0 0 8px 0',
        paddingLeft: 100,
      }}
    >
      {title}
    </h2>
  );
}

function RailRow({
  dateLabel,
  accent,
  children,
}: {
  dateLabel: string;
  accent: string;
  children: React.ReactNode;
}) {
  return (
    <div
      data-page-block
      style={{
        display: 'grid',
        gridTemplateColumns: '90px 1fr',
        gap: 10,
        marginBottom: 12,
        position: 'relative',
      }}
    >
      <div
        style={{
          fontSize: 9.5,
          fontFamily: "'JetBrains Mono', 'IBM Plex Mono', ui-monospace, monospace",
          color: '#555',
          paddingTop: 2,
          textAlign: 'right',
          paddingRight: 6,
          borderRight: `1px solid ${accent}55`,
        }}
      >
        {dateLabel || ''}
      </div>
      <div>{children}</div>
    </div>
  );
}
