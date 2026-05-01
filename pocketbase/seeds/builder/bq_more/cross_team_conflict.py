"""Earn Trust — resolved conflict between two teams via shared deprecation policy."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Cross-Team Conflict — Building Bridges",
    "Tell me about a time when two teams were in conflict and you helped resolve it.",
    situation=(
        "Our platform team owned the public API gateway. The product team built on top of it. "
        "Tension had been building for two quarters: platform was shipping breaking changes on a "
        "two-week notice, and product was missing customer commitments because their integrations "
        "kept breaking. The product lead had escalated twice; the platform lead felt accused of "
        "being uncooperative. By the time I got pulled in, the two leads weren't speaking directly "
        "— everything was going through their respective directors."
    ),
    task=(
        "I was a senior engineer on neither team but had worked with both. My director asked me to "
        "see if I could mediate before it became a re-org problem. There was no formal authority — "
        "I had to earn the right to broker an agreement."
    ),
    action=(
        "I started by talking to each side separately, with one ground rule: 'I'm not here to take "
        "sides; I'm here to understand what each of you actually needs.' Platform's pain: every "
        "deprecation request from product turned into 'never deprecate this,' which prevented them "
        "from removing tech debt. Product's pain: they couldn't plan a quarter when an endpoint "
        "could vanish in 14 days. Both were right; neither was being unreasonable in isolation. I "
        "wrote up the two positions side by side as a one-pager — no editorialising, just 'here is "
        "what each team needs.' I shared it with both leads BEFORE proposing anything. Then I "
        "drafted a deprecation policy: tier endpoints by stability promise (experimental, stable, "
        "deprecated), each tier has a defined notice period (no notice / 90 days / 180 days), "
        "platform gets a quarterly 'sunset slot' to retire deprecated endpoints, product gets "
        "advance visibility via a public deprecation calendar. I ran it past both leads in "
        "separate 1:1s, took their edits, then convened a single 45-minute meeting to ratify. I "
        "kept that meeting tight — agenda was 'agree on the policy, identify owner for the "
        "calendar, set first review in 30 days.' Not a re-litigation of past grievances."
    ),
    result=(
        "The policy was adopted in that meeting with two minor edits. Six months later, the "
        "platform team had successfully sunset 11 deprecated endpoints (vs 0 in the prior year), "
        "and product hadn't missed a customer commitment to a breaking change. The two leads were "
        "talking directly again. The policy doc became the template the company used for two more "
        "platform-product boundaries. My director told me later that the most important thing I "
        "did was the side-by-side doc — naming each team's needs without judgement let both leads "
        "feel heard before any negotiation started. I learned that cross-team conflict is almost "
        "always a missing CONTRACT, not a missing apology."
    ),
    key_strengths=["Mediation", "Diplomacy", "Cross-functional thinking", "Written-contract bias"],
    framework_tips=[
        "Talk to each side SEPARATELY first; surface real needs without the other side defending",
        "Document positions side-by-side without editorialising — let the doc do the diplomacy",
        "Propose a structural fix (policy, contract) rather than a behavioural fix (be nicer)",
        "Get edits in 1:1s before convening — the joint meeting should be ratification, not negotiation",
        "Escalation is a last resort, not a first move",
    ],
    tips=[
        "Pick a story where YOU weren't on either team — credibility comes from neutrality.",
        "Show the structural fix (a written policy) — that's more durable than any one meeting.",
        "Show that both sides got something AND gave up something — symmetric trade-offs.",
        "Quantify the post-resolution outcome — endpoints retired, commitments hit.",
        "Don't make either side the villain in your retelling.",
    ],
    common_pitfalls=[
        "Picking a story where you mediated by simply 'getting them in a room' — no structural fix",
        "Taking a side in your retelling — interviewers hear it",
        "No durable artefact — just 'we talked it out'",
        "Skipping the separate-conversations step and going straight to a joint meeting",
        "Escalating early instead of trying to broker first",
    ],
    follow_up_questions=[
        "What if one of the leads had refused to engage?",
        "How did you decide what tier each endpoint belonged to?",
        "Have you mediated a conflict where neither side was being reasonable?",
        "What would you do if the policy started breaking down 6 months later?",
    ],
    what_look_for=[
        "Neutrality and earned trust from both sides",
        "Structural / contractual resolution vs interpersonal one",
        "Separate 1:1s before joint meeting",
        "Durable artefact that outlives the specific conflict",
        "Quantified post-resolution outcome",
    ],
    tags=["conflict", "cross-team", "mediation", "trust", "earn-trust"],
    categories=["Communication", "Leadership", "Amazon Leadership Principles"],
)
