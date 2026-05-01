"""BQ: Calculated risk — two-way door decisions under uncertainty."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Calculated Risk - Two-Way Door Decisions",
    "Tell me about a time you made a decision with incomplete information. How did you assess the risk?",
    situation=(
        "We had a two-week window to validate a new pricing-tier experiment before our enterprise "
        "renewal cycle began. Engineering had shipped the experiment behind a feature flag, but "
        "QA was wedged on a separate compliance launch and could only commit to a partial sweep "
        "of the happy path. The product lead wanted the experiment live by Friday so sales could "
        "cite real activation data in renewal calls; the QA lead wanted another full week. I was "
        "the engineer accountable for the rollout, and I had to decide whether to ship Friday "
        "without full QA, with three of our six platform stakeholders unreachable in EMEA off-sites."
    ),
    task=(
        "I owned the rollout decision: ship Friday with a partial QA sweep and missing stakeholder "
        "alignment, or hold for another week and miss the renewal-cycle window. 'Hold' was safe but "
        "expensive in lost sales signal. 'Ship' was fast but uncertain. My job was to figure out "
        "whether this was a two-way door I could walk back through, or a one-way door I shouldn't "
        "walk through alone."
    ),
    action=(
        "I ran an explicit reversibility analysis on a single page before deciding. "
        "First, blast-radius scoping: the feature flag was scoped to <5% of accounts (a single "
        "geographic segment), gated behind a kill switch I could flip from a Slack slash command "
        "in under 30 seconds, and isolated from billing — pricing was displayed but no charges were "
        "issued during the experiment window. So 'wrong' meant 'a few hundred accounts see a "
        "confusing pricing tile,' not 'we billed someone incorrectly.' "
        "Second, I listed the failure modes the missing QA pass could surface: (a) UI regression "
        "on the pricing page, (b) the experiment-assignment service mis-bucketing accounts, "
        "(c) a stale-cache bug double-counting activations. I spent two hours scripting smoke checks "
        "for each — synthetic accounts, a bucket-distribution probe that ran every 5 minutes, and a "
        "Grafana panel for activation deltas vs control. None of these replaced QA, but each gave "
        "me a fast feedback loop: any of those three failure modes would surface within ~10 minutes "
        "of going live, not days later. "
        "Third, I wrote down the rollback plan explicitly: kill switch flip, accounts revert to "
        "control, activation events tagged 'experiment-aborted' so the data team could exclude "
        "them. Mean time to rollback: under 2 minutes from detection. "
        "Fourth, I scoped the unreachable stakeholders. Two of the three were informational "
        "(would have been told, not asked); only one — the data-platform lead — had veto authority "
        "on the schema for the new activation events. I emailed her a 6-line summary, the schema "
        "diff, and a clear 'I plan to ship Friday at 10:00 UTC unless you flag a concern by 09:00 "
        "UTC; the change is fully reversible.' She replied at 23:00 her time with one schema tweak; "
        "I incorporated it. "
        "Fifth, I made the call transparent. I posted in the engineering channel at 09:30 UTC "
        "Friday: 'Shipping pricing-tier experiment behind flag X to 5% of segment Y at 10:00. "
        "Partial QA sweep complete; I have synthetic monitoring for failure modes A/B/C; rollback "
        "is a single Slack command. Reversibility is high; blast radius is bounded. Pinging me here "
        "is the fastest way to flag concerns.' Two engineers asked clarifying questions; nobody "
        "objected. I shipped at 10:02."
    ),
    result=(
        "The bucket-distribution probe caught a real bug 14 minutes after launch — the experiment "
        "was assigning ~8% of traffic instead of 5% because of a rounding bug in the assignment "
        "hash. I flipped the kill switch, the team patched it in 40 minutes, I re-shipped, and the "
        "bucket distribution stabilised. Net customer-visible impact: ~30 accounts saw the "
        "experimental pricing tile for under 15 minutes; none could transact on it. The experiment "
        "ran cleanly for the rest of the renewal window; sales cited a 22% lift in tier-upgrade "
        "intent on enterprise renewal calls. The QA lead reviewed my reversibility doc the "
        "following Monday and said it was the kind of artifact she'd want every team to produce "
        "before shipping under partial QA — we adopted it as a template ('reversibility "
        "pre-mortem') for any flag-gated rollout that runs ahead of full QA. "
        "I learned three things. First, 'incomplete information' is rarely a binary; the right "
        "question is what *kind* of incompleteness, and whether you can buy back the missing "
        "information cheaply with monitoring. Second, the value of a two-way door is precisely "
        "the speed and confidence of the rollback — if you can't articulate the rollback in one "
        "sentence, it isn't actually a two-way door. Third, transparency is a risk-mitigation "
        "tool: announcing the decision publicly with the reversibility argument lets peers "
        "stress-test it before launch, and it leaves a paper trail if the call later needs to be "
        "defended."
    ),
    key_strengths=["Decisiveness", "Risk assessment", "Pragmatism", "Reversibility analysis", "Transparent communication"],
    framework_tips=[
        "Distinguish two-way doors (reversible) from one-way doors (irreversible) before deciding speed",
        "Scope blast radius explicitly: who is affected, in what way, recoverable how",
        "Buy back missing QA with synthetic monitoring and short feedback loops, not optimism",
        "Write the rollback plan in one sentence — if you can't, it isn't reversible",
        "Distinguish stakeholders who need to be ASKED from those who need to be TOLD; address each appropriately",
        "Announce the decision publicly with the reversibility argument — peers will stress-test it",
    ],
    tips=[
        "Use Amazon's two-way / one-way door language explicitly — it's the framing interviewers want.",
        "Quantify blast radius (% of users, recoverability time, dollars at risk).",
        "Show that monitoring SUBSTITUTED for the missing QA, not that you skipped verification.",
        "Show the rollback worked when it had to — bonus credit for catching a real bug.",
        "Do not pick a story where the 'risk' was actually a one-way door dressed up as reversible.",
        "Show the lesson became durable team practice (the reversibility pre-mortem template).",
    ],
    common_pitfalls=[
        "Calling something a 'calculated risk' when it was actually a one-way door",
        "No explicit reversibility / blast-radius analysis — just gut feel",
        "Skipping QA without substituting monitoring or feedback loops",
        "Acting around unreachable stakeholders without trying to reach them",
        "Hiding the decision instead of announcing it transparently",
        "No durable artifact (template, runbook) that absorbs the lesson",
    ],
    follow_up_questions=[
        "How do you tell a two-way door from a one-way door in practice?",
        "What if the kill switch hadn't worked when you tried it?",
        "What would you have done if the data-platform lead had said no?",
        "Have you ever taken a calculated risk that BACKFIRED — what did you learn?",
        "Where's the line between 'calculated risk' and 'reckless'?",
        "How do you decide when you have *enough* information to decide?",
    ],
    what_look_for=[
        "Explicit reversibility framing (two-way vs one-way doors)",
        "Quantified blast radius and bounded downside",
        "Fast feedback loops / monitoring as a substitute for missing verification",
        "One-sentence rollback plan that actually worked",
        "Transparent communication before, during, and after the decision",
        "Durable lesson encoded in team practice, not just personal reflection",
    ],
    tags=["bias-for-action", "risk", "decisions", "two-way-door", "reversibility", "feature-flags"],
    categories=["Decision Making", "Initiative", "Amazon Leadership Principles"],
)
