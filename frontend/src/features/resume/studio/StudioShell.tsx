// Three-pane Studio with independent scroll containers.
//
//   ┌─ Sections (own scroll) ┐ ┌─ Active editor (own scroll) ┐ ┌─ Live preview (own scroll) ┐
//   │ 1 Personal             │ │  form OR design OR tailor   │ │                            │
//   │ 2 Experience           │ │  OR ATS OR history          │ │   A4 page                  │
//   │ …                      │ │                             │ │   updates live             │
//   │                        │ │                             │ │                            │
//   │  ┄┄┄┄┄                 │ │                             │ │                            │
//   │ Design / Tailor /      │ │                             │ │                            │
//   │ ATS / History          │ │                             │ │                            │
//   └────────────────────────┘ └─────────────────────────────┘ └────────────────────────────┘
//
// Each pane sets its own height to 100% of the studio shell and owns
// its own `overflow-y: auto`. The page itself never scrolls — every
// scrollable surface is a pane, so scrolling sections doesn't move
// the form, scrolling the form doesn't move the preview, etc.

import { useEffect, useState } from 'react';
import {
  Download,
  Gauge,
  History,
  Layout as LayoutIcon,
  Palette,
  Wand2,
} from 'lucide-react';
import type { Resume, ResumeData, SectionKey, TemplateConfig } from '../types';
import type { UseResumeResult } from '../hooks/useResume';
import { emptyLinks, type ResumeLinks } from '../links/types';
import { loadLibrarySnapshot, type LibraryData } from '../links/library';
import { SECTION_LABELS } from '../utils';
import SectionNav from './SectionNav';
import PreviewPane from './PreviewPane';
import DesignSidebar from './DesignSidebar';
import { EnhancementProvider } from './EnhancementContext';
import HistoryTab from './tabs/HistoryTab';
import ATSTab from './tabs/ATSTab';
import TailorTab from './tabs/TailorTab';
import TemplatesTab from './tabs/TemplatesTab';
import ExportTab from './tabs/ExportTab';
import PersonalInfoEditor from './editors/PersonalInfoEditor';
import ExperienceEditor from './editors/ExperienceEditor';
import EducationEditor from './editors/EducationEditor';
import SkillsEditor from './editors/SkillsEditor';
import ProjectsEditor from './editors/ProjectsEditor';
import PublicationsEditor from './editors/PublicationsEditor';
import ProfilesEditor from './editors/ProfilesEditor';

export type ToolKey =
  | 'templates'
  | 'design'
  | 'tailor'
  | 'ats'
  | 'history'
  | 'export';
export type ActiveKey = SectionKey | ToolKey;

// Every value the studio recognises as a tab. ResumeStudio uses this
// to validate the `?tab=` URL parameter before passing it down.
export const VALID_TABS: readonly ActiveKey[] = [
  'personal',
  'experience',
  'education',
  'skills',
  'projects',
  'publications',
  'profiles',
  'templates',
  'design',
  'tailor',
  'ats',
  'history',
  'export',
] as const;

const TOOLS: { key: ToolKey; label: string; icon: typeof Palette }[] = [
  { key: 'templates', label: 'Templates', icon: LayoutIcon },
  { key: 'design', label: 'Design', icon: Palette },
  { key: 'tailor', label: 'Tailor', icon: Wand2 },
  { key: 'ats', label: 'ATS Score', icon: Gauge },
  { key: 'history', label: 'History', icon: History },
  { key: 'export', label: 'Export', icon: Download },
];

const TOOL_LABELS: Record<ToolKey, string> = {
  templates: 'Templates',
  design: 'Design',
  tailor: 'Tailor',
  ats: 'ATS Score',
  history: 'Version history',
  export: 'Export',
};

const ACTIVE_HINTS: Record<ActiveKey, string> = {
  personal: 'Name, contact, headline, and a short summary.',
  experience:
    'Roles in reverse chronological order. Lead bullets with action verbs and measurable outcomes.',
  education: 'Degrees, institutions, and the most relevant coursework.',
  skills:
    'Group skills by category — Languages, Frameworks, Cloud, Tools — so the eye scans them fast.',
  projects:
    'Side projects, open source, and notable production work that ships outside a single employer.',
  publications:
    "Papers, talks, articles. Add a one-line summary that says what's interesting.",
  profiles: 'Public profiles you want recruiters to land on.',
  templates: 'Pick the template that frames your content. Look-and-feel knobs live under Design.',
  design: 'Tune typography, accent color, and page margins. Changes update the preview live.',
  tailor:
    'Anchor this resume to a tracked Application — paste or pull a JD, then let AI rewrite bullets to match.',
  ats:
    'Hybrid score that combines deterministic rule checks with an AI quality pass. Keyword gaps surface against the JD you pick.',
  history:
    'Auto-saves stamp a snapshot at most once per minute. Restoring overwrites the current draft.',
  export:
    'Server PDF, browser print, .docx, HTML, Markdown, plain text, or JSON Resume — pending edits flush before each export.',
};

type Props = {
  result: UseResumeResult;
  // Controlled by the host page (ResumeStudio) so the URL `?tab=`
  // parameter is the single source of truth. The shell never owns
  // this state directly — every selection round-trips through the
  // host so the URL stays in sync.
  active: ActiveKey;
  onActiveChange: (next: ActiveKey) => void;
};

export default function StudioShell({ result, active, onActiveChange }: Props) {
  const setActive = onActiveChange;
  const [wide, setWide] = useState<boolean>(() =>
    typeof window === 'undefined' ? true : window.innerWidth >= 1024,
  );
  const [lib, setLib] = useState<LibraryData | null>(null);

  useEffect(() => {
    const onResize = () => setWide(window.innerWidth >= 1024);
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    loadLibrarySnapshot().then(setLib).catch(() => {});
  }, []);

  const onRestore = (next: ResumeData, nextLinks?: ResumeLinks) => { result.setData(next); result.setLinks(nextLinks ?? emptyLinks()); };
  const isSection = (k: ActiveKey): k is SectionKey =>
    !TOOLS.some((t) => t.key === k);

  const headerLabel = isSection(active) ? SECTION_LABELS[active] : TOOL_LABELS[active as ToolKey];

  return (
    <EnhancementProvider resume={result.data}>
    <div
      style={{
        // The shell fills its flex parent (ResumeStudio's body wrapper).
        // On wide screens it becomes a 3-column grid where each column
        // is its own scroll container; on narrow screens it stacks
        // vertically and the body scrolls naturally.
        flex: '1 1 0',
        minHeight: 0,
        display: 'grid',
        gap: 16,
        gridTemplateColumns: wide ? '230px minmax(0, 1fr) minmax(0, 1.15fr)' : 'minmax(0, 1fr)',
      }}
    >
      <aside
        data-studio-pane="sections"
        style={{
          minHeight: 0,
          height: wide ? '100%' : 'auto',
          display: 'flex',
          flexDirection: 'column',
          gap: 14,
        }}
      >
        <div
          style={{
            flex: 1,
            minHeight: 0,
            overflowY: 'auto',
            overflowX: 'hidden',
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}
        >
          <SectionNav
            data={result.data}
            setData={result.setData}
            active={isSection(active) ? active : null}
            onSelect={(k) => setActive(k)}
          />
        </div>

        <ToolsRail
          active={isSection(active) ? null : (active as ToolKey)}
          onSelect={(k) => setActive(k)}
        />
      </aside>

      <section
        data-studio-pane="form"
        style={{
          minHeight: 0,
          height: wide ? '100%' : 'auto',
          overflowY: wide ? 'auto' : 'visible',
          overflowX: 'hidden',
          paddingRight: wide ? 4 : 0,
        }}
      >
        <SectionHeader label={headerLabel} hint={ACTIVE_HINTS[active]} />
        <ActiveContent
          active={active}
          isSection={isSection(active)}
          data={result.data}
          setData={result.setData}
          links={result.links}
          setLinks={result.setLinks}
          lib={lib}
          templateId={result.templateId}
          setTemplateId={result.setTemplateId}
          design={result.design}
          setDesign={result.setDesign as (next: TemplateConfig | ((prev: TemplateConfig) => TemplateConfig)) => void}
          resume={result.resume as Resume | null}
          onRestore={onRestore}
          flush={result.flush}
        />
      </section>

      <section
        data-studio-pane="preview"
        style={{
          minHeight: 0,
          height: wide ? '100%' : 'auto',
          // Scroll lives on the shaded preview card now (PreviewPane),
          // not the column — that way the surround stays anchored to
          // the column bounds and the resume folds inside it.
          overflow: 'visible',
        }}
      >
        <PreviewPane
          data={result.data}
          templateId={result.templateId}
          design={result.design}
        />
      </section>
    </div>
    </EnhancementProvider>
  );
}

// ---------------------------------------------------------------------------
//                            Sub-components
// ---------------------------------------------------------------------------

function SectionHeader({ label, hint }: { label: string; hint: string }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div className="eyebrow" style={{ fontSize: 9.5, marginBottom: 4 }}>
        {label}
      </div>
      <p style={{ margin: 0, fontSize: 12, color: 'var(--text-3)', lineHeight: 1.5 }}>
        {hint}
      </p>
    </div>
  );
}

function ToolsRail({
  active,
  onSelect,
}: {
  active: ToolKey | null;
  onSelect: (k: ToolKey) => void;
}) {
  return (
    <div
      data-studio-rail="tools"
      className="flex flex-col gap-2"
      style={{ paddingTop: 8 }}
    >
      <div className="flex items-center justify-between px-1">
        <div className="eyebrow" style={{ fontSize: 9.5 }}>
          Tools
        </div>
      </div>
      <div className="flex flex-col gap-1">
        {TOOLS.map(({ key, label, icon: Icon }) => {
          const isActive = active === key;
          return (
            <button
              key={key}
              type="button"
              onClick={() => onSelect(key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 10px',
                background: isActive ? 'var(--accent)' : 'var(--bg-elev)',
                color: isActive ? 'var(--bg-elev)' : 'var(--text)',
                border: 0,
                borderRadius: 'var(--radius)',
                boxShadow: isActive ? 'none' : 'inset 0 0 0 1px var(--border)',
                fontSize: 13,
                fontWeight: 500,
                cursor: 'pointer',
                textAlign: 'left',
              }}
            >
              <Icon
                size={14}
                strokeWidth={1.7}
                style={{ opacity: isActive ? 1 : 0.85, flexShrink: 0 }}
              />
              <span>{label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

type ActiveContentProps = {
  active: ActiveKey;
  isSection: boolean;
  data: ResumeData;
  setData: (next: ResumeData | ((prev: ResumeData) => ResumeData)) => void;
  links: ResumeLinks;
  setLinks: (next: ResumeLinks | ((prev: ResumeLinks) => ResumeLinks)) => void;
  lib: LibraryData | null;
  templateId: string;
  setTemplateId: (id: string) => void;
  design: TemplateConfig;
  setDesign: (next: TemplateConfig | ((prev: TemplateConfig) => TemplateConfig)) => void;
  resume: Resume | null;
  onRestore: (data: ResumeData, nextLinks?: ResumeLinks) => void;
  flush: () => Promise<void>;
};

function ActiveContent(props: ActiveContentProps) {
  const { active, isSection, data, setData } = props;

  if (isSection) {
    switch (active as SectionKey) {
      case 'personal':
        return <PersonalInfoEditor data={data} setData={setData} />;
      case 'experience':
        return (
          <ExperienceEditor
            data={data}
            setData={setData}
            links={props.links}
            setLinks={props.setLinks}
            lib={props.lib}
          />
        );
      case 'education':
        return <EducationEditor data={data} setData={setData} />;
      case 'skills':
        return <SkillsEditor data={data} setData={setData} />;
      case 'projects':
        return (
          <ProjectsEditor
            data={data}
            setData={setData}
            links={props.links}
            setLinks={props.setLinks}
            lib={props.lib}
          />
        );
      case 'publications':
        return <PublicationsEditor data={data} setData={setData} />;
      case 'profiles':
        return <ProfilesEditor data={data} setData={setData} />;
    }
  }

  switch (active as ToolKey) {
    case 'templates':
      return (
        <TemplatesTab
          templateId={props.templateId}
          setTemplateId={props.setTemplateId}
          design={props.design}
        />
      );
    case 'design':
      return (
        <DesignSidebar design={props.design} setDesign={props.setDesign} />
      );
    case 'tailor':
      return (
        <TailorTab
          data={data}
          resume={props.resume}
          setData={setData}
          links={props.links}
          setLinks={props.setLinks}
        />
      );
    case 'ats':
      return <ATSTab data={data} resume={props.resume} />;
    case 'history':
      return <HistoryTab resume={props.resume} onRestore={props.onRestore} />;
    case 'export':
      return (
        <ExportTab
          resume={props.resume}
          data={data}
          onBeforeExport={props.flush}
        />
      );
  }
}

