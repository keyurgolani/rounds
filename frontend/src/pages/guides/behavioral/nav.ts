import type { GuideNavGroup } from '../shared/GuideNav';

export const behavioralNavGroups: GuideNavGroup[] = [
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
      { slug: 'story-bank',   label: 'Story Bank' },
      { slug: 'senior-scope', label: 'Senior Scope' },
      { slug: 'repair',       label: 'Repair' },
    ],
  },
];
