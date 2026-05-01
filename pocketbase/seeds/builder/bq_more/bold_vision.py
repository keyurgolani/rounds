"""Think Big — proposed a bold long-term vision (event-driven services).

Story: pitched moving from a monolith to event-driven services to unlock
multiple cross-team blockers; built the foundational eventing layer in a
hack week and got 3 teams adopting before formal roadmap approval."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Bold Vision — Thinking Beyond the Quarter",
    "Tell me about a time you proposed something that went beyond your team's normal scope.",
    situation=(
        "Our platform was a 7-year-old monolith. Every team had at least one quarterly "
        "initiative blocked on it: the orders team needed async fan-out for refunds, the "
        "notifications team was polling our DB every 30s to detect changes, and analytics "
        "was reverse-engineering writes from binlogs. Each team had a one-quarter workaround "
        "on the books. None of them addressed the shared root cause: we had no event "
        "backbone, so every cross-team interaction was a synchronous REST call or a polling "
        "loop. I'd watched 4 quarters of these patches accumulate."
    ),
    task=(
        "Nobody owned 'event infrastructure' — it was nobody's quarterly goal. But the "
        "compounded cost across teams was in the multi-quarter range, and the workarounds "
        "were making the monolith harder to ever decompose. I wanted to propose a "
        "multi-quarter, multi-team shift to event-driven services, starting with a thin "
        "eventing layer that would unblock the immediate 3 teams."
    ),
    action=(
        "I started with a 6-page vision doc: current state (the 4 stuck initiatives with "
        "their team-quarter cost), proposed end state (event backbone with a small set of "
        "well-defined topics, services emitting events, the monolith as one of many "
        "publishers/subscribers), and a phased path — pilot → 3-team adoption → broader "
        "roadmap. I deliberately did NOT ask for headcount in the doc; I asked for "
        "permission to prototype. Over a hack week I built the foundational layer: a thin "
        "Kafka wrapper with schema-registry integration, a publisher SDK, and one reference "
        "consumer. I made it work for a real use case end-to-end (refund fan-out for the "
        "orders team) so the demo wasn't a toy. Then I went door-to-door: I showed the "
        "prototype to the orders, notifications, and analytics tech leads, and offered to "
        "pair with each of them for half a day to wire up their first event. All three "
        "agreed. Within 6 weeks, the 3 teams had production traffic flowing through the "
        "eventing layer — not because of a roadmap mandate but because it solved their "
        "actual problem cheaper than their workaround. THEN I went back to my director and "
        "the architecture review board with 'here's the vision, here's the prototype, here "
        "are the 3 teams already on it, here's what formal investment unlocks.' I named "
        "the risks honestly: schema drift, dual-write inconsistency during migration, and "
        "the operational burden of running Kafka well. I proposed a dedicated 4-engineer "
        "platform team for two quarters to harden it."
    ),
    result=(
        "The architecture review board approved the platform team. Over the following year, "
        "the eventing layer became the default integration pattern — by Q4, 11 services "
        "were publishing or consuming, and 3 of the originally stuck initiatives had "
        "shipped. The notifications team retired its polling loop, cutting 40% off our "
        "primary DB read load. Two new services that quarter were built event-native from "
        "day one — they couldn't have existed in the old monolith-first world without "
        "another quarter of plumbing. Six months later the eventing layer was cited in our "
        "architecture strategy doc as 'the substrate for service decomposition.' I learned "
        "that bold visions land when you do the smallest credible thing first, get other "
        "teams committed before you ask leadership for headcount, and present the "
        "investment case as 'fund what's already working' rather than 'fund my idea.'"
    ),
    key_strengths=[
        "Vision",
        "Persuasion",
        "Patience for long-term",
        "Prototype-driven advocacy",
        "Cross-team coalition building",
    ],
    framework_tips=[
        "Anchor the vision in compounded current pain — quantify across teams, not just yours",
        "Ship a credible prototype before you ask for headcount — concrete beats abstract",
        "Build the coalition (other teams adopting) BEFORE you ask leadership to formalise",
        "Phase the ask: prototype → adoption → formal investment, not 'fund my vision' up front",
        "Name the risks before leadership has to ask",
    ],
    tips=[
        "'Bold' should mean multi-quarter / multi-team, not just 'a bigger feature.'",
        "Quantify the status quo cost in dollars or engineer-quarters — vision without cost is wishful thinking.",
        "Lead with the prototype and the early adopters, not the slide deck.",
        "Show the patience — early adoption took weeks, formal approval took longer; you didn't bail when it was slow.",
        "Credit the early-adopter teams who took the risk with you.",
    ],
    common_pitfalls=[
        "Vision without a working prototype — leadership can't sanity-check the cost",
        "Asking for headcount up front instead of proving traction first",
        "Going rogue — building infra without buy-in from would-be adopters",
        "Not naming the risks (schema drift, operational burden, migration cost)",
        "Hero narrative — 'I single-handedly modernised the platform'",
        "No quantified impact at the end (just 'it became standard')",
    ],
    follow_up_questions=[
        "What if the first adopting team had hit a serious bug in the prototype?",
        "How did you decide which 3 teams to approach first?",
        "What if leadership had said no to formal investment after the pilot worked?",
        "What did you cut from the original vision to keep the prototype small?",
        "How did you handle the engineers who thought event-driven was over-engineering?",
    ],
    what_look_for=[
        "Multi-quarter / multi-team scope (real 'big')",
        "Concrete prototype before formal ask",
        "Coalition built before headcount requested",
        "Risk transparency",
        "Patience through the slow institutional approval cycle",
        "Quantified long-term impact",
    ],
    tags=["think-big", "vision", "strategy", "ambitious"],
    categories=["Strategic Thinking", "Innovation", "Amazon Leadership Principles"],
)
