"""Behavioral question: Tight deadline — Deliver Results / Bias for Action."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Tight Deadline — Trade-offs Under Pressure",
    "Tell me about a time you had to deliver something under a very tight deadline. How did you approach the trade-offs?",
    situation=(
        "Our company's annual customer-advisory-board summit was 5 weeks out, and the CEO had "
        "promised the board a live demo of a new 'unified analytics' surface that pulled together "
        "three previously siloed dashboards. The deadline was fixed — 30 board members and 6 press "
        "analysts would be in the room. The original engineering estimate from the previous PM was "
        "10 engineer-weeks. We had 2 engineers (me + a mid-level) for 5 calendar weeks — about 8 "
        "engineer-weeks of capacity, with 1 week reserved for hardening and rehearsal."
    ),
    task=(
        "I was the tech lead and the only person accountable for the demo working end-to-end. I had "
        "to either reduce scope to fit ~7 weeks of executable work, or pull in help and risk a "
        "messy integration close to the wire."
    ),
    action=(
        "I started with a written prioritisation pass using MoSCoW. MUST: the three dashboards "
        "rendering inside one shell, single sign-on, and the headline KPI tile the CEO had "
        "specifically mentioned in the keynote draft (~5 engineer-weeks). SHOULD: cross-dashboard "
        "filtering, drill-down navigation (~3 weeks). COULD: theme polish, export-to-PDF, saved "
        "views (~2 weeks). I shared the MoSCoW list with the CEO's chief of staff, the product VP, "
        "and the design lead in a 30-minute meeting and got explicit sign-off on cutting the COULD "
        "tier and deferring SHOULD-tier filtering to a 'demo-only' mocked version (real data, but "
        "filtering UI behind a feature flag). I parallelised: I owned the shell + SSO + KPI tile; "
        "the mid-level owned dashboard embedding. Daily 10-minute standups; any blocker over 4 "
        "hours escalated to me. At the start of week 3 I ran an explicit risk review — we were on "
        "track for MUST but the embedding was flakier than expected on Safari (the CEO's browser). "
        "I rerouted us to a Chromium-based demo laptop with the CEO's chief of staff's blessing "
        "rather than burn 4 days on Safari quirks. Week 4 we did a full dry-run with the CEO's "
        "team in the actual room with the actual projector; we found 3 paper-cuts (slow first "
        "load, a colour-contrast issue, a stale label) and fixed all three by Friday. Week 5 was "
        "rehearsal-only — no new code."
    ),
    result=(
        "Demo went off without a glitch. The CEO got a standing 'huh, finally' from one board "
        "member who'd been complaining about the dashboard sprawl for two years. Three of the six "
        "press analysts referenced the unified surface in their write-ups. The deferred SHOULD-"
        "tier filtering shipped 4 weeks later as a real (non-mocked) feature; the COULD-tier "
        "polish never shipped because usage data showed nobody asked for it. My VP later said the "
        "win was 'the absence of fire-drills the week before' — i.e., the early MoSCoW sign-off "
        "and the week-3 risk review took the panic out of the runway. I learned that under tight "
        "deadlines the lever isn't 'work harder,' it's 'cut scope earlier and in writing, with "
        "stakeholders who can't later say they didn't agree.'"
    ),
    key_strengths=[
        "Prioritization",
        "Communication",
        "Bias for Action",
        "Trade-off thinking",
        "Stakeholder management",
    ],
    framework_tips=[
        "Pick a single prioritisation framework (MoSCoW / RICE) and apply it in writing",
        "Get explicit stakeholder sign-off on cuts BEFORE you build, not after you slip",
        "Schedule a mid-project risk review — not 'as needed,' a calendar event",
        "Reserve the last ~20% of calendar time for hardening + rehearsal, not new code",
    ],
    tips=[
        "Show the explicit prioritisation framework — interviewers want the structure, not the heroics.",
        "Quantify the deadline stakes (audience, dollars, reputation) so the trade-offs feel real.",
        "Name the cuts specifically — 'we cut export-to-PDF and theme polish,' not 'we cut scope.'",
        "Show the communication artefact — meeting, doc, sign-off — that protects everyone if questions come up later.",
        "Distinguish 'demo-quality' from 'production-quality' if you used mocks; honesty about that is a strength.",
    ],
    common_pitfalls=[
        "Heroics narrative — '80-hour weeks got us there'",
        "Vague 'we cut scope' without naming what or who signed off",
        "No mid-project checkpoint — 'we just kept going'",
        "Over-promising and shipping a demo that breaks live",
        "No reserved hardening / rehearsal window",
    ],
    follow_up_questions=[
        "What if a stakeholder had refused to sign off on the cuts?",
        "How did you choose between MoSCoW and RICE for this project?",
        "What would you have done if the week-3 risk review had shown you were 2 weeks behind, not on track?",
        "How did you manage your mid-level engineer's stress during the run-up?",
        "Have you ever missed a deadline like this? What happened?",
    ],
    what_look_for=[
        "Explicit prioritisation framework applied in writing",
        "Stakeholder sign-off captured before cuts, not after slips",
        "Proactive risk-review checkpoint vs reactive panic",
        "Trade-offs named specifically (what was cut, what was deferred, what was mocked)",
        "Calm, planned execution rather than heroic overtime",
    ],
    tags=["deadline", "priority", "trade-off", "scoping", "deliver-results", "bias-for-action"],
    categories=[
        "Execution",
        "Time Management",
        "Amazon Leadership Principles",
    ],
)
