"""BQ: AI-Driven Impact — delivered something you couldn't have otherwise."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "AI-Driven Impact — Delivered Through AI Partnership",
    "Tell me about a time you used AI to deliver something you couldn't have delivered otherwise — or couldn't have delivered as quickly.",
    situation=(
        "Our 12-person platform team had a six-week deadline to ship a self-service migration tool that "
        "would let 400+ internal teams move their services from a deprecated config format to the new "
        "one. Hand-doing the migrations would have taken a year of dedicated engineering. The "
        "alternative — a deterministic codemod — looked tractable until we surveyed 30 sample services "
        "and found 11 different idiomatic patterns, three of them undocumented, and at least one team "
        "writing config in YAML annotations inside Python comments. A pure AST-based codemod would "
        "miss the long tail; a regex pass would corrupt the weird cases."
    ),
    task=(
        "I owned the migration tool. My job was to ship something that 400 teams could run on their "
        "own service with high confidence, in six weeks, without me reviewing each PR. 'Manual review' "
        "was the path of least resistance for me personally, but it would have made me a bottleneck "
        "for a year. I had to find a way to get to high-confidence automated migration even on the "
        "weird cases."
    ),
    action=(
        "I used Claude as a deterministic-tool-augmenter, not as the tool itself. Concretely: "
        "the codemod started as a Python AST pass that handled the four most common patterns cleanly "
        "and emitted a structured 'unmatched' record for everything else. The unmatched record "
        "captured the file path, the surrounding lines, and the team's style guide URL if one existed. "
        "I then wrote a small driver that, for each unmatched record, called Claude with a tightly "
        "scoped prompt: 'Given this config snippet and this target schema, propose the equivalent in "
        "the new format. Return JSON with three fields: proposed_replacement, confidence (high / "
        "medium / low), and one_sentence_justification.' I deliberately kept the prompt narrow — "
        "the model wasn't doing migration strategy, just pattern-matching a known input to a known "
        "output shape that the codemod could then apply. "
        "I built a verification layer the model couldn't shortcut. Every proposed replacement got "
        "fed back into the AST parser to confirm it produced valid config in the new format; if it "
        "didn't parse, the proposal was rejected automatically. For proposals that did parse, the "
        "tool generated a side-by-side diff and a synthetic test that exercised the migrated service "
        "against a recorded request fixture. Only proposals where (a) the diff round-tripped, (b) the "
        "synthetic test passed, and (c) the model self-reported 'high' confidence were applied "
        "automatically. 'Medium' became a PR for a human to approve; 'low' became a ticket for the "
        "owning team. I narrated this design out loud in the team review: 'the AI is doing pattern "
        "match, not migration; the codemod and the test harness are the source of truth.' "
        "I also wrote what I'd do if the model hallucinated. I sampled 50 unmatched cases manually "
        "before launch, ran them through the pipeline, and counted how often Claude was wrong even "
        "when it self-reported 'high.' False-confident rate was 4% — too high to ship as-is. I added "
        "a second pass that asked a different model (GPT-5) to validate Claude's proposal, and "
        "rejected any case where the two disagreed. This dropped the false-confident rate to under 1%."
    ),
    result=(
        "We migrated 387 of 412 services automatically in five weeks. 19 services landed as "
        "human-review PRs (the medium-confidence bucket) and got merged in another week. 6 services "
        "stayed as tickets for the owning team — all were the 'YAML in Python comments' edge cases "
        "where the right call was for the human to refactor first. Net engineering cost: ~7 weeks of "
        "my time and ~$340 in API spend, vs an estimated 10 person-years for hand migration. "
        "Three lessons I'd defend in an interview. First, the AI was a force multiplier on a "
        "well-scoped task, not the architect — I'd have failed if I'd let it design the migration "
        "strategy. Second, the verification layer was non-negotiable: every model output had to "
        "round-trip through deterministic checks (parse, diff, test) before it touched a file. "
        "Third, the two-model cross-check materially raised confidence at a tiny marginal cost; "
        "'AI agreeing with itself' isn't a strong signal, but two independent models agreeing is."
    ),
    key_strengths=[
        "AI-Driven Impact",
        "Verification rigor",
        "Scoping AI to a narrow task",
        "Cost-benefit analysis",
        "Communicating AI use clearly",
    ],
    framework_tips=[
        "Frame the AI as a tool inside YOUR architecture — not as the architect",
        "Name the verification layer explicitly: how do you know the AI was right?",
        "Quantify the human-work delta the AI bought you, not just the raw speedup",
        "Surface the failure modes you anticipated and the safeguards you built for each",
        "Distinguish 'AI did pattern match' from 'AI made the decision'",
    ],
    tips=[
        "Pick a story where the AI was demonstrably load-bearing — not just 'I used Copilot to autocomplete'",
        "Have the cost numbers ready (your time, API spend, alternative cost) — Meta will probe scope",
        "Be ready to defend the choice to delegate: why was this task safe for the model and not others?",
        "Mention at least one verification mechanism — Meta grades 'did you trust but verify?'",
        "Have a story for both 'AI raised the ceiling' (you couldn't have done it) and 'AI raised the floor' (you did it faster); the former is stronger for AI-Driven Impact",
    ],
    common_pitfalls=[
        "Telling a 'Copilot autocompleted my function' story — too small to land AI-Driven Impact",
        "Letting the AI sound like the architect; Meta is grading YOUR engineering judgment",
        "Hand-waving the verification step ('I checked it') instead of naming the mechanism",
        "Inflating the speedup claim without a credible baseline of what hand-doing would have cost",
        "Skipping the failure-mode analysis — Meta will ask 'what happens when the AI is wrong?'",
    ],
    follow_up_questions=[
        "What was your verification mechanism when the AI was uncertain?",
        "How did you decide which subtasks were safe to delegate and which weren't?",
        "What would you have done differently if you'd had to hand-migrate the long tail?",
        "How did you scope your prompt to constrain what the model could decide?",
        "What was your rollback plan if a migrated service broke in production?",
    ],
    what_look_for=[
        "AI used as a narrow tool inside a designed system, not as a free agent",
        "Explicit verification: how candidate knew the AI was correct",
        "Quantified cost-benefit (time saved, dollars spent, alternative path)",
        "Failure-mode anticipation and concrete safeguards",
        "Candidate retained ownership of the engineering judgment",
    ],
    tags=[
        "ai-driven-impact",
        "ai-collaboration",
        "force-multiplier",
        "verification",
        "tool-design",
    ],
    categories=["AI Collaboration", "Innovation & Creativity"],
)
