import { Navigate, useParams } from 'react-router-dom';
import type { GuideTrack } from './guideTypes';
import { TRACK_CONFIGS } from './guideTypes';
import CodingGuide from './coding/CodingGuide';
import SystemDesignGuide from './system-design/SystemDesignGuide';
import BehavioralGuide from './behavioral/BehavioralGuide';
import AICodingGuide from './ai-coding/AICodingGuide';
import BuilderGuide from './builder/BuilderGuide';

const slugRedirects: Record<GuideTrack, Record<string, string>> = {
  coding: {
    'interview-strategy':   'cheatsheet',
    'pattern-playbook':     'patterns',
    'optimization-testing': 'complexity',
    'practice-plan':        'patterns',
  },
  'system-design': {
    'interview-strategy':       'round-flow',
    'requirements-estimation':  'capacity-math',
    'core-components':          'building-blocks',
    'data-storage':             'building-blocks',
    'tradeoffs-reliability':    'reliability',
    'practice-playbook':        'round-flow',
  },
  behavioral: {
    'story-crafting':    'story-bank',
    'signal-rubric':     'mental-model',
    'senior-behavioral': 'senior-scope',
    'practice-playbook': 'repair',
  },
  'ai-coding': {},
  builder: {},
};

export default function GuidePage({ track = 'system-design' }: { track?: GuideTrack | 'take-home' }) {
  const { slug } = useParams<{ slug: string }>();

  if (track === 'take-home') {
    return <Navigate to="/builder/guide" replace />;
  }

  if (slug && slugRedirects[track][slug]) {
    return <Navigate to={`${TRACK_CONFIGS[track].guidePath}/${slugRedirects[track][slug]}`} replace />;
  }
  switch (track) {
    case 'coding':        return <CodingGuide />;
    case 'system-design': return <SystemDesignGuide />;
    case 'behavioral':    return <BehavioralGuide />;
    case 'ai-coding':     return <AICodingGuide />;
    case 'builder':       return <BuilderGuide />;
  }
}
