import type { CSSProperties, ReactNode, RefObject } from 'react';
import { ArrowRight, BookOpen, CheckCircle2, ListChecks, Map, ShieldCheck, Target } from 'lucide-react';
import { Link } from 'react-router-dom';
import AppHeader from '../../components/shell/AppHeader';
import BackLink from '../../components/shell/BackLink';
import SectionNav, { type SectionNavItem } from '../../components/shell/SectionNav';
import type { GuideChecklist, GuideConfig, GuideRecord, GuideResource, GuideSection } from './guideTypes';

export const cardStyle: CSSProperties = {
  padding: 24,
  borderRadius: 'var(--radius-lg)',
  background: 'var(--bg-elev)',
  boxShadow: 'var(--shadow-card)',
};

export const warCardStyle: CSSProperties = {
  borderRadius: 'calc(var(--radius-lg) + 6px)',
  background: 'linear-gradient(135deg, var(--bg-elev), var(--bg))',
  boxShadow: 'var(--shadow-card)',
  border: '1px solid var(--border)',
};

export function getGuidePages(guide: GuideRecord) {
  return guide.resources.flatMap((category) => category.items);
}

export function getSection(guide: GuideRecord, id: string) {
  return guide.sections.find((section) => section.id === id);
}

export function splitSignal(item: string) {
  const [signal, move] = item.split(/->(.+)/).map((part) => part.trim());
  return { signal, move: move || item };
}

export function splitLabel(item: string) {
  const [label, detail] = item.split(/:(.+)/).map((part) => part.trim());
  return { label, detail: detail || item };
}

export function SectionHeading({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <h2
      id={id}
      className="display-italic"
      style={{ fontSize: 'clamp(26px, 5vw, 38px)', lineHeight: 1, fontWeight: 400, margin: 0, scrollMarginTop: 24 }}
    >
      {children}
    </h2>
  );
}

export function WarHeading({ id, eyebrow, title, description }: { id?: string; eyebrow: string; title: string; description?: string }) {
  return (
    <div id={id} style={{ scrollMarginTop: 24 }}>
      <div className="mono" style={{ color: 'var(--accent)', fontSize: 11, letterSpacing: '0.14em' }}>
        {eyebrow.toUpperCase()}
      </div>
      <h2 className="display-italic" style={{ margin: '8px 0 0', fontSize: 'clamp(30px, 5vw, 48px)', lineHeight: 0.95, fontWeight: 400 }}>
        {title}
      </h2>
      {description && <p style={{ margin: '12px 0 0', color: 'var(--text-2)', lineHeight: 1.65, maxWidth: 760 }}>{description}</p>}
    </div>
  );
}

export function NumberedList({ items }: { items: string[] }) {
  return (
    <ol className="grid gap-3" style={{ margin: 0, padding: 0, listStyle: 'none' }}>
      {items.map((item, index) => (
        <li key={item} className="flex gap-3" style={{ color: 'var(--text-2)', lineHeight: 1.55 }}>
          <span
            className="mono"
            style={{ flex: '0 0 auto', width: 26, height: 26, display: 'grid', placeItems: 'center', borderRadius: 999, background: 'var(--accent-soft)', color: 'var(--accent)', fontSize: 11 }}
          >
            {index + 1}
          </span>
          <span>{item}</span>
        </li>
      ))}
    </ol>
  );
}

export function WarActionList({ items, compact = false }: { items: string[]; compact?: boolean }) {
  return (
    <ol className="grid" style={{ gap: compact ? 8 : 12, margin: 0, padding: 0, listStyle: 'none' }}>
      {items.map((item, index) => (
        <li key={`${index}-${item}`} className="flex gap-3" style={{ alignItems: 'flex-start', padding: compact ? '8px 0' : '10px 0', borderTop: index === 0 ? '0' : '1px solid var(--border)' }}>
          <span
            className="mono"
            style={{ flex: '0 0 auto', minWidth: 30, height: 24, display: 'grid', placeItems: 'center', borderRadius: 999, background: index === 0 ? 'var(--accent)' : 'var(--accent-soft)', color: index === 0 ? 'var(--bg-elev)' : 'var(--accent)', fontSize: 10.5 }}
          >
            {String(index + 1).padStart(2, '0')}
          </span>
          <span style={{ color: 'var(--text-2)', lineHeight: 1.55, fontSize: compact ? 13 : 14 }}>{item}</span>
        </li>
      ))}
    </ol>
  );
}

export function WarStat({ label, value, icon: Icon }: { label: string; value: ReactNode; icon: typeof Target }) {
  return (
    <div style={{ ...warCardStyle, padding: 18 }}>
      <div className="flex items-center gap-3">
        <span style={{ width: 38, height: 38, display: 'grid', placeItems: 'center', borderRadius: 999, background: 'var(--accent-soft)', color: 'var(--accent)', flex: '0 0 auto' }}>
          <Icon size={18} />
        </span>
        <div>
          <div className="display-italic" style={{ fontSize: 28, lineHeight: 1 }}>{value}</div>
          <div className="mono" style={{ fontSize: 10, color: 'var(--text-4)', letterSpacing: '0.12em' }}>{label.toUpperCase()}</div>
        </div>
      </div>
    </div>
  );
}

export function ChecklistChips({ checklist }: { checklist: GuideChecklist }) {
  return (
    <div style={{ ...warCardStyle, padding: 18 }}>
      <div className="flex items-center gap-2 mb-3">
        <CheckCircle2 size={16} style={{ color: 'var(--accent)' }} />
        <h3 style={{ margin: 0, fontSize: 15 }}>{checklist.title}</h3>
      </div>
      <div className="flex flex-wrap gap-2">
        {checklist.items.map((item) => (
          <span key={item} className="pill" style={{ fontSize: 11.5, color: 'var(--text-2)', background: 'var(--bg)', boxShadow: 'inset 0 0 0 1px var(--border)' }}>
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

export function FormulaCard({ item, index }: { item: string; index: number }) {
  const [formula, note] = item.includes('=') ? item.split(/=(.+)/).filter(Boolean) : [item, ''];
  return (
    <div style={{ ...warCardStyle, padding: 18, background: index % 2 ? 'var(--bg-elev)' : 'var(--bg)' }}>
      <div className="mono" style={{ color: 'var(--accent)', fontSize: 10.5, letterSpacing: '0.12em' }}>
        FORMULA {String(index + 1).padStart(2, '0')}
      </div>
      <div style={{ marginTop: 10, color: 'var(--text)', fontWeight: 650, lineHeight: 1.35 }}>{formula.trim()}</div>
      {note && <p style={{ margin: '8px 0 0', color: 'var(--text-3)', fontSize: 13, lineHeight: 1.45 }}>= {note.trim()}</p>}
    </div>
  );
}

export function GuidePageCard({ resource, guidePath }: { resource: GuideResource; guidePath: string }) {
  return (
    <Link to={`${guidePath}/${resource.slug}`} className="card card-hover" style={{ display: 'block', padding: 18, textDecoration: 'none', color: 'var(--text)', background: 'var(--bg)', minHeight: 132 }}>
      <div className="flex items-start justify-between gap-3">
        <span style={{ width: 36, height: 36, display: 'grid', placeItems: 'center', borderRadius: 999, background: 'var(--accent-soft)', color: 'var(--accent)', flex: '0 0 auto' }}>
          <BookOpen size={16} />
        </span>
        <ArrowRight size={16} style={{ color: 'var(--text-4)', flex: '0 0 auto' }} />
      </div>
      <h3 style={{ margin: '16px 0 0', fontSize: 16, lineHeight: 1.25 }}>{resource.title}</h3>
      <p style={{ margin: '8px 0 0', color: 'var(--text-3)', fontSize: 13, lineHeight: 1.45 }}>{resource.summary}</p>
    </Link>
  );
}

export function GuideRightRailLayout({
  scrollRef,
  sectionItems,
  children,
  mainGap = 'wide',
  railAt = 'xl',
}: {
  scrollRef: RefObject<HTMLDivElement>;
  sectionItems: SectionNavItem[];
  children: ReactNode;
  mainGap?: 'normal' | 'wide';
  railAt?: 'lg' | 'xl';
}) {
  const gridClass = railAt === 'lg' ? 'grid gap-6 items-start lg:grid-cols-[minmax(0,1fr)_260px]' : 'grid gap-6 xl:grid-cols-[minmax(0,1fr)_250px] items-start';
  const desktopRailClass = railAt === 'lg' ? 'hidden lg:block' : 'hidden xl:block';
  const mobileNavClass = railAt === 'lg' ? 'lg:hidden' : 'xl:hidden';
  const mainClass = mainGap === 'normal' ? 'grid gap-6' : 'grid gap-7';

  return (
    <div className={gridClass}>
      <main className={mainClass} style={{ minWidth: 0, gridColumn: 1 }}>
        <div className={mobileNavClass}>
          <SectionNav items={sectionItems} scrollContainer={scrollRef} />
        </div>
        {children}
      </main>
      <aside className={desktopRailClass} style={{ position: 'sticky', top: 16, gridColumn: 2 }}>
        <SectionNav items={sectionItems} scrollContainer={scrollRef} nonSticky />
      </aside>
    </div>
  );
}

export function GuideCommandStrip({
  id,
  eyebrow,
  description,
  primaryLabel,
  config,
  guidePages,
  stats,
}: {
  id: string;
  eyebrow: string;
  description: string;
  primaryLabel: string;
  config: GuideConfig;
  guidePages: GuideResource[];
  stats: { label: string; value: ReactNode; icon: typeof Target }[];
}) {
  return (
    <section id={id} style={{ ...warCardStyle, padding: 18, scrollMarginTop: 24 }}>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_auto] lg:items-center">
        <div>
          <div className="mono" style={{ color: 'var(--accent)', fontSize: 10.5, letterSpacing: '0.14em' }}>{eyebrow.toUpperCase()}</div>
          <p style={{ margin: '8px 0 0', color: 'var(--text-2)', lineHeight: 1.55, maxWidth: 860 }}>{description}</p>
          <div className="flex flex-wrap gap-3" style={{ marginTop: 14 }}>
            <Link to={config.questionsPath} className="btn btn-primary" style={{ textDecoration: 'none' }}>
              {primaryLabel} <ArrowRight size={16} />
            </Link>
            {guidePages[0] && <Link to={`${config.guidePath}/${guidePages[0].slug}`} className="btn btn-ghost" style={{ textDecoration: 'none' }}>Start first drill</Link>}
          </div>
        </div>
        <div className="grid gap-2" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', minWidth: 320 }}>
          {stats.map((stat) => <WarStat key={stat.label} {...stat} />)}
        </div>
      </div>
    </section>
  );
}

export function TimelineCards({ steps }: { steps: { time: string; label: string; detail: string }[] }) {
  return (
    <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
      {steps.map((step, index) => (
        <div key={`${step.time}-${step.label}`} style={{ ...warCardStyle, padding: 18 }}>
          <div className="flex items-center justify-between gap-3">
            <span className="mono" style={{ color: 'var(--accent)', fontSize: 11 }}>{step.time}</span>
            <span className="mono" style={{ color: 'var(--text-4)', fontSize: 10 }}>{String(index + 1).padStart(2, '0')}</span>
          </div>
          <h3 style={{ margin: '18px 0 0', fontSize: 18 }}>{step.label}</h3>
          <p style={{ margin: '8px 0 0', color: 'var(--text-3)', fontSize: 13, lineHeight: 1.5 }}>{step.detail}</p>
        </div>
      ))}
    </div>
  );
}

export function DecisionLaneGrid({ lanes }: { lanes: { title: string; signal: string; move: string; icon: typeof Target }[] }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {lanes.map(({ title, signal, move, icon: Icon }) => (
        <details key={title} open style={{ ...warCardStyle, padding: 18 }}>
          <summary className="flex items-center gap-3" style={{ cursor: 'pointer', listStyle: 'none' }}>
            <span style={{ width: 38, height: 38, borderRadius: 999, background: 'var(--accent-soft)', color: 'var(--accent)', display: 'grid', placeItems: 'center', flex: '0 0 auto' }}>
              <Icon size={18} />
            </span>
            <span style={{ minWidth: 0 }}>
              <strong style={{ display: 'block', fontSize: 16 }}>{title}</strong>
              <span style={{ color: 'var(--text-3)', fontSize: 13 }}>{signal}</span>
            </span>
          </summary>
          <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid var(--border)', color: 'var(--text-2)', lineHeight: 1.55 }}>{move}</div>
        </details>
      ))}
    </div>
  );
}

export function SignalCards({ section, prefix }: { section?: GuideSection; prefix: string }) {
  if (!section) return null;
  return (
    <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
      {section.items.map((item, index) => {
        const { signal, move } = splitSignal(item);
        return (
          <article key={item} style={{ ...warCardStyle, padding: 18 }}>
            <div className="mono" style={{ color: 'var(--accent)', fontSize: 10.5, letterSpacing: '0.12em' }}>{prefix} {String(index + 1).padStart(2, '0')}</div>
            <h3 style={{ margin: '12px 0 0', fontSize: 16, lineHeight: 1.3 }}>{signal}</h3>
            <p style={{ margin: '8px 0 0', color: 'var(--text-3)', fontSize: 13, lineHeight: 1.5 }}>{move}</p>
          </article>
        );
      })}
    </div>
  );
}

export function LabelDetailCards({ section, prefix }: { section?: GuideSection; prefix: string }) {
  if (!section) return null;
  return (
    <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))' }}>
      {section.items.map((item, index) => {
        const { label, detail } = splitLabel(item);
        return (
          <article key={item} style={{ ...warCardStyle, padding: 18 }}>
            <div className="mono" style={{ color: 'var(--accent)', fontSize: 10.5, letterSpacing: '0.12em' }}>{prefix} {String(index + 1).padStart(2, '0')}</div>
            <h3 style={{ margin: '12px 0 0', fontSize: 17 }}>{label}</h3>
            <p style={{ margin: '8px 0 0', color: 'var(--text-3)', fontSize: 13, lineHeight: 1.5 }}>{detail}</p>
          </article>
        );
      })}
    </div>
  );
}

export function PracticeFocusedPage({
  guide,
  config,
  scrollRef,
  sectionItems,
  eyebrow,
  ctaText,
}: {
  guide: GuideRecord;
  config: GuideConfig;
  scrollRef: RefObject<HTMLDivElement>;
  sectionItems: SectionNavItem[];
  eyebrow: string;
  ctaText: string;
}) {
  return (
    <div className="h-full flex flex-col min-h-0">
      <AppHeader eyebrow={eyebrow} title={guide.title} description={guide.description} />
      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto px-5 sm:px-8 pb-8 pt-6">
        <GuideRightRailLayout scrollRef={scrollRef} sectionItems={sectionItems} mainGap="normal">
          <div className="flex items-center justify-between gap-3 flex-wrap" style={{ ...warCardStyle, padding: 14 }}>
            <BackLink to={config.guidePath} />
            <Link to={config.questionsPath} className="pill mono" style={{ textDecoration: 'none', color: 'var(--accent)' }}>PRACTICE PROMPTS</Link>
          </div>
          <section className="grid gap-4">
            {guide.sections.map((section, index) => (
              <article key={section.id} id={section.id} style={{ ...warCardStyle, padding: 22, scrollMarginTop: 24 }}>
                <div className="grid gap-5 lg:grid-cols-[190px_minmax(0,1fr)]">
                  <div>
                    <div className="mono" style={{ color: 'var(--accent)', fontSize: 10.5, letterSpacing: '0.12em' }}>DRILL {String(index + 1).padStart(2, '0')}</div>
                    <h3 className="display-italic" style={{ margin: '10px 0 0', fontSize: 32, lineHeight: 1, fontWeight: 400 }}>{section.title}</h3>
                    <p style={{ margin: '12px 0 0', color: 'var(--text-3)', fontSize: 13.5, lineHeight: 1.55 }}>{section.summary}</p>
                  </div>
                  <WarActionList items={section.items} />
                </div>
              </article>
            ))}
          </section>
          <section id="checklists" className="grid gap-4">
            <WarHeading eyebrow="Checklist Rail" title="Scan this before you close the drill" />
            <div className="grid gap-3 lg:grid-cols-2">
              {guide.checklists.map((checklist) => <ChecklistChips key={checklist.title} checklist={checklist} />)}
            </div>
          </section>
          <section style={{ ...warCardStyle, padding: 20 }}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p style={{ margin: 0, color: 'var(--text-2)', lineHeight: 1.55 }}>{ctaText}</p>
              <Link to={config.guidePath} className="btn btn-primary" style={{ textDecoration: 'none' }}>All guide pages <ArrowRight size={16} /></Link>
            </div>
          </section>
        </GuideRightRailLayout>
      </div>
    </div>
  );
}

export function GenericGuideLayout({
  guide,
  config,
  slug,
  scrollRef,
  sectionItems,
}: {
  guide: GuideRecord;
  config: GuideConfig;
  slug?: string;
  scrollRef: RefObject<HTMLDivElement>;
  sectionItems: SectionNavItem[];
}) {
  const topicCount = getGuidePages(guide).length;
  const backTo = slug ? config.guidePath : config.questionsPath;

  return (
    <div className="h-full flex flex-col min-h-0">
      <AppHeader eyebrow={config.eyebrow} title={guide.title} description={guide.description} />
      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto px-5 sm:px-8 pb-8 pt-6">
        <div className="grid gap-6" style={{ gridTemplateColumns: 'minmax(0, 1fr)' }}>
          <div className="flex items-center justify-between gap-3 flex-wrap">
            <BackLink to={backTo} />
            {slug && <Link to={config.guidePath} className="pill mono" style={{ textDecoration: 'none', color: 'var(--accent)' }}>ALL GUIDE PAGES</Link>}
          </div>

          <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
            {[
              { icon: Map, label: 'Strategy Sections', value: guide.sections.length },
              { icon: ListChecks, label: 'Checklist Sets', value: guide.checklists.length },
              { icon: ShieldCheck, label: slug ? 'Focused Page' : 'Guide Pages', value: slug ? 1 : topicCount },
            ].map(({ icon: Icon, label, value }) => (
              <div key={label} className="card" style={{ padding: 20 }}>
                <div className="flex items-center gap-3">
                  <span style={{ width: 38, height: 38, display: 'grid', placeItems: 'center', borderRadius: 999, background: 'var(--accent-soft)', color: 'var(--accent)' }}>
                    <Icon size={18} />
                  </span>
                  <div>
                    <div className="display-italic" style={{ fontSize: 28, lineHeight: 1 }}>{value}</div>
                    <div className="mono" style={{ fontSize: 10.5, color: 'var(--text-4)', letterSpacing: '0.1em' }}>{label.toUpperCase()}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <GuideRightRailLayout scrollRef={scrollRef} sectionItems={sectionItems} mainGap="normal" railAt="lg">
            {guide.sections.map((section, index) => (
              <section key={section.id} style={cardStyle} className="fade-up">
                <div className="flex items-start gap-4">
                  <span className="mono" style={{ flex: '0 0 auto', color: 'var(--text-4)', fontSize: 11, letterSpacing: '0.12em', paddingTop: 8 }}>
                    {String(index + 1).padStart(2, '0')}
                  </span>
                  <div className="grid gap-4" style={{ minWidth: 0 }}>
                    <SectionHeading id={section.id}>{section.title}</SectionHeading>
                    <p style={{ margin: 0, color: 'var(--text-3)', lineHeight: 1.65 }}>{section.summary}</p>
                    <NumberedList items={section.items} />
                  </div>
                </div>
              </section>
            ))}

            <section id="checklists" style={cardStyle}>
              <div className="grid gap-5">
                <SectionHeading>Fast Checklists</SectionHeading>
                <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
                  {guide.checklists.map((checklist) => (
                    <div key={checklist.title} className="card" style={{ padding: 20, background: 'var(--bg)' }}>
                      <h3 style={{ margin: '0 0 12px', fontSize: 16 }}>{checklist.title}</h3>
                      <ul className="grid gap-2" style={{ margin: 0, paddingLeft: 18, color: 'var(--text-2)' }}>
                        {checklist.items.map((item) => <li key={item}>{item}</li>)}
                      </ul>
                    </div>
                  ))}
                </div>
              </div>
            </section>

            {guide.resources.some((category) => category.items.length > 0) && (
              <section id="guide-pages" style={cardStyle}>
                <div className="grid gap-5">
                  <div>
                    <SectionHeading>Guide Pages</SectionHeading>
                    <p style={{ margin: '12px 0 0', color: 'var(--text-3)', lineHeight: 1.6 }}>Continue with focused pages that boil the source material into interview-ready strategy.</p>
                  </div>
                  <div className="grid gap-5">
                    {guide.resources.map((category) => (
                      <div key={category.category} className="grid gap-3">
                        <h3 className="mono" style={{ margin: 0, fontSize: 11, color: 'var(--text-4)', letterSpacing: '0.12em' }}>{category.category.toUpperCase()}</h3>
                        <div className="grid gap-3" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))' }}>
                          {category.items.map((resource) => <GuidePageCard key={resource.slug} resource={resource} guidePath={config.guidePath} />)}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            )}
          </GuideRightRailLayout>
        </div>
      </div>
    </div>
  );
}
