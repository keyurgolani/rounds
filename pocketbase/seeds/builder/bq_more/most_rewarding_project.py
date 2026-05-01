"""Self-reflection — most rewarding career project.

Story: a multi-year customer-onboarding rebuild that I owned end-to-end —
shows pride in the work, ownership through hard trade-offs, measurable
business and customer impact, and the personal growth that came from
leading a real cross-functional effort for the first time."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Most Rewarding Project — Career-Defining Work",
    "Tell me about the most rewarding project of your career. Why was it meaningful to you?",
    situation=(
        "Three years into my career I was a senior engineer on a B2B SaaS platform whose "
        "onboarding had quietly become the company's biggest growth bottleneck. New customers "
        "took an average of 47 days from contract signature to first production use. Sales was "
        "closing deals; CS was burning out white-gloving every account; ~22% of new customers "
        "churned within their first 6 months and the post-mortems almost always traced back to "
        "a rough first 60 days. There was no single owner — onboarding was a fractured set of "
        "spreadsheets, ad-hoc scripts, and tribal knowledge spread across sales engineering, "
        "CS, and three different product teams. Leadership knew the number was bad; nobody had "
        "the air cover or the cross-team pull to fix it. I asked for it."
    ),
    task=(
        "I volunteered to own the rebuild. The mandate I negotiated was unusually broad for my "
        "level: define what 'good onboarding' meant, design the system, lead a virtual team "
        "across engineering, CS, and product, and own the funnel metrics for the next year. It "
        "was the first time I'd be accountable for a number, not a feature — and the first "
        "time I'd be the most senior IC in the room on a problem that wasn't purely "
        "technical."
    ),
    action=(
        "I started by spending two weeks NOT writing code. I shadowed 6 onboarding sessions "
        "end-to-end, interviewed 14 customers (some in their first week, some at 3 months, "
        "some who had churned), and sat with the CS team to map every email, ticket, and "
        "Zoom call in the first 60 days. The picture that emerged: the real bottleneck wasn't "
        "any single step — it was hand-offs. Customers waited 4-9 days between stages because "
        "no system tracked who owed whom what. I wrote a one-pager defining 'time-to-first-"
        "value' (TTFV) as the headline metric and proposing three workstreams: a guided "
        "in-product setup flow, a CS-facing onboarding console with explicit hand-off states, "
        "and a self-serve sample-data path for technical buyers who wanted to evaluate without "
        "sales. I socialised it with each affected team's tech lead and PM BEFORE taking it to "
        "the VP — by the time it hit the staff meeting, every team I needed had already signed "
        "off. I scoped the first phase tight: 90 days, two engineers plus me, just the in-"
        "product flow and the hand-off state machine. I deliberately deferred the self-serve "
        "path to phase 2 because I'd seen too many ambitious cross-team projects collapse "
        "under their own scope. Through the build I made three calls I'm still proud of: "
        "(1) I killed a beautifully-architected templating system one of my engineers had "
        "built because it was 3 weeks of work and YAGNI-grade speculative; we shipped a "
        "switch statement instead. (2) When CS pushed for a feature that would have helped "
        "their internal workflow but added 2 clicks for the customer, I held the line and "
        "proposed a separate CS-only view instead. (3) Halfway through phase 1, our analytics "
        "showed the highest-friction step wasn't where we'd assumed — it was a credentials "
        "exchange we'd planned to leave alone. I re-planned mid-phase to fix it, took the 2-"
        "week schedule hit, and communicated the slip with the data, not apologies. Phase 1 "
        "shipped at day 96. Phase 2 (the self-serve path) shipped two quarters later. I "
        "stayed accountable for the metric for a full year after launch — running a monthly "
        "review with sales, CS, and product where we walked the funnel and named the next "
        "bottleneck."
    ),
    result=(
        "Over 12 months, TTFV dropped from 47 days to 11 days — a 76% reduction. 6-month "
        "churn fell from 22% to 9%. CS reclaimed roughly 30% of their capacity, which the org "
        "redirected from manual onboarding into expansion accounts; that team booked an "
        "additional ~$4.2M in expansion revenue in the following year that the CFO partially "
        "attributed to the onboarding rebuild. The self-serve path opened a new mid-market "
        "segment we couldn't economically serve before — ~140 self-serve customers in year "
        "one. The onboarding console became a permanent CS tool. Internally, the project "
        "became the template for how we ran cross-functional initiatives: dedicated owner, "
        "explicit metric, scoped phases, monthly funnel review. Personally, this was the work "
        "that taught me the difference between being a senior engineer and being a leader. I "
        "learned that the hardest part of a high-impact project isn't the architecture — it's "
        "the unglamorous discipline of saying no to scope, holding a metric for a year after "
        "launch, and pre-aligning stakeholders so the meeting where you 'get approval' is a "
        "formality. It's still the project I'm proudest of: not because of the numbers, but "
        "because I went in as someone who built features and came out as someone who could be "
        "trusted to own an outcome."
    ),
    key_strengths=[
        "Ownership of an outcome (not a deliverable)",
        "Cross-functional leadership",
        "Scope discipline",
        "Customer empathy through direct research",
        "Long-horizon accountability (12-month metric ownership)",
        "Self-awareness about personal growth",
    ],
    framework_tips=[
        "Pick a project where the impact is measurable AND the personal growth is articulable",
        "Lead with WHY it was rewarding — pride should be visible, not performed",
        "Quantify business impact (TTFV, churn, revenue) and customer impact (real stories)",
        "Show the hard calls you made, not just the happy outcome",
        "Name the personal growth — what did this project make you capable of?",
    ],
    tips=[
        "Pick a project that genuinely was the most rewarding — interviewers can tell when you're reaching.",
        "Quantify both directions: business impact AND time invested. A '3-week project' is rarely 'most rewarding.'",
        "Be specific about WHY it was rewarding — impact, ownership, learning, relationships, or all four.",
        "Show the unglamorous work (alignment, scope cuts, holding the metric a year later), not just the launch.",
        "Distinguish 'rewarding' from 'highest-status' — they're not the same and interviewers know it.",
        "End with what the project made you CAPABLE of next, not just how it felt.",
    ],
    common_pitfalls=[
        "Picking a story that's actually about prestige, not personal meaning",
        "Vague pride ('I felt proud') without naming what specifically was rewarding",
        "No measurable outcome — pride without impact reads as ego",
        "Hero narrative — taking credit for collaborative work",
        "Skipping the hard parts — the trade-offs, the wrong turns, the tedium",
        "No self-awareness about what you LEARNED — just a victory lap",
        "Picking something too recent to know whether it was actually rewarding",
    ],
    follow_up_questions=[
        "What would you do differently if you ran this project again?",
        "What was the hardest moment, and what got you through it?",
        "How did this project change how you approach work now?",
        "What did you NOT get to do that you wish you had?",
        "Was there a moment you considered handing it off? Why didn't you?",
        "Who else deserves credit for this — and what specifically did they contribute?",
    ],
    what_look_for=[
        "Genuine pride backed by specifics, not generic enthusiasm",
        "Ownership of an outcome over a long horizon (months / years, not weeks)",
        "Quantified business and customer impact",
        "Self-awareness about personal growth — what the project made them capable of",
        "Crediting collaborators while still owning their specific contribution",
        "Articulable lessons that show up in how they work now",
    ],
    tags=["pride", "impact", "ownership", "career"],
    categories=["Self-Awareness", "Career Reflection", "Amazon Leadership Principles"],
)
