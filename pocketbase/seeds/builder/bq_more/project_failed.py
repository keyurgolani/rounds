from builder.bq_questions import _bq

PAYLOAD = _bq(
    "Failed Project — Learning From Setback",
    "Tell me about a time when a project you led failed. What happened and what did you learn?",
    situation=(
        "I led a 6-month effort to build an AI-powered 'smart suggestions' panel inside our B2B "
        "analytics product. Leadership had committed the feature to three enterprise customers in "
        "renewal conversations, the eng investment was ~$480K, and we were tracking it as a Q3 OKR. "
        "I owned the spec, the architecture, and the rollout plan. The premise was that ML-ranked "
        "next-best-actions would lift engagement on the dashboard."
    ),
    task=(
        "I was tech lead. My job was to scope, deliver, and validate impact. I was also the person "
        "who originally pitched the idea, which made me anchored to it more than I should have been."
    ),
    action=(
        "I shipped on time. The model worked, latency was under 200ms, the panel rendered cleanly. "
        "We ran an A/B test for 4 weeks. Adoption was 3.1% of weekly active users, and of those, "
        "the median user clicked one suggestion and never came back. I pushed for a second iteration "
        "with re-ranked suggestions; that bumped adoption to 3.4% and stalled. At that point I "
        "stopped defending the project and ran 12 customer interviews I should have run before "
        "writing a line of code. The pattern was clear: our users came to the dashboard with a "
        "specific question already in mind, so a suggestion panel was answering a question nobody "
        "was asking. I wrote a kill memo with the data, recommended sunsetting, and presented it to "
        "the VP. We turned the feature off, repurposed the ranking infrastructure for a search "
        "relevance project that did have demand, and I wrote a public retro."
    ),
    result=(
        "The feature was killed after 5 months in production. ~$480K of eng time produced no "
        "measurable lift; ~$140K of the underlying ranking infrastructure was salvaged for search "
        "relevance, which later moved a real metric (zero-result searches down 38%). The three "
        "renewal customers were unhappy but renewed after we replaced the commitment with a "
        "concrete export feature they actually wanted. Personally, I changed two behaviours: (1) "
        "I now require a written 'why won't this work' doc and at least 8 customer conversations "
        "before any feature over 4 weeks of eng; (2) I set adoption kill-criteria up front, in "
        "writing, before launch — so the decision to stop is pre-committed and not a debate when "
        "ego is on the line."
    ),
    key_strengths=["Self-awareness", "Ownership", "Continuous learning", "Intellectual honesty"],
    framework_tips=[
        "Name the failure plainly — don't dress it up as 'a learning opportunity'",
        "Quantify the cost: dollars, time, opportunity",
        "Own your specific contribution to the failure, not the team's",
        "End with the concrete behaviour change, not a generic platitude",
    ],
    tips=[
        "Pick a real failure with real cost, not a near-miss that worked out anyway.",
        "Use 'I' for the mistakes, not 'we' — ownership shows up in pronouns.",
        "Show the moment you recognised it was failing, not just the postmortem.",
        "The behaviour change at the end has to be specific and testable, not 'I learned to listen more.'",
    ],
    common_pitfalls=[
        "Choosing a failure that wasn't really your fault (blaming the team or external factors)",
        "Skipping the cost — failures that didn't cost anything aren't failures",
        "Vague lessons like 'communication is important' instead of a concrete process change",
        "Defending the original decision instead of acknowledging the misjudgment",
    ],
    follow_up_questions=[
        "At what point did you realise the project was going to fail, and what did you do in the gap before you acted?",
        "How did you communicate the failure to leadership and to the customers who'd been promised the feature?",
        "What signal would have told you earlier that this was the wrong bet?",
        "Have you applied the lessons since, and to what specific decision?",
    ],
    what_look_for=[
        "Honest ownership of the specific decision that led to the failure",
        "Quantified cost — money, time, customer trust",
        "Recognition signal: how they noticed it was failing and how long they waited",
        "A concrete, testable behaviour change actually applied to later work",
    ],
    tags=["failure", "learning", "ownership", "resilience"],
    categories=["Self-Awareness", "Growth", "Amazon Leadership Principles"],
)
