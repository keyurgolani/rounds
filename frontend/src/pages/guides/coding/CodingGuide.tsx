import { useLayoutEffect, useRef } from 'react';
import { Navigate, useParams } from 'react-router-dom';
import { TRACK_CONFIGS } from '../guideTypes';
import { codingNavGroups } from './nav';
import CodingDashboard from './CodingDashboard';
import MentalModel from './pages/MentalModel';
import Cheatsheet from './pages/Cheatsheet';
import CodeKit from './pages/CodeKit';
import Patterns from './pages/Patterns';
import Complexity from './pages/Complexity';

const KNOWN_SLUGS = ['mental-model', 'cheatsheet', 'code-kit', 'patterns', 'complexity'] as const;
type Slug = (typeof KNOWN_SLUGS)[number];

export default function CodingGuide() {
  const config = TRACK_CONFIGS.coding;
  const { slug } = useParams<{ slug: string }>();
  const scrollRef = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    scrollRef.current?.scrollTo({ top: 0, left: 0 });
  }, [slug]);

  if (!slug) {
    return (
      <CodingDashboard
        config={config}
        navGroups={codingNavGroups}
        scrollRef={scrollRef}
      />
    );
  }

  if (!KNOWN_SLUGS.includes(slug as Slug)) {
    return <Navigate to={config.guidePath} replace />;
  }

  const common = { config, navGroups: codingNavGroups, scrollRef };
  switch (slug as Slug) {
    case 'mental-model': return <MentalModel {...common} />;
    case 'cheatsheet':   return <Cheatsheet {...common} />;
    case 'code-kit':     return <CodeKit {...common} />;
    case 'patterns':     return <Patterns {...common} />;
    case 'complexity':   return <Complexity {...common} />;
  }
}
