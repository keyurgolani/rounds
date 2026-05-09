// Creative — split. A vertical accent band runs the full height of
// the page on the left edge; content sits to the right of it.
// Section heads have a small tick that visually connects to the band.
// Distinct rhythm — your eye runs down the band like a margin tab.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

const BAND_WIDTH = 6; // mm

export default function SplitTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#234e70';
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
      {/* Vertical accent band — anchored to the page's inner left edge */}
      <div
        aria-hidden
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          bottom: 0,
          width: `${BAND_WIDTH}mm`,
          background: accent,
        }}
      />
      <div style={{ paddingLeft: 10 }}>
        <header style={{ marginBottom: 16 }}>
          <div
            style={{
              fontSize: 26,
              fontWeight: 700,
              letterSpacing: '-0.01em',
              color: '#111',
              lineHeight: 1.05,
            }}
          >
            {p.fullName || 'Your name'}
          </div>
          {p.title && (
            <div style={{ fontSize: 13, color: accent, marginTop: 3, fontWeight: 600 }}>
              {p.title}
            </div>
          )}
          {meta && (
            <div style={{ fontSize: 10, color: '#555', marginTop: 6 }}>{meta}</div>
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
                  <div style={{ fontWeight: 700 }}>{e.position || '—'}</div>
                  <div style={{ fontSize: 10, color: '#555' }}>
                    {formatDateRange(e.startDate, e.endDate, e.current)}
                  </div>
                </div>
                <div style={{ fontSize: 10.5, color: '#444' }}>
                  {joinNonEmpty([e.company, e.location])}
                </div>
                {e.description && (
                  <div style={{ fontSize: 10.5, marginTop: 3 }}>{e.description}</div>
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
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                  <div style={{ fontWeight: 700 }}>{pr.name || '—'}</div>
                  <div style={{ fontSize: 10, color: '#555' }}>
                    {formatDateRange(pr.startDate, pr.endDate)}
                  </div>
                </div>
                {pr.technologies.length > 0 && (
                  <div style={{ fontSize: 10.5, color: '#444' }}>{pr.technologies.join(' · ')}</div>
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
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                  <div style={{ fontWeight: 700 }}>{ed.institution || '—'}</div>
                  <div style={{ fontSize: 10, color: '#555' }}>
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
                <span style={{ fontWeight: 700 }}>{sk.category}:</span>{' '}
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
                <div style={{ fontSize: 10.5, color: '#555' }}>
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
                <span style={{ fontWeight: 700 }}>{pf.network}:</span>{' '}
                <span>{pf.url || pf.username || '—'}</span>
              </div>
            ))}
          </Section>
        )}
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
    <section style={{ marginBottom: 12 }}>
      <h2
        style={{
          fontSize: 11,
          fontWeight: 700,
          letterSpacing: '0.16em',
          textTransform: 'uppercase',
          color: accent,
          margin: '0 0 6px 0',
          position: 'relative',
        }}
      >
        <span
          aria-hidden
          style={{
            position: 'absolute',
            left: -10,
            top: '50%',
            width: 8,
            height: 1.5,
            background: accent,
            transform: 'translateY(-50%)',
          }}
        />
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
