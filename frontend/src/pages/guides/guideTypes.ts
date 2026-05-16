export type RoundPhase = {
  id: string;
  label: string;
  say: string;
  write: string;
};

export type PatternFamily =
  | 'linear'
  | 'search'
  | 'graph'
  | 'dp'
  | 'backtracking'
  | 'stack-heap';

export type CodeLanguage = 'python' | 'javascript' | 'java';

export type PatternEntry = {
  id: string;
  family: PatternFamily;
  title: string;
  trigger: string;
  state: string;
  watch: string;
  skeletons: Record<CodeLanguage, string>;
};

export type CheatsheetRow = {
  id: string;
  family: PatternFamily;
  trigger: string;
  state: string;
  move: string;
  watch: string;
};

export type CodeKitMethod = { name: string; purpose: string };

export type CodeKitShelf = {
  id: string;
  number: string; // '01', '02', …
  name: string;
  concepts: string[];
  methods: CodeKitMethod[];
  implementations: Record<CodeLanguage, string>;
};

export type ComplexityCell = {
  row: string;   // 'n≤1k'
  col: string;   // 'O(n²)'
  status: 'pass' | 'warn' | 'fail';
};

export type ConstraintTarget = {
  inputBand: string;       // 'n ≤ 100k'
  target: string;          // 'O(n log n) or O(n)'
  naturalPatterns: string[]; // ['heap', 'sort+sweep', 'hash map']
};

export type RadarPattern = {
  id: string;
  name: string;
  trigger: string;
  topicSlug: 'patterns' | 'code-kit' | 'complexity' | 'cheatsheet';
};

export type StateExample = {
  pattern: string;
  state: string;
};

export type CodingContent = {
  dashboard: {
    title: string;
    description: string;
    roundPhases: RoundPhase[];        // 8 entries
    patternRadar: RadarPattern[];     // 12 entries
    codeStylePact: string;
  };
  mentalModel: {
    thesis: string;
    stateExamples: StateExample[];    // 5 entries
    edgeCases: string[];              // 6 entries
  };
  cheatsheet: {
    preflight: string[];              // 7 chips
    complexityCeiling: string[];      // 4 short strings
    patternMatrix: CheatsheetRow[];   // 14 rows
  };
  codeKit: { shelves: CodeKitShelf[] }; // 10 shelves
  patterns: { entries: PatternEntry[] }; // 16 entries
  complexity: {
    compass: { rows: string[]; cols: string[]; cells: ComplexityCell[] };
    constraintTargets: ConstraintTarget[];
    proofLanguage: string[];
    costReference: { op: string; cost: string }[];
  };
};

// System Design ──────────────────────────────────────────────────────────────

export type ForceComponentLink = {
  force: 'users' | 'scale' | 'latency' | 'consistency' | 'reliability' | 'retention';
  component:
    | 'cache' | 'queue' | 'storage' | 'cdn' | 'search' | 'stream'
    | 'replication' | 'sharding' | 'multi-region' | 'consensus' | 'cold-storage';
};

export type DecisionMove = {
  id: string;
  trigger: string;
  move: string;
  watch: string;
  eyebrow?: string; // optional label rendered above the trigger by DecisionDeck
};

export type SDRoundPhase = {
  id: string;
  minutes: string; // '0–5'
  label: string;
  checklist: string[];
};

export type StorageRow = {
  kind: string;          // 'Relational'
  useWhen: string;
  primaryKeyShape: string;
  tradeOffNamed: string;
};

export type FailureMitigation = { failure: string; mitigation: string };

export type ReliabilityPattern = {
  id: string;
  pattern: string;
  handles: string;
  risk: string;
};

export type SystemDesignContent = {
  dashboard: {
    title: string;
    description: string;
    boardLayoutCaption: string;
    timeline: SDRoundPhase[];   // 6 entries
    pressureMenu: string[];     // 8 chips
    seniorPhrases: string[];    // 4 lines
  };
  mentalModel: {
    thesis: string;
    forceComponentLinks: ForceComponentLink[];
    earnItsSeatQuestions: string[]; // 4 questions
    pathBeforeInfraNote: string;
  };
  cheatsheet: {
    preflight: string[];        // 9 chips
    decisionDeck: DecisionMove[]; // 8 moves
    traps: string[];
  };
  roundFlow: {
    phases: SDRoundPhase[];     // 6 entries (same shape as dashboard.timeline)
    usefulPhrases: string[];    // 6 lines
  };
  capacityMath: {
    formulas: { label: string; formula: string }[]; // 7 entries
    interpretations: { threshold: string; implication: string }[];
    sloRows: { target: string; minutesPerMonth: string; designChoice: string }[];
  };
  buildingBlocks: {
    components: DecisionMove[]; // ~9 component decision blocks
    storage: StorageRow[];      // 7 rows
    keysIndexesNotes: string[];
    shardingNotes: string[];
  };
  reliability: {
    failureMenu: FailureMitigation[]; // 8 entries
    patterns: ReliabilityPattern[];   // 8 entries
    seniorFraming: string[];          // 6 lines
  };
};

// Behavioral ─────────────────────────────────────────────────────────────────

export type StarSegment = {
  id: 'situation' | 'task' | 'action' | 'result' | 'reflection';
  label: string;
  seconds: string; // '15s' or '60-90s'
  what: string;
};

export type SignalKey =
  | 'impact' | 'conflict' | 'failure' | 'ambiguity'
  | 'leadership' | 'mentorship' | 'pressure' | 'customer-focus';

export type SignalCard = {
  key: SignalKey;
  name: string;
  artifacts: string[];
  metrics: string[];
  stakeholders: string[];
  criteria: string[];
};

export type QuestionType = {
  id: string;
  trigger: string;
  signal: string;
  move: string;
  watch: string;
};

export type ScopeTier = {
  level: 'mid' | 'senior' | 'staff' | 'principal';
  label: string;
  examples: string[];
  numbers: string[];
};

export type WeakStrongPair = {
  weak: string;
  missing: string;
  strong: string;
};

export type BehavioralContent = {
  dashboard: {
    title: string;
    description: string;
    starStrip: StarSegment[]; // 5 segments
    signalGrid: { key: SignalKey; name: string }[]; // 8 chips
    evidencePact: string;
    amazonRule: { intro: string; principles: string[] };
  };
  mentalModel: {
    thesis: string;
    signalDecoder: { opener: string; signal: string; evidence: string }[]; // ~8 rows
    starAnatomy: StarSegment[];
    defendRiskyInterpretation: string[];
  };
  cheatsheet: {
    preflight: string[];
    starStrip: StarSegment[];
    questionDeck: QuestionType[]; // 8 entries
    redFlagFixes: string[];
  };
  storyBank: {
    signals: SignalCard[]; // 8 entries
    storyFormat: { field: string; example: string }[];
    reusableAngles: { angle: string; lead: string }[];
  };
  seniorScope: {
    ladder: ScopeTier[]; // 4 tiers
    answerFrame: string[]; // 6 elements
    defensiveFraming: { case: string; reframe: string }[];
  };
  repair: {
    rewrites: WeakStrongPair[]; // 6-10 pairs
    scorecardDimensions: { name: string; one: string; two: string; three: string }[]; // 5 dims
    mockDrillSteps: string[]; // 6 steps
  };
};

// Routing helper ─────────────────────────────────────────────────────────────

/** Slimmer config consumed by the new track packages. Does not include the
 *  legacy `fetch` / `loadingEyebrow` fields. */
export const TRACK_CONFIGS = {
  'system-design': {
    guidePath: '/system-design/guide',
    questionsPath: '/system-design/questions',
    eyebrow: 'System Design · Study Center',
  },
  coding: {
    guidePath: '/coding/guide',
    questionsPath: '/coding/questions',
    eyebrow: 'Coding · Study Center',
  },
  behavioral: {
    guidePath: '/behavioral/guide',
    questionsPath: '/behavioral/questions',
    eyebrow: 'Behavioral · Study Center',
  },
  'ai-coding': {
    guidePath: '/ai-coding/guide',
    questionsPath: '/ai-coding',
    eyebrow: 'AI Coding · Study Center',
  },
  builder: {
    guidePath: '/builder/guide',
    questionsPath: '/builder',
    eyebrow: 'Builder · Study Center',
  },
} as const;

export type GuideTrack = keyof typeof TRACK_CONFIGS;
export type TrackConfig = (typeof TRACK_CONFIGS)[keyof typeof TRACK_CONFIGS];

// AI Coding ──────────────────────────────────────────────────────────────────

export type AIFlavor =
  | 'audit' | 'drive' | 'debug-refactor' | 'prompt-spec' | 'mini-app';

export type AIPolicy = 'off' | 'candidate-choice' | 'on';

export type AIFlavorCard = {
  id: AIFlavor;
  label: string;
  tests: string;            // "what this round tests"
  dominantMove: string;
  trap: string;
};

export type PromptTemplate = {
  id: string;
  label: string;
  purpose: string;
  template: string;         // multi-line template literal
  whyEachPart: string;
};

export type AntiTemplate = {
  bad: string;
  why: string;
};

export type AIDefectExample = {
  id: string;
  defect: string;           // e.g. "phantom imports"
  snippet: string;          // 5-10 line code excerpt
  catch: string;            // how to spot it
};

export type AICompanyRow = {
  company: string;
  format: string;
  timeBudgetMin: string;    // e.g. "45-60"
  aiPolicyDefault: AIPolicy;
  leanInto: string;
};

export type AICodingContent = {
  dashboard: {
    title: string;
    description: string;
    flavorMatrix: AIFlavorCard[];          // 5 entries
    whatThisTests: string;
    companies: string[];                    // chip row
    timeBudget: string;                     // "45-60 min"
  };
  mentalModel: {
    thesis: string;
    trustVerifyStages: { stage: string; do: string }[]; // 3 stages
    verifyChecklist: string[];              // 4-5 items
    seniorSignal: string;
  };
  cheatsheet: {
    policyModes: { mode: AIPolicy; when: string; expectation: string }[]; // 3
    flavorDeck: { id: AIFlavor; trigger: string; move: string; watch: string }[]; // 5
    redFlags: string[];                     // 4-6 items
  };
  promptPlaybook: {
    anatomy: { id: string; label: string; what: string }[]; // 4 boxes
    templates: PromptTemplate[];            // 4-6 prompts
    antiTemplates: AntiTemplate[];          // 3-4 items
  };
  reviewHabits: {
    checklist: { dim: string; check: string }[]; // 5 dimensions
    defects: AIDefectExample[];             // 5-6 examples
    defenseScripts: string[];               // 4-5 lines
  };
  companies: AICompanyRow[];                 // 5-8 rows
};

// Builder (Real World Problems) ──────────────────────────────────────────────

export type BuilderFlavor =
  | 'services-apis' | 'data-etl' | 'concurrency-systems' | 'domain-modeled';

export type BuilderFlavorCard = {
  id: BuilderFlavor;
  label: string;
  tests: string;
  dominantMove: string;
  trap: string;
};

export type TimeBudgetPlan = {
  totalMinutes: number;     // 60 / 90 / 120 / 180
  phases: { id: string; minutes: string; label: string; do: string }[]; // 6 phases
  whatSlipsFirst: string;
};

export type DomainPrimer = {
  id: string;
  domain: string;
  model: string;            // 3-line domain model
  trap: string;             // the one trap that always shows up
};

export type BuilderContent = {
  dashboard: {
    title: string;
    description: string;
    flavorMatrix: BuilderFlavorCard[];      // 4 entries
    policyDistribution: { off: number; choice: number; on: number }; // 2 / 6 / 12
    timeTiers: string[];                    // ['30 min','45 min','60 min','90 min','120 min','180 min']
    submissionPact: string;
  };
  mentalModel: {
    thesis: string;
    triageTriangle: { corner: string; meaning: string }[]; // 3 corners
    shipMeans: string[];                    // 4 items
    whatToCut: string[];                    // 4 items
  };
  cheatsheet: {
    timeTiers: { tier: string; reasonable: string }[]; // 6 tiers
    flavorDeck: { id: BuilderFlavor; trigger: string; move: string; watch: string }[]; // 4
    aiPolicyMoves: { policy: 'off' | 'candidate-choice' | 'on'; behave: string }[]; // 3
  };
  timePlan: {
    plans: TimeBudgetPlan[];                 // 4 plans (60/90/120/180)
  };
  submission: {
    readmeTemplate: string;                  // multi-line template literal
    commitHygiene: string[];                 // 4 items
    reviewerFirstPass: string[];             // 5 items
  };
  domainCheats: {
    primers: DomainPrimer[];                 // 6-8 entries
  };
};
