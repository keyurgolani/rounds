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

const COMPANY_ROWS: AICompanyRow[] = [
  {
    company: 'Meta',
    format: 'Live AI pairing, 60 min (E5 AI round, reported on Blind late 2024)',
    timeBudgetMin: '60',
    aiPolicyDefault: 'on',
    leanInto:
      'Demonstrate a clear review loop: verbalize every AI output you accept, reject, or modify and why — the E5 signal is engineering judgment, not keystrokes.',
  },
  {
    company: 'Shopify',
    format: 'Take-home + async walkthrough',
    timeBudgetMin: '60–90',
    aiPolicyDefault: 'on',
    leanInto:
      'Ship a clean, minimal working product with a tight README; Shopify reviewers value merchant-facing correctness and speed-to-market over architectural elegance.',
  },
  {
    company: 'Stripe',
    format: 'Live coding, structured pairing session',
    timeBudgetMin: '45–60',
    aiPolicyDefault: 'candidate-choice',
    leanInto:
      'Correctness and idempotency matter above all else — if you use AI, show that you have verified every edge case the prompt names and that your solution handles double-execution safely.',
  },
  {
    company: 'Cloudflare',
    format: 'Live systems coding with edge constraints',
    timeBudgetMin: '45–60',
    aiPolicyDefault: 'candidate-choice',
    leanInto:
      'Focus on latency budget and cold-start behavior; if AI generates a solution with an unbounded retry loop or a blocking call, catch it and explain the fix in terms of p95 latency.',
  },
  {
    company: 'Airbnb',
    format: 'Live coding, product engineering focus',
    timeBudgetMin: '45–60',
    aiPolicyDefault: 'candidate-choice',
    leanInto:
      'Product correctness and naming matter as much as algorithmic efficiency; Airbnb reviewers look for readable, domain-legible code, so rename any AI-generated variable names that are generic or misleading.',
  },
  {
    company: 'Linear',
    format: 'Take-home, real codebase context',
    timeBudgetMin: '60–90',
    aiPolicyDefault: 'on',
    leanInto:
      'Linear values taste: clean interfaces, minimal surface area, no dead code. Trim every AI-generated line that does not earn its seat, and make commit hygiene part of your output.',
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
