"""Earn Trust / Have Backbone — negotiated a difficult vendor SLA via BATNA + win-win framing."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Negotiated a Difficult Deal — Vendor SLA Renegotiation",
    "Tell me about a time you negotiated a difficult deal.",
    situation=(
        "We depended on a third-party data provider for a feature that drove 30% of our daily "
        "active sessions. The contract was up for renewal. The vendor proposed a 4x price increase "
        "(from $480K to $1.9M/year), justified by 'market rate adjustment,' AND they wanted to "
        "weaken the SLA from 99.9% to 99.5% — a tenfold increase in allowable downtime. Their "
        "account manager was firm: 'this is what other customers pay.' Our finance team had no "
        "appetite for the price hike; engineering had no appetite for the SLA degradation. We had "
        "60 days until contract expiry."
    ),
    task=(
        "I was the engineering owner for the integration. My VP asked me to lead the negotiation "
        "alongside our procurement lead. We needed to land a deal that fit budget AND held the "
        "SLA — or to credibly walk away."
    ),
    action=(
        "I started by building our BATNA before negotiating, not during. I spent two weeks "
        "evaluating two alternatives: a competing vendor (Vendor B) and an in-house build using "
        "open data sources for ~70% of the use cases. Vendor B quoted $1.1M with a 99.9% SLA but "
        "needed 4 months to migrate. The in-house option was 6 engineer-months and would cover "
        "the long tail. With those numbers in hand, I had a real walk-away. Then I LISTENED. I "
        "asked the vendor's account manager what was driving the increase. He admitted, off the "
        "record, that their CFO had set a hard floor on per-account ARR, and the SLA reduction "
        "was actually about their own reliability problems with a key upstream — they were "
        "hedging. That reframed the negotiation from 'haggle on price' to 'solve their CFO "
        "problem and our reliability problem together.' I proposed a win-win: a 3-year deal at "
        "$950K/yr (their CFO gets ARR commitment + total contract value above $2.8M; our finance "
        "gets a price ceiling), 99.9% SLA preserved on the slice WE depended on (their stable "
        "endpoints), with credits at 2x the standard rate if breached. I gave them advance "
        "notice that we had Vendor B and an in-house option costed and ready — not as a threat, "
        "but as 'we're being transparent about our alternatives.' I let them counter. They came "
        "back at $1.05M; I held at $975K with a slightly relaxed SLA on a non-critical endpoint "
        "as the give. We closed there."
    ),
    result=(
        "Final deal: $975K/year for 3 years, 99.9% SLA on critical endpoints, 2x penalty credits, "
        "quarterly business reviews with their reliability team. Versus their opening: $925K/year "
        "saved, SLA preserved. Versus walking away: 4 months of migration risk avoided. Over the "
        "3 years the vendor hit SLA every quarter (the QBRs forced their reliability work). My "
        "VP asked me to write up the playbook — BATNA before negotiation, listen for the real "
        "constraint, propose a structure that solves both sides' problems. I learned that hard "
        "negotiations get unstuck when you stop bargaining over the stated position and start "
        "asking what's driving it."
    ),
    key_strengths=["BATNA development", "Active listening", "Win-win structuring", "Backbone with respect"],
    framework_tips=[
        "Build your BATNA BEFORE negotiating — a real walk-away changes the entire dynamic",
        "Listen for the OTHER side's constraint — the stated position is rarely the real driver",
        "Reframe from 'haggle' to 'solve both sides' problems together'",
        "Be transparent about alternatives — credibility, not threats",
        "Trade asymmetrically — give on what they value, hold on what you value",
    ],
    tips=[
        "Quantify your BATNA — the alternatives you cost out are the real source of leverage.",
        "Show genuine listening — what's the OTHER side's constraint? Their ask is usually a symptom.",
        "Frame the close as win-win, but also show the give-and-take — both sides moved.",
        "Don't make the other side the villain. They had real constraints too.",
        "Quantify the outcome — savings vs opening, savings vs walk-away, SLA preserved.",
    ],
    common_pitfalls=[
        "Negotiating without a real BATNA — the other side senses bluff",
        "Treating it as zero-sum when it's actually a constraint-mismatch",
        "Skipping the listening phase and counter-proposing immediately",
        "Bluffing about alternatives you haven't actually costed",
        "Heroic narrative — 'I beat them down on price' — misses the durable relationship",
    ],
    follow_up_questions=[
        "What if the vendor had called your bluff on Vendor B?",
        "How did you decide what to give and what to hold?",
        "Have you ever walked away from a negotiation? What happened?",
        "How would you have handled it if their account manager hadn't been candid about the CFO constraint?",
    ],
    what_look_for=[
        "BATNA development with real numbers, not bluff",
        "Active listening that surfaces the real constraint",
        "Win-win structuring vs zero-sum bargaining",
        "Backbone — willingness to walk — paired with respect for the counterparty",
        "Quantified outcome (price, SLA, term)",
    ],
    tags=["negotiation", "contract", "backbone", "trust"],
    categories=["Communication", "Decision Making", "Amazon Leadership Principles"],
)
