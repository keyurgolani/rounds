"""BQ: Disagreed with a peer engineer — resolved through data."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Disagreed With Peer — Resolving Through Data",
    "Tell me about a time you disagreed with a peer engineer about an approach. How did you resolve it?",
    situation=(
        "We were designing a cache layer for a high-read product catalog service serving "
        "~40K req/s. A peer engineer — equally senior, equally opinionated — wanted to use "
        "DynamoDB with DAX. I wanted to use Redis (ElastiCache). Both of us had built "
        "production systems on our preferred stack and both of us had a strong prior. We "
        "had a design review in 5 days and our manager asked us to come back with one "
        "recommendation, not two."
    ),
    task=(
        "Land on a single recommendation we both could commit to, without it devolving "
        "into a status battle or a senior-most-engineer-wins outcome. The 'right' answer "
        "wasn't obvious from first principles for our specific workload."
    ),
    action=(
        "First I separated the disagreement into the parts that were factual (latency, "
        "cost, ops burden) from the parts that were preference (familiarity, taste). "
        "Then I went to him directly: 'we both have priors here; let's let the workload "
        "tell us. Two days, one prototype each, same load profile, same SLOs, then we "
        "pick.' He agreed — partly because the framing didn't position either of us as "
        "wrong upfront. We co-wrote a one-pager naming the decision criteria BEFORE "
        "running the test: p99 read latency under 5ms, cost per million reads, ops "
        "complexity (1-5 score), failure-mode story. He prototyped DynamoDB+DAX; I "
        "prototyped Redis. We shared a synthetic load script so the inputs were "
        "identical. After 2 days the data was clear: Redis hit p99=1.8ms vs DAX p99=4.2ms "
        "for our access pattern (small hot keys, very high read ratio); cost was within "
        "15%; ops was a wash because we already ran ElastiCache for another service. I "
        "wrote up the result and explicitly listed where DynamoDB+DAX would have won "
        "(write-heavy workloads, multi-region replication needs) so he could see I "
        "wasn't burying his case."
    ),
    result=(
        "We jointly recommended Redis at the design review; the doc had both names on "
        "it. The cache shipped 6 weeks later and held p99 under 2ms in production. More "
        "importantly, this became the team's pattern for disagreements between peers — "
        "agree on criteria first, prototype small, let data decide. He and I have "
        "since paired on three more designs and explicitly use 'do we need a bake-off?' "
        "as a tiebreaker. I learned that peer disagreements get poisonous when ego "
        "fuses to position; the way out is to make the criteria the thing you're loyal "
        "to, not the answer."
    ),
    key_strengths=["Data-driven thinking", "Collaboration", "Ego-light", "Structured decision-making"],
    framework_tips=[
        "Separate factual disagreement from taste disagreement before arguing",
        "Agree on decision criteria BEFORE running the experiment",
        "Run a small, time-boxed bake-off rather than debate further",
        "Name where the OTHER side would have won — keeps the relationship intact",
    ],
    tips=[
        "Pick a real technical disagreement with substance — not a 'we both agreed quickly' story.",
        "Show that you proposed the resolution mechanism (the bake-off), not just the answer.",
        "Quantify both prototypes' results — that's the credibility.",
        "Credit the peer's case explicitly; this is what 'ego-light' actually looks like.",
    ],
    common_pitfalls=[
        "Framing the peer as wrong or unreasonable — the interviewer hears it",
        "No quantitative resolution — just 'we talked it out'",
        "Skipping the criteria-first step — looks like post-hoc justification",
        "Hero narrative where you 'won' the argument",
    ],
    follow_up_questions=[
        "What if the bake-off had been inconclusive?",
        "How is this different from disagreeing with a manager?",
        "Have you ever lost a peer bake-off? What did you do?",
    ],
    what_look_for=[
        "Criteria-first thinking",
        "Willingness to run a falsifying experiment",
        "Crediting the other side",
        "Durable relationship with the peer afterward",
    ],
    tags=["disagreement", "peer", "data", "resolution"],
    categories=["Collaboration", "Decision Making", "Amazon Leadership Principles"],
)
