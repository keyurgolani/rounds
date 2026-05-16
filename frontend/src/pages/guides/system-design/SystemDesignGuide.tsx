import { useLayoutEffect, useRef } from 'react';
import { Navigate, useParams } from 'react-router-dom';
import { TRACK_CONFIGS } from '../guideTypes';
import { systemDesignNavGroups } from './nav';
import SystemDesignDashboard from './SystemDesignDashboard';
import MentalModel from './pages/MentalModel';
import Cheatsheet from './pages/Cheatsheet';
import RoundFlow from './pages/RoundFlow';
import CapacityMath from './pages/CapacityMath';
import BuildingBlocks from './pages/BuildingBlocks';
import Reliability from './pages/Reliability';

const KNOWN_SLUGS = [
  'mental-model', 'cheatsheet', 'round-flow',
  'capacity-math', 'building-blocks', 'reliability',
] as const;
type Slug = (typeof KNOWN_SLUGS)[number];

export default function SystemDesignGuide() {
  const config = TRACK_CONFIGS['system-design'];
  const { slug } = useParams<{ slug: string }>();
  const scrollRef = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => { scrollRef.current?.scrollTo({ top: 0, left: 0 }); }, [slug]);

  if (!slug) {
    return <SystemDesignDashboard config={config} navGroups={systemDesignNavGroups} scrollRef={scrollRef} />;
  }
  if (!KNOWN_SLUGS.includes(slug as Slug)) {
    return <Navigate to={config.guidePath} replace />;
  }

  const common = { config, navGroups: systemDesignNavGroups, scrollRef };
  switch (slug as Slug) {
    case 'mental-model':    return <MentalModel {...common} />;
    case 'cheatsheet':      return <Cheatsheet {...common} />;
    case 'round-flow':      return <RoundFlow {...common} />;
    case 'capacity-math':   return <CapacityMath {...common} />;
    case 'building-blocks': return <BuildingBlocks {...common} />;
    case 'reliability':     return <Reliability {...common} />;
  }
}
