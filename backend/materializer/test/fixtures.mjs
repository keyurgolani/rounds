// Shared materializer fixtures (ROUNDS-00A-L04): the image's tests and the
// frontend's preview-parity test (frontend/test/materializerParity.test.tsx)
// render the same resumes.

// Every section and field a template can show, including text that looks
// like markup, which must render as text.
export const RICH = Object.freeze({
  personalInfo: {
    fullName: 'Ada Lovelace',
    email: 'ada@example.test',
    phone: '+44 20 0000 0000',
    location: 'London',
    website: 'https://example.test/ada',
    linkedin: 'linkedin.com/in/ada',
    github: 'github.com/ada',
    title: 'Analyst & Programmer',
    subtitle: 'Notes on the <Engine>',
    summary: 'First to publish an algorithm for a machine. "Quotes", \'apostrophes\', and <tags> stay text.',
  },
  experience: [
    {
      id: 'exp-1',
      company: 'Analytical Engine Co.',
      position: 'Programmer',
      location: 'London',
      startDate: '1842-01',
      current: true,
      description: 'Translated and annotated the Menabrea paper.',
      highlights: ['Wrote Note G, the Bernoulli program', 'Described loops & subroutines'],
    },
    {
      id: 'exp-2',
      company: 'Difference Engine Ltd',
      position: 'Correspondent',
      startDate: '1833-06',
      endDate: '1841-12',
      highlights: ['Reviewed designs'],
    },
  ],
  education: [
    {
      id: 'edu-1',
      institution: 'Private tutors',
      degree: 'Mathematics',
      field: 'Analysis',
      location: 'London',
      startDate: '1828-01',
      endDate: '1835-01',
      gpa: '4.0',
      description: 'Studied with Mary Somerville and Augustus De Morgan.',
    },
  ],
  skills: [
    { id: 'sk-1', category: 'Mathematics', items: ['Calculus', 'Bernoulli numbers'] },
    { id: 'sk-2', category: 'Machines', items: ['Punched cards'] },
  ],
  projects: [
    {
      id: 'pr-1',
      name: 'Bernoulli Program',
      description: 'The first published program.',
      technologies: ['Analytical Engine', 'Cards'],
      url: 'https://example.test/note-g',
      github: 'github.com/ada/note-g',
      startDate: '1842-07',
      endDate: '1843-09',
      highlights: ['Computed B7', 'Traced every variable'],
    },
  ],
  publications: [
    {
      id: 'pub-1',
      title: 'Sketch of the Analytical Engine',
      publisher: 'Taylor\'s Scientific Memoirs',
      releaseDate: '1843-09',
      url: 'https://example.test/sketch',
      summary: 'Translation with notes A to G.',
    },
  ],
  profiles: [
    { id: 'pf-1', network: 'GitHub', username: 'ada', url: 'https://example.test/gh/ada' },
    { id: 'pf-2', network: 'Mastodon', username: '@ada' },
  ],
});

// A text that appears only in each hideable section, to show it's gone.
export const SECTION_MARKERS = Object.freeze({
  experience: 'Analytical Engine Co.',
  education: 'Private tutors',
  skills: 'Bernoulli numbers',
  projects: 'Bernoulli Program',
  publications: 'Sketch of the Analytical Engine',
  profiles: 'Mastodon',
});

export const HIDDEN = Object.freeze({
  ...RICH,
  hiddenSections: ['experience', 'education', 'skills', 'projects', 'publications', 'profiles'],
});

// A design the Design tab writes: margin, body size, accent, and bullet.
export const DESIGN = Object.freeze({
  spacing: { margin: 12 },
  typography: { body: { size: 10.5 } },
  colors: { primary: '#2F5D4A' },
  bulletStyle: 'dash',
});
