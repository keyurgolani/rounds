"""BQ extra: Hire and Develop the Best — tough hiring decision (bar-raising).

Distinct from LP-06 (mentorship). This focuses on a hiring/no-hire trade-off
where the candidate looked strong on paper but had a specific concern, and
the interviewer pushed back against schedule pressure to hire fast.
"""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Tough Hiring Call — Raising the Bar",
    "Tell me about a tough hiring decision you made. What was the trade-off and how did you handle it?",
    situation=(
        "We were 4 weeks into a 6-week hiring sprint for a senior backend role; the team "
        "was burning out covering the open headcount. A candidate came through who was "
        "technically strong — clean coding round, solid system design — but in my "
        "behavioural loop I'd flagged communication concerns: he interrupted me twice, "
        "talked over the hypothetical 'junior engineer' in a mentoring scenario, and "
        "framed two past conflicts as 'the other person didn't understand.' The hiring "
        "manager wanted to extend an offer the next morning."
    ),
    task=(
        "I was the bar-raiser on the loop. I had to decide whether to flag a no-hire, "
        "weighing my behavioural signal against a tired team's real need for headcount "
        "and a hiring manager who already had the offer letter drafted."
    ),
    action=(
        "I went back to my interview notes the same evening and pulled the verbatim "
        "quotes — three specific moments, with timestamps and what I'd asked. I "
        "circulated those to the loop before the debrief instead of waiting for the "
        "room. In the debrief I led with the data: 'I'm leaning no-hire on "
        "communication; here are three quotes — tell me if I'm reading them wrong.' I "
        "explicitly invited disconfirmation. Two interviewers had noticed similar "
        "moments but had written them off as nerves. I named the trade-off out loud: "
        "'we're tired, the pipeline is thin, and this candidate clears the technical "
        "bar — but if we hire someone who steamrolls juniors, we'll spend 12 months "
        "managing it and the team gets MORE tired, not less.' I proposed a concrete "
        "alternative: extend the search by 3 weeks, and in parallel re-engage two "
        "earlier candidates we'd lukewarm-passed on. The hiring manager pushed back "
        "hard; I held the line on the no-hire but acknowledged his cost ('if we don't "
        "find someone in 3 weeks, I'll own that with you'). The bar-raiser veto stuck."
    ),
    result=(
        "We passed on the candidate. Three weeks later we hired one of the re-engaged "
        "candidates — slightly weaker on system design, materially stronger on "
        "collaboration — who ramped in 2 months and is now mentoring two juniors on "
        "the team. Six months out, I learned through a backchannel that the original "
        "candidate had been let go from the company that did hire him for repeated "
        "peer-conflict issues. The hiring manager later told me he'd been wrong to "
        "push for speed; we now run an explicit 'communication evidence' rubric in our "
        "debriefs. I learned that schedule pressure is the loudest voice in the room "
        "and the bar-raiser's job is to make the quieter signal — the specific quote, "
        "the specific moment — louder than the pressure."
    ),
    key_strengths=[
        "Bar Raising",
        "Long-term thinking",
        "Patience under schedule pressure",
        "Evidence-based debrief",
    ],
    framework_tips=[
        "Lead the debrief with specific quotes and moments, not adjectives",
        "Name the trade-off explicitly — 'tired team vs 12 months of management overhead'",
        "Invite disconfirmation before stating your position",
        "Propose a concrete alternative, not just a no",
        "Own the cost of holding the line ('I'll find another candidate with you')",
    ],
    tips=[
        "Pick a story where the trade-off was real — strong technical, real concern, real schedule pressure.",
        "Quote yourself and the candidate verbatim if you can — 'he said X' beats 'he seemed dismissive'.",
        "Show you sought disconfirmation, not just confirmation, of your own read.",
        "Show you owned the cost of the no-hire — not 'I said no and walked away'.",
        "Avoid hindsight-as-evidence ('it turned out he was bad at his next job') — the call must be defensible without that.",
    ],
    common_pitfalls=[
        "Vague concerns ('cultural fit', 'gut feeling') without specific evidence",
        "Framing the story as 'I was right and they were wrong' — collaboration disappears",
        "Folding under schedule pressure and rationalising it as compromise",
        "Picking a story where the candidate was clearly bad — that's not a 'tough' call",
        "No proposed alternative — bar-raiser as a brake, not a partner",
    ],
    follow_up_questions=[
        "What if the hiring manager had overruled you?",
        "How do you distinguish 'nerves in an interview' from a real behavioural signal?",
        "Have you ever been wrong about a no-hire?",
        "How do you debrief when you're the most senior voice in the room and might bias others?",
        "What evidence would have changed your mind in this case?",
    ],
    what_look_for=[
        "Specific evidence (quotes, moments) over adjectives",
        "Active disconfirmation-seeking in the debrief",
        "Long-term team-cost framing vs short-term headcount pressure",
        "Constructive alternatives, not just opposition",
        "Calibration — willingness to acknowledge what would have changed the call",
    ],
    tags=["hiring", "bar-raise", "talent", "calibration"],
    categories=["Talent", "Leadership", "Amazon Leadership Principles"],
)
