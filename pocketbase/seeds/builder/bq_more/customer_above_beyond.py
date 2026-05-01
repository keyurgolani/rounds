"""BQ: Customer Obsession — Going above and beyond for a customer."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Customer Obsession — Going the Extra Mile",
    "Tell me about a time you went above and beyond for a customer.",
    situation=(
        "A mid-sized fintech customer on our enterprise tier — about 9% of regional ARR — had "
        "quietly committed to a regulator-driven launch that required exporting 18 months of "
        "transaction history into a non-standard XBRL-flavoured format. They hadn't told us. "
        "Their CSM found out on a Thursday afternoon when the customer's compliance lead "
        "mentioned offhand that 'the audit deliverable is due Monday morning.' Our product "
        "supported CSV and Parquet exports; the regulator-required schema mapped to neither. "
        "If they missed the filing they faced a fine and, more importantly to them, a "
        "supervisory black mark that would follow them for years."
    ),
    task=(
        "I was the on-call engineer for the data-export service that weekend. The formal answer "
        "was 'file a feature request, ETA 6–8 weeks.' The honest answer was that this customer "
        "had bet on us, had a real deadline, and the gap between what we shipped and what they "
        "needed was a schema mapping — not a product limitation. I had to decide whether to "
        "treat this as someone else's problem on Monday or as mine that weekend."
    ),
    action=(
        "I called the CSM and the customer's compliance lead Thursday evening to get the actual "
        "schema spec — not the marketing description, the regulator's PDF. I read it that night "
        "and confirmed our internal export pipeline already had every field they needed; only "
        "the output adapter was missing. Friday I cleared it with my manager (texted him: 'one "
        "weekend, scoped to this customer, won't ship to main until reviewed') and with the "
        "platform tech lead so I wasn't ghost-shipping. I wrote a custom XBRL adapter as a "
        "feature-flagged plugin — gated to that customer's tenant ID so blast radius was zero. "
        "I wrote unit tests against three sample filings the customer sent, ran the export "
        "against their staging tenant Saturday morning, and walked their compliance lead "
        "through the output on a video call. We caught two field-mapping bugs together and I "
        "fixed them by Saturday evening. Sunday I ran the full 18-month export, validated the "
        "checksums against their internal ledger, and handed off the file. I also wrote a "
        "one-page runbook for the CSM in case the customer needed to re-run, and I filed a "
        "proper feature request Monday so the adapter could become a real product capability "
        "instead of a permanent special-case."
    ),
    result=(
        "Customer filed on time. The compliance lead emailed our CEO unprompted; the customer "
        "renewed for two years at a 14% uplift four weeks later, citing the weekend as the "
        "reason they trusted us with a larger contract. The feature-flagged adapter was "
        "code-reviewed properly the next sprint, generalised behind a schema-mapping config, "
        "and shipped GA two months later — three other regulated customers turned it on in the "
        "first quarter, so the one-customer fix paid for itself as a product. I learned two "
        "things: (1) the gap between 'we don't support that' and 'we can't support that' is "
        "usually a weekend, if you actually read the spec; and (2) ad-hoc help only counts as "
        "customer obsession if you also feed the fix back into the product so the next "
        "customer doesn't need a heroic on-call engineer."
    ),
    key_strengths=["Customer empathy", "Initiative", "Going beyond scope", "Productisation mindset"],
    framework_tips=[
        "Anchor the customer pain in something concrete — money, deadline, regulator, reputation",
        "Show you cleared the extraordinary work with the right people — not cowboy heroics",
        "Quantify what 'above and beyond' cost you AND what it returned to the business",
        "Close the loop by feeding the one-off fix back into the product so it scales",
    ],
    tips=[
        "Pick a story where the extraordinary effort was actually disproportionate — a weekend, a custom build, a hand-delivered escalation — not just 'I replied quickly'.",
        "Show containment: feature flag, tenant-gated, manager-aware. Going above and beyond is not the same as going around the rules.",
        "Quantify the customer outcome (renewal, NPS, retention) AND the product outcome (feature shipped, learnings).",
        "Show the productisation step — interviewers are checking that you don't romanticise heroics, you institutionalise the fix.",
    ],
    common_pitfalls=[
        "Heroic narrative with no alignment — manager and tech lead found out after the fact",
        "Above-and-beyond that was actually just 'I did my job under pressure' — no real extraordinary effort",
        "No business outcome quantified — 'the customer was happy' is not a result",
        "One-off rescue with no feedback loop into the product — next customer with the same problem still needs a hero",
    ],
    follow_up_questions=[
        "How did you decide this customer was worth a weekend — would you have done it for a smaller customer?",
        "What if your manager had said no on Friday — would you still have done it?",
        "How did you make sure the custom code didn't become permanent technical debt?",
        "Where's the line between customer obsession and unsustainable hero work for your team?",
    ],
    what_look_for=[
        "Genuine extraordinary effort, not repackaged routine work",
        "Alignment with manager and platform owners — disciplined heroics, not cowboy fixes",
        "Quantified customer AND business outcome (renewal, expansion, NPS)",
        "Productisation: the one-off was fed back so the next customer doesn't need a rescue",
    ],
    tags=["customer", "obsession", "empathy", "initiative"],
    categories=["Customer Focus", "Service", "Amazon Leadership Principles"],
)
