"""BQ: Ethical dilemma at work — Earn Trust / Highest Standards."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Ethical Dilemma — Surfaced a Concern at Personal Cost",
    "Tell me about a time you faced an ethical dilemma at work.",
    situation=(
        "Two weeks before a major launch, our product analytics team asked engineering to add a "
        "client-side event that would log full URLs of pages users navigated to inside their own "
        "private workspaces — including filenames in document URLs. The PM framed it as 'we need "
        "engagement signal.' Legal hadn't seen the spec. Our ToS allowed 'usage analytics' but "
        "users would not have reasonably expected their private filenames to be sent to our "
        "servers. I was the engineer scoped to ship it."
    ),
    task=(
        "Decide whether to ship as-specified, push back, or escalate — knowing the launch was "
        "tight, the PM was a peer of my manager, and 'being difficult' had a real political cost."
    ),
    action=(
        "I started by writing the concern down precisely so I wasn't arguing on vibes: 'we are "
        "about to log content-derived strings (filenames) from private workspaces without a "
        "privacy review or an explicit user disclosure.' I 1:1'd the PM first — not to accuse, "
        "to check whether I was missing context. He confirmed legal hadn't reviewed and said "
        "'we'll do it post-launch.' I told him directly I wasn't comfortable shipping that order, "
        "and that I'd raise it. I did NOT just refuse silently or go around him. I sent a written "
        "summary to my manager and CC'd the privacy team's intake alias the same day, with three "
        "options: (1) ship without the URL field, (2) hash filenames client-side, (3) delay one "
        "sprint for a privacy review. I named the cost of each. When the PM pushed back in a "
        "group channel ('this is going to slip the launch'), I stayed factual: 'the question is "
        "whether logging private filenames without disclosure is consistent with our privacy "
        "posture; that's a privacy-team call, not mine or yours.' I prepared myself to take a "
        "performance hit if leadership decided I'd been obstructive."
    ),
    result=(
        "Privacy team responded within 48 hours: option 1 (drop the URL field) for launch, with "
        "a properly-disclosed event spec for v1.1. The launch slipped 3 days, not a sprint. Six "
        "months later that same privacy team cited the intake as an example of 'engineer-"
        "initiated escalation that prevented a real issue' — a competitor in the same space was "
        "fined for an analogous logging practice that quarter. My manager's review feedback "
        "included 'raised a hard issue at the right time, through the right channel.' The PM and "
        "I worked together fine afterwards because I'd gone to him first, not around him. I "
        "learned that the right escalation path matters as much as the escalation itself: written, "
        "to the people who can actually decide, with options instead of just objections."
    ),
    key_strengths=[
        "Integrity under schedule pressure",
        "Right-channel escalation (not silent refusal, not going around the PM)",
        "Options-based framing rather than pure objection",
        "Willingness to absorb personal cost",
    ],
    framework_tips=[
        "Write the concern down precisely before arguing it — vibes lose, specifics win",
        "Talk to the person you disagree with FIRST, then escalate — not after",
        "Escalate to the function that owns the decision (privacy, legal, security), not just up the management chain",
        "Bring options with named costs, not just 'no'",
        "Be ready to take the personal cost — that's what makes it ethics, not preference",
    ],
    tips=[
        "Pick a story where the ethical concern was genuinely live — not a retroactive moralisation.",
        "Show the structured escalation: 1:1 first, then written, then the right function.",
        "Name the personal cost you were willing to absorb (political capital, schedule blame, review hit).",
        "Avoid saviour narrative — credit the privacy/legal team that actually made the call.",
        "Distinguish 'I refused' (passive, weak) from 'I escalated through proper channels' (active, accountable).",
    ],
    common_pitfalls=[
        "Picking a story where the ethical issue is obvious in hindsight but wasn't really at the time",
        "Going around the PM/peer instead of to them first — looks like backstabbing",
        "Silent refusal without a written record — leaves no audit trail and looks obstructive",
        "No named personal cost — a cost-free ethical stand isn't really a stand",
        "Saviour framing where YOU 'saved the company' — privacy/legal owns the decision, not you",
    ],
    follow_up_questions=[
        "What if leadership had decided to ship as-specified anyway?",
        "How did you decide WHEN to escalate vs let it ride?",
        "Have you ever raised a concern that turned out to be wrong?",
        "How did you rebuild the relationship with the PM afterwards?",
    ],
    what_look_for=[
        "Right-channel escalation (1:1 first, then written, then the deciding function)",
        "Specific concern stated in policy / customer-trust terms, not personal discomfort",
        "Options-based framing rather than blanket refusal",
        "Acceptance of personal/political cost",
        "Crediting the function that actually decided",
    ],
    tags=["ethics", "integrity", "earn-trust", "backbone"],
    categories=["Integrity", "Decision Making", "Amazon Leadership Principles"],
)
