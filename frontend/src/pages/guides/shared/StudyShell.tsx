import type { ReactNode, RefObject } from 'react';
import AppHeader from '../../../components/shell/AppHeader';
import GuideNav, { type GuideNavGroup } from './GuideNav';
import StudyPracticeBar from './StudyPracticeBar';
import InterviewLengthPicker from './InterviewLengthPicker';
import type { GuideTrack } from '../guideTypes';

type Props = {
  eyebrow: string;
  title: string;
  description: string;
  navGroups: GuideNavGroup[];
  trackBasePath: string;       // e.g. '/coding/guide'
  scrollRef: RefObject<HTMLDivElement>;
  children: ReactNode;
};

/** '/coding/guide' -> 'coding'. Mirrors TRACK_CONFIGS keys. */
function trackFromBasePath(basePath: string): GuideTrack | null {
  const slug = basePath.replace(/^\//, '').replace(/\/guide$/, '');
  const known: GuideTrack[] = [
    'system-design',
    'coding',
    'behavioral',
    'ai-coding',
    'builder',
  ];
  return (known as string[]).includes(slug) ? (slug as GuideTrack) : null;
}

export default function StudyShell({
  eyebrow,
  title,
  description,
  navGroups,
  trackBasePath,
  scrollRef,
  children,
}: Props) {
  const track = trackFromBasePath(trackBasePath);

  return (
    <div className="h-full flex flex-col min-h-0">
      <AppHeader
        eyebrow={eyebrow}
        title={title}
        description={description}
        actions={track ? <StudyPracticeBar track={track} compact /> : undefined}
      />
      <div
        ref={scrollRef}
        role="main"
        className="flex-1 min-h-0 overflow-y-auto"
      >
        {/* Sticky pill nav + length picker. The practice progress + CTA
            now live in the page header (compact strip) so the in-page
            sticky region is just the section navigation. */}
        <div
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 20,
            background: 'var(--bg)',
            paddingInline: 'var(--page-pad-x)',
            paddingTop: 'var(--gap-sm)',
            paddingBottom: 0,
          }}
        >
          <div
            className="flex flex-wrap"
            style={{
              gap: 'var(--gap-md)',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingBottom: 'var(--gap-sm)',
              borderBottom: '1px solid var(--border)',
            }}
          >
            <GuideNav
              groups={navGroups}
              trackBasePath={trackBasePath}
              orientation="horizontal"
            />
            {track && <InterviewLengthPicker track={track} />}
          </div>
        </div>

        {/* Content column — full width, no reading-width cap. Diagrams
            and prose stretch to the available viewport so the page
            doesn't leave dead space on the sides. */}
        <div
          className="grid"
          style={{
            gap: 'var(--gap-lg)',
            padding: 'var(--gap-lg) var(--page-pad-x) var(--gap-lg)',
            width: '100%',
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
