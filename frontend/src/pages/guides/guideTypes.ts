export type GuideSection = {
  id: string;
  title: string;
  summary: string;
  items: string[];
};

export type GuideChecklist = {
  title: string;
  items: string[];
};

export type GuideResource = {
  title: string;
  slug: string;
  summary: string;
};

export type GuideResourceCategory = {
  category: string;
  items: GuideResource[];
};

export type GuideRecord = {
  title: string;
  description: string;
  sections: GuideSection[];
  checklists: GuideChecklist[];
  resources: GuideResourceCategory[];
};

export const GUIDE_CONFIGS = {
  'system-design': {
    apiBase: '/api/system-design/guide',
    guidePath: '/system-design/guide',
    questionsPath: '/system-design/questions',
    eyebrow: 'System Design · Guide',
    loadingEyebrow: 'System Design',
  },
  coding: {
    apiBase: '/api/coding/guide',
    guidePath: '/coding/guide',
    questionsPath: '/coding/questions',
    eyebrow: 'Coding · Guide',
    loadingEyebrow: 'Coding',
  },
  behavioral: {
    apiBase: '/api/behavioral/guide',
    guidePath: '/behavioral/guide',
    questionsPath: '/behavioral/questions',
    eyebrow: 'Behavioral · Guide',
    loadingEyebrow: 'Behavioral',
  },
} as const;

export type GuideTrack = keyof typeof GUIDE_CONFIGS;
export type GuideConfig = (typeof GUIDE_CONFIGS)[GuideTrack];
