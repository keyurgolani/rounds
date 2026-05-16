import { useLayoutEffect, useRef } from 'react';
import { Navigate, useParams } from 'react-router-dom';
import { TRACK_CONFIGS } from '../guideTypes';
import { builderNavGroups } from './nav';
import BuilderDashboard from './BuilderDashboard';
import MentalModel from './pages/MentalModel';
import Cheatsheet from './pages/Cheatsheet';
import TimePlan from './pages/TimePlan';
import Submission from './pages/Submission';
import DomainCheats from './pages/DomainCheats';

const KNOWN_SLUGS = ['mental-model', 'cheatsheet', 'time-plan', 'submission', 'domain-cheats'] as const;
type Slug = (typeof KNOWN_SLUGS)[number];

export default function BuilderGuide() {
  const config = TRACK_CONFIGS.builder;
  const { slug } = useParams<{ slug: string }>();
  const scrollRef = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => { scrollRef.current?.scrollTo({ top: 0, left: 0 }); }, [slug]);

  if (!slug) {
    return <BuilderDashboard config={config} navGroups={builderNavGroups} scrollRef={scrollRef} />;
  }
  if (!KNOWN_SLUGS.includes(slug as Slug)) {
    return <Navigate to={config.guidePath} replace />;
  }
  const common = { config, navGroups: builderNavGroups, scrollRef };
  switch (slug as Slug) {
    case 'mental-model':  return <MentalModel {...common} />;
    case 'cheatsheet':    return <Cheatsheet {...common} />;
    case 'time-plan':     return <TimePlan {...common} />;
    case 'submission':    return <Submission {...common} />;
    case 'domain-cheats': return <DomainCheats {...common} />;
  }
}
