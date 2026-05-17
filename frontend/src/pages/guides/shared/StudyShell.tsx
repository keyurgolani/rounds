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
      <AppHeader eyebrow={eyebrow} title={title} description={description} />
      <div
        ref={scrollRef}
        role="main"
        className="flex-1 min-h-0 overflow-y-auto"
      >
        {/* Sticky top region: practice progress + CTA above, then the
            pill nav + length picker. Both regions stick to the top of
            the scrollable column so they remain accessible while the
            user reads. */}
        <div
          style={{
            position: 'sticky',
            top: 0,
            zIndex: 20,
            background: 'var(--bg)',
            paddingInline: 'var(--page-pad-x)',
            paddingTop: 'var(--gap-md)',
            paddingBottom: 0,
          }}
        >
          {track && <StudyPracticeBar track={track} />}
          <div
            className="flex flex-wrap"
            style={{
              gap: 'var(--gap-md)',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginTop: 'var(--gap-sm)',
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

        {/* Content column — full width with a reading-width cap so long
            paragraphs don't run edge to edge. Diagrams that need more
            room can break out via their own width:100% styling. */}
        <div
          className="grid"
          style={{
            gap: 'var(--gap-lg)',
            padding: 'var(--gap-lg) var(--page-pad-x) var(--gap-lg)',
            maxWidth: 'min(960px, 100%)',
            margin: '0 auto',
            width: '100%',
          }}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
