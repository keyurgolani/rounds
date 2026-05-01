"""LP-04 / LP-08 (Are Right, A Lot / Think Big) — Balancing short-term needs
with long-term thinking.

Story: pressure to ship a feature in a way that would create maintenance
burden; negotiated a phased path with feature-flag scaffolding so short-term
velocity didn't hurt long-term agility.
"""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Short-Term vs Long-Term — Balanced Velocity with Agility",
    "Tell me about a time you balanced short-term needs with long-term thinking.",
    situation=(
        "We were 5 weeks from a high-visibility partner launch when sales committed to a custom "
        "pricing-tier feature for a Fortune-500 prospect worth ~$2.4M ARR. The prospect's "
        "procurement deadline was hard. The 'fast' implementation that two engineers had "
        "started would have hard-coded the partner's tier into our pricing service with three "
        "if-statements scattered across the checkout flow, the invoice generator, and the "
        "entitlement service. It would ship in 2 weeks. But our pricing roadmap for the next "
        "year had three more enterprise tiers planned, and the if-statement pattern would have "
        "to be unwound — or duplicated — for each of them. I'd seen this movie before at a "
        "previous company; the unwinding took 8 months."
    ),
    task=(
        "I was the tech lead on pricing. I had to land the partner deal on time AND not lock the "
        "team into a maintenance trap that would slow every future tier launch. The PM and the "
        "account exec wanted the fastest path; my own team wanted to stop and build the 'right' "
        "tier-config framework, which would have taken 7 weeks and missed the deadline."
    ),
    action=(
        "I rejected both extremes and proposed a phased path. Phase 1 (2.5 weeks): ship the "
        "partner-specific behaviour behind a single feature flag and a tier-config interface "
        "with exactly one implementation — the partner's. The interface had three methods "
        "(pricing rules, invoice format, entitlement scope) that mirrored where the if-"
        "statements would have lived; the flag scaffolding meant the production code path went "
        "through the interface, not around it. Phase 2 (4 weeks, post-launch): generalise the "
        "interface to support the next two tiers on the roadmap, with the partner tier as the "
        "first real consumer. I quantified the trade-off explicitly in a one-pager: the "
        "if-statement path was 0.5 weeks faster up-front but, by my estimate, would cost ~6 "
        "engineer-weeks per future tier (3 tiers x 6 = 18 weeks) plus a likely outage from "
        "scattered logic drift. The interface-with-flag path cost 0.5 weeks more now and ~1 "
        "engineer-week per future tier. Break-even after the first additional tier. I "
        "pre-socialised with the PM 1:1 — she pushed back on the half-week ('every day "
        "matters') and I conceded a small scope cut on a non-blocking analytics event to "
        "absorb it. I took the proposal to the director with the PM in the room so it landed "
        "as a joint recommendation, not a tech-vs-product fight. I named the risks: the "
        "interface might over-fit the partner's shape; we'd revisit at Phase 2 with the next "
        "tier in hand. I owned the interface scaffolding myself so the two engineers could "
        "stay focused on partner-specific logic."
    ),
    result=(
        "Phase 1 shipped 2 days before the procurement deadline. Partner deal closed; $2.4M ARR "
        "booked. The feature flag let us soft-launch to the partner first and catch a billing-"
        "rounding bug before any other customer could hit it. Phase 2 generalisation shipped 5 "
        "weeks later; the next two enterprise tiers (planned for Q2 and Q3) each launched in "
        "~1 engineer-week of pricing-service work instead of the 6 we'd projected for the "
        "if-statement path. By the end of the year we'd onboarded 4 enterprise tiers on the "
        "framework with zero pricing-service outages. The director called the 'flag-and-"
        "interface-now, generalise-later' pattern out as a template in an architecture review "
        "and two other teams adopted it. I learned that the right answer to 'short-term vs "
        "long-term' is rarely a choice between the two — it's usually a small structural "
        "investment up front that buys back optionality without slipping the date."
    ),
    key_strengths=["Long-term thinking", "Pragmatic trade-offs", "Phased delivery", "Stakeholder alignment"],
    framework_tips=[
        "Reject the false binary — find the small structural investment that preserves both",
        "Quantify the long-term cost in engineer-weeks per future use-case, not vibes",
        "Use feature flags / interfaces as scaffolding so today's code path is tomorrow's seam",
        "Pre-socialise with the PM before going to leadership — present as a joint recommendation",
        "Phase the work: ship the smallest correct shape now, generalise when the second consumer arrives",
    ],
    tips=[
        "Pick a story where the 'fast' path was genuinely tempting — otherwise the trade-off isn't real.",
        "Quantify the long-term cost: engineer-weeks per future tier, outage probability, attrition risk.",
        "Show you found a third option, not just 'I held the line on quality.'",
        "Show the partnership with the PM — short-term vs long-term is usually a tech-vs-product seam.",
        "Show post-launch metrics that prove the long-term investment paid off.",
    ],
    common_pitfalls=[
        "Framing it as 'I refused to ship the hack' — that's standards, not balance",
        "No quantification of the long-term cost; just 'it would have been hard to maintain'",
        "Picking a story where the long-term win never materialised (no proof the investment paid off)",
        "Going around the PM / business stakeholder instead of bringing them along",
        "Over-engineering — 'I built a generic framework for hypothetical future needs'",
    ],
    follow_up_questions=[
        "What if the second tier had never come — was the half-week wasted?",
        "How did you decide where to draw the interface boundary?",
        "What if the PM had insisted on the if-statement path?",
        "Have you ever picked the short-term path and regretted it?",
        "How do you tell when an abstraction is premature vs when it's load-bearing?",
    ],
    what_look_for=[
        "Finds the third option — not a binary short-vs-long",
        "Quantified long-term cost (engineer-weeks, outage probability)",
        "Phased delivery with feature flags / interfaces as scaffolding",
        "Partnership with PM / business — not a unilateral tech push",
        "Post-launch evidence the long-term investment actually paid off",
    ],
    tags=["long-term", "trade-off", "planning", "strategy"],
    categories=["Strategic Thinking", "Decision Making", "Amazon Leadership Principles"],
)
