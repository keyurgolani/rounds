import type { GuideNavGroup } from '../shared/GuideNav';

export const systemDesignNavGroups: GuideNavGroup[] = [
  {
    label: 'Frame',
    items: [
      { slug: '',             label: 'Dashboard' },
      { slug: 'mental-model', label: 'Mental Model' },
      { slug: 'cheatsheet',   label: 'Cheatsheet' },
    ],
  },
  {
    label: 'Topics',
    items: [
      { slug: 'round-flow',      label: 'Round Flow' },
      { slug: 'decisions',       label: 'Decisions' },
      { slug: 'capacity-math',   label: 'Capacity Math' },
      { slug: 'building-blocks', label: 'Building Blocks' },
      { slug: 'reliability',     label: 'Reliability' },
    ],
  },
];
