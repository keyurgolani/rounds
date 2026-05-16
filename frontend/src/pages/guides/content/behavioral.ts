import type { BehavioralContent } from '../guideTypes';

// ─────────────────────────────────────────────────────────────────────────────
// Long literals declared FIRST to avoid temporal dead zone when referenced
// inside the behavioralContent export below.
// ─────────────────────────────────────────────────────────────────────────────

const STAR_STRIP: BehavioralContent['dashboard']['starStrip'] = [
  { id: 'situation',  label: 'Situation',  seconds: '15s',    what: 'Project, stakes, constraint — fast.' },
  { id: 'task',       label: 'Task',       seconds: '10s',    what: 'Your responsibility and success target.' },
  { id: 'action',     label: 'Action',     seconds: '60–90s', what: 'Decisions, trade-offs, communication, execution, repair.' },
  { id: 'result',     label: 'Result',     seconds: '15–25s', what: 'Quantified outcome + secondary effect.' },
  { id: 'reflection', label: 'Reflection', seconds: '10–20s', what: 'What changed in your operating system; where you reused it.' },
];

const SIGNAL_GRID: BehavioralContent['dashboard']['signalGrid'] = [
  { key: 'impact',          name: 'Impact' },
  { key: 'conflict',        name: 'Conflict' },
  { key: 'failure',         name: 'Failure' },
  { key: 'ambiguity',       name: 'Ambiguity' },
  { key: 'leadership',      name: 'Leadership' },
  { key: 'mentorship',      name: 'Mentorship' },
  { key: 'pressure',        name: 'Pressure' },
  { key: 'customer-focus',  name: 'Customer focus' },
];

export const behavioralContent: BehavioralContent = {
  dashboard: {
    title: 'Behavioral Interview Field Guide',
    description:
      'Study how to decode the signal, structure answers, surface evidence, and repair vague responses. Evidence beats adjectives.',
    starStrip: STAR_STRIP,
    signalGrid: SIGNAL_GRID,
    evidencePact:
      'Evidence beats adjectives. Show decisions, trade-offs, artifacts, and outcomes — not claims about traits.',
    amazonRule: {
      intro:
        'Amazon 2-5 rule: prepare two strong stories for each of the five most-tested leadership principles.',
      principles: [
        'Ownership',
        'Customer Obsession',
        'Bias for Action',
        'Earn Trust',
        'Deliver Results',
      ],
    },
  },

  mentalModel: {
    thesis: 'Evidence beats adjectives.',
    signalDecoder: [
      { opener: '"Tell me about yourself"',           signal: 'motivation + trajectory + role fit', evidence: 'present-past-future in 60 seconds' },
      { opener: '"Tell me about a disagreement"',     signal: 'empathy + judgment + influence',     evidence: 'both sides + decision criteria + outcome' },
      { opener: '"Tell me about a failure"',          signal: 'ownership + honesty + learning',     evidence: 'your bad assumption + repair work + later proof' },
      { opener: '"Tell me about an ambiguous problem"', signal: 'structure + autonomy + prioritization', evidence: 'narrowed options + named trade-off + alignment' },
      { opener: '"Tell me about a tight deadline"',   signal: 'prioritization + risk management',   evidence: 'what you cut and why + observable outcome' },
      { opener: '"Tell me about a time you led"',     signal: 'influence + standards + delegation', evidence: 'how others changed behavior because of you' },
      { opener: '"Tell me about feedback you got"',   signal: 'coachability',                        evidence: 'feedback → reaction → action → later proof' },
      { opener: '"Tell me about mentorship"',         signal: 'multiplied impact',                  evidence: "mentee's later behavior + your operating mechanism" },
    ],
    starAnatomy: STAR_STRIP,
    defendRiskyInterpretation: [
      'If you failed: state the other side fairly, then your decision criteria.',
      'If you disagreed: explain what was reasonable about the opposing position.',
      'If you escalated: explain what you tried first.',
      'If you said no: state the criteria you used and the alternative you offered.',
    ],
  },

  cheatsheet: {
    preflight: ['trait', 'context', 'action', 'judgment', 'outcome', 'learning'],
    starStrip: STAR_STRIP,
    questionDeck: [
      { id: 'about-yourself',     trigger: '"Tell me about yourself"',         signal: 'motivation, trajectory, fit',   move: 'present-past-future in 60s; lead with what you want next',                       watch: "don't recite resume" },
      { id: 'disagreement',       trigger: '"Tell me about a disagreement"',   signal: 'empathy + judgment + influence', move: 'state both sides + criteria + how the outcome or relationship changed',           watch: 'not just "we worked it out"' },
      { id: 'failure',            trigger: '"Tell me about a failure"',        signal: 'ownership + honesty',           move: 'own your part first; then repair work; then later proof behavior changed',       watch: "don't blame context" },
      { id: 'ambiguity',          trigger: '"Tell me about an ambiguous problem"', signal: 'structure + autonomy',      move: 'how you narrowed options + named trade-off + alignment mechanism',                watch: "didn't wait for clarity" },
      { id: 'deadline',           trigger: '"Tell me about a tight deadline"', signal: 'prioritization + risk',         move: 'what you cut + why + outcome + post-launch follow-up',                            watch: 'not heroic overtime' },
      { id: 'leadership',         trigger: '"Tell me about a time you led"',   signal: 'influence + standards',         move: 'how others changed behavior because of your influence or operating mechanism',    watch: 'not org-chart authority' },
      { id: 'feedback-received',  trigger: '"Tell me about feedback"',         signal: 'coachability',                  move: 'feedback → emotional reaction → action → later proof',                            watch: "not just 'I improved'" },
      { id: 'mentorship',         trigger: '"Tell me about mentoring someone"', signal: 'multiplied impact',            move: 'mentee\'s later behavior + how you scaled the mechanism',                          watch: "not just 'I taught X'" },
    ],
    redFlagFixes: [
      'replace blame with ownership',
      'replace vague "we" with clear "I"',
      'add numbers',
      'cut setup',
      'name the trade-off',
      'include reflection',
      'show follow-up behavior',
    ],
  },

  storyBank: {
    signals: [
      {
        key: 'impact',          name: 'Impact',
        artifacts: ['dashboard', 'A/B test result', 'launch RFC', 'PR list'],
        metrics: ['p95 latency', 'revenue', 'adoption %', 'incident count'],
        stakeholders: ['PM', 'design', 'data', 'leadership'],
        criteria: ['user-facing impact', 'business metric moved'],
      },
      {
        key: 'conflict',        name: 'Conflict',
        artifacts: ['decision log', 'RFC discussion', 'meeting summary'],
        metrics: ['decision speed', 'follow-on alignment'],
        stakeholders: ['cross-team peer', 'partner team lead'],
        criteria: ['both sides represented fairly', 'criteria-driven decision'],
      },
      {
        key: 'failure',         name: 'Failure',
        artifacts: ['post-mortem', 'retro notes', 'remediation plan'],
        metrics: ['blast radius', 'time to detect', 'time to recover'],
        stakeholders: ['oncall', 'manager', 'affected customer'],
        criteria: ['own your part first', 'prevention proof later'],
      },
      {
        key: 'ambiguity',       name: 'Ambiguity',
        artifacts: ['scoping doc', 'options memo', 'spike notes'],
        metrics: ['time to first decision', 'options narrowed'],
        stakeholders: ['unclear owner', 'leadership', 'partner teams'],
        criteria: ['structure created from nothing', 'trade-off named'],
      },
      {
        key: 'leadership',      name: 'Leadership',
        artifacts: ['working group charter', 'standards doc', 'review mechanism'],
        metrics: ['# people influenced', 'standard adopted by N teams'],
        stakeholders: ['peers outside reporting line', 'cross-org leaders'],
        criteria: ['behavior change in others', 'durable mechanism'],
      },
      {
        key: 'mentorship',      name: 'Mentorship',
        artifacts: ['1:1 notes', 'feedback memo', 'promotion case'],
        metrics: ["mentee's later level", "mentee's later impact"],
        stakeholders: ['direct mentee', "mentee's manager"],
        criteria: ['multiplier effect proven', 'reused mechanism'],
      },
      {
        key: 'pressure',        name: 'Pressure',
        artifacts: ['incident timeline', 'cut-list', 'rollback plan'],
        metrics: ['recovery time', 'reduction in repeat incidents'],
        stakeholders: ['oncall', 'customer support', 'leadership'],
        criteria: ['calm prioritization', 'communication cadence'],
      },
      {
        key: 'customer-focus',  name: 'Customer focus',
        artifacts: ['user interview notes', 'support escalation', 'feature spec'],
        metrics: ['CSAT', 'NPS', 'support volume drop'],
        stakeholders: ['support', 'sales', 'real customer'],
        criteria: ['customer pain named', 'measurable reduction'],
      },
    ],
    storyFormat: [
      { field: 'Title',       example: 'One-line memory hook (e.g., "Payments retry storm postmortem")' },
      { field: 'Signals',     example: 'ownership, failure, customer-focus' },
      { field: 'Numbers',     example: '$1.2M GMV at risk; 8 services; 3-week timeline; 14 incidents prevented later' },
      { field: 'Actions',     example: '3 verb-first bullets — what YOU decided, communicated, executed' },
      { field: 'Follow-ups',  example: 'Why this choice / what alternative / what you would change now' },
      { field: 'Weak spot',   example: 'Likely interviewer concern + how you would clarify' },
    ],
    reusableAngles: [
      { angle: 'Impact angle',     lead: 'lead with metric and why it mattered' },
      { angle: 'Conflict angle',   lead: 'lead with disagreement and how you built alignment' },
      { angle: 'Failure angle',    lead: 'lead with your bad assumption and the repair work' },
      { angle: 'Ambiguity angle',  lead: 'lead with missing context and how you created structure' },
      { angle: 'Leadership angle', lead: 'lead with how you influenced people outside your reporting line' },
      { angle: 'Growth angle',     lead: 'lead with feedback received and behavior changed' },
    ],
  },

  seniorScope: {
    ladder: [
      {
        level: 'mid',
        label: 'Mid-level',
        examples: ['Owned feature or service with clear requirements'],
        numbers: ['1 team', '1 service', 'tens of thousands of users'],
      },
      {
        level: 'senior',
        label: 'Senior',
        examples: ['Owned ambiguous project with cross-functional alignment, risk, rollout'],
        numbers: ['2–3 teams', 'hundreds of thousands of users', 'multi-quarter timeline'],
      },
      {
        level: 'staff',
        label: 'Staff',
        examples: ['Changed org direction or platform standard across multiple teams'],
        numbers: ['5+ teams', 'millions of users', 'org-wide operating model'],
      },
      {
        level: 'principal',
        label: 'Principal',
        examples: ['Created strategy across domains; influenced leadership decisions'],
        numbers: ['business-line scope', 'multi-org operating model', 'multi-year horizon'],
      },
    ],
    answerFrame: [
      'Open with outcome ("This reduced incidents by 38% across three teams.")',
      'Name the ambiguity (unclear owner / conflicting goals / missing data)',
      'Name decision criteria (reversibility / blast radius / cost / reliability)',
      'Show alignment mechanism (RFC / prototype / phased rollout)',
      'Show operating maturity (observability / rollback / runbook / post-launch review)',
      'End with lesson applied at larger scope',
    ],
    defensiveFraming: [
      { case: 'You escalated',         reframe: 'explain what you tried first and why escalation was the smaller risk' },
      { case: 'You disagreed',         reframe: "state the other side's valid concern before your position" },
      { case: 'You failed',            reframe: 'quantify impact, repair, prevention, and later proof' },
      { case: 'Project was assigned',  reframe: 'explain where you added judgment beyond the assignment' },
      { case: 'Results were mixed',    reframe: 'separate what worked, what did not, and what you changed' },
      { case: 'Many people helped',    reframe: 'say your exact role and credit the team for shared outcome' },
    ],
  },

  repair: {
    rewrites: [
      { weak: 'We improved performance.',
        missing: 'no actor, no metric, no mechanism',
        strong: 'I profiled p95 latency, found N+1 queries in the feed handler, added batching, and reduced p95 from 1.8s to 420ms.' },
      { weak: 'There was conflict on the team.',
        missing: 'no actor, no sides, no resolution mechanism',
        strong: 'PM wanted launch speed; infra wanted rollback safety. I proposed a staged rollout with a kill switch — PM got launch, infra got safety.' },
      { weak: 'I learned communication is important.',
        missing: 'generic lesson, no proof it changed behavior',
        strong: 'I now send written decision logs before cross-team reviews — reduced re-litigation in our last three projects.' },
      { weak: 'My manager asked me to lead the migration.',
        missing: 'no judgment, looks assigned not chosen',
        strong: 'After seeing repeated incidents from the old auth path, I proposed the migration plan, got buy-in from infra and security, and led the cutover.' },
      { weak: 'It was a hard project.',
        missing: 'no stakes, no constraint, no decision',
        strong: 'We had 6 weeks to ship a regulated feature with one engineer leaving. I cut scope to three of the eight requirements and shipped a v1 that met legal in time.' },
      { weak: 'I helped the team.',
        missing: 'no specific action, no measurable change',
        strong: 'I drafted the on-call runbook; alert acks dropped from 12 min to 3 min average across the next quarter.' },
    ],
    scorecardDimensions: [
      { name: 'Specificity', one: 'vague',                two: 'named actions',                    three: 'actions plus numbers/artifacts' },
      { name: 'Ownership',   one: 'mostly "we"',          two: 'some "I"',                          three: 'clear personal decisions + follow-through' },
      { name: 'Judgment',    one: 'no trade-off',         two: 'trade-off named',                   three: 'criteria + alternative explained' },
      { name: 'Impact',      one: 'no result',            two: 'qualitative result',                three: 'quantified result + secondary effect' },
      { name: 'Reflection',  one: 'generic lesson',       two: 'specific lesson',                   three: 'later behavior proof' },
    ],
    mockDrillSteps: [
      '5 min: choose one story and write only STAR(R) bullets',
      '5 min: answer once in 2 minutes; record it',
      '5 min: cut setup, add numbers/artifacts',
      '5 min: answer the same story as conflict / failure / leadership angle',
      '5 min: answer three follow-ups (why this choice, alternative, what changed later)',
      '5 min: score red flags + rewrite the opening sentence',
    ],
  },
};
