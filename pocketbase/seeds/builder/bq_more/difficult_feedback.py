"""BQ extra: Insist on Highest Standards — giving difficult feedback."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Difficult Feedback — Direct With Care",
    "Tell me about a time you had to give difficult feedback to a colleague.",
    situation=(
        "A senior peer on my team — 4 years more tenured than me — proposed a redesign for our "
        "notification service. His doc introduced a new in-house pub/sub layer, a custom retry "
        "DSL, and a bespoke schema registry. Our actual problem was a 2% delivery-failure rate "
        "from one misconfigured queue. The doc had been circulating for a week with vague "
        "'looks good' comments; nobody wanted to push back on him because he was respected and "
        "had recently lost a promotion cycle."
    ),
    task=(
        "I was a peer engineer, not his lead. I had to tell him the design was "
        "overcomplicated for the actual problem, without it landing as 'junior dunks on senior' "
        "or as a hit on someone already feeling bruised."
    ),
    action=(
        "I prepared first. I re-read his doc twice and wrote down the parts I genuinely agreed "
        "with (the schema-registry idea was good for a future need) and the parts I thought were "
        "scope creep. I framed using SBI — Situation, Behaviour, Impact — privately, not in the "
        "doc thread. I asked him for a 1:1 coffee, not a meeting on the calendar with a loaded "
        "title. I led with: 'I want to give you direct feedback on the notifications doc — is "
        "now a good time?' Then: 'The doc proposes three new subsystems. The delivery-failure "
        "data points to one misconfigured queue. I'm worried we'll spend a quarter building "
        "infrastructure that doesn't address the metric we're trying to move.' I stopped and "
        "listened. He pushed back — said the new layer would prevent future classes of bugs. I "
        "acknowledged that, then asked: 'if we shipped just the queue fix, what would still be "
        "broken in 6 months?' He paused, said 'honestly, probably nothing urgent.' I offered to "
        "co-write a smaller doc with him that kept the schema-registry idea as a Phase 2. I "
        "followed up two days later to check how he was sitting with it."
    ),
    result=(
        "He revised the doc himself the next day, scoped it to the queue fix plus a thin "
        "schema-registry stub. The fix shipped in 3 weeks; failure rate dropped from 2% to "
        "0.05%. The schema-registry Phase 2 was deprioritised after data showed the queue fix "
        "had solved 95% of the pain. More importantly, our working relationship got stronger — "
        "he started looping me in early on designs because, in his words, 'you'll tell me when "
        "I'm overbuilding.' I learned that difficult feedback lands when you (1) prepare the "
        "evidence, (2) deliver privately and quickly rather than letting it fester in doc "
        "threads, (3) lead with what you agree with, and (4) ask questions instead of issuing "
        "verdicts. The relationship is the thing you're protecting — not your comfort."
    ),
    key_strengths=[
        "Candor",
        "Empathy",
        "Long-term relationship thinking",
        "SBI framing",
        "Question-led delivery",
    ],
    framework_tips=[
        "Use SBI (Situation–Behaviour–Impact) — concrete, not characterological",
        "Deliver privately and promptly; don't let it fester in public threads",
        "Lead with what you genuinely agree with — establishes the goodwill the hard part needs",
        "Ask questions ('what would still be broken in 6 months?') instead of issuing verdicts",
        "Follow up — feedback isn't a one-shot delivery, it's a small relationship investment",
    ],
    tips=[
        "Pick a story where the feedback was genuinely uncomfortable — not 'I told a junior to add tests.'",
        "Show preparation — what you wrote down, how you framed it.",
        "Show the receiver's reaction, including pushback. A no-pushback story is suspicious.",
        "Show concrete behaviour change AND a preserved (or improved) relationship.",
        "Avoid hero framing — you're helping a colleague, not teaching them a lesson.",
    ],
    common_pitfalls=[
        "Sandwich feedback (praise–criticism–praise) that buries the actual point",
        "Delivering in public — doc thread, group Slack — instead of 1:1",
        "Characterological framing ('you're overengineering') instead of behavioural ('this doc proposes three new subsystems')",
        "No follow-up — feedback delivered and abandoned",
        "Making it about you ('I had to tell him') vs about the work and the colleague",
    ],
    follow_up_questions=[
        "What was his initial reaction? How did you handle it?",
        "What if he had pushed back hard or been defensive?",
        "Have you ever given feedback that landed badly? What did you do?",
        "How do you decide whether to give feedback at all vs let it go?",
        "How do you give feedback upward — to a manager or skip-level?",
    ],
    what_look_for=[
        "Direct delivery without harshness — 'direct with care' calibration",
        "Preparation and structure (SBI or equivalent)",
        "Private, timely, evidence-based",
        "Listening for the receiver's response, not lecturing",
        "Preserved or improved relationship after",
    ],
    tags=["feedback", "candor", "peer", "conflict", "highest-standards"],
    categories=["Communication", "People Skills", "Amazon Leadership Principles"],
)
