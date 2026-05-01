"""Behavioral question: Disagreed with manager (Have Backbone, Disagree
and Commit). Mirrors the schema produced by `_bq()` in
`builder.bq_questions`."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Disagreed With Manager — Backbone in Action",
    "Tell me about a time you disagreed with your manager. What did you do?",
    situation=(
        "I was the tech lead for our checkout service rewrite, a 6-month project to migrate "
        "from a Rails monolith to a set of Go microservices behind an API gateway. Three weeks "
        "before the planned cutover, my manager pushed for a single big-bang deploy on a "
        "Saturday night to 'rip the band-aid off' — he was under pressure from the VP to hit "
        "the quarter-end date. I believed a big-bang carried unacceptable risk: we processed "
        "around $4.2M/day in checkout volume, and our integration tests still had 11 known "
        "flaky cases on the new stack."
    ),
    task=(
        "As tech lead I owned the rollout plan and on-call risk. I had to either back the "
        "big-bang my manager wanted, or make a credible case for a phased dark-launch — and "
        "do it without making him look bad in front of the VP."
    ),
    action=(
        "I asked my manager for 30 minutes 1:1 before escalating anywhere. I came in with a "
        "one-pager comparing two options: big-bang vs. shadow-traffic + 1%/10%/50%/100% ramp "
        "over 8 days. I had pulled the numbers — our last big-bang deploy (the cart service in "
        "Q2) had caused a 47-minute partial outage and an estimated $138K in lost orders, and "
        "two of our 11 flaky integration tests touched the payment-authorization path. I told "
        "him plainly: 'I think a big-bang here is the wrong call, and I want to walk you "
        "through why before we commit.' He pushed back — the date was the date. I proposed a "
        "compromise: keep the public commitment to the quarter-end date, but define 'done' as "
        "100% shadow traffic by that date and full cutover one week later, framed as a "
        "'staged GA.' I drafted the language he could take to the VP. He thought about it "
        "overnight, agreed, and we updated the plan together. Once the decision was made I "
        "stopped re-litigating it: I owned the comms to the team, wrote the rollback runbook, "
        "and ran the bridge during each ramp step."
    ),
    result=(
        "We hit 100% shadow traffic on the original date and finished cutover 6 days later "
        "with zero customer-facing incidents. The shadow phase caught two real bugs — a "
        "currency-rounding mismatch on JPY orders and a retry storm against the fraud service "
        "— either of which would have been a Sev-2 in a big-bang. My manager later told me he "
        "was glad I'd pushed back; he'd been anchored on the date and hadn't priced the "
        "downside. I learned that disagreeing well is mostly preparation: bring data, propose "
        "the alternative in writing, give your manager a face-saving path, and once the call "
        "is made, commit visibly."
    ),
    key_strengths=[
        "Backbone — pushed back on a senior decision",
        "Data-driven argument with quantified downside",
        "Constructive disagreement (private first, with an alternative)",
        "Disagree-and-commit follow-through",
        "Ownership of execution after the decision",
    ],
    framework_tips=[
        "Disagree privately first, escalate only if needed",
        "Bring a written alternative, not just objections",
        "Quantify the downside of the path you're opposing",
        "Give your manager a face-saving way to change course",
        "Once the decision is made, commit visibly — don't sulk or re-litigate",
    ],
    tips=[
        "Pick a real disagreement with real stakes — not 'we disagreed about a font.'",
        "Show you went to your manager directly before going around them.",
        "Quantify both sides: cost of their plan, cost of yours, expected value of each.",
        "Demonstrate you separated 'being right' from 'getting your way' — the goal is the best outcome, not the win.",
        "End with the commit half: what you did after the decision was made, especially if it didn't fully go your way.",
        "Be specific about how you delivered the disagreement — tone, venue, written or verbal.",
    ],
    common_pitfalls=[
        "Telling a story where you 'won' and your manager was simply wrong — interviewers read this as ego, not backbone.",
        "Skipping the commit half — disagreement without follow-through is just complaining.",
        "Vague stakes ('it was important') with no numbers, customers, or concrete risk.",
        "Going around your manager first; escalation before a private conversation reads as bad judgment.",
        "Picking a trivial disagreement to stay safe — this signals you avoid real conflict.",
    ],
    follow_up_questions=[
        "What if your manager had said no — would you have escalated? To whom?",
        "Has there been a time you disagreed, committed, and the decision turned out badly? What did you do?",
        "How do you decide when a disagreement is worth raising versus letting go?",
        "How did you make sure the team didn't see you as undermining your manager afterward?",
        "What would you do differently if you had this conversation again?",
    ],
    what_look_for=[
        "Genuine willingness to push back on authority, not just on peers.",
        "Disagreement delivered with respect and a concrete alternative — not just objections.",
        "Quantified reasoning about risk and trade-offs, not gut feel.",
        "Clear evidence of commit-after-decide: visible support for the chosen path even when it isn't theirs.",
        "Self-awareness about when to escalate and when to drop it.",
    ],
    tags=["disagreement", "backbone", "manager", "conflict", "disagree-and-commit"],
    categories=["Communication", "Leadership", "Amazon Leadership Principles"],
)
