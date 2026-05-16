import { useLayoutEffect, useRef } from 'react';
import { Navigate, useParams } from 'react-router-dom';
import { TRACK_CONFIGS } from '../guideTypes';
import { aiCodingNavGroups } from './nav';
import AICodingDashboard from './AICodingDashboard';
import MentalModel from './pages/MentalModel';
import Cheatsheet from './pages/Cheatsheet';
import PromptPlaybook from './pages/PromptPlaybook';
import ReviewHabits from './pages/ReviewHabits';
import Companies from './pages/Companies';

const KNOWN_SLUGS = ['mental-model', 'cheatsheet', 'prompt-playbook', 'review-habits', 'companies'] as const;
type Slug = (typeof KNOWN_SLUGS)[number];

export default function AICodingGuide() {
  const config = TRACK_CONFIGS['ai-coding'];
  const { slug } = useParams<{ slug: string }>();
  const scrollRef = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => { scrollRef.current?.scrollTo({ top: 0, left: 0 }); }, [slug]);

  if (!slug) {
    return <AICodingDashboard config={config} navGroups={aiCodingNavGroups} scrollRef={scrollRef} />;
  }
  if (!KNOWN_SLUGS.includes(slug as Slug)) {
    return <Navigate to={config.guidePath} replace />;
  }
  const common = { config, navGroups: aiCodingNavGroups, scrollRef };
  switch (slug as Slug) {
    case 'mental-model':    return <MentalModel {...common} />;
    case 'cheatsheet':      return <Cheatsheet {...common} />;
    case 'prompt-playbook': return <PromptPlaybook {...common} />;
    case 'review-habits':   return <ReviewHabits {...common} />;
    case 'companies':       return <Companies {...common} />;
  }
}
