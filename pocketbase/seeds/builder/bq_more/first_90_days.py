"""BQ extra: structured first 90 days at a new role."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Adaptability — First 90 Days at a New Job",
    "Walk me through your first 90 days at a previous job.",
    situation=(
        "I joined a 40-engineer payments platform team as a senior engineer after five years at a "
        "smaller startup. New domain (payments compliance), new stack (Go + Kafka after years of "
        "Python + REST), new team norms, and a manager I'd met exactly twice during interviews. The "
        "team was mid-migration from a monolith to services and had no formal onboarding doc."
    ),
    task=(
        "Ramp fast enough to be a net contributor by the end of the quarter without breaking things, "
        "earning trust, or skipping the context I'd need to make good calls in months 4-12."
    ),
    action=(
        "I split the 90 days into four phases with explicit goals.\n\n"
        "Week 1 — listen. I scheduled 1:1s with my manager, my tech lead, and the two engineers "
        "whose code I'd most likely touch. I asked the same three questions to everyone: 'what's "
        "going well?', 'what's broken?', 'what would you want a new senior engineer to be careful "
        "about?' I took notes, didn't propose anything, and shipped exactly one PR — a typo fix in "
        "the README — just to learn the review and CI flow end-to-end.\n\n"
        "Weeks 2-4 — build context. I read the two services I'd own, top-down: the public API, the "
        "main handlers, then the data model. I kept a personal 'questions doc' instead of "
        "interrupting people; once it had ~10 entries I'd batch them into one 30-min session with "
        "the tech lead. I shadowed one on-call rotation as the secondary. I did 1:1s with adjacent "
        "team leads (fraud, ledger, gateway) so I'd know who to ping in a real incident, not "
        "discover them under pressure.\n\n"
        "Weeks 4-8 — small visible win. I picked a well-scoped, low-blast-radius task off the "
        "backlog: a flaky retry path in the refund worker that woke on-call most weekends. Small "
        "enough I could finish, painful enough that fixing it earned real goodwill. I wrote the "
        "design as a half-page doc, ran it past the tech lead before coding, shipped behind a flag, "
        "and rolled out over a week. On-call pages from that worker dropped to zero.\n\n"
        "Weeks 8-12 — bigger scope. With trust banked, I volunteered to own a piece of the monolith-"
        "to-service migration nobody wanted: the dispute service extraction. I wrote a phased "
        "migration plan, got buy-in from the two teams that integrated with it, and led the first "
        "two phases by end of quarter. I also wrote a 'first 30 days' doc from my own notes and "
        "handed it to my manager — the next hire used it."
    ),
    result=(
        "By day 90 I was on the on-call rotation as primary, owned the dispute extraction, and had "
        "shipped the refund-worker fix that eliminated ~6 weekend pages a month. My manager's Q1 "
        "review called out 'ramped faster than expected, especially given the stack change.' The "
        "onboarding doc I wrote got adopted as the team's official one and shaved an estimated week "
        "off the next two hires' ramps. The biggest lesson: treating ramp as a project with phases "
        "and explicit deliverables — not a vague 'get up to speed' — kept me from drifting into the "
        "trap of either coding too early (before I understood the system) or reading too long "
        "(before I'd earned trust by shipping)."
    ),
    key_strengths=[
        "Structured ramp planning",
        "Listening before proposing",
        "Trust-building via small wins",
        "Durable artifacts (onboarding doc)",
    ],
    framework_tips=[
        "Treat ramp as a project with phases, not a vague 'get up to speed'",
        "Week 1 is for listening — resist the urge to propose changes",
        "First shipped change should be small and visible — bank trust before scope",
        "Capture your own confusion as you go; it's the next hire's onboarding doc",
    ],
    tips=[
        "Show explicit phasing — listen, learn, ship-small, scope-up — not 'I worked hard.'",
        "Quantify the small win (pages eliminated, hours saved) so it's concrete.",
        "Show you talked to adjacent teams, not just your own — context width matters.",
        "Show a durable artifact you left behind (the onboarding doc) — outlives the ramp.",
    ],
    common_pitfalls=[
        "Proposing big changes in week 1 before understanding why things are the way they are",
        "Heads-down coding for 90 days with no relationship-building",
        "Picking a too-big first project and missing the trust-banking small win",
        "No measurable outcome by day 90 — just 'I learned a lot'",
    ],
    follow_up_questions=[
        "What did you NOT do in the first 30 days that you might have been tempted to?",
        "How did you decide which small win to pick?",
        "What would you do differently if you joined a smaller / earlier-stage team?",
    ],
    what_look_for=[
        "Phased plan with explicit deliverables, not vague effort",
        "Listening-first posture before proposing changes",
        "Calibrated first project — small enough to finish, real enough to matter",
        "Durable contribution beyond personal ramp (docs, runbooks, etc.)",
    ],
    tags=["onboarding", "adaptability", "learning", "ramp"],
    categories=["Adaptability", "Self-Direction", "Amazon Leadership Principles"],
)
