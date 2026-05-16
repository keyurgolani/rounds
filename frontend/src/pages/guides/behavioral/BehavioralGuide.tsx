import { useLayoutEffect, useRef } from 'react';
import { Navigate, useParams } from 'react-router-dom';
import { TRACK_CONFIGS } from '../guideTypes';
import { behavioralNavGroups } from './nav';
import BehavioralDashboard from './BehavioralDashboard';
import MentalModel from './pages/MentalModel';
import Cheatsheet from './pages/Cheatsheet';
import StoryBank from './pages/StoryBank';
import SeniorScope from './pages/SeniorScope';
import Repair from './pages/Repair';

const KNOWN_SLUGS = ['mental-model', 'cheatsheet', 'story-bank', 'senior-scope', 'repair'] as const;
type Slug = (typeof KNOWN_SLUGS)[number];

export default function BehavioralGuide() {
  const config = TRACK_CONFIGS.behavioral;
  const { slug } = useParams<{ slug: string }>();
  const scrollRef = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => { scrollRef.current?.scrollTo({ top: 0, left: 0 }); }, [slug]);

  if (!slug) {
    return <BehavioralDashboard config={config} navGroups={behavioralNavGroups} scrollRef={scrollRef} />;
  }
  if (!KNOWN_SLUGS.includes(slug as Slug)) {
    return <Navigate to={config.guidePath} replace />;
  }
  const common = { config, navGroups: behavioralNavGroups, scrollRef };
  switch (slug as Slug) {
    case 'mental-model': return <MentalModel {...common} />;
    case 'cheatsheet':   return <Cheatsheet {...common} />;
    case 'story-bank':   return <StoryBank {...common} />;
    case 'senior-scope': return <SeniorScope {...common} />;
    case 'repair':       return <Repair {...common} />;
  }
}
