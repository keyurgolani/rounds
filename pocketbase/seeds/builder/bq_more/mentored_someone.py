"""BQ extra: 'Tell me about a time you mentored someone' — Hire and Develop the Best.

Distinct angle from LP-06 (which focuses on tacit-knowledge transfer for a new
grad). This story emphasises long-arc mentorship: helping a struggling mid-level
engineer through a stuck promotion packet by teaching debugging methodology
and self-advocacy, with a measurable outcome 6 months later."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Mentored Someone — Investing in Growth",
    "Tell me about a time you mentored a teammate or junior engineer. What changed?",
    situation=(
        "A mid-level engineer on my team — let's call him R — had been stuck at the same level "
        "for two cycles. He was a strong implementer but had a reputation for 'flailing' on "
        "ambiguous bugs: he'd jump between hypotheses, change three things at once, and end up "
        "unable to explain what had actually fixed the issue. His manager had told him in his "
        "last review that 'debugging maturity' was the gap blocking promotion, but no one had "
        "told him HOW to close it. He came to me after a particularly bad week — two days lost "
        "chasing a bug that turned out to be a stale build cache — and asked if I'd help."
    ),
    task=(
        "I wasn't his manager and there was no formal mentorship program. The ask was open-ended "
        "('help me get unstuck on debugging') and the underlying ask was bigger ('help me get "
        "promoted'). I had to decide whether to take it on, and if I did, how to make the time "
        "investment durable rather than another well-meaning ad-hoc effort."
    ),
    action=(
        "I started by asking R to walk me through the most recent bug, narrating his thought "
        "process. The diagnosis surfaced fast: he had no explicit hypothesis-tracking step. He "
        "was holding everything in his head, so the cheapest action (try the next hunch) always "
        "won over the right action (write down what you've ruled out). I introduced him to a "
        "lightweight framework I'd learned the hard way myself: a 'bug journal' with three "
        "columns — Observation, Hypothesis, Test/Disconfirmation. Every bug session, fill in the "
        "table; nothing leaves your head. We then did three structured pairing sessions on "
        "real on-call bugs from his queue. I drove the first one to model it, he drove the second "
        "with me observing, and on the third I sat silent and only spoke if he asked. After "
        "each, we did a 10-minute retro: where did you almost change two things at once? where "
        "did you stop disconfirming too early? In parallel, I noticed his promo packet draft "
        "described his work in implementation terms ('shipped feature X') rather than impact "
        "terms ('reduced p99 by Y, unblocked Z customers'). I spent 45 minutes with him reframing "
        "three of his recent projects in the language of the promotion bar his org used. I told "
        "his manager what we were doing — not to take credit, but so growth would be visible "
        "and so my coaching wouldn't conflict with his manager's signals. We kept biweekly 30-min "
        "1:1s for 6 months."
    ),
    result=(
        "Within 6 weeks, R closed an ambiguous production bug that had been bouncing between "
        "two teams for a month — and in his postmortem, he attached his bug-journal entries as "
        "the artefact. His tech lead mentioned it in the team retro. He was promoted at the next "
        "cycle, ~6 months after our first session, with the same manager who'd previously "
        "flagged the gap writing the rec letter. R later told me the bug journal was the single "
        "habit change that mattered; he still uses it. Two of his teammates picked it up after "
        "seeing his postmortems. I learned that mentorship lands when you make the implicit "
        "explicit (a written framework beats verbal advice every time), when you let the mentee "
        "drive (model → assist → fade), and when you loop in the formal manager so growth is "
        "visible in the system that actually decides promotion."
    ),
    key_strengths=["Coaching", "Empathy", "Patience", "Long-term thinking"],
    framework_tips=[
        "Diagnose the specific gap (debugging methodology) before prescribing — don't generic-mentor",
        "Make implicit knowledge explicit: a written framework (bug journal) > verbal advice",
        "Use model → assist → fade pairing so the mentee builds the muscle, not dependence on you",
        "Loop in the formal manager — growth that isn't visible to the promotion decider doesn't count",
        "Stay engaged past the immediate problem (biweekly 1:1s for 6 months, not a one-off)",
    ],
    tips=[
        "Show you diagnosed the actual gap (process / tacit knowledge) vs assuming it was skill or effort.",
        "Show a concrete artefact — the bug journal, the reframed promo packet — not just 'I gave advice.'",
        "Quantify the outcome (promoted in 6 months, bug closed in week 6, teammates adopting the practice).",
        "Credit the mentee for doing the work; you provided scaffolding, not the result.",
        "Show the long-arc commitment (6 months of biweekly 1:1s) — drive-by mentorship doesn't change behaviour.",
    ],
    common_pitfalls=[
        "Saviour narrative — 'I got him promoted'",
        "No diagnosis step — generic 'I helped him with debugging'",
        "One-off help with no follow-through or habit-formation",
        "Going around the formal manager instead of looping them in",
        "Claiming credit for the mentee's work or the artefacts they produced",
    ],
    follow_up_questions=[
        "How did you make time for this alongside your day job?",
        "What if R had pushed back on the bug journal as too much overhead?",
        "Have you used this model for anyone else since?",
        "What would you do differently if you were doing it again?",
        "How did you avoid stepping on his manager's toes?",
    ],
    what_look_for=[
        "Diagnostic vs prescriptive mentoring (named the specific gap)",
        "Concrete frameworks / artefacts that outlast the mentor's involvement",
        "Sustained engagement (months, not minutes) with a fade-out plan",
        "Crediting the mentee and the manager rather than self-aggrandising",
        "Quantified, durable outcome (promotion + behaviour spread to teammates)",
    ],
    tags=["mentorship", "coaching", "growth", "develop"],
    categories=["People Development", "Leadership", "Amazon Leadership Principles"],
)
