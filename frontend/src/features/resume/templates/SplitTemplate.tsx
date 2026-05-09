// Creative — split. A real two-zone split: the left third is
// accent-tinted and holds identity (name + title + contact) and
// the side-bar sections (skills, profiles, optional education);
// the right two-thirds are white and carry the narrative bulk
// (summary, experience, projects, publications). The left bg uses
// a soft accent tint (≈10% opacity) so any accent the user picks —
// dark or pale — keeps the text on the left readable.
//
// Distinct from `Compact` (which is two-column for *density*) — Split
// is two-column for *visual hierarchy*. Distinct from `Banner` and
// `Inverted` because the colored zone runs the full *height*, not
// just the top.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

// Hex accent + alpha → rgba tint for a soft sidebar background.
function tint(hex: string, alpha: number): string {
  const m = /^#?([a-f0-9]{6})$/i.exec(hex);
  if (!m) return hex;
  const n = parseInt(m[1], 16);
  const r = (n >> 16) & 255;
  const g = (n >> 8) & 255;
  const b = n & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export default function SplitTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#234e70';
  const fontFamily =
    design?.typography?.body?.family ?? "'Inter', 'Helvetica Neue', system-ui, sans-serif";
  const fontSize = design?.typography?.body?.size ?? 10.5;
  const marginMm = (design?.spacing?.margin ?? 14) | 0;

  const p = data.personalInfo;

  return (
    <A4Page marginMm={marginMm} fontFamily={fontFamily} fontSize={fontSize} bulletStyle={design?.bulletStyle}>
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 2fr)',
          // Pull the grid out to the page edges so the left tint
          // reads as a true zone, not a padded card.
          margin: `${-marginMm}mm`,
          minHeight: `calc(297mm - ${marginMm * 2}mm)`,
        }}
      >
        {/* --- Left zone: identity + sidebar sections --- */}
        <aside
          style={{
            background: tint(accent, 0.12),
            borderRight: `2px solid ${accent}`,
            padding: `${marginMm}mm 6mm ${marginMm}mm ${marginMm}mm`,
          }}
        >
          <div
            style={{
              fontSize: 22,
              fontWeight: 700,
              letterSpacing: '-0.01em',
              color: '#111',
              lineHeight: 1.05,
            }}
          >
            {p.fullName || 'Your name'}
          </div>
          {p.title && (
            <div
              style={{
                fontSize: 11,
                color: accent,
                marginTop: 4,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.12em',
              }}
            >
              {p.title}
            </div>
          )}

          <ContactList p={p} accent={accent} />

          {data.skills.length > 0 && (
            <SideSection title="Skills" accent={accent}>
              {data.skills.map((sk) => (
                <div key={sk.id} style={{ marginBottom: 6 }}>
                  <div style={{ fontWeight: 700, fontSize: 9.5 }}>{sk.category}</div>
                  <div style={{ fontSize: 9.5, color: '#333', lineHeight: 1.45 }}>
                    {sk.items.join(', ')}
                  </div>
                </div>
              ))}
            </SideSection>
          )}

          {data.education.length > 0 && (
            <SideSection title="Education" accent={accent}>
              {data.education.map((ed) => (
                <div key={ed.id} data-page-block style={{ marginBottom: 7 }}>
                  <div style={{ fontWeight: 700, fontSize: 10 }}>{ed.institution || '—'}</div>
                  <div style={{ fontSize: 9.5, color: '#444' }}>
                    {joinNonEmpty([ed.degree, ed.field])}
                  </div>
                  <div style={{ fontSize: 9, color: '#555', marginTop: 1 }}>
                    {formatDateRange(ed.startDate, ed.endDate)}
                    {ed.gpa && ` · GPA ${ed.gpa}`}
                  </div>
                </div>
              ))}
            </SideSection>
          )}

          {data.profiles.length > 0 && (
            <SideSection title="Profiles" accent={accent}>
              {data.profiles.map((pf) => (
                <div key={pf.id} style={{ marginBottom: 3, fontSize: 9.5 }}>
                  <div style={{ fontWeight: 700 }}>{pf.network}</div>
                  <div style={{ color: '#333', wordBreak: 'break-word' }}>
                    {pf.url || pf.username || '—'}
                  </div>
                </div>
              ))}
            </SideSection>
          )}
        </aside>

        {/* --- Right zone: the narrative --- */}
        <main
          style={{
            padding: `${marginMm}mm ${marginMm}mm ${marginMm}mm 6mm`,
          }}
        >
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
                  <div style={{ fontSize: 10.5, color: accent }}>
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
                    <div style={{ fontSize: 10.5, color: accent }}>{pr.technologies.join(' · ')}</div>
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

          {data.publications.length > 0 && (
            <Section title="Publications" accent={accent}>
              {data.publications.map((pb) => (
                <div key={pb.id} data-page-block style={{ marginBottom: 6 }}>
                  <div style={{ fontWeight: 700 }}>{pb.title}</div>
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
        </main>
      </div>
    </A4Page>
  );
}

function ContactList({
  p,
  accent,
}: {
  p: ResumeData['personalInfo'];
  accent: string;
}) {
  const rows: { label: string; value?: string }[] = [
    { label: 'Location', value: p.location },
    { label: 'Email', value: p.email },
    { label: 'Phone', value: p.phone },
    { label: 'Web', value: p.website },
    { label: 'LinkedIn', value: p.linkedin },
    { label: 'GitHub', value: p.github },
  ].filter((r) => Boolean(r.value && r.value.trim()));

  if (rows.length === 0) return null;

  return (
    <div style={{ marginTop: 12, marginBottom: 12, fontSize: 9.5, lineHeight: 1.5 }}>
      {rows.map((r) => (
        <div key={r.label} style={{ marginBottom: 2 }}>
          <div
            style={{
              fontSize: 8.5,
              fontWeight: 700,
              color: accent,
              textTransform: 'uppercase',
              letterSpacing: '0.12em',
            }}
          >
            {r.label}
          </div>
          <div style={{ color: '#333', wordBreak: 'break-word' }}>{r.value}</div>
        </div>
      ))}
    </div>
  );
}

function SideSection({
  title,
  accent,
  children,
}: {
  title: string;
  accent: string;
  children: React.ReactNode;
}) {
  return (
    <section style={{ marginTop: 14 }}>
      <h2
        style={{
          fontSize: 10.5,
          fontWeight: 700,
          letterSpacing: '0.16em',
          textTransform: 'uppercase',
          color: accent,
          margin: '0 0 6px 0',
          paddingBottom: 2,
          borderBottom: `1px solid ${accent}55`,
        }}
      >
        {title}
      </h2>
      <div>{children}</div>
    </section>
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
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: accent,
          margin: '0 0 6px 0',
          paddingBottom: 2,
          borderBottom: `1px solid ${accent}33`,
        }}
      >
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
