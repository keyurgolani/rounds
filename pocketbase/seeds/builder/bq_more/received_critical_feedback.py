"""BQ extra: Learn and Be Curious — receiving critical feedback and turning it into growth."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Received Critical Feedback — Turning It Into Growth",
    "Tell me about a time you received critical feedback. How did you respond?",
    situation=(
        "Six months into my tech-lead role, my skip-level manager pulled me into a 1:1 after "
        "observing a few of our design reviews. His feedback was blunt: 'You're too quiet in "
        "design reviews. You let other people's framing carry, and when you do speak it's at "
        "the end after the decision has already drifted. People can't tell what you actually "
        "think — and that's a problem for a tech lead.' It stung because I'd thought I was "
        "being thoughtful by listening first; what he saw was someone hedging."
    ),
    task=(
        "Decide whether the feedback was right, then — if it was — change the underlying "
        "behaviour, not just the surface symptom. Avoid the trap of nodding politely and "
        "doing nothing different by Monday."
    ),
    action=(
        "First, I sat with it for a day instead of replying right away — the defensive 'but I "
        "was listening' rebuttal was loud in my head and I didn't trust it. The next morning "
        "I went back through the last 6 design-review docs and timestamped my comments. The "
        "pattern was undeniable: I'd commented on 4 of 6, always in the last third of the "
        "thread, and never on the most contested point. He was right. Then I designed a "
        "deliberate practice rather than a vague resolution. Concretely: (1) for every design "
        "doc that crossed my desk, I would identify the single most controversial decision "
        "before the meeting and write down my position with reasoning; (2) in the meeting I "
        "would speak first on that point, not last — even if I was wrong, I'd be wrong on "
        "record; (3) I added a 5-minute pre-meeting prep block to my calendar so I couldn't "
        "skip the prep step. I told my skip-level the plan and asked him to call out — "
        "privately — any review where he saw me regress. I also told my manager so a second "
        "person was watching. For the first month it felt unnatural; my first 'speak first' "
        "comment on a queueing design was actually wrong, and a senior engineer corrected me "
        "in front of the room. I thanked her publicly, used it as the example for the rest of "
        "the meeting, and kept going."
    ),
    result=(
        "Within two months my skip-level commented unprompted that I was 'showing up' in "
        "reviews; within four, two peer engineers told me they now waited for my read on "
        "contested points before forming their own. The 'wrong on record' moment turned out "
        "to be the unlock — once the team saw I'd take a real position and update publicly, "
        "the reviews themselves got sharper because nobody was hedging anymore. Six months "
        "later I was asked to facilitate the org-wide architecture review forum, partly "
        "because of that shift. The deeper lesson: my initial defensive reaction was the "
        "signal, not the noise — the parts of feedback I most want to dismiss are usually "
        "the parts that have a kernel of truth I haven't faced. And vague resolutions ('I'll "
        "speak up more') don't change behaviour; specific mechanics ('speak first on the most "
        "controversial point, with prep on the calendar') do."
    ),
    key_strengths=[
        "Self-awareness",
        "Coachability",
        "Maturity",
        "Behaviour change via mechanism, not willpower",
        "Public accountability",
    ],
    framework_tips=[
        "Sit with the feedback for a day before responding — the defensive reaction fades, the signal stays",
        "Verify it with evidence (re-read the artefacts, count the data points) — don't take or reject feedback on vibes",
        "Translate vague resolutions into concrete mechanics with calendar / checklist anchors",
        "Recruit a witness — tell the giver and one other person your plan so the change is observed, not just felt",
        "Treat the first public failure of the new behaviour as proof it's working, not as a setback",
    ],
    tips=[
        "Pick feedback that genuinely stung — if you 'instantly knew it was right', it wasn't critical, it was confirming.",
        "Show the initial defensive reaction honestly. Interviewers trust the story more when the human reaction is in it.",
        "Show how you VERIFIED the feedback (data, artefacts, second opinion) — not just 'I decided he was right.'",
        "Translate the change into specific mechanics, not vague intent ('I'll be more X'). A calendar block beats a resolution.",
        "Show a measurable change in behaviour AND that the giver / others noticed — feedback received in private but invisible afterward isn't a story.",
    ],
    common_pitfalls=[
        "Picking flattering 'feedback' ('I was told I take on too much') — that's not critical, it's a humblebrag",
        "Skipping the defensive reaction — interviewers know it was there; pretending otherwise reads as low self-awareness",
        "Vague behaviour change ('I started speaking up more') with no concrete mechanism or evidence",
        "Not closing the loop with the feedback giver — they don't know their input mattered",
        "Treating the feedback as a one-time fix instead of a sustained habit",
        "Making it about the giver's delivery ('the way they said it was harsh') rather than the content",
    ],
    follow_up_questions=[
        "What was your very first reaction when you heard it?",
        "Did you push back at any point — and if so, on what?",
        "How did you decide the feedback was right rather than dismissing it?",
        "What would you have done if, after investigating, you'd concluded the feedback was wrong?",
        "Has anyone given you similar feedback since? What did that tell you?",
        "Have you used what you learned to give critical feedback to someone else?",
    ],
    what_look_for=[
        "Genuine receptiveness vs performative acceptance",
        "Evidence-based verification of the feedback, not vibes",
        "Concrete behaviour change with a mechanism, not a resolution",
        "Sustained change visible to the giver and others",
        "Maturity around the initial defensive reaction — named, not hidden",
        "A meta-lesson about how the candidate now relates to feedback in general",
    ],
    tags=["feedback", "growth", "self-awareness", "learning", "coachability"],
    categories=["Self-Improvement", "Coachability", "Amazon Leadership Principles"],
)
