"""BQ: Customer Obsession — Closing the loop on customer feedback to improve the product."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Customer Obsession — Used Customer Feedback to Improve the Product",
    "Tell me about a time you used customer feedback to improve your product.",
    situation=(
        "I led a small team owning the self-serve checkout flow for a B2B SaaS product. The "
        "headline funnel metric — visit-to-paid conversion — had been flat at ~2.3% for six "
        "months despite three rounds of UI polish from the design team. Our customer-success "
        "org collected support tickets in Zendesk but nobody on engineering was reading them "
        "regularly; the weekly digest was a single slide in the all-hands deck and it always "
        "said 'no major themes this week.' I'd inherited the area three months earlier and "
        "had a hunch we were optimising the wrong thing."
    ),
    task=(
        "I wanted to understand why conversion was stuck before approving another round of "
        "visual redesign. My job was to either confirm the design hypothesis or surface a "
        "better one — using actual customer voice, not internal opinions — and then drive a "
        "concrete improvement against a business metric, not a vanity one."
    ),
    action=(
        "I set a standing 30-minute slot every Friday morning to read the previous week's "
        "checkout-related support tickets — raw, not the CS digest. After three weeks I had "
        "tagged about 240 tickets into a quick spreadsheet of themes. The top theme wasn't "
        "what design had assumed (visual hierarchy / button placement). It was a single "
        "concrete frustration: customers couldn't tell which of their 3-5 corporate billing "
        "emails the receipt would go to, so finance teams were blocking the purchase mid-flow "
        "until they could verify. Roughly 38% of tickets touched this; the affected sessions "
        "showed a clear drop-off at the payment step. I wrote a one-page brief with the "
        "ticket counts, six verbatim customer quotes, and the funnel data. I shared it with "
        "design and PM and proposed a small scoped change instead of another redesign: a "
        "billing-email picker with a clearly visible 'send a copy to' field on the payment "
        "step. I scoped it to two weeks of work for one engineer, gated it behind a 50/50 A/B "
        "test, and committed to revert if the test didn't move the conversion needle. I also "
        "asked CS to forward me the next 30 days of tickets directly so we'd see if the "
        "complaint class actually disappeared."
    ),
    result=(
        "The A/B test showed a +0.6 percentage-point lift in visit-to-paid conversion (from "
        "2.3% to 2.9%, ~26% relative) with statistical significance after 11 days; we shipped "
        "to 100%. The billing-email complaint class dropped from 38% of checkout tickets to "
        "under 4% within a month. Annualised, the conversion lift was worth roughly $1.4M in "
        "incremental ARR for what turned out to be 9 engineer-days of work — well above any "
        "of the prior redesign rounds. Beyond the number, the durable change was the habit: "
        "the Friday ticket-reading slot became a team ritual, and we caught two more "
        "actionable themes in the next quarter the same way. I learned that customer feedback "
        "is almost always sitting in the support queue already; the work isn't gathering it, "
        "it's making someone responsible for reading it and feeding it back into the roadmap."
    ),
    key_strengths=["Customer empathy", "Closing the feedback loop", "Data-driven prioritisation", "Scoped experimentation"],
    framework_tips=[
        "Show you went to the raw customer voice (tickets, calls, sessions) — not the summarised digest",
        "Quantify the theme ('38% of tickets') so the prioritisation is defensible",
        "Tie the change to a business metric (conversion, retention, ARR), not a vanity output",
        "Institutionalise the loop — a one-time read isn't customer obsession, a recurring habit is",
    ],
    tips=[
        "Pick a story where customer feedback OVERRULED an internal hypothesis — that's the punchline interviewers look for.",
        "Show the sample size of the feedback (ticket count, % of complaints) so it's clearly a pattern, not a one-off.",
        "Quantify both the customer outcome (complaint volume drop) AND the business outcome (conversion, ARR).",
        "End on the durable mechanism — the recurring habit, the dashboard, the ritual — not just the one shipped feature.",
    ],
    common_pitfalls=[
        "'We listened to customers' without specifics — no ticket counts, no quotes, no themes",
        "Acting on a single loud customer instead of a quantified pattern",
        "Shipping the change but never verifying the complaint class actually disappeared",
        "One-off heroics with no feedback loop institutionalised after",
    ],
    follow_up_questions=[
        "How did you decide which feedback theme to act on first?",
        "What did you do with the OTHER themes you found in the tickets?",
        "How did you handle internal pushback — design had a different hypothesis, right?",
        "Would you have shipped if the A/B test had been flat?",
    ],
    what_look_for=[
        "Direct contact with raw customer voice (not summarised internally)",
        "Quantified pattern recognition before acting",
        "Business-metric outcome, not just 'customers were happier'",
        "Durable mechanism — the feedback loop becomes a recurring practice, not a one-time act",
    ],
    tags=["customer", "feedback", "empathy", "data-driven"],
    categories=["Customer Focus", "Product Thinking", "Amazon Leadership Principles"],
)
