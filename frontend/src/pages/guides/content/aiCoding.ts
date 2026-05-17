import type {
  AICodingContent,
  AIFlavorCard,
  AIDefectExample,
  AICompanyRow,
  PromptTemplate,
  AntiTemplate,
} from '../guideTypes';

// ─────────────────────────────────────────────────────────────────────────────
// Long literals declared FIRST to avoid temporal dead zone when referenced
// inside the aiCodingContent export below.
// ─────────────────────────────────────────────────────────────────────────────

const FLAVOR_MATRIX: AIFlavorCard[] = [
  {
    id: 'audit',
    label: 'Audit',
    tests:
      'Judgment on AI-written code that passes visible tests but diverges from prompt intent or hides a landmine.',
    dominantMove:
      'Re-read the prompt, then re-derive the data flow from scratch — do not anchor on the AI output.',
    trap:
      'Trusting that passing visible tests equals correctness; the hidden tests and edge cases are where the landmines live.',
  },
  {
    id: 'drive',
    label: 'Drive',
    tests:
      'Pairing rhythm and review quality while adding a feature under explicit constraints.',
    dominantMove:
      'Prompt → review → integrate in tight loops; never let the assistant outpace your ability to explain the delta.',
    trap:
      'Accepting a large generated diff without reading it line-by-line; the AI can silently break an existing invariant.',
  },
  {
    id: 'debug-refactor',
    label: 'Debug / Refactor',
    tests:
      'Speed of mental-model building in unfamiliar code with AI as a navigator, not a driver.',
    dominantMove:
      'Use the AI to produce a high-level summary of the codebase, then verify every hot path line-by-line yourself before applying any fix.',
    trap:
      "Accepting the AI's diagnosis without re-running the failing case; the AI summarizes what the code says, not what the spec requires.",
  },
  {
    id: 'prompt-spec',
    label: 'Prompt / Spec',
    tests:
      'Precision in specification — whether your prompt is unambiguous enough that a blind AI execution passes hidden tests.',
    dominantMove:
      'Structure every prompt as Goal + Constraints + Examples + Return shape; underspecified prompts produce plausible-looking wrong code.',
    trap:
      'Open-ended prompts like "fix this" or "implement X" with no constraints, no examples, and no expected return shape.',
  },
  {
    id: 'mini-app',
    label: 'Mini-app',
    tests:
      'Requirements-to-working-product flow: locking scope, scaffolding once, then iterating toward a shippable result.',
    dominantMove:
      'Lock requirements before touching a keyboard, scaffold the spine in one shot, then iterate on behaviors — never the other way around.',
    trap:
      'Letting features creep before the happy path works end-to-end; a partially-built app with three bonus features beats nothing.',
  },
];

const PROMPT_TEMPLATES: PromptTemplate[] = [
  {
    id: 'tpl-audit',
    label: 'Audit',
    purpose:
      'Systematically interrogate AI-written code for divergence from the original prompt.',
    template: `You are an expert code reviewer. I will give you a function and the original prompt that generated it.

Original prompt:
<original_prompt>

Generated code:
<generated_code>

Do the following:
1. Re-state what the prompt requires in your own words.
2. Trace through the data flow for the example input <example_input>.
3. List every assumption the code makes that the prompt does not explicitly state.
4. Identify any hallucinated APIs, imports, or function signatures.
5. Return a verdict: PASS, DIVERGES, or LANDMINE, with a one-sentence reason.`,
    whyEachPart:
      'Forcing the AI to re-state the prompt exposes drift before you read a single line of code. The explicit verdict prevents wishy-washy summaries.',
  },
  {
    id: 'tpl-debug',
    label: 'Debug',
    purpose:
      'Build a mental model of an unfamiliar codebase fast, then pin the exact failing path.',
    template: `You are a senior engineer helping me debug a failing test. Here is the context:

Failing test:
<failing_test_body>

Full stack trace:
<stack_trace>

Relevant source files (paste only files you suspect):
<file_1>
<file_2>

Do the following:
1. Summarize what each pasted file is responsible for in one sentence.
2. Identify the exact line where the failure originates, citing file and line number.
3. Explain why that line fails for the given input.
4. Propose a minimal fix (< 10 lines) and explain any risk it introduces.

Do NOT refactor anything outside the failing path.`,
    whyEachPart:
      'Bounding the AI to a minimal fix prevents scope creep. Asking for the exact line forces the AI to commit to a hypothesis rather than hedging.',
  },
  {
    id: 'tpl-spec',
    label: 'Spec / Prompt-Spec',
    purpose:
      'Write a prompt precise enough that a blind AI execution passes hidden tests.',
    template: `Implement the following function in <language>:

Function signature:
<signature>

Goal:
<one_sentence_goal>

Constraints:
- <constraint_1>
- <constraint_2>
- <constraint_3>

Examples:
Input:  <example_input_1>
Output: <expected_output_1>

Input:  <example_input_2>
Output: <expected_output_2>

Return shape:
<exact_return_type_or_schema>

Edge cases to handle explicitly:
- <edge_case_1>
- <edge_case_2>

Do not import any library not in the standard library. Do not add logging or print statements.`,
    whyEachPart:
      'Examples lock the happy path; explicit edge cases close the gap between what the prompt says and what the hidden tests check. The return shape constraint prevents the AI from inventing a different wire format.',
  },
  {
    id: 'tpl-refactor',
    label: 'Refactor',
    purpose:
      'Improve code structure without changing observable behavior, and verify the AI did not introduce regressions.',
    template: `Refactor the following function to improve <improvement_goal>.

Original function:
<function_body>

Constraints:
- The public API (function name, parameter types, return type) must not change.
- All existing tests in <test_file_path> must still pass.
- Do not add new dependencies.
- Keep the change to < <max_line_delta> lines of diff.

After the refactored code, add a section "What changed and why" with one bullet per meaningful change.`,
    whyEachPart:
      'improvement_goal names the improvement axis (e.g. readability, performance, testability). One axis at a time keeps the diff reviewable. The diff-size constraint forces a focused change. The "What changed and why" section gives you something concrete to verify and makes it easy to say out loud what you changed during the review.',
  },
  {
    id: 'tpl-miniapp',
    label: 'Mini-app',
    purpose:
      'Scaffold a self-contained working app from explicit requirements without scope creep.',
    template: `Build a <language> command-line app that satisfies these requirements:

Requirements (implement ALL of these, no more):
1. <requirement_1>
2. <requirement_2>
3. <requirement_3>

Inputs: <how the user provides input>
Outputs: <exact format of output, e.g. one JSON object per line>

Constraints:
- Single file, no external dependencies beyond the standard library.
- Runnable as: <exact invocation command>
- On invalid input, print a one-line error to stderr and exit with code 1.

Do NOT add features beyond the numbered requirements. Implement a minimal working version first, then stop.`,
    whyEachPart:
      'Explicit requirements list prevents the AI from inventing bonus features. The invocation command forces a concrete run target you can test immediately.',
  },
];

const ANTI_TEMPLATES: AntiTemplate[] = [
  {
    bad: 'Fix this.',
    why:
      'No goal, no constraints, no return shape — the AI will pick the most plausible interpretation, which may not match the spec or the hidden tests.',
  },
  {
    bad: 'Rewrite this to be cleaner.',
    why:
      'Without a diff-size bound or API stability constraint, the AI will rename everything and change the return type, silently breaking callers.',
  },
  {
    bad: 'Write tests for this function.',
    why:
      "Without a target behavior description and explicit edge cases, the AI writes tests that pass its own generated code, not tests that catch the AI's own errors.",
  },
  {
    bad: 'Debug the error.',
    why:
      'No stack trace, no failing test, no relevant file — the AI will generate a plausible-sounding hypothesis that has a 50% chance of being wrong.',
  },
];

const DEFECTS: AIDefectExample[] = [
  {
    id: 'defect-phantom-import',
    defect: 'Phantom import',
    snippet: `# AI-generated code
from collections import OrderedCounter  # does not exist

def count_by_order(items):
    c = OrderedCounter(items)
    return list(c.items())`,
    catch:
      "Run the file before reviewing logic. Phantom imports raise ImportError immediately and are easy to miss in a code review if you're skimming.",
  },
  {
    id: 'defect-silent-fallback',
    defect: 'Silent fallback hiding the real failure',
    snippet: `async function fetchConfig(id: string): Promise<Config> {
  try {
    const res = await api.get(\`/config/\${id}\`);
    return res.data;
  } catch {
    // AI added this silently
    return DEFAULT_CONFIG;
  }
}`,
    catch:
      "The try/catch swallows every error including network failures and 404s, returning DEFAULT_CONFIG without any signal. The caller never knows the fetch failed. Look for bare catch blocks with a return inside — they're the AI's favorite way to make tests pass.",
  },
  {
    id: 'defect-off-by-one-slice',
    defect: 'Off-by-one in slice bounds',
    snippet: `def sliding_max(nums: list[int], k: int) -> list[int]:
    result = []
    for i in range(len(nums) - k):  # should be range(len(nums) - k + 1)
        window = nums[i:i + k]
        result.append(max(window))
    return result

# sliding_max([1,3,2,5], 2) => [3,3] but last window [2,5] is missing`,
    catch:
      'Trace through the boundary: when i = len(nums) - k, the window is nums[-k:] which is valid. The loop must include that index. Always verify the last iteration explicitly.',
  },
  {
    id: 'defect-async-double-await',
    defect: 'Race from async double-await',
    snippet: `async function transferFunds(from: string, to: string, amount: number) {
  const balance = await getBalance(from);
  // another request can modify balance between these two awaits
  if (balance >= amount) {
    await debit(from, amount);
    await credit(to, amount);
  }
}`,
    catch:
      'The balance check and debit are not atomic. A concurrent transfer can observe the same balance and both proceed. Look for check-then-act patterns separated by an await — they are almost always a race without a distributed lock or a conditional database update.',
  },
  {
    id: 'defect-spec-drift',
    defect: 'Drift from spec',
    snippet: `# Prompt said: return the top-3 items by score, descending
# AI returned:
def top_items(items):
    return sorted(items, key=lambda x: x['score'])[:3]
    # sorted() is ascending by default — returns the LOWEST 3 scores`,
    catch:
      'Sort direction is the single most common spec-drift defect. Always check: ascending vs descending, and whether the slice [:k] takes the first or last k elements after sorting.',
  },
  {
    id: 'defect-cycle-no-guard',
    defect: 'Unbounded traversal on cyclic input',
    snippet: `def length(head):
    count = 0
    node = head
    while node:           # AI assumed acyclic; on a cycle this never exits
        count += 1
        node = node.next
    return count`,
    catch:
      "Run it on an input with a cycle (or anything you didn't construct yourself). If the function uses `while node` with no visited-set or step-count cap, assume the AI ignored the cycle possibility.",
  },
];

// Per-company rounds grounded in public research as of May 2026. Each row
// captures format, the AI-tool policy default we could verify, what's
// graded, and the actionable lean-into. Sources surface in the page so
// candidates can audit claims before the round. Formats shift fast —
// the "Verify with the recruiter" section in Companies.tsx is the
// canonical reminder.
const COMPANY_ROWS: AICompanyRow[] = [
  // ───────── AI labs (where AI-coding rounds are most documented) ─────────
  {
    company: 'Anthropic',
    format:
      'Two-stage technical loop: 90-min take-home or live screen on CoderPad / Colab / Replit (often a build-from-scratch system like an in-memory DB with TTL or a thread-safe LRU), then a 4-hour onsite with 4 rounds including pair-programming, system design, and safety-flavored behavioral.',
    timeBudgetMin: '90 screen / 45–60 onsite',
    aiPolicyDefault: 'off',
    tools:
      "Anthropic's candidate guidance explicitly says 'no AI assistance unless we indicate otherwise' for live and take-home coding. Google + Stack Overflow are fine. Anthropic reversed its blanket May-2025 AI hiring ban in July 2025 but live coding remains AI-off by default.",
    rubric:
      'Engineering judgment over cleverness. Problem decomposition, correctness, edge cases, code clarity, ability to iterate as the interviewer escalates requirements (the multi-level problem format), concurrency and mutation reasoning.',
    leanInto:
      'Narrate first-principles reasoning aloud; start with the simplest correct solution then layer complexity as the interviewer adds requirements. Write modular code from the first line because levels 3–4 will demand refactors. Surface edge cases and concurrency hazards before being asked. Tie behavioral answers to safety-first decision-making — it is a real signal.',
    followUps:
      '"What happens if two threads call this simultaneously?" "Now add a TTL / persistence / compression layer — refactor what you have."',
    sources: [
      "Anthropic's official candidate AI guidance — https://www.anthropic.com/candidate-ai-guidance",
      "Anqi Silvia, 'My 2025 Anthropic Software Engineer Interview Experience' (Medium) — https://medium.com/@anqi.silvia/my-2025-anthropic-software-engineer-interview-experience-9fc15cd81a99",
      "TechCrunch, 'Anthropic has to keep revising its technical interview test' (Jan 2026) — https://techcrunch.com/2026/01/22/anthropic-has-to-keep-revising-its-technical-interview-test-so-you-cant-cheat-on-it-with-claude/",
      'interviewing.io Anthropic guide — https://interviewing.io/anthropic-interview-questions',
    ],
  },
  {
    company: 'OpenAI',
    format:
      'Single 60-min live coding in CoderPad (sometimes HackerRank) — typically one long multi-part problem (time-indexed data, stateful iterators, rate limiter, O(1) cache, small OOP design). Code must run and pass tests in-session. Full loop is 4–6 hours back-to-back across 1–2 days mixing coding, ML coding (optional), system design in Excalidraw, and behavioral.',
    timeBudgetMin: '60',
    aiPolicyDefault: 'off',
    tools:
      'No published OpenAI policy permitting AI in live coding. 2025 candidate writeups consistently describe pure CoderPad / HackerRank sessions with an interviewer watching — confirm with recruiter.',
    rubric:
      'Production-grade code, not algorithmic trickery. Correctness, edge cases, structure, ability to extend an existing snippet as the interviewer escalates. The bar is famously unforgiving — strong reports of 3/4 coding being below pass.',
    leanInto:
      'Clarify the prompt for a full minute before typing — problems are deliberately under-specified. Build incrementally so you have a passing solution at every checkpoint; interviewers add follow-ups mid-solution and want extensions, not rewrites. Write tests as you go and run them. Think aloud about edge cases even when not asked.',
    followUps:
      '"Now make it handle out-of-order events." "Extend this to support multiple consumers / TTL / cancellation."',
    sources: [
      'OpenAI official interview guide — https://openai.com/interview-guide/',
      "Anqi Silvia, 'My 8 Coding Questions from the 2025 OpenAI Interview' (Medium) — https://medium.com/@anqi.silvia/my-8-coding-questions-from-the-2025-openai-interview-d0df24773d33",
      'Hello Interview, OpenAI Coding Interviews 2025 — https://www.hellointerview.com/blog/openai-coding-questions',
    ],
  },
  {
    company: 'Google / DeepMind',
    format:
      'Google product SWE — traditional 4–5 rounds, ~45 min each, LeetCode medium-to-hard, plus behavioral and (senior) system design. NEW H2 2026 pilot: a code-comprehension round with Gemini provided as an AI assistant (US junior/mid SWE first). DeepMind research-engineer loops emphasise ML coding (debug a training pipeline, design end-to-end training) plus system design and research-fit.',
    timeBudgetMin: '45',
    aiPolicyDefault: 'candidate-choice',
    tools:
      'Gemini provided only in the H2 2026 code-comprehension pilot round; all other rounds remain AI-off. The pilot is small and US-only as of May 2026 — most candidates still face the classic AI-off loop.',
    rubric:
      'Pilot round: AI fluency — prompt engineering, output validation, debugging. Google calls out "human-led, AI-assisted." Non-pilot rounds: classic Google rubric (correctness, complexity analysis, communication). DeepMind layers ML depth and research-taste signals.',
    leanInto:
      'Practice with Gemini specifically before the pilot round, not Claude / ChatGPT. Show a visible loop: hypothesise → write a targeted prompt → validate (run it, read it, challenge it) → iterate. Narrate prompt choices. Never paste-and-accept. For non-pilot rounds treat as classic algorithms-and-clean-code. For DeepMind, be ready to debug a broken training loop or reason about a paper.',
    followUps:
      '"Why did you trust that Gemini output? How would you verify?" "What is the failure mode if this codebase scales 10x?"',
    sources: [
      "Exponent, 'Google's AI-Assisted Coding Interview (2026 Guide)' — https://www.tryexponent.com/blog/google-ai-coding-interview",
      "Entrepreneur, 'Google Is Testing a Transformative New Interview Rule' (2026) — https://www.entrepreneur.com/business-news/google-is-testing-a-new-rule-transform-job-interviews",
      'Shopifreaks, Google pilots AI-assisted SWE interview (2026) — https://www.shopifreaks.com/google-pilots-new-software-engineering-interview-process-that-lets-candidates-use-ai-assistant-gemini-during-coding-rounds/',
      'Andrey Zharkov, ML / Research Engineer interviews 2025 — https://asmekal.github.io/blog/posts/interviews-2025-ml-research-engineer-uk',
    ],
  },
  {
    company: 'Meta',
    format:
      'One 60-min AI-Enabled Coding round in a specialised CoderPad with a built-in AI chat panel; multi-file project (file tree, terminal, unit-test runner) where you build, extend, or debug — not two short algorithm problems. E5 onsite = AI-enabled coding + traditional coding + system design + behavioral; E6+ leans more on the AI-enabled round.',
    timeBudgetMin: '60',
    aiPolicyDefault: 'candidate-choice',
    tools:
      'Model dropdown inside CoderPad: GPT-4o mini, GPT-5, Claude Sonnet 4 / 4.5, Claude Haiku, Claude Opus 4, Gemini 2.5 Pro, Llama 4 Maverick. Languages: Java, C++, C#, Python, Kotlin, TypeScript. No external IDEs.',
    rubric:
      'Four competencies (Problem Solving, Code Quality, Verification, Communication) reinterpreted for AI: independent reasoning before delegating, prompt granularity, continuous review and testing of AI output, narration. Meta frames it as "partnership with AI, not replacement by AI."',
    leanInto:
      'State your plan and acceptance criteria before touching the AI. Navigate the multi-file codebase yourself for a minute or two so you can speak to it. Use small scoped prompts (one function, one bug) rather than dumping the whole problem. Read every AI suggestion aloud and call out what you are changing or rejecting. Run the provided unit tests early and often. Treat the AI like a junior pair, not an oracle.',
    followUps:
      '"Why did you pick that model / change models?" "Walk me through this block the AI wrote — what would you change before shipping?"',
    sources: [
      'Hello Interview, Meta AI-Enabled Coding guide (2026) — https://www.hellointerview.com/blog/meta-ai-enabled-coding',
      "interviewing.io, How to use AI in Meta's AI-assisted coding interview — https://interviewing.io/blog/how-to-use-ai-in-meta-s-ai-assisted-coding-interview-with-real-prompts-and-examples",
      'Hello Interview, Meta E5 Guide 2026 — https://www.hellointerview.com/guides/meta/e5',
      'Design Gurus / dglearning Substack, Inside the Meta 2026 Loop — https://dglearning.substack.com/p/inside-the-meta-2026-loop-rounds',
    ],
  },

  // ───────── Big tech ─────────
  {
    company: 'Microsoft / GitHub',
    format:
      'Microsoft proper — 3–4 rounds of 45–60 min on CoderPad / HackerRank, LeetCode easy-to-medium (mid+: 2 medium + 2 hard), one system design at mid/senior, one behavioral. GitHub — async take-home delivered through "Interview-bot" submitted via PR, followed by 3 onsite rounds in one day (2 technical + 1 behavioral). GitHub Copilot product team reportedly closer to the GitHub model than Microsoft proper.',
    timeBudgetMin: '45–60',
    aiPolicyDefault: 'off',
    tools:
      'Microsoft — no AI in live rounds; candidates report "the team wanted people who could explain their code, not just prompt a model." GitHub take-home — submitted via PR with full editor / internet access; whether Copilot specifically is allowed is undocumented — confirm with recruiter.',
    rubric:
      'Microsoft — correctness, communication, fundamentals (DS & A, OS / multithreading), ability to defend decisions without blaming tools. GitHub — production-leaning: automated tests against the PR plus interviewer scoring (clean commit hygiene, idiomatic code, documentation, test coverage).',
    leanInto:
      'Microsoft — solid LC-medium fluency (target 100–150 problems), narrate trade-offs, brush up multithreading and concurrency (often-flagged unexpected topic), never excuse a bug with "the tool generated that." GitHub — treat the take-home like a real PR: clean commits, README with setup / run / test, real tests, thoughtful error handling, open-source-style polish.',
    followUps:
      'Microsoft: "How would this behave under contention?" GitHub: "Walk me through your PR — what would you change with another day?"',
    sources: [
      "GitHub Engineering Blog, 'How GitHub does take-home technical interviews' — https://github.blog/developer-skills/career-growth/how-github-does-take-home-technical-interviews/",
      'IGotAnOffer, Microsoft software engineer interview — https://igotanoffer.com/blogs/tech/microsoft-software-development-engineer-interview',
      'Interview Query, GitHub SWE guide — https://www.interviewquery.com/interview-guides/github-software-engineer',
    ],
  },
  {
    company: 'Amazon',
    format:
      'Standard onsite loop of 4–5 rounds (typically 2 coding, 1 system design at SDE II+, 1 bar-raiser behavioral, 1 hiring manager). Each technical round is a hybrid — ~15–20 min Leadership Principles, then a coding problem in a shared editor. No dedicated AI-assisted round. AWS Bar Raiser leans harder on Ownership and Deliver Results; AWS skews to depth on the candidate\'s past systems.',
    timeBudgetMin: '45–60',
    aiPolicyDefault: 'off',
    tools:
      'No AI. Amazon has publicly stated candidates may not use AI tools (including "interview teleprompter" assistants) and disqualifies candidates caught using them. Internally engineers use Amazon Q Developer; not available to candidates.',
    rubric:
      'Roughly 50/50 between code (correctness, clarity, complexity, edge cases, runnable / debug-able) and the 16 Leadership Principles. Bar Raiser can veto on LP signal alone. STAR-formatted stories expected; interviewers ask LP follow-ups mid-coding.',
    leanInto:
      'Have 12–15 STAR stories pre-mapped to Customer Obsession, Ownership, Bias for Action, Dive Deep, Are Right A Lot, Deliver Results, Earn Trust. Narrate trade-offs in LP language ("for Customer Obsession I would favor the slower but more accurate path"). Write working runnable code (not pseudocode). Proactively state edge cases and test them. Do NOT mention or use AI tooling.',
    followUps:
      '"Walk me through a time you disagreed with your tech lead on an implementation — what did you do?" "How would this code change if traffic 100x\'d?"',
    sources: [
      "IT Pro, 'Amazon bans AI tools during job interviews' (2024–2025) — https://www.itpro.com/business/careers-and-training/amazon-bans-ai-tools-during-job-interviews",
      'IGotAnOffer, Amazon SDE interview process — https://igotanoffer.com/blogs/tech/amazon-interview-process',
      'AWS Careers, How We Hire — https://aws.amazon.com/careers/how-we-hire/',
    ],
  },
  {
    company: 'Apple',
    format:
      '5–6 rounds (mostly virtual in 2026): 1–2 algorithmic coding, 1 system design (ICT4+), 1 team-specific deep dive (iOS / Swift, kernel, ML internals), 1 behavioral / values. Coding is whiteboard-style in a plain shared editor — often Apple\'s internal collaborative editor — with limited or no code execution. Some teams use take-home for specialised roles.',
    timeBudgetMin: '45–60',
    aiPolicyDefault: 'off',
    tools:
      'No AI. Apple explicitly prohibits AI tools (ChatGPT, Copilot, Cursor, "interview copilots") in live coding, online assessments, and take-homes; violations are disqualifying per multiple candidate writeups.',
    rubric:
      'Correctness and code quality under pressure. System design weighted toward privacy, on-device constraints, energy, and hardware / locality reasoning (cloud-first answers are penalised for relevant teams). Behavioral: ownership, user empathy, quality bar, cross-functional collaboration with design / hardware. Famously opaque — final decision committee-driven.',
    leanInto:
      'Show first-principles reasoning aloud — derive complexity before coding, name invariants, justify data structures from constraints. For system design, lead with privacy and on-device trade-offs ("can this stay on device?", "what is the energy cost?"). In behavioral, anchor stories to user impact and the bar you held. Do NOT reference AI tools in a way that suggests reliance.',
    followUps:
      '"How would your design change if this had to run on-device with no network?" "Tell me about a time you held the line on quality when the team wanted to ship."',
    sources: [
      'Exponent, Apple Software Engineer Interview Guide 2026 — https://www.tryexponent.com/guides/apple-software-engineer-interview',
      'InterviewQuery, Apple SWE Interview Guide 2026 — https://www.interviewquery.com/interview-guides/apple-software-engineer',
      'InterviewPilot, Apple SWE Experience ICT3 / ICT4 2025–2026 — https://interviewpilot.dev/interview-experiences/apple',
    ],
  },

  // ───────── AI-dev-tool startups ─────────
  {
    company: 'Cursor',
    format:
      'Recruiter / manager screen (45 min, informal); 1–3 technical phone screens (60 min each) on the Cursor codebase plus algorithm and applied AI-editor problems; final stage is an in-person 1–2 day project (8 hrs / day) building something real with the team, with kickoff, midday check-in, and demo / presentation.',
    timeBudgetMin: '45 screen / 60 per technical / 8 hrs per onsite day',
    aiPolicyDefault: 'candidate-choice',
    tools:
      'Mixed. CEO Michael Truell publicly states first technical screens are run WITHOUT AI beyond autocomplete (a fair-evaluation filter for raw skill). Later rounds permit ChatGPT, Google, and Cursor itself for targeted queries — not for offloading larger tasks. Onsite gives access to internal docs and a Slack channel.',
    rubric:
      'Raw programming skill and reasoning (early), then product sense, taste, autonomy, system design, collaboration in ambiguity, and depth of engagement with Cursor\'s DX philosophy. AI-on rounds explicitly grade judgment: "Why did you accept that suggestion?"',
    leanInto:
      'Be fluent without AI for the first screen — algorithms and codebase-navigation skills still matter. Show real Cursor usage history and opinions on its DX; vague familiarity gets flagged. In AI-on rounds, narrate every accept / reject out loud — judgment is the signal, not throughput. For the 2-day onsite, ask in Slack, ship something demoable, and pitch a feature you would actually want in Cursor.',
    followUps:
      '"Why did you accept that code?" "What is the benefit of your approach over what Cursor suggested?" "What feature would you build into Cursor and why?"',
    sources: [
      "Inside Cursor's hiring strategy (CEO Michael Truell quotes) — https://dnyuz.com/2025/06/12/inside-cursors-hiring-strategy-no-ai-in-interviews-and-a-2-day-project-with-the-team/",
      'Exponent Cursor SWE Interview Guide — https://www.tryexponent.com/guides/cursor-software-engineer-interview',
      "Brian Jenney, 'The CTO Told Me to Leave Cursor On. The Interview Got Harder.' — https://brianjenney.medium.com/the-cto-told-me-to-leave-cursor-on-the-interview-got-harder-22524a0bbd28",
    ],
  },
  {
    company: 'Replit',
    format:
      "Replit's own four official stages: recruiter chat, hiring-manager interview, technical (live or take-home — varies by role), and panel interview. Candidate reports describe a short (~30 min) take-home inside Replit, a 1-hour live coding session in Replit multiplayer, then a virtual onsite mini-project day with a morning scoping call and afternoon demo, plus a founder culture-fit call.",
    timeBudgetMin: '30 take-home / 60 live screen / full day onsite project',
    aiPolicyDefault: 'candidate-choice',
    tools:
      'Replit itself throughout (take-home, live, onsite project) — the platform\'s multiplayer + live execution is leveraged. No explicit statement that Replit Agent is required or forbidden in interviews — confirm with recruiter.',
    rubric:
      'Practical engineering on running code (fetch an API, parse, render, debug under pressure), collaboration ("treat the Slack channel like teammates"), product opinions on Replit itself, ability to scope and demo a project end-to-end in a day, navigating ambiguity. Explicitly anti-LeetCode-trivia.',
    leanInto:
      'Build something on Replit before applying — they explicitly tell rejected candidates to do this, and a point of view on the product is graded. During the onsite day, over-communicate in the Slack channel (status updates, design decisions, blockers) — the channel is part of the evaluation, not a help desk. Make sure your code actually runs and you can debug live without panicking. Bring a sharp opinion on how to make Replit / Replit Agent better.',
    followUps:
      '"What would you change about Replit?" "How would you design this feature for our users?"',
    sources: [
      'Replit official Interview Process — https://replit.com/interview-process',
      'Replit blog, What We Look for When We Interview — https://blog.replit.com/get-hired',
      'Taro candidate writeup, Jan 2025 — https://www.jointaro.com/interviews/companies/replit/experiences/software-engineer-san-francisco-california-january-1-2025-no-offer-positive-6ce50a63/',
    ],
  },
  {
    company: 'Lovable',
    format:
      'Application form, exploratory recruiter intro call, then either a "show something you have built" walkthrough OR a 1–2 day remote-or-onsite workshop with the team (track-dependent). Candidate-reported flow includes a short live coding for baseline fluency and follow-on technical interviews (system design, troubleshooting) before the workshop.',
    timeBudgetMin: '30–45 intro / short live / 1–2 day workshop',
    aiPolicyDefault: 'candidate-choice',
    tools:
      "No public statement on AI policy. Given Anton Osika's 'bias to build / ship fast' framing, AI tooling (potentially including Lovable itself) is plausibly expected in the workshop, but this is not documented — confirm with recruiter.",
    rubric:
      "Anton Osika's stated four traits: slope (learning speed), breadth (generalist over specialist), curiosity, bias to build / ship. Workshop evaluates ownership, velocity, prototyping speed, translating ambiguous user pain into tickets, and customer-facing communication. 'Founder-type people who get stuff done' is the explicit bar.",
    leanInto:
      'Bring a portfolio of shipped side projects — "show something you have built" is a literal interview stage. Demonstrate range (design + code + product thinking), not just deep specialty. In the workshop, ship a working prototype fast and iterate visibly — speed and end-to-end ownership are the signal. Show you can translate fuzzy user pain into crisp tickets; engineers there are customer-facing.',
    followUps:
      '"Tell me about a time you built something from scratch with almost no documentation." "What have you shipped recently and what did you learn from real users?"',
    sources: [
      'Lovable Careers page — https://lovable.dev/careers',
      'Anton Osika, 4 hiring traits (Business Insider via AOL) — https://www.aol.com/lovables-ceo-tells-us-hes-031236469.html',
      "Lenny's Podcast, Building Lovable with Anton Osika — https://podpulse.ai/podcast-notes-and-takeaways/lennys-podcast-product-growth-career-building-lovable-10m-arr-in-60-days-with-15-people-anton-osika-ceo-and-co-founder",
    ],
  },
  {
    company: 'Vercel',
    format:
      'Recruiter phone screen; hiring-manager interview (role-dependent coding); a Collaboration Stage drawing from Deep Dive, System Design, Data Structures & Algorithms, and Fullstack Coding Challenge components; optional Leadership interview. The Fullstack Coding Challenge is screen-shared live; some role variants run 3–5 hrs as a take-home where you build a small web app on your own machine.',
    timeBudgetMin: '60 live / 3–5 hrs fullstack variant',
    aiPolicyDefault: 'off',
    tools:
      "Vercel's published prep guide explicitly states 'AI tools are not permitted during the interview' for the Fullstack Coding Challenge. v0 is positioned as a preparation resource, not as a required interview tool. For other rounds, AI policy is not officially stated — confirm with recruiter.",
    rubric:
      'Deep Dive grades "how you think, build, and ship — balancing shipping velocity, quality, and impact." System Design grades architectural decisions. DS & A grades correctness. Fullstack Coding grades design, debugging, and decision-making. Code DX and quality of write-up weigh heavily on take-home work.',
    leanInto:
      'Practice live coding WITHOUT AI for the fullstack round — this is the official policy and the most common candidate-surprise point. Build a small Next.js / React app end-to-end on the clock with clean DX (clear README, sensible structure, deployable). Narrate trade-offs aloud — velocity vs quality vs impact is literally on the rubric. Show Next.js / Edge / deployment-platform familiarity. Have a real point of view on v0 even if you do not use it.',
    followUps:
      'Reported topics: rate limiter design, applied Next.js / web fundamentals, product-engineering trade-offs (e.g. shipping velocity vs correctness).',
    sources: [
      'Vercel official engineering prep guide (v0 app) — https://vercel-eng-prep-guide.v0.app/',
      'Exponent, Interviewing at Vercel (2025) — https://www.tryexponent.com/companies/vercel',
      'Vercel blog, Summer Internship at Vercel — https://vercel.com/blog/summer-internship-at-vercel',
    ],
  },

  // ───────── Product companies ─────────
  {
    company: 'Shopify',
    format:
      'Live BYOE AI pairing — empty GitHub repo, screen-shared over Google Meet; two rounds (screening + onsite). Not async take-homes.',
    timeBudgetMin: '60',
    aiPolicyDefault: 'on',
    tools:
      'Bring-your-own-everything — Cursor, Claude Code, ChatGPT, GitHub Copilot, and any other assistant are explicitly fair game. Candidates report running multiple tools in parallel (Cursor as IDE + Claude Code in terminal + browser ChatGPT).',
    rubric:
      'Workflow and decision-making (how you build context and direct the AI), architectural extensibility, agency over the AI (you drive, not the model), code quality even on AI-generated lines (naming, magic numbers, dead code), test design and coverage, continuous narration of intent. CTO Farhan Thawar calls out being able to look at AI output and say "there is a line that is wrong."',
    leanInto:
      'Ship a clean, minimal working product with a tight README — Shopify reviewers value merchant-facing correctness and speed-to-market over architectural elegance. Demonstrate agency over the AI by rejecting bad suggestions out loud and naming why.',
    followUps:
      'Iterative complexity instead of new problems — "now make the cache capacity user-configurable", "what changes if this needs to be thread-safe", "what would your test list look like if we shipped this to a merchant tomorrow."',
    sources: [
      "Hello Interview, Shopify's AI Coding Interview: How to Prepare — https://www.hellointerview.com/blog/shopify-ai-enabled-coding",
      'Pragmatic Engineer, How AI is changing software engineering at Shopify (Farhan Thawar) — https://newsletter.pragmaticengineer.com/p/how-ai-is-changing-software-engineering',
      "First Round Review, From Memo to Movement: Shopify's Cultural Adoption of AI — https://www.firstround.com/ai/shopify",
    ],
  },
  {
    company: 'Stripe',
    format:
      'Signature integration round on a real GitHub repo + Stripe API docs with full internet access (live, 45–60 min); closer to a live take-home than a whiteboard pairing. Loop also includes a separate writing exercise.',
    timeBudgetMin: '45–60',
    aiPolicyDefault: 'candidate-choice',
    tools:
      'Guides say candidates are "free to use external resources such as documentation or StackOverflow, just as you would on the job," implying candidate-choice. Whether Cursor / Copilot specifically are sanctioned varies by loop — confirm with recruiter.',
    rubric:
      'Correctness and idempotency in payments-shaped problems (retries scoped to (merchant, endpoint), persisting request hashes), navigating an unfamiliar codebase by reading docs before guessing, reading error responses carefully, descriptive naming. The "effective engineer" axis often outweighs raw correctness in calibration.',
    leanInto:
      'Correctness and idempotency above all else — if you use AI, show that you have verified every edge case the prompt names and that your solution handles double-execution safely. Read the docs before reaching for an answer; cite the section you grounded a decision on.',
    followUps:
      '"What happens if the same idempotency key arrives with a different request body?" "How would you expire idempotency records?" "Walk me through what your client sees if the network drops mid-request."',
    sources: [
      'Exponent, Stripe Software Engineer Interview Guide (2026) — https://www.tryexponent.com/guides/stripe-software-engineer-interview',
      'Interview Query, Stripe Software Engineer Interview Guide — https://www.interviewquery.com/interview-guides/stripe-software-engineer',
      'Prepfully, Stripe Software Engineer Exhaustive Interview Guide 2026 — https://prepfully.com/interview-guides/stripe-software-engineer',
    ],
  },
  {
    company: 'Cloudflare',
    format:
      'Live systems coding with edge constraints in CoderPad / HackerRank (non-AI rounds), plus a dedicated 45-min AI-assisted round in the onsite loop where candidates use prompts to fix bugs in an unfamiliar project. Loop typically 4–5 rounds total including the "Orange Cloud" 30-min culture round.',
    timeBudgetMin: '45–60',
    aiPolicyDefault: 'candidate-choice',
    tools:
      'AI-assisted round requires AI use to fix bugs in an unfamiliar codebase; specific tooling (Cursor vs Copilot vs Workers AI playground) varies by source — confirm with recruiter. Non-AI rounds use CoderPad / HackerRank only.',
    rubric:
      'Production-quality, readable code over algorithmic cleverness. Networking and distributed-systems fluency (HTTP/3, DNS, TLS, Anycast, V8 isolates, Workers KV, Durable Objects). Reasoning about scale without leaning on managed cloud services. Clean error handling and testing. Cultural fit ("Orange Cloud round" — transparency, curiosity).',
    leanInto:
      'Focus on latency budget and cold-start behavior; if AI generates a solution with an unbounded retry loop or a blocking call, catch it and explain the fix in terms of p95 latency. For non-AI rounds, demonstrate edge-native reasoning (V8 isolates, Durable Objects) and a real point of view on serverless trade-offs.',
    followUps:
      '"How would you run untrusted customer code safely at the edge?" "How does your design behave on a cold start?" "Walk me through the TLS handshake your request just made."',
    sources: [
      "TechPrep, Cloudflare's Interview Process (2026) — https://www.techprep.app/blog/cloudflare-interview-process",
      'Dataford, Cloudflare Software Engineer Interview Guide 2026 — https://dataford.io/interview-guides/cloudflare/software-engineer',
      'LeetCode Discuss, Cloudflare SSE Bangalore March 2026 — https://leetcode.com/discuss/post/7901539/',
    ],
  },
  {
    company: 'Airbnb',
    format:
      'Live coding with product-engineering focus on a shared editor with real, runnable code (no pseudocode accepted). Standard 45-min onsite coding round. Strong cultural weight on Belonging and Being a Host across the loop.',
    timeBudgetMin: '45',
    aiPolicyDefault: 'candidate-choice',
    tools:
      'AI policy not publicly documented in current candidate reports — confirm with recruiter. Airbnb has publicly said ~60% of new internal code is AI-generated (TechCrunch May 2026), but candidate use during live coding is unconfirmed.',
    rubric:
      'Correctness with passing tests, clean and domain-legible implementation, readable naming, time / space trade-off awareness, ability to validate your own solution with examples under time pressure. Strong cultural weight on Belonging and Being a Host.',
    leanInto:
      'Product correctness and naming matter as much as algorithmic efficiency; reviewers look for readable, domain-legible code, so rename any AI-generated variable names that are generic or misleading. For behavioral, have a story ready for "tell me about a time you made someone feel they belong."',
    followUps:
      '"Can you write a test that would catch a regression here?" "What is the time complexity and where does it bite?" "Rename these variables so a teammate reading this in six months understands the domain."',
    sources: [
      'Exponent, Airbnb Software Engineer Interview Guide 2026 — https://www.tryexponent.com/guides/airbnb-swe-interview',
      'Prepfully, Complete Airbnb Software Engineer interview guide (2026) — https://prepfully.com/interview-guides/airbnb-software-engineer',
      'TechCrunch, Airbnb says AI now writes 60% of its new code (May 2026) — https://techcrunch.com/2026/05/08/airbnb-says-ai-now-writes-60-of-its-new-code/',
    ],
  },
  {
    company: 'Linear',
    format:
      'Take-home (4–8 hrs) earlier in the process, followed by a paid 2–5 day work trial on a real project at the end of the loop (final stage, all roles). The work trial is the differentiator.',
    timeBudgetMin: '240 take-home / 2–5 days trial',
    aiPolicyDefault: 'candidate-choice',
    tools:
      'AI policy not publicly documented for the work trial — confirm with recruiter. Linear\'s engineering culture is "AI when it reliably helps." The trial gives access to real internal tools and a real project; practical use of assistants is likely permitted unless restricted.',
    rubric:
      'Craft (depth in domain), judgment (reasoning through trade-offs), ownership (full-stack responsibility), clarity (communication). Take-home write-up quality is weighted heavily — often the most important signal in the loop. Work trial adds communication, self-direction, responsiveness to feedback, and product judgment. Bar is explicit: "anything other than a strong yes is a no."',
    leanInto:
      'Linear values taste: clean interfaces, minimal surface area, no dead code. Trim every AI-generated line that does not earn its seat, and make commit hygiene part of your output. Treat the write-up as a first-class deliverable, not a coversheet.',
    followUps:
      '"Why did you model the data this way?" "What would you do differently with another day?" "Where does this break under offline-first sync?"',
    sources: [
      'Linear, How we hire at Linear — https://linear.app/now/how-we-hire-at-linear',
      'Linear, Why and how we do work trials at Linear — https://linear.app/now/why-and-how-we-do-work-trials-at-linear',
      "Lenny's Newsletter, Adding a work trial to your interview process — https://www.lennysnewsletter.com/p/adding-a-work-trial-to-your-interview",
    ],
  },
  {
    company: 'Notion',
    format:
      'Phone screen → CoderPad technical screen (practical implementation, e.g. basic text editor) → 4-hour virtual onsite (2 coding rounds, 1 system design, 1 values / behavioral). 2025–2026 onsite now includes an AI-enabled coding round.',
    timeBudgetMin: '60',
    aiPolicyDefault: 'on',
    tools:
      'Claude Code and Cursor are specifically named as expected / familiar tooling for the AI-enabled round. Notion engineers internally use both heavily (per The Information, shifting from Cursor toward Claude Code / Codex), so candidates are expected to demonstrate fluency with at least one.',
    rubric:
      'Practical problem-solving over LeetCode patterns; appropriate data-structure choice; edge-case handling; clean code; product understanding (knowing how Notion\'s actual product works); data modeling and database-index reasoning in the system design round; cultural fit on the values round.',
    leanInto:
      'Show fluent, opinionated use of Claude Code or Cursor on a practical implementation problem (text-editor-shaped tasks are common). Narrate why you accepted, rejected, or modified each AI suggestion. Connect your data-structure and schema choices to Notion-shaped product problems rather than abstract puzzles.',
    followUps:
      '"How would you support undo / redo here?" "What changes if multiple users edit this concurrently?" "Walk me through the index you would add and why."',
    sources: [
      'linkjob.ai, How I Passed My 2026 Notion Software Engineer Interview — https://www.linkjob.ai/interview-questions/notion-software-engineer-interview-questions/',
      'Interview Query, Notion Labs Software Engineer Interview Guide — https://www.interviewquery.com/interview-guides/notion-labs-software-engineer',
      "The Information, Claude Code and Codex Are Outpacing Cursor Among Notion's Engineers — https://www.theinformation.com/newsletters/ai-agenda/notion-switching-cursor-claude-code-codex",
    ],
  },
  {
    company: 'Databricks',
    format:
      'Recruiter screen (30), technical phone screen (60, CoderPad live coding), hiring manager (60, behavioral), then virtual onsite of ~4–5 rounds: Coding 1 (algorithms), Coding 2 (data structures / implementation), Concurrency & Multithreading (signature — thread safety, locking, races), System Design (often in Google Docs), Cross-functional / Values. Implementation-heavy and runnable.',
    timeBudgetMin: '60',
    aiPolicyDefault: 'off',
    tools:
      'No public statement permitting AI in interviews; coding is in monitored CoderPad sessions. Treat as AI-off — confirm with recruiter.',
    rubric:
      'Code correctness, clarity, and production-readiness (testing instincts, error handling, naming) — more than puzzle cleverness. Deep concurrency primitives, memory model, distributed-systems trade-offs. For AI / data / ML-platform roles: Spark internals, Delta Lake / lakehouse architecture, streaming semantics (Structured Streaming + Kafka), storage-vs-compute reasoning. References weighted heavily; ~25% of passing candidates get re-teamed post-loop.',
    leanInto:
      'Treat every coding problem as "would I ship this to prod?" — write tests, handle nulls and timeouts, name things well, comment trade-offs. For the concurrency round, talk through invariants and shared state before reaching for locks, and know your language\'s memory model. For system design, lead with data-intensive concerns (skew, partitioning, exactly-once vs at-least-once, backpressure, replay) rather than generic load-balancer-and-Redis stack; mention DDIA-style reasoning explicitly.',
    followUps:
      '"What goes wrong if two threads call this method simultaneously?" "How would this pipeline behave during a Kafka partition rebalance?"',
    sources: [
      'interviewing.io, Databricks interview questions — https://interviewing.io/databricks-interview-questions',
      'Prepfully, Databricks SWE Interview Guide 2026 — https://prepfully.com/interview-guides/databricks-software-engineer',
      'Tech Interview Org, Databricks Interview Guide 2026 — https://www.techinterview.org/post/3233460280/databricks-interview-guide-2026-spark-internals-delta-lake-and-lakehouse-architecture/',
    ],
  },
];

// ─────────────────────────────────────────────────────────────────────────────
// Primary export — references the const locals above
// ─────────────────────────────────────────────────────────────────────────────

export const aiCodingContent: AICodingContent = {
  dashboard: {
    title: 'AI Coding',
    description:
      'How to use an AI assistant to its ceiling and catch what it misses — across every format modern companies run.',
    flavorMatrix: FLAVOR_MATRIX,
    whatThisTests: 'Judgment about AI output, not raw coding throughput.',
    companies: ['Meta', 'Shopify', 'Stripe', 'Cloudflare', 'Airbnb', 'Linear'],
    timeBudget: '45–60 min',
  },

  mentalModel: {
    thesis: 'Trust the AI like a fast junior. Verify like a senior.',
    trustVerifyStages: [
      {
        stage: 'Read AI output',
        do: 'Read every generated line once before running it — form your own hypothesis about what it does.',
      },
      {
        stage: 'Verify against intent',
        do: 'Check that the code satisfies the prompt goal, handles the named edge cases, and imports only real APIs.',
      },
      {
        stage: 'Ship',
        do: 'Commit only what you can explain; if a block is opaque to you, rewrite it or at minimum add an inline comment.',
      },
    ],
    verifyChecklist: [
      'Matches the prompt\'s stated intent and return shape',
      'No hallucinated APIs, imports, or function signatures',
      'Edge cases the prompt named are actually handled',
      'You can explain every non-trivial line in your own words',
      'All tests pass — including the ones you wrote yourself',
    ],
    seniorSignal:
      'Out loud: state what the AI got right, what it missed or misunderstood, and what you changed and why.',
  },

  cheatsheet: {
    policyModes: [
      {
        mode: 'off',
        when:
          'The problem statement says no AI tools, or the interviewer confirms no external assistance.',
        expectation:
          'Pure algorithmic and implementation skill; the interviewer is evaluating unaided problem solving.',
      },
      {
        mode: 'candidate-choice',
        when:
          "The interviewer says 'use whatever you're comfortable with' or the policy is unspecified.",
        expectation:
          'You choose whether to use AI, but must explain every decision; using AI without reviewing output is worse than not using it.',
      },
      {
        mode: 'on',
        when:
          'The problem explicitly instructs you to use an AI assistant or provides one in the interview environment.',
        expectation:
          'The round grades your judgment — how you prompt, review, and integrate AI output — not whether you used it.',
      },
    ],
    flavorDeck: [
      {
        id: 'audit',
        trigger: 'You are handed AI-written code that passes all visible tests.',
        move: 'Re-read the original prompt, re-derive the data flow for one concrete input, then check for hallucinated APIs and off-by-one bounds.',
        watch:
          'The happy path usually works; look at null inputs, empty collections, and the behavior at the boundary of any slice or range.',
      },
      {
        id: 'drive',
        trigger: 'You must add a feature to an existing codebase using an AI assistant.',
        move: 'Write a tight prompt (goal + constraints + signature), review the output before pasting it, integrate, run tests, repeat in loops of < 5 min.',
        watch:
          'Silent regressions: the AI can rename a function, change a return type, or remove a guard silently — always diff before integrating.',
      },
      {
        id: 'debug-refactor',
        trigger: 'You are dropped into 200-500 lines of unfamiliar code with a failing test.',
        move: 'Ask the AI for a one-paragraph summary of each file, then trace the failing call path yourself line-by-line before proposing any fix.',
        watch:
          "The AI's diagnosis is a hypothesis, not a fact — re-run the failing test after every change to confirm the fix is surgical and not a coincidental green.",
      },
      {
        id: 'prompt-spec',
        trigger: 'You must write a prompt whose AI-generated output will be judged against hidden tests.',
        move: 'Structure the prompt as Goal + Constraints + at least 2 examples + Return shape; then read it as if you had no prior context.',
        watch:
          'Ambiguous pronouns, missing edge cases, and unspecified behavior on invalid input are the three most common causes of hidden-test failures.',
      },
      {
        id: 'mini-app',
        trigger: 'You must build a small self-contained app from a requirements list.',
        move: 'Enumerate requirements before touching a keyboard, scaffold the spine in one prompt, verify the happy path end-to-end, then iterate on individual behaviors.',
        watch:
          'Feature creep from the AI: it will add logging, config files, and bonus flags — cut everything not in the numbered requirements before submitting.',
      },
    ],
    redFlags: [
      'Hallucinated import paths or function names that do not exist in the standard library or stated dependencies',
      'Silent prompt drift: each AI iteration shifts further from the original spec without you noticing',
      'Treating AI as an authority on performance or correctness without running a benchmark or a test',
      'Skipping the rubric to chase a tangent the AI introduced (e.g., adding a bonus feature that was not asked for)',
      'Accepting the first output that compiles without tracing at least one concrete input through it',
      'Forgetting to re-run the full test suite after an AI edit that touched shared state or a utility function',
    ],
  },

  promptPlaybook: {
    anatomy: [
      {
        id: 'goal',
        label: 'Goal',
        what: 'One sentence stating exactly what the function must accomplish, in the language of the problem domain.',
      },
      {
        id: 'constraints',
        label: 'Constraints',
        what: 'Explicit limits: input bounds, allowed libraries, performance budget, API stability requirements, no behavior changes outside the named path.',
      },
      {
        id: 'examples',
        label: 'Examples',
        what: 'At least two concrete input/output pairs, including one edge case (empty, single element, or boundary value).',
      },
      {
        id: 'return-shape',
        label: 'Return shape',
        what: 'The exact return type or wire format — type signature, JSON schema, or an annotated example output — so the AI cannot invent a plausible alternative.',
      },
    ],
    templates: PROMPT_TEMPLATES,
    antiTemplates: ANTI_TEMPLATES,
  },

  reviewHabits: {
    checklist: [
      {
        dim: 'Correctness vs intent',
        check:
          'Trace the AI output against the prompt goal for at least one concrete input and one edge case; do not accept "it looks right".',
      },
      {
        dim: 'Hallucinated dependencies',
        check:
          'Every import and external call must exist in the stated language version and dependency set — verify by scanning imports before running.',
      },
      {
        dim: 'Edge cases',
        check:
          'Confirm every edge case named in the prompt is explicitly handled; null, empty, zero, and boundary-value inputs are the most common omissions.',
      },
      {
        dim: 'Performance budget',
        check:
          'Identify the dominant loop or recursive call and confirm the complexity fits the stated constraint (e.g., n ≤ 10^5 needs at most O(n log n)).',
      },
      {
        dim: 'Naming and readability',
        check:
          'Rename any variable or function whose name does not match its role in the domain; AI-generated names like `result2` or `tempData` are a review failure.',
      },
    ],
    defects: DEFECTS,
    defenseScripts: [
      "I changed it because the AI's version returned a default on every error, which would have hidden real failures in production — now it raises so the caller can decide.",
      "I would not trust this in production as-is: the sort direction was wrong and would have returned the lowest scores instead of the highest.",
      "The AI's implementation was correct for the happy path but silently ignored the empty-input case, which the spec says should raise ValueError.",
      "I kept the AI's structure but rewrote the inner loop — the original had an off-by-one that skipped the last window, which I found by tracing index len(nums)-k.",
      "I trust the logic now because I re-ran all existing tests and added two new ones for the edge cases the AI left implicit; all five pass.",
    ],
  },

  companies: COMPANY_ROWS,
};
