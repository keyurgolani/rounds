import type { ReactNode, RefObject } from 'react';
import AppHeader from '../../../components/shell/AppHeader';
import GuideNav, { type GuideNavGroup } from './GuideNav';
import StudyPracticeBar from './StudyPracticeBar';
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
  const known: GuideTrack[] = ['system-design', 'coding', 'behavioral', 'ai-coding', 'builder'];
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
        className="flex-1 min-h-0"
        style={{ padding: 'var(--page-pad-y) var(--page-pad-x)' }}
      >
        <div
          className="grid xl:grid-cols-[248px_minmax(0,1fr)] items-stretch h-full min-h-0"
          style={{ gap: 'var(--gap-lg)' }}
        >
          <aside
            className="hidden xl:flex card"
            style={{
              flexDirection: 'column',
              padding: 'var(--pad-sm)',
              height: '100%',
              overflowY: 'auto',
            }}
          >
            <GuideNav
              groups={navGroups}
              trackBasePath={trackBasePath}
              orientation="vertical"
            />
          </aside>
          <div
            ref={scrollRef}
            role="main"
            className="flex flex-col min-h-0 overflow-y-auto"
            style={{
              minWidth: 0,
              gap: 'var(--gap-lg)',
              paddingRight: 2, // scrollbar gutter
              paddingBottom: 'var(--gap-sm)',
            }}
          >
            <div className="xl:hidden">
              <GuideNav
                groups={navGroups}
                trackBasePath={trackBasePath}
                orientation="horizontal"
              />
            </div>
            {children}
            {track && <StudyPracticeBar track={track} />}
          </div>
        </div>
      </div>
    </div>
  );
}
