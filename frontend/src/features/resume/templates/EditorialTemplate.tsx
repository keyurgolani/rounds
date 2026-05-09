// Magazine / editorial style. Big italic display-serif name, italic
// small-caps section heads, a thin column rule between Skills and
// Profiles in the footer block. Senior-IC / staff-eng feel — works
// best when the candidate has a real narrative to tell and benefits
// from the more refined visual register.
//
// The body stays single-column for ATS safety; only the small footer
// (Skills + Profiles) is two-column with a vertical rule between them.

import type { ResumeData, TemplateConfig } from '../types';
import { A4Page, formatDateRange, joinNonEmpty } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

export default function EditorialTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#3a2c4a';
  const fontFamily =
    design?.typography?.body?.family ??
    "'Source Serif Pro', 'Georgia', 'Times New Roman', serif";
  const headFamily =
    design?.typography?.heading?.family ??
    "'Playfair Display', 'Georgia', serif";
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
      <header style={{ marginBottom: 16, textAlign: 'center' }}>
        <div
          style={{
            fontFamily: headFamily,
            fontStyle: 'italic',
            fontSize: 38,
            fontWeight: 400,
            lineHeight: 1.0,
            color: '#181018',
            letterSpacing: '-0.01em',
          }}
        >
          {p.fullName || 'Your name'}
        </div>
        {p.title && (
          <div
            style={{
              fontSize: 11,
              color: accent,
              marginTop: 6,
              textTransform: 'uppercase',
              letterSpacing: '0.22em',
              fontWeight: 600,
            }}
          >
            {p.title}
          </div>
        )}
        <div
          style={{
            margin: '10px auto 0',
            width: 50,
            height: 1,
            background: accent,
          }}
        />
        {meta && (
          <div style={{ fontSize: 10, color: '#555', marginTop: 8 }}>{meta}</div>
        )}
      </header>

      {p.summary && (
        <Section title="Summary" headFamily={headFamily} accent={accent}>
          <p style={{ margin: 0, lineHeight: 1.55 }}>{p.summary}</p>
        </Section>
      )}

      {data.experience.length > 0 && (
        <Section title="Experience" headFamily={headFamily} accent={accent}>
          {data.experience.map((e) => (
            <div key={e.id} data-page-block style={{ marginBottom: 12 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
                <div style={{ fontWeight: 700, fontSize: 12 }}>
                  {e.position || '—'}
                  {e.company && (
                    <span style={{ fontWeight: 400, fontStyle: 'italic', color: '#555' }}>
                      {' · '}{e.company}
                    </span>
                  )}
                </div>
                <div
                  style={{
                    fontSize: 10,
                    color: '#666',
                    fontStyle: 'italic',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {formatDateRange(e.startDate, e.endDate, e.current)}
                </div>
              </div>
              {e.location && (
                <div style={{ fontSize: 10, color: '#777', fontStyle: 'italic' }}>{e.location}</div>
              )}
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
        <Section title="Projects" headFamily={headFamily} accent={accent}>
          {data.projects.map((pr) => (
            <div key={pr.id} data-page-block style={{ marginBottom: 10 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
                <div style={{ fontWeight: 700, fontSize: 12 }}>{pr.name || '—'}</div>
                <div style={{ fontSize: 10, color: '#666', fontStyle: 'italic', whiteSpace: 'nowrap' }}>
                  {formatDateRange(pr.startDate, pr.endDate)}
                </div>
              </div>
              {pr.technologies.length > 0 && (
                <div style={{ fontSize: 10, color: '#777', fontStyle: 'italic' }}>
                  {pr.technologies.join(' · ')}
                </div>
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
            </div>
          ))}
        </Section>
      )}

      {data.education.length > 0 && (
        <Section title="Education" headFamily={headFamily} accent={accent}>
          {data.education.map((ed) => (
            <div key={ed.id} data-page-block style={{ marginBottom: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'baseline' }}>
                <div style={{ fontWeight: 700 }}>{ed.institution || '—'}</div>
                <div style={{ fontSize: 10, color: '#666', fontStyle: 'italic', whiteSpace: 'nowrap' }}>
                  {formatDateRange(ed.startDate, ed.endDate)}
                </div>
              </div>
              <div style={{ fontSize: 10.5, color: '#444', fontStyle: 'italic' }}>
                {joinNonEmpty([ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : undefined])}
              </div>
            </div>
          ))}
        </Section>
      )}

      {data.publications.length > 0 && (
        <Section title="Publications" headFamily={headFamily} accent={accent}>
          {data.publications.map((pb) => (
            <div key={pb.id} data-page-block style={{ marginBottom: 6 }}>
              <div style={{ fontWeight: 700, fontSize: 11 }}>{pb.title}</div>
              <div style={{ fontSize: 10, color: '#666', fontStyle: 'italic' }}>
                {joinNonEmpty([pb.publisher, pb.releaseDate])}
              </div>
            </div>
          ))}
        </Section>
      )}

      {/* Footer block: Skills | Profiles, two-column with column rule */}
      {(data.skills.length > 0 || data.profiles.length > 0) && (
        <div
          style={{
            marginTop: 6,
            paddingTop: 12,
            borderTop: `1px solid ${accent}33`,
            display: 'grid',
            gridTemplateColumns: data.skills.length && data.profiles.length ? '1fr auto 1fr' : '1fr',
            gap: 16,
            alignItems: 'start',
          }}
        >
          {data.skills.length > 0 && (
            <div>
              <FooterHead title="Skills" headFamily={headFamily} accent={accent} />
              {data.skills.map((sk) => (
                <div key={sk.id} style={{ marginBottom: 3, fontSize: 10 }}>
                  <span style={{ fontWeight: 700 }}>{sk.category}:</span>{' '}
                  <span>{sk.items.join(', ')}</span>
                </div>
              ))}
            </div>
          )}
          {data.skills.length > 0 && data.profiles.length > 0 && (
            <div style={{ width: 1, alignSelf: 'stretch', background: `${accent}33` }} />
          )}
          {data.profiles.length > 0 && (
            <div>
              <FooterHead title="Profiles" headFamily={headFamily} accent={accent} />
              {data.profiles.map((pf) => (
                <div key={pf.id} style={{ marginBottom: 2, fontSize: 10 }}>
                  <span style={{ fontWeight: 700 }}>{pf.network}:</span>{' '}
                  <span>{pf.url || pf.username || '—'}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </A4Page>
  );
}

function Section({
  title,
  headFamily,
  accent,
  children,
}: {
  title: string;
  headFamily: string;
  accent: string;
  children: React.ReactNode;
}) {
  return (
    <section style={{ marginBottom: 14 }}>
      <h2
        style={{
          fontFamily: headFamily,
          fontStyle: 'italic',
          fontSize: 16,
          fontWeight: 400,
          color: accent,
          margin: '0 0 8px 0',
          letterSpacing: '0.01em',
        }}
      >
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}

function FooterHead({
  title,
  headFamily,
  accent,
}: {
  title: string;
  headFamily: string;
  accent: string;
}) {
  return (
    <div
      style={{
        fontFamily: headFamily,
        fontStyle: 'italic',
        fontSize: 12,
        color: accent,
        marginBottom: 4,
      }}
    >
      {title}
    </div>
  );
}
