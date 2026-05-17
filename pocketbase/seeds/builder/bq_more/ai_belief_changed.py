"""BQ: AI belief you held a year ago that you no longer hold."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "AI Belief You Changed in the Last Year",
    "What's something about working with AI you believed a year ago that you no longer believe?",
    situation=(
        "A year ago I believed two things strongly that I now think were wrong. The one I'd talk "
        "about in an interview is this: I believed AI-assisted coding was strictly a "
        "productivity multiplier for senior engineers — that juniors should NOT use it heavily "
        "because it would short-circuit the learning that comes from struggling with problems. "
        "I held this belief because of how I'd seen Copilot used on a previous team: a junior "
        "engineer on that team had become very fast at producing code and very slow at "
        "diagnosing problems, because every bug-hunting session involved deferring to the AI "
        "instead of building the mental model of the system. I generalized that experience into "
        "a rule: 'juniors should use AI for autocomplete only, not for problem-solving.'"
    ),
    task=(
        "About six months ago I was assigned to mentor two new grads joining my team. I had to "
        "decide what to advise them about AI tooling. My instinct was to enforce my old "
        "heuristic. But the team culture had shifted — engineers around them were using AI "
        "heavily and effectively. A blanket 'don't use AI on the hard parts' rule would have "
        "set the two grads up to be confused outsiders. I had to decide whether my belief was "
        "actually grounded or whether I was generalizing from one bad example."
    ),
    action=(
        "I tested the belief instead of trusting it. I asked both grads, for the first three "
        "weeks, to keep a daily log of every time they used AI on a non-trivial task — what "
        "they asked, what the model returned, and how they decided whether to accept it. I "
        "told them upfront this wasn't a surveillance exercise; I'd read their logs to learn "
        "what good and bad AI use looks like for someone new, and we'd discuss together. "
        "Three weeks of logs taught me what I'd been missing. The grad who'd been my biggest "
        "concern (the more eager one) wasn't using AI to short-circuit thinking — she was using "
        "it as a 'speed-up the boring part' tool. She'd write the first cut herself, get stuck "
        "on, say, the regex syntax, ask Claude, accept the answer, and move on. The pattern "
        "looked exactly like the kind of healthy reference-lookup an experienced engineer would "
        "have done. The OTHER grad was doing what I'd been worried about — pasting problems "
        "wholesale and accepting the first reasonable-looking answer. But his issue wasn't 'too "
        "much AI'; it was 'no mental model of when to verify.' The fix was to teach the "
        "verification skill explicitly, not to ban the tool. "
        "I started a weekly 1:1 segment with both grads called 'narrate the accept/reject.' "
        "They'd bring an example of an AI suggestion they'd accepted that week and walk me "
        "through why. We'd dig into: 'what was your prior?', 'what would you have done if "
        "Claude had said the opposite?', 'how did you verify?'. After eight weeks, the second "
        "grad's reject rate (the rate at which he pushed back on AI suggestions instead of "
        "accepting them) had roughly tripled, and his standalone debugging skills were "
        "noticeably stronger. The verification skill turned out to be teachable directly, and "
        "the AI use was the *practice surface* for teaching it — not a barrier to teaching it. "
        "What changed for me, concretely: I'd been treating AI use and learning depth as a "
        "trade-off ('the more they lean on AI, the less they understand'). The right framing is "
        "actually that AI use exposes the verification gap rather than creating it. A junior "
        "without AI looks like 'they don't know what to do.' A junior with AI looks like 'they "
        "accept whatever the AI says.' Same underlying skill gap, but the AI use makes it "
        "visible faster, which means it's teachable faster."
    ),
    result=(
        "Both grads ramped to first-real-PR-merged in about four weeks vs the team average of "
        "six. The 'narrate the accept/reject' pattern got picked up by two other mentors on the "
        "team for their direct reports. I've stopped treating 'how much AI is OK for juniors?' "
        "as a useful question; the real question is 'how do we build the verification skill, "
        "and what's the fastest practice surface for it?' AI happens to be a very fast "
        "practice surface for it. "
        "If I were asked to defend this in the interview, I'd say: I was wrong because I was "
        "generalizing from one engineer's anti-pattern instead of looking at what skill was "
        "actually missing. The deeper update is that I now treat my AI-related opinions as "
        "*hypotheses* rather than rules — I check them against real data on real engineers "
        "before deciding what to coach. The half-life of correct intuitions about how AI "
        "interacts with engineering practice is probably six months right now; rules I held "
        "two years ago are mostly wrong, and rules I hold today probably won't survive next "
        "year. That's an uncomfortable place to operate as a senior engineer, but pretending "
        "otherwise would be worse."
    ),
    key_strengths=[
        "Continuous AI Learning",
        "Updating beliefs based on evidence",
        "Mentorship judgment",
        "Distinguishing surface symptoms from underlying skills",
        "Calibrated uncertainty",
    ],
    framework_tips=[
        "Name the OLD belief clearly and credit it (where did it come from? what evidence supported it?)",
        "Name the NEW belief clearly and what evidence forced the update",
        "Show the bridge: the specific experiment or experience that moved you",
        "Acknowledge the half-life of AI-related beliefs is short right now",
        "End with the meta-update: how you now hold AI beliefs (as hypotheses, not rules)",
    ],
    tips=[
        "Have a real belief change ready — generic 'AI is more capable than I thought' is too thin",
        "Strongest beliefs to update are about HOW people work, not WHAT models can do — Meta is testing your judgment about humans+AI, not your tracking of model capabilities",
        "Credit the old belief — it had to be reasonable for the update to be impressive",
        "Make the change concrete and recent (within ~12 months)",
        "Name what you'd predict will be your NEXT updated belief — shows you're still thinking",
    ],
    common_pitfalls=[
        "'I thought AI would never write good code, and now it can' — too obvious, weak signal",
        "Not crediting the old belief — sounds like you held the belief lazily",
        "No specific experiment or experience that drove the change",
        "Framing as 'I was wrong' instead of 'I updated based on new evidence'",
        "Skipping the meta-update — Meta wants candidates who hold beliefs lightly in fast-moving domains",
    ],
    follow_up_questions=[
        "What's a belief you currently hold about AI that you suspect you'll update in the next year?",
        "How do you decide which AI opinions to share with your team vs hold privately?",
        "What's a belief you've held STEADILY through the last year — what made it durable?",
        "When did you realize the old belief was wrong, and how long after that did you stop acting on it?",
        "How do you protect yourself from updating to whatever's currently trendy?",
    ],
    what_look_for=[
        "Real, specific, recent belief change",
        "Evidence-driven update, not vibes",
        "Old belief credited as having been reasonable",
        "Meta-update about how the candidate holds beliefs in fast-moving domains",
        "Forward-looking — willing to name what they'd update next",
    ],
    tags=[
        "continuous-ai-learning",
        "calibrated-belief",
        "mentorship",
        "updating-priors",
        "ai-driven-impact",
    ],
    categories=["AI Collaboration", "Learning & Growth"],
)
