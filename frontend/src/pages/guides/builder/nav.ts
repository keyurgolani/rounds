import type { GuideNavGroup } from '../shared/GuideNav';

export const builderNavGroups: GuideNavGroup[] = [
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
      { slug: 'time-plan',     label: 'Time Plan' },
      { slug: 'submission',    label: 'Submission' },
      { slug: 'domain-cheats', label: 'Domain Cheats' },
    ],
  },
];
