// Recruiter-tested "12 out of 10" layout. Single-column, sans-serif,
// ALL-CAPS section heads with a thin accent rule, disc bullets,
// pipe-delimited skill blocks. Header carries a dual professional
// title (Title • Subtitle) and a single pipe-joined contact line.
//
// Detects a SkillGroup whose category is exactly "ATS Keywords"
// (case-insensitive, whitespace-tolerant) and renders it in a
// dedicated compact block; other categories render as
// "Category  item | item | item" rows in the main Skills section.
//
// Honors data.sectionOrder and data.hiddenSections — section
// rendering is driven by sectionOrder() so dragging Skills above
// Experience in the Section nav reorders the resume.

import type { ReactNode } from 'react';
import type {
  ResumeData,
  SectionKey,
  SkillGroup,
  TemplateConfig,
} from '../types';
import { sectionOrder } from '../utils';
import { A4Page, formatDateRange, joinPipes } from './parts';

type Props = { data: ResumeData; design?: TemplateConfig };

const ATS_KEYWORDS_REGEX = /^\s*ats\s*keywords\s*$/i;

function isAtsCategory(category: string): boolean {
  return ATS_KEYWORDS_REGEX.test(category);
}

export default function LangstaffTemplate({ data, design }: Props) {
  const accent = design?.colors?.primary ?? '#1f3b56';
  const fontFamily =
    design?.typography?.body?.family ?? "'Inter', 'Helvetica Neue', system-ui, sans-serif";
  const fontSize = design?.typography?.body?.size ?? 10.5;
  const marginMm = (design?.spacing?.margin ?? 14) | 0;

  const p = data.personalInfo;
  const dualTitle = p.subtitle ? `${p.title ?? ''} • ${p.subtitle}` : (p.title ?? '');
  const contact = joinPipes([p.phone, p.email, p.location, p.website, p.linkedin, p.github]);

  const order = sectionOrder(data).filter((k) => !data.hiddenSections?.includes(k));
  const nonAtsSkills = data.skills.filter((sk) => !isAtsCategory(sk.category));
  const atsKeywords = data.skills.filter((sk) => isAtsCategory(sk.category));

  return (
    <A4Page
      marginMm={marginMm}
      fontFamily={fontFamily}
      fontSize={fontSize}
      bulletStyle={design?.bulletStyle ?? 'disc'}
    >
      <Header
        name={p.fullName || 'Your name'}
        dualTitle={dualTitle}
        contact={contact}
        accent={accent}
      />

      {order.map((key) => renderSection(key, data, nonAtsSkills, accent))}

      {atsKeywords.length > 0 && !data.hiddenSections?.includes('skills') && (
        <Section title="ATS Keywords" accent={accent}>
          {atsKeywords.map((sk) => (
            <div
              key={sk.id}
              style={{
                marginBottom: 2,
                fontSize: fontSize - 0.5,
                color: '#333',
                lineHeight: 1.5,
                overflowWrap: 'anywhere',
              }}
            >
              {joinPipes(sk.items)}
            </div>
          ))}
        </Section>
      )}
    </A4Page>
  );
}

function Header({
  name,
  dualTitle,
  contact,
  accent,
}: {
  name: string;
  dualTitle: string;
  contact: string;
  accent: string;
}) {
  return (
    <header style={{ marginBottom: 14, borderBottom: `1.5px solid ${accent}`, paddingBottom: 8 }}>
      <div
        style={{
          fontSize: 24,
          fontWeight: 700,
          letterSpacing: '-0.005em',
          color: accent,
          textTransform: 'uppercase',
        }}
      >
        {name}
      </div>
      {dualTitle && (
        <div style={{ fontSize: 12.5, color: '#222', marginTop: 3 }}>{dualTitle}</div>
      )}
      {contact && (
        <div
          style={{
            fontSize: 10,
            color: '#444',
            marginTop: 5,
            lineHeight: 1.5,
            overflowWrap: 'anywhere',
          }}
        >
          {contact}
        </div>
      )}
    </header>
  );
}

function renderSection(
  key: SectionKey,
  data: ResumeData,
  nonAtsSkills: SkillGroup[],
  accent: string,
): ReactNode {
  switch (key) {
    case 'personal':
      return data.personalInfo.summary ? (
        <Section key={key} title="Professional Summary" accent={accent}>
          <p style={{ margin: 0 }}>{data.personalInfo.summary}</p>
        </Section>
      ) : null;
    case 'experience':
      return data.experience.length > 0 ? (
        <Section key={key} title="Professional Experience" accent={accent}>
          {data.experience.map((e) => (
            <div key={e.id} data-page-block style={{ marginBottom: 10 }}>
              <div style={{ fontWeight: 700 }}>{e.position || '—'}</div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 8,
                  fontSize: 10.5,
                  color: '#333',
                }}
              >
                <span>{joinPipes([e.company, e.location])}</span>
                <span style={{ color: '#555' }}>
                  {formatDateRange(e.startDate, e.endDate, e.current)}
                </span>
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
      ) : null;
    case 'education':
      return data.education.length > 0 ? (
        <Section key={key} title="Education" accent={accent}>
          {data.education.map((ed) => (
            <div key={ed.id} data-page-block style={{ marginBottom: 8 }}>
              <div style={{ fontWeight: 700 }}>{ed.institution || '—'}</div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 8,
                  fontSize: 10.5,
                  color: '#333',
                }}
              >
                <span>
                  {joinPipes([ed.degree, ed.field, ed.gpa ? `GPA ${ed.gpa}` : undefined, ed.location])}
                </span>
                <span style={{ color: '#555' }}>
                  {formatDateRange(ed.startDate, ed.endDate)}
                </span>
              </div>
              {ed.description && (
                <div style={{ fontSize: 10.5, marginTop: 2 }}>{ed.description}</div>
              )}
            </div>
          ))}
        </Section>
      ) : null;
    case 'skills':
      return nonAtsSkills.length > 0 ? (
        <Section key={key} title="Skills" accent={accent}>
          {nonAtsSkills.map((sk) => (
            <div
              key={sk.id}
              style={{ marginBottom: 4, lineHeight: 1.55, overflowWrap: 'anywhere' }}
            >
              {sk.category && (
                <span style={{ fontWeight: 700 }}>{sk.category}&emsp;</span>
              )}
              <span>{joinPipes(sk.items)}</span>
            </div>
          ))}
        </Section>
      ) : null;
    case 'projects':
      return data.projects.length > 0 ? (
        <Section key={key} title="Projects" accent={accent}>
          {data.projects.map((pr) => (
            <div key={pr.id} data-page-block style={{ marginBottom: 10 }}>
              <div style={{ fontWeight: 700 }}>{pr.name || '—'}</div>
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  gap: 8,
                  fontSize: 10.5,
                  color: '#333',
                }}
              >
                <span>{joinPipes(pr.technologies)}</span>
                <span style={{ color: '#555' }}>
                  {formatDateRange(pr.startDate, pr.endDate)}
                </span>
              </div>
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
      ) : null;
    case 'publications':
      return data.publications.length > 0 ? (
        <Section key={key} title="Publications" accent={accent}>
          {data.publications.map((pb) => (
            <div key={pb.id} data-page-block style={{ marginBottom: 6 }}>
              <div style={{ fontWeight: 700 }}>{pb.title}</div>
              <div style={{ fontSize: 10.5, color: '#555' }}>
                {joinPipes([pb.publisher, pb.releaseDate])}
              </div>
              {pb.summary && (
                <div style={{ fontSize: 10.5, marginTop: 2 }}>{pb.summary}</div>
              )}
            </div>
          ))}
        </Section>
      ) : null;
    case 'profiles':
      return data.profiles.length > 0 ? (
        <Section key={key} title="Profiles" accent={accent}>
          {data.profiles.map((pf) => (
            <div key={pf.id} style={{ marginBottom: 2 }}>
              <span style={{ fontWeight: 700 }}>{pf.network}&emsp;</span>
              <span>{pf.url || pf.username || '—'}</span>
            </div>
          ))}
        </Section>
      ) : null;
    default:
      return null;
  }
}

function Section({
  title,
  accent,
  children,
}: {
  title: string;
  accent: string;
  children: ReactNode;
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
          borderBottom: `1px solid ${accent}`,
          paddingBottom: 3,
        }}
      >
        {title}
      </h2>
      <div>{children}</div>
    </section>
  );
}
