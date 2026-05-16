import type { GuideNavGroup } from '../shared/GuideNav';

export const codingNavGroups: GuideNavGroup[] = [
  {
    label: 'Frame',
    items: [
      { slug: '',             label: 'Dashboard' },
      { slug: 'mental-model', label: 'Mental Model' },
      { slug: 'cheatsheet',   label: 'Cheatsheet' },
      { slug: 'code-kit',     label: 'Code Kit' },
    ],
  },
  {
    label: 'Topics',
    items: [
      { slug: 'patterns',   label: 'Patterns' },
      { slug: 'complexity', label: 'Complexity' },
    ],
  },
];
