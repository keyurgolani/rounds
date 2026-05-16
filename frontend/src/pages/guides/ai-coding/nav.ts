import type { GuideNavGroup } from '../shared/GuideNav';

export const aiCodingNavGroups: GuideNavGroup[] = [
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
      { slug: 'prompt-playbook', label: 'Prompt Playbook' },
      { slug: 'review-habits',   label: 'Review Habits' },
      { slug: 'companies',       label: 'Companies' },
    ],
  },
];
