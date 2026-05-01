"""Ambiguous, ill-defined problem — framing & first steps."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Ambiguous Problem — Framing and First Steps",
    "Tell me about a time you took on a project with extremely ambiguous requirements. How did you start?",
    situation=(
        "My VP forwarded me a one-line request from the CFO: 'make our checkout faster.' That was "
        "the entire ask. No metric, no target, no scope, no owner. Checkout spanned 4 services owned "
        "by 3 teams; 'faster' could mean p50 latency, p99 latency, conversion-funnel duration, or "
        "perceived speed. I had a 6-week unofficial expectation to come back with 'something concrete.'"
    ),
    task=(
        "Convert a one-line ambiguous ask into a defined problem with a metric, a baseline, a target, "
        "and a credible plan — and then ship something — without burning weeks chasing the wrong "
        "definition of 'fast.'"
    ),
    action=(
        "I refused to start coding. Week 1: I scoped the ambiguity down to a metric. I read the "
        "CFO's prior memos, talked to the support lead, and pulled the funnel analytics. The "
        "support data showed cart-abandonment spiking on the payment step; the funnel data showed "
        "p95 time-from-cart-to-confirmation was 28 seconds — long enough to lose users. I "
        "redefined 'faster' as 'reduce p95 cart-to-confirmation from 28s to under 10s,' and wrote "
        "a one-pager naming the metric, the baseline, the target, and three candidate "
        "interventions. I sent the doc to the CFO's chief of staff and to the 3 owning teams' "
        "tech leads asking: 'is this the right metric?' Two days, two sign-offs, one "
        "re-prioritisation (make it p99, not p95). Week 2: I ran a 1-week instrumentation spike "
        "to find the bottleneck. The data showed 19 of 28 seconds were spent in a synchronous "
        "fraud-check call that blocked rendering of the confirmation page. I then proposed three "
        "interventions ranked by cost: (a) make fraud-check async with a fallback (cheap, 1 "
        "engineer-week, recovers ~14s), (b) regional fraud-cache (medium, 4 engineer-weeks, "
        "recovers ~17s), (c) full pipeline rewrite (expensive, 1 quarter, recovers ~20s). I "
        "shipped (a) first to prove the framing was right; I deferred (b) and (c) until we had "
        "production data."
    ),
    result=(
        "The async fraud-check shipped in week 4. p99 cart-to-confirmation dropped from 28s to "
        "11s — within rounding distance of the 10s target. Cart-abandonment on the payment step "
        "fell 6 percentage points; the finance team estimated ~$1.2M/quarter in recovered revenue. "
        "We never built (c); the data showed (b) had diminishing returns and got de-prioritised. "
        "The one-pager became the team's 'checkout performance' charter for the next year. I "
        "learned that the first work in an ambiguous project is almost always definition, not "
        "execution — and that turning a one-liner into a metric + baseline + target + sign-off "
        "is itself the deliverable for week one."
    ),
    key_strengths=[
        "Ambiguity decomposition",
        "Metric-driven framing",
        "Stakeholder alignment",
        "Decisiveness via cheapest viable intervention",
    ],
    framework_tips=[
        "Convert the ambiguous verb ('faster', 'better') into a measurable metric with a baseline and target",
        "Spend week one on definition, not on coding",
        "Get the framing signed off in writing before executing — cheap insurance",
        "Run a short instrumentation / discovery spike before proposing interventions",
        "Rank interventions by cost; ship the cheapest first to validate the framing",
    ],
    tips=[
        "Show the explicit decomposition: ambiguous ask → metric → baseline → target → spike → interventions → ship.",
        "Quantify the framing artefacts — '28s baseline,' '10s target,' '$1.2M/quarter' — not 'we made it faster.'",
        "Show stakeholder confirmation of YOUR framing before you executed — that's how ambiguity gets disarmed.",
        "Show that you shipped the cheapest credible intervention first, not the most ambitious one.",
        "Avoid heroics; sell the structure of how you got from one line to a delivered outcome.",
    ],
    common_pitfalls=[
        "Jumping straight to a solution without defining the metric",
        "Choosing a metric without stakeholder confirmation — easy to optimise the wrong thing",
        "Letting the spike turn into a multi-month investigation",
        "Proposing the most ambitious intervention first instead of the cheapest viable one",
        "No quantified outcome — 'it felt faster' is not a result",
    ],
    follow_up_questions=[
        "What if the stakeholders had disagreed with your metric?",
        "How did you decide between fixing fraud-check vs other candidates?",
        "What would you have done if the cheapest intervention hadn't moved the metric?",
        "How do you know when 'definition' is done and execution should start?",
    ],
    what_look_for=[
        "Decomposition of an ambiguous verb into a measurable metric",
        "Explicit baseline + target + stakeholder sign-off",
        "Spike-before-build discipline",
        "Cheapest-credible-intervention bias (Bias for Action)",
        "Quantified outcome and willingness to defer the more ambitious options",
    ],
    tags=["ambiguity", "framing", "strategy", "first-principles", "bias-for-action"],
    categories=["Strategic Thinking", "Leadership", "Amazon Leadership Principles"],
)
