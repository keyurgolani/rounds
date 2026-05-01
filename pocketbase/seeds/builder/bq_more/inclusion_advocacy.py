"""BQ: Strive to Be Earth's Best Employer — Advocated for inclusion or diversity."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Best Employer — Advocated for Inclusion or Diversity",
    "Tell me about a time you advocated for inclusion or diversity.",
    situation=(
        "I was a senior engineer on a 9-person platform team. We were hiring two mid-level "
        "engineers and the recruiting partner sent over the first slate: 6 candidates, all "
        "men, all from a similar set of 3 companies. I'd seen this pattern on the previous "
        "two hires and stayed quiet; the team had grown more homogeneous each round. "
        "Separately, in our planning meetings, our newest hire — a woman who'd joined from a "
        "smaller company — would make a point and ten minutes later a senior engineer would "
        "restate it and the room would treat it as new. She'd mentioned it to me once over "
        "coffee, half-joking. I'd nodded and moved on."
    ),
    task=(
        "Two specific things I could act on: the homogeneous interview slate landing on my "
        "desk that week, and the talked-over pattern in our planning meetings. Neither was "
        "officially my problem — I wasn't the hiring manager and I wasn't the meeting owner. "
        "But I'd been quiet on both before and the pattern was getting worse, not better."
    ),
    action=(
        "On the slate: I went to the hiring manager with specific data, not a complaint. I "
        "pulled the last 18 months of slates from our ATS — 4 of 5 had been single-demographic. "
        "I proposed three concrete changes: (1) require at least 2 candidates from "
        "underrepresented backgrounds on every slate before scheduling onsites, (2) expand "
        "sourcing beyond the 3 'usual companies' to include 2 specific orgs with strong "
        "underrepresented engineer pipelines I'd researched, (3) add a structured rubric to "
        "the loop so we'd evaluate the same skills the same way for everyone. I framed it as "
        "'we will make better hires' — not as a quota. The hiring manager pushed back on (1) "
        "as a 'delay'; I countered with the previous slates' time-to-hire and showed the "
        "delay would be ~5 days, not weeks. He agreed to all three on a 6-month trial.\n\n"
        "On the meeting pattern: I didn't want to put the affected engineer on the spot, so "
        "I did two things. First, I started doing 'amplification' — when she made a point "
        "and it got skipped, I'd say 'I want to come back to what Priya said about X — that "
        "matters because…' and credit her by name. I asked her privately first whether that "
        "would help or feel patronising; she said it would help if I did it sparingly and "
        "credited her, not 'someone earlier.' Second, I proposed to the meeting owner that "
        "we adopt a 'written first 5 minutes' format for planning — everyone writes their "
        "open questions in the doc before discussion. He agreed to try it for 4 weeks."
    ),
    result=(
        "On hiring: of the next 4 slates, 3 met the diverse-slate bar. We hired one engineer "
        "from an underrepresented background and one from the 'usual' pool — both strong. "
        "Six months later the hiring manager extended the trial indefinitely; he told me the "
        "structured rubric had also caught two cases where we'd have made bad hires on the "
        "old gut-feel loop. On meetings: within two months Priya was speaking ~3x as much in "
        "planning per my rough count, and 'restate-without-credit' was visibly rarer. She "
        "later told me the amplification mattered less than the written-first format — the "
        "format leveled the playing field structurally; the amplification was a stopgap. I "
        "learned that advocacy lands when you bring specific, concrete proposals tied to "
        "outcomes (better hires, better decisions) rather than abstract appeals; and that "
        "the affected person is the right judge of what kind of help actually helps."
    ),
    key_strengths=[
        "Concrete proposals over abstract advocacy",
        "Data-driven framing",
        "Asking the affected person what helps",
        "Structural fixes over personality fixes",
    ],
    framework_tips=[
        "Frame the change in outcome terms (better hires, better decisions), not optics",
        "Bring specific data — slate composition, time-to-hire, participation counts",
        "Ask the affected person what kind of help would actually help",
        "Prefer structural changes (rubrics, written-first formats) to behavioural reminders",
    ],
    tips=[
        "Pick a story with a tangible action and a measurable outcome — not 'I cared about diversity.'",
        "Show you got buy-in from the people who actually owned the process (hiring manager, meeting owner).",
        "Credit the affected person; don't claim a saviour role.",
        "Distinguish stopgap behaviours (amplification) from durable structural changes (rubric, written-first).",
    ],
    common_pitfalls=[
        "Saviour narrative — 'I championed her'",
        "Vague advocacy without a specific change implemented",
        "Acting on behalf of someone without asking them what helps",
        "Framing as quota / optics rather than outcomes",
    ],
    follow_up_questions=[
        "How did you handle pushback from the hiring manager on the slate requirement?",
        "What if Priya had asked you NOT to amplify her in meetings?",
        "How do you sustain these changes when you move teams or new people join?",
    ],
    what_look_for=[
        "Concrete actions and measurable outcomes",
        "Buy-in from process owners, not unilateral fixes",
        "Affected-person agency (asked what helps)",
        "Structural over behavioural fixes",
    ],
    tags=["inclusion", "diversity", "earn-trust", "empathy"],
    categories=["People Skills", "Inclusivity", "Amazon Leadership Principles"],
)
