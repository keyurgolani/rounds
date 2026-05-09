// Creative — confetti. Decorative accent flecks scattered across the
// header strip; the rest is a clean sans-serif resume. Playful enough
// to feel personable, restrained enough to stay professional.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

// Fixed-position flecks so the layout is deterministic across renders
// (otherwise the export and preview can diverge). Coordinates are %
// of the header strip's box.
const FLECKS: { left: number; top: number; size: number; rotate: number }[] = [
  { left: 4, top: 18, size: 6, rotate: 12 },
  { left: 14, top: 64, size: 4, rotate: -28 },
  { left: 28, top: 8, size: 7, rotate: 42 },
  { left: 36, top: 78, size: 5, rotate: -10 },
  { left: 50, top: 28, size: 3, rotate: 6 },
  { left: 62, top: 70, size: 6, rotate: 18 },
  { left: 74, top: 12, size: 4, rotate: -22 },
  { left: 86, top: 50, size: 5, rotate: 30 },
  { left: 92, top: 20, size: 3, rotate: -6 },
];

export default function ConfettiTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#9b3a8a';
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
      <header style={{ position: 'relative', height: 80, marginBottom: 12, overflow: 'hidden' }}>
        <div aria-hidden style={{ position: 'absolute', inset: 0, opacity: 0.55 }}>
          {FLECKS.map((f, i) => (
            <span
              key={i}
              style={{
                position: 'absolute',
                left: `${f.left}%`,
                top: `${f.top}%`,
                width: f.size,
                height: f.size,
                background: accent,
                transform: `rotate(${f.rotate}deg)`,
                borderRadius: i % 2 === 0 ? 1 : 999,
              }}
            />
          ))}
        </div>
        <div style={{ position: 'relative', zIndex: 1 }}>
          <div
            style={{
              fontSize: 28,
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
          {p.subtitle && (
            <div style={{ fontSize: 11, color: '#555', marginTop: 1 }}>{p.subtitle}</div>
          )}
          {meta && (
            <div style={{ fontSize: 10, color: '#555', marginTop: 6 }}>{meta}</div>
          )}
        </div>
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
          color: '#222',
          margin: '0 0 6px 0',
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
        }}
      >
        <span
          aria-hidden
          style={{
            width: 0,
            height: 0,
            borderLeft: '5px solid transparent',
            borderRight: '5px solid transparent',
            borderBottom: `7px solid ${accent}`,
          }}
        />
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
