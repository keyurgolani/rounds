import type {
  BuilderContent,
  BuilderFlavorCard,
  TimeBudgetPlan,
  DomainPrimer,
} from '../guideTypes';

// ─────────────────────────────────────────────────────────────────────────────
// Long literals declared FIRST to avoid temporal dead zone when referenced
// inside the builderContent export below.
// ─────────────────────────────────────────────────────────────────────────────

const FLAVOR_MATRIX: BuilderFlavorCard[] = [
  {
    id: 'services-apis',
    label: 'Services / APIs',
    tests: 'Production-shaped backend behavior — contract correctness, error paths, and startup story.',
    dominantMove:
      'Lock the wire contract first (input shape, output shape, error codes), build the happy path, then add 1-2 error paths.',
    trap:
      'Shipping the framework demo, not your problem solution — the interviewer asked for a rate limiter, not a fully wired Express app with middleware.',
  },
  {
    id: 'data-etl',
    label: 'Data / ETL',
    tests: 'Real-data resilience: messy CSV, multi-format JSON, nulls, duplicates, and encoding surprises.',
    dominantMove:
      'Round-trip a tiny synthetic file end-to-end first; once the pipeline runs clean on good data, add the messiness one case at a time.',
    trap:
      'Trusting the input schema you were given — the hidden tests send malformed rows, missing columns, and mixed types that the sample file omits.',
  },
  {
    id: 'concurrency-systems',
    label: 'Concurrency / Systems',
    tests: 'Correctness under contention — the primitive must hold its invariants when called concurrently.',
    dominantMove:
      'Draw the state machine first, then build the smallest primitive that survives concurrent calls without data loss or deadlock.',
    trap:
      'Swapping a lock for a queue and calling it solved — queues defer the contention problem, they do not eliminate it; the consumer still needs safe shared-state access.',
  },
  {
    id: 'domain-modeled',
    label: 'Domain-modeled',
    tests: 'Modeling the real-world entities and the relationships between them with enough fidelity that the core invariants hold.',
    dominantMove:
      'Name the entities, then the operations on those entities, then the invariants each operation must preserve — in that order.',
    trap:
      'Missing the one invariant the prompt is testing — domain problems always have a single load-bearing rule (discount order, timezone handling, float vs int money) that the rest of the problem depends on.',
  },
];

const TIME_PLANS: TimeBudgetPlan[] = [
  {
    totalMinutes: 60,
    phases: [
      {
        id: 'read-clarify',
        minutes: '0-5',
        label: 'Read & clarify',
        do: 'Read prompt twice. Restate the contract in your own words. Note 1 question you would ask if this were a real sprint — write it in the README as a stated assumption.',
      },
      {
        id: 'sketch',
        minutes: '5-10',
        label: 'Sketch',
        do: 'One paragraph: data flow, interface shape, where the complexity lives. No code yet.',
      },
      {
        id: 'build-happy',
        minutes: '10-35',
        label: 'Build happy path',
        do: 'End-to-end smallest working version. Skip every "what if" until the happy path passes a real invocation.',
      },
      {
        id: 'edge-cases',
        minutes: '35-45',
        label: 'Edge cases',
        do: 'Add the 1-2 edges the prompt named explicitly. Leave the rest out and note them in the README.',
      },
      {
        id: 'polish-readme',
        minutes: '45-55',
        label: 'Polish + README',
        do: 'Setup / Run / Test / Design / Trade-offs. 4-6 lines per section. No marketing, no apologies.',
      },
      {
        id: 'submit',
        minutes: '55-60',
        label: 'Submit',
        do: 'git log reads as a story. No "wip" commits. Push.',
      },
    ],
    whatSlipsFirst:
      'Edge-case coverage. At 60 min, name the cuts in the README rather than skip silently — a documented cut is a sign of judgment, not a sign of incompleteness.',
  },
  {
    totalMinutes: 90,
    phases: [
      {
        id: 'read-clarify',
        minutes: '0-5',
        label: 'Read & clarify',
        do: 'Read prompt twice. Restate the contract. Write 1-2 clarifying assumptions directly in the README before touching code.',
      },
      {
        id: 'sketch',
        minutes: '5-15',
        label: 'Sketch',
        do: 'Data flow diagram or a paragraph with entity names, operations, and invariants. Pick the data structure before writing a line.',
      },
      {
        id: 'build-happy',
        minutes: '15-45',
        label: 'Build happy path',
        do: 'End-to-end working version. Run it against a real input before moving on.',
      },
      {
        id: 'edge-cases',
        minutes: '45-65',
        label: 'Edge cases',
        do: 'Add every edge the prompt named. Add one you inferred from the domain. Note anything you skipped.',
      },
      {
        id: 'polish-readme',
        minutes: '65-80',
        label: 'Polish + README',
        do: 'Setup / Run / Test / Design / Trade-offs. Add a "What I would do next" section if time allows.',
      },
      {
        id: 'submit',
        minutes: '80-90',
        label: 'Submit',
        do: 'Squash any "wip" commits. Verify clean run from a fresh terminal. Push.',
      },
    ],
    whatSlipsFirst:
      'Polish. At 90 min, functional is graded; visual alignment, inline comments, and extra test assertions are not. Cut them and ship.',
  },
  {
    totalMinutes: 120,
    phases: [
      {
        id: 'read-clarify',
        minutes: '0-10',
        label: 'Read & clarify',
        do: 'Read prompt twice. Write a one-paragraph restatement of the contract with explicit assumptions. Flag any ambiguity you would resolve in a real sprint.',
      },
      {
        id: 'sketch',
        minutes: '10-20',
        label: 'Sketch',
        do: 'Data flow + entity model + the one design decision you want to explain in the README. Commit this as the first commit.',
      },
      {
        id: 'build-happy',
        minutes: '20-55',
        label: 'Build happy path',
        do: 'Working end-to-end version with a test. Commit when the happy path passes.',
      },
      {
        id: 'edge-cases',
        minutes: '55-80',
        label: 'Edge cases',
        do: 'All named edges plus 1-2 inferred. Each handled, each tested. Commit per logical chunk.',
      },
      {
        id: 'polish-readme',
        minutes: '80-110',
        label: 'Polish + README',
        do: 'Setup / Run / Test / Design / Trade-offs / What I would do next. One design decision should get a full paragraph explaining why this over the alternative.',
      },
      {
        id: 'submit',
        minutes: '110-120',
        label: 'Submit',
        do: 'Read the README as a stranger. Fix one thing. Verify clean run. Push.',
      },
    ],
    whatSlipsFirst:
      'Design-notes depth. At 120 min you have time for one careful explanation; spend it on the riskiest decision, not on the safe choices that justify themselves.',
  },
  {
    totalMinutes: 180,
    phases: [
      {
        id: 'read-clarify',
        minutes: '0-10',
        label: 'Read & clarify',
        do: 'Read prompt twice. Write a restatement with assumptions. Identify the one design question that changes the architecture.',
      },
      {
        id: 'sketch',
        minutes: '10-25',
        label: 'Sketch',
        do: 'Full entity model, operation list, invariants, and the two or three structural options. Pick one and say why in a commit message or the README.',
      },
      {
        id: 'build-happy',
        minutes: '25-70',
        label: 'Build happy path',
        do: 'Working implementation with a test suite covering the happy path. Commit per feature.',
      },
      {
        id: 'edge-cases',
        minutes: '70-110',
        label: 'Edge cases',
        do: 'All named and inferred edges. Observability hook (logging or error codes) where the problem domain warrants it.',
      },
      {
        id: 'polish-readme',
        minutes: '110-160',
        label: 'Polish + README',
        do: 'Production-shaped README: Setup / Run / Test / Design / Trade-offs / What I would do next. Include a deployable artifact (Dockerfile or start.sh) if time allows.',
      },
      {
        id: 'submit',
        minutes: '160-180',
        label: 'Submit',
        do: 'Read the full README and git log as if you are the reviewer. No wip commits. Tag the final commit if the problem requests a deliverable artifact.',
      },
    ],
    whatSlipsFirst:
      'Premature abstraction. At 180 min the temptation is to add one more interface or generic helper — resist it. The polish time is finite and reviewers grade the README and the commit story, not the abstraction count.',
  },
];

const DOMAIN_PRIMERS: DomainPrimer[] = [
  {
    id: 'shopping-cart-pricing',
    domain: 'Shopping cart pricing engine',
    model:
      'Cart → LineItem → PricingRule\nadd, remove, recompute total\nDiscount order: percent-off → flat-off → tax',
    trap:
      'Applying discounts in the wrong order — percent-off and flat-off interact differently depending on which runs first, and tax must always be last.',
  },
  {
    id: 'calendar-conflicts',
    domain: 'Calendar conflict checker',
    model:
      'Calendar → Event → TimeSlot\ninsert, delete, conflict-check\nOverlap: start < other.end AND end > other.start',
    trap:
      'Assuming all events live in the same timezone — a conflict check that ignores timezone offsets will pass all same-tz tests and silently fail on cross-tz inputs.',
  },
  {
    id: 'expense-splitter',
    domain: 'Expense splitter',
    model:
      'Group → Member → Expense → Share\nadd expense, compute balances, settle\nMoney in cents (int), never float',
    trap:
      'Using float for currency — 0.1 + 0.2 !== 0.3 in IEEE 754; store all amounts as integer cents and convert to display strings only at the presentation layer.',
  },
  {
    id: 'ticket-router',
    domain: 'Ticket routing system',
    model:
      'Ticket → Queue → Agent → Skill\nassign, escalate, re-queue\nRoute by: skill-match first, then capacity',
    trap:
      'Routing on label alone without checking agent capacity or skill match — a ticket routed to a full or wrong-skill queue is silently lost until the test measures queue depth.',
  },
  {
    id: 'rate-limiter',
    domain: 'Rate limiter',
    model:
      'Key → Window → Counter\ncheck(key), increment(key), reset on window expiry\nFixed-window vs sliding-window: pick one, name it',
    trap:
      'Separating check-and-increment into two non-atomic operations — under concurrent load, two requests can both pass the check before either increments, allowing a burst through the limit.',
  },
  {
    id: 'feature-flag-service',
    domain: 'Feature flag service',
    model:
      'Flag → Audience → Rule → Override\nevaluate(flag, context), override(flag, user)\nEvaluation order: override beats rule beats default',
    trap:
      'Evaluating rules before overrides — if a user-level override is processed after a segment rule, the override has no effect and the silent wrong value is returned without error.',
  },
  {
    id: 'idempotent-webhook',
    domain: 'Idempotent webhook receiver',
    model:
      'Request → IdempotencyKey → Result\nprocess(key, payload), replay(key)\nPersist result before returning; check key before processing',
    trap:
      'Persisting the result after completing the side effect — if the process crashes between the side effect and the persist, a replay sees no stored result and executes the side effect twice.',
  },
  {
    id: 'search-pagination-cursor',
    domain: 'Search pagination cursor',
    model:
      'Query → Cursor → Page → Result\nencode-cursor(last item), decode-cursor(token), next-page(cursor)\nCursor encodes position + sort key, not page number',
    trap:
      'Using a position-based (offset) cursor — if the underlying data is inserted or deleted between pages, offset cursors skip or duplicate rows; a stable sort-key cursor survives mutations.',
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// Primary export — references the const locals above
// ─────────────────────────────────────────────────────────────────────────────

export const builderContent: BuilderContent = {
  dashboard: {
    title: 'Builder (Real World Problems)',
    description:
      'How to attack a take-home or live real-world engineering problem — scope it right, ship it clean, and document what you cut.',
    flavorMatrix: FLAVOR_MATRIX,
    policyDistribution: { off: 2, choice: 6, on: 12 },
    timeTiers: ['30 min', '45 min', '60 min', '90 min', '120 min', '180 min'],
    submissionPact:
      'What you submit matters as much as what you build. A working, well-documented 80% solution beats an over-engineered 100% that nobody can run.',
  },

  mentalModel: {
    thesis: 'Ship small. Prove early. Document what you cut.',
    triageTriangle: [
      {
        corner: 'Scope',
        meaning:
          'Pull on scope — add requirements — and you must either accept lower quality or spend more time; something has to give.',
      },
      {
        corner: 'Quality',
        meaning:
          'Pull on quality — add tests, polish, abstractions — and you must either narrow scope or extend the time budget; there is no free lunch.',
      },
      {
        corner: 'Time',
        meaning:
          'Pull on time — compress the deadline — and you must either cut scope or accept rougher quality; what you ship is a subset, not a draft of the full thing.',
      },
    ],
    shipMeans: [
      'Clones and runs in under 2 minutes from a fresh terminal — no undocumented environment variables, no manual pre-steps.',
      'One happy-path test passes and proves the contract — the reviewer can confirm correct behavior without reading implementation.',
      'README answers setup / run / test / design / trade-offs — 80% of follow-up questions should be pre-empted.',
      'Commits read as a story, not a final diff dump — the reviewer can follow how the solution evolved.',
    ],
    whatToCut: [
      'Stretch goals the prompt did not ask for — scope creep hurts more than it helps when the core is not yet solid.',
      'Prettiness — alignment, colors, icons — reviewers grade correctness and clarity, not visual polish.',
      'Tests for paths the prompt did not name — name the untested paths in the README instead of spending time on them.',
      'Premature abstractions for a single caller — one concrete implementation is easier to read and extend than a generic interface with one implementor.',
    ],
  },

  cheatsheet: {
    timeTiers: [
      {
        tier: '30 min',
        reasonable:
          'Happy path only. One edge case. README is 4 lines: setup / run / test / design notes.',
      },
      {
        tier: '45 min',
        reasonable:
          'Happy path + 1-2 edge cases. README adds a trade-offs paragraph.',
      },
      {
        tier: '60 min',
        reasonable:
          'Happy path + edge cases + 1 stretch goal if the core is solid. README adds "what I would do next".',
      },
      {
        tier: '90 min',
        reasonable:
          'All of the above + 1 design polish: logging, retries, or a split into clean modules. README explains the key design decision.',
      },
      {
        tier: '120 min',
        reasonable:
          'Full happy + edges + observability story + thoughtful structure. README includes one full paragraph on the riskiest design decision.',
      },
      {
        tier: '180 min',
        reasonable:
          'Production-shaped: full README with design rationale, 1-2 careful abstractions that earn their complexity, and a deployable artifact (Dockerfile or start.sh).',
      },
    ],
    flavorDeck: [
      {
        id: 'services-apis',
        trigger: 'Small backend with an explicit input/output contract (HTTP, RPC, or function API).',
        move: 'Pick the framework you are fastest in. Define the wire contract as a typed interface or schema comment before writing a handler. Happy path first, then 1-2 error paths, then startup docs.',
        watch:
          'Over-architecting: middleware layers, dependency injection, and config files the prompt did not ask for. Also: missing the startup story — if it takes more than 2 minutes to clone and run, the reviewer will not debug it.',
      },
      {
        id: 'data-etl',
        trigger: 'Given a file or stream of real-ish data, normalize, transform, and report.',
        move: 'Create a tiny synthetic input file that covers the happy path. Write the pipeline end-to-end against that input first. Then feed in the malformed version and handle failures explicitly.',
        watch:
          'The provided sample file is always clean. The hidden tests send malformed rows, missing fields, mixed types, and encoding edge cases. Read the spec for the declared failure mode (skip / raise / fill-default) and implement it consistently.',
      },
      {
        id: 'concurrency-systems',
        trigger: 'Small concurrent primitive — cache, queue, pool, limiter — that must hold invariants under concurrent access.',
        move: 'Draw the state machine before writing code: what are the valid states, what transitions are allowed, what must never happen. Build the smallest primitive that passes a concurrent stress test.',
        watch:
          'Check-then-act races: reading state and then writing state in two separate steps without a lock or atomic operation. Also watch for deadlock if you hold two locks — always acquire in a consistent order.',
      },
      {
        id: 'domain-modeled',
        trigger: 'A slice of a real product — pricing, scheduling, splitting, routing — with explicit rules.',
        move: 'Name every entity. List every operation. Write every invariant as a comment or a test assertion. Then implement the operations in the order the invariants depend on them.',
        watch:
          'Missing the load-bearing rule: every domain problem has one constraint that everything else depends on. Find it in the prompt, write a test for it first, and make sure your model preserves it under every operation.',
      },
    ],
    aiPolicyMoves: [
      {
        policy: 'off',
        behave:
          'No AI for code generation. Say so in the README — one line is enough. Be precise: copy-paste from Stack Overflow or a web search is also AI-adjacent in spirit; when in doubt, ask the interviewer what counts.',
      },
      {
        policy: 'candidate-choice',
        behave:
          "Use AI deliberately and own the output. In the README, list the calls you made — 'wrote the CSV parser with AI assistance; reviewed and rewrote the retry loop by hand.' Reviewers want to see intent and judgment, not abstinence.",
      },
      {
        policy: 'on',
        behave:
          'Use AI freely, but verify every output before it ships. The README should make clear what was AI-generated versus what you reviewed and edited — this is what the interviewer is grading.',
      },
    ],
  },

  timePlan: {
    plans: TIME_PLANS,
  },

  submission: {
    readmeTemplate: `# <Project Name>

## Setup
\`\`\`
<install command, e.g. pip install -r requirements.txt or npm install>
\`\`\`
Environment variables (if any):
- \`<VAR_NAME>\`: <what it controls, and the default if omitted>

## Run
\`\`\`
<exact invocation command, e.g. python main.py --input data.csv>
\`\`\`

## Test
\`\`\`
<test command, e.g. pytest or npm test>
\`\`\`

## Design
<Paragraph 1: shape of the solution — entities, operations, data flow. One concrete sentence per entity.>

<Paragraph 2: the one design decision that mattered most — why this approach over the obvious alternative.>

## Trade-offs
- <Thing you chose>: <why this over the alternative — one sentence per bullet.>
- <Thing you cut>: <why it was the right cut given the time budget.>
- <Assumption you made>: <what you assumed and what would change if the assumption is wrong.>

## What I would do next
- <Item 1: the highest-leverage thing left undone.>
- <Item 2: the edge case you named but did not cover.>
- <Item 3: the observability or operational concern that matters in production.>`,

    commitHygiene: [
      'Small, focused commits — one logical change per commit so the reviewer can follow the build order without reading every diff.',
      "Present-tense imperative subject line: 'add cart validator' not 'added cart validator' or 'adding cart validator'.",
      'Body explains why-not-just-what — the diff shows what changed; the commit message should say why the change was the right move.',
      'No final "wip" or "cleanup" commit. Squash stash-commits before pushing — the story ends clean.',
    ],

    reviewerFirstPass: [
      'Does it clone and run in under 2 minutes from a fresh terminal with only the documented steps?',
      'Does the happy-path test pass on a clean checkout — without any undocumented setup?',
      'Does the README answer 80% of the questions I would ask in a follow-up call?',
      'Does the code read clearly — do names match what things actually do, and is the shape of the solution visible without deep tracing?',
      'Does the commit history tell a coherent story — can I see the build order and understand why each commit happened?',
    ],
  },

  domainCheats: {
    primers: DOMAIN_PRIMERS,
  },
};
