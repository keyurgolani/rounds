import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../../api/client';
import AppHeader from '../../components/shell/AppHeader';
import BackLink from '../../components/shell/BackLink';
import type { SectionNavItem } from '../../components/shell/SectionNav';
import BehavioralGuideExperience from './BehavioralGuideExperience';
import CodingGuideExperience from './CodingGuideExperience';
import { GenericGuideLayout } from './GuideShared';
import { GUIDE_CONFIGS, type GuideRecord, type GuideTrack } from './guideTypes';
import SystemDesignGuideExperience from './SystemDesignGuideExperience';

export default function GuidePage({ track = 'system-design' }: { track?: GuideTrack }) {
  const config = GUIDE_CONFIGS[track];
  const { slug } = useParams<{ slug: string }>();
  const [guide, setGuide] = useState<GuideRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    scrollRef.current?.scrollTo({ top: 0, left: 0 });
  }, [track, slug, guide?.title]);

  useEffect(() => {
    let isActive = true;

    setLoading(true);
    setError(null);
    setGuide(null);

    api
      .get<GuideRecord>(slug ? `${config.apiBase}/${slug}` : config.apiBase)
      .then((record) => {
        if (isActive) setGuide(record);
      })
      .catch((err: unknown) => {
        if (isActive) setError(err instanceof Error ? err.message : 'Unable to load guide');
      })
      .finally(() => {
        if (isActive) setLoading(false);
      });

    return () => {
      isActive = false;
    };
  }, [config.apiBase, slug]);

  const sectionItems = useMemo<SectionNavItem[]>(() => {
    if (!guide) return [];
    const items = [
      ...guide.sections.map((section) => ({ id: section.id, label: section.title })),
      { id: 'checklists', label: 'Checklists' },
    ];
    if (guide.resources.some((category) => category.items.length > 0)) {
      items.push({ id: 'guide-pages', label: 'Guide pages' });
    }
    return items;
  }, [guide]);

  if (loading) {
    return (
      <div className="h-full flex flex-col min-h-0">
        <AppHeader eyebrow={config.loadingEyebrow} title="Interview Guide" description="Loading the API-backed guide..." />
        <div className="p-8" style={{ color: 'var(--text-3)' }}>Loading...</div>
      </div>
    );
  }

  if (error || !guide) {
    return (
      <div className="h-full flex flex-col min-h-0">
        <AppHeader eyebrow={config.loadingEyebrow} title="Interview Guide" description="The guide could not be loaded." />
        <div className="p-8">
          <BackLink to={config.questionsPath} />
          <div className="card mt-5" style={{ padding: 24, color: 'var(--text-2)' }}>
            {error ?? 'No guide record was found.'}
          </div>
        </div>
      </div>
    );
  }

  if (track === 'system-design') {
    return <SystemDesignGuideExperience guide={guide} config={config} slug={slug} scrollRef={scrollRef} />;
  }

  if (track === 'coding') {
    return <CodingGuideExperience guide={guide} config={config} slug={slug} scrollRef={scrollRef} />;
  }

  if (track === 'behavioral') {
    return <BehavioralGuideExperience guide={guide} config={config} slug={slug} scrollRef={scrollRef} />;
  }

  return <GenericGuideLayout guide={guide} config={config} slug={slug} scrollRef={scrollRef} sectionItems={sectionItems} />;
}
