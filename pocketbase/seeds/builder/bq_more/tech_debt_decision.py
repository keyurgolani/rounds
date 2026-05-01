"""LP-07 (Insist on Highest Standards) — Tech debt vs new features.

Story: convinced leadership to allocate 30% of next quarter to migrating off a
fragile legacy framework after measuring its outage cost.
"""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Tech Debt Decision — Tipping Point",
    "Tell me about a time you made a hard call about tech debt vs new features.",
    situation=(
        "Our payments service ran on a 6-year-old internal framework that the original authors had "
        "left two years prior. Over the previous 12 months it had caused 7 customer-facing outages "
        "totalling 14 hours of downtime, and our deploy time had crept from 8 minutes to 42 minutes "
        "because every change required two manual config edits and a flaky integration step. "
        "Engineer churn on the team was running at ~30%/year, and exit interviews repeatedly named "
        "the framework. Meanwhile the roadmap had a packed feature backlog the PM was protecting."
    ),
    task=(
        "I was the tech lead. I had to decide whether to keep paying the tax sprint after sprint, or "
        "make the case to leadership that we needed to stop and migrate — and convince a feature-"
        "focused PM and a skeptical director to give up roadmap capacity for it."
    ),
    action=(
        "I refused to argue on aesthetics. First I quantified the pain: I pulled the 12-month "
        "incident log and computed the framework's outage cost — 14 hours x $180K/hr revenue impact "
        "+ on-call burden + the engineering hours spent firefighting — about $3.1M annualised. I "
        "added the deploy-time delta (34 extra minutes x ~80 deploys/quarter x 6 engineers = ~270 "
        "engineer-hours/quarter lost) and the attrition replacement cost. Then I wrote a 5-page "
        "'debt budget' proposal: 30% of next quarter (about 7 engineer-weeks) to migrate the two "
        "highest-traffic endpoints off the legacy framework onto our standard stack, with a phased "
        "milestone plan (M1: scaffolding + dual-write; M2: cutover endpoint A; M3: cutover endpoint "
        "B; M4: decommission). I named the risks honestly — migration could uncover hidden coupling, "
        "we might miss one feature deadline — and proposed exit criteria for each milestone. I "
        "pre-socialised it 1:1 with the PM, who pushed back hard ('we have commitments'); I "
        "responded with: 'one more outage of this size costs more than this quarter's feature "
        "delta.' I refined the doc with her concerns, then took it to the director with the PM in "
        "the room. We got 30% allocated. I owned the M1 scaffolding myself so the team could keep "
        "shipping; I held a weekly checkpoint on debt-budget burn and feature-burndown side by side "
        "so leadership could see both."
    ),
    result=(
        "Migration shipped on schedule across the quarter. Deploy time dropped from 42 minutes to "
        "9 minutes. In the 6 months post-migration, we had 0 framework-attributable outages (vs the "
        "prior 12-month rate of ~3.5/quarter). Defect rate on the migrated endpoints fell ~60%. "
        "Velocity on net-new features actually rose the following quarter because the legacy tax "
        "was gone — we shipped 14 features against a planned 11. Two engineers who'd been "
        "interviewing externally told me the migration was the reason they stayed. The director "
        "later used the 'debt budget' framing as a template for two other teams. I learned that "
        "tech debt arguments win on dollars, not principles — and that 'highest standards' isn't "
        "preserved by complaining about the framework, it's preserved by doing the math and asking "
        "for the budget."
    ),
    key_strengths=["Long-term thinking", "Pragmatism", "Persuasion", "Quantified trade-offs"],
    framework_tips=[
        "Convert debt pain into dollars before asking for budget — outages, deploy time, attrition",
        "Frame as a 'debt budget' (% of capacity) not 'we need to stop features'",
        "Phase the migration into milestones with exit criteria; leadership trusts plans they can audit",
        "Pre-socialise with the PM before going to leadership — never ambush a partner",
        "Show feature-burndown and debt-burn together so the cost is visible in real time",
    ],
    tips=[
        "Pick a story where you held a real standard at real cost — not a side project nobody opposed.",
        "Quantify outage cost, deploy delta, attrition. 'It's fragile' isn't an argument; '$3M/yr' is.",
        "Show you proposed a phased migration, not a rewrite — leadership fears 'rewrite' for good reason.",
        "Show post-migration metrics: outages, deploy time, defect rate, velocity. Both leading and lagging.",
        "Credit the team and the partner PM — this isn't a solo-genius story.",
    ],
    common_pitfalls=[
        "Arguing on engineering aesthetics instead of business cost",
        "Asking for an open-ended rewrite instead of a budgeted, phased migration",
        "No exit criteria — 'we'll know when we're done' loses leadership trust",
        "Going around the PM instead of bringing them along",
        "Not measuring after — without before/after numbers, the next debt argument has no precedent",
    ],
    follow_up_questions=[
        "What if leadership had said no?",
        "How did you decide which endpoints to migrate first?",
        "How do you tell debt that's worth paying down from debt that's worth living with?",
        "What did you cut from the feature roadmap to free the 30%, and how did you choose?",
        "Have you ever pushed for a debt paydown and been wrong?",
    ],
    what_look_for=[
        "Quantified debt cost (dollars, hours, attrition) — not vibes",
        "Phased migration with exit criteria — not a blank-cheque rewrite",
        "Partnership with PM / leadership — not a unilateral push",
        "Before/after measurement",
        "Calibration: knows which debt to pay down and which to leave",
    ],
    tags=["tech-debt", "trade-off", "quality", "standards"],
    categories=["Engineering Strategy", "Long-term Thinking", "Amazon Leadership Principles"],
)
