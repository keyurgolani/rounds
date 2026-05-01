"""BQ extra: 'Tell me about a time you helped an underperforming teammate turn
around' — Hire and Develop the Best.

Distinct angle from LP-06 (new-grad tacit-knowledge) and from `mentored_someone`
(long-arc promotion coaching). This story is about TURNAROUND under struggle:
a mid-level peer (not a direct report) whose output had decayed to the point of
hurting the team's velocity. The work is the honest conversation, naming the
specific gaps, pairing through them, and setting milestones with check-ins —
not generic mentorship."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Helped an Underperforming Teammate Turn Around",
    "Tell me about a time you helped an underperforming teammate turn things around.",
    situation=(
        "On my team, a mid-level engineer — call her M — had been a solid contributor for two "
        "years, but over a single quarter her output collapsed. PRs sat open for a week before "
        "she'd respond to review comments; two of her last three projects had slipped past their "
        "committed dates by 3+ weeks each; her on-call shifts were ending with unresolved tickets "
        "passed to the next rotation. The team noticed. Two senior engineers had quietly started "
        "rerouting work around her, and one of them complained to me that 'we shouldn't be staffing "
        "M on the critical path anymore.' She wasn't on a PIP yet, but she was a quarter away. "
        "I was a peer (same level), not her manager — but I'd worked closely with her on a prior "
        "project and we trusted each other."
    ),
    task=(
        "Decide whether to step in (it wasn't my job, technically), and if so, how to do it "
        "without being condescending, without going around her manager, and without papering over "
        "what was actually a real performance problem. The team's velocity was being hurt; "
        "ignoring it was a choice with a cost too."
    ),
    action=(
        "I started with the conversation, not a plan. I asked M for a coffee and said the thing "
        "directly: 'I've noticed your last few projects slipped and I want to check in — is "
        "everything okay, and would it help to talk about what's going on?' She was relieved "
        "someone had asked. The honest answer surfaced in 20 minutes: she'd taken on an ambiguous "
        "platform-migration project that she didn't know how to scope, had been afraid to say "
        "'I'm stuck' because she thought it would look bad after a strong year, and had been "
        "spending evenings spinning her wheels — which then degraded her reviews and on-call "
        "because she was exhausted. Two specific gaps, not a general decline: (1) she didn't have "
        "a method for decomposing an ambiguous, multi-month project into reviewable chunks, and "
        "(2) she'd lost the habit of asking for help early. I asked if she'd want to work on it "
        "together; she said yes. Concretely: we sat down and decomposed the migration into 8 "
        "milestones with explicit demos at each; I offered to be her thinking partner for 30 "
        "minutes twice a week for the next month, and we agreed up front this would taper. We "
        "set three checkpoints — weeks 2, 4, and 6 — where we'd honestly assess whether the "
        "turnaround was working, with the option for her to escalate to her manager herself if "
        "it wasn't. I told her I'd give her hard feedback if I saw the slippage pattern returning, "
        "and she could do the same for me. I also encouraged her to bring her manager into the "
        "loop herself, so the formal system could see the trajectory; she did, in her next 1:1, "
        "and her manager was supportive (and grateful — he'd seen the symptoms but not the cause). "
        "I did NOT tell anyone else on the team what we were doing; the rerouting around her was "
        "her problem to fix by shipping, not mine to manage."
    ),
    result=(
        "By week 4, M had hit milestones 1-3 of the migration on schedule; the demo at milestone "
        "3 was the first time the team had seen concrete progress on that project in two months. "
        "By week 6, she was running her own pairing sessions with a junior engineer who'd joined "
        "the team. By month 3, the migration shipped on its (renegotiated, realistic) date, and "
        "the senior engineers who'd been rerouting work around her stopped doing so without me "
        "or anyone else flagging it. Her next review was a 'meets expectations' rebound, no PIP. "
        "She told me later the unlock wasn't the milestones themselves — it was being asked the "
        "honest question early, before the situation became a formal performance case. I learned "
        "two things: turnarounds are usually unblockable by an early honest conversation that "
        "names the specific behaviour rather than the general decline; and a peer can do work a "
        "manager structurally can't, because there's no power asymmetry — but you have to loop "
        "the manager in or you're undermining the system."
    ),
    key_strengths=["Coaching", "Empathy", "Direct communication", "Patience"],
    framework_tips=[
        "Lead with the honest question, not a plan — diagnosis before prescription",
        "Name specific behaviours (slipped dates, unresolved tickets), not general traits ('underperforming')",
        "Decompose the underlying work problem — turnarounds usually have a tractable cause",
        "Set explicit milestones and check-in dates with an off-ramp to escalate if it's not working",
        "Loop in the formal manager — peer coaching that bypasses the manager undermines the system",
        "Don't broadcast — the rerouting team members are not yours to manage; her shipping resolves it",
    ],
    tips=[
        "Pick a peer (not a direct report) story — it shows you can coach without positional authority.",
        "Show the diagnostic conversation — many candidates jump straight to 'I built a plan.'",
        "Show specificity: name the actual gaps (project decomposition + asking for help), not vague 'mindset.'",
        "Show the milestones and check-ins — turnaround is not a vibe, it's a structure.",
        "Show you looped in the manager rather than going around — and that the manager was relieved.",
        "Credit the teammate for doing the actual work; you provided scaffolding and an honest conversation.",
        "Quantify the outcome (milestones hit on schedule, no PIP, project shipped, behaviour stuck).",
    ],
    common_pitfalls=[
        "Saviour narrative — 'I rescued her career'",
        "Generic 'I gave her pep talks' with no specific gap diagnosed and no concrete structure",
        "Going around the manager — peer coaching has to be visible to the formal system",
        "Broadcasting the situation to the team (humiliating, and not your call)",
        "Not naming the cost of inaction — without that, 'helping' looks optional rather than necessary",
        "No off-ramp — what if the turnaround hadn't worked? You should have a plan for that too",
        "Confusing this with mentorship of someone already growing; turnaround is help under struggle",
    ],
    follow_up_questions=[
        "What if she had said 'I'm fine, leave me alone' when you first asked?",
        "What if the turnaround hadn't worked by your week-6 checkpoint?",
        "How did you make sure you weren't undermining her manager's authority?",
        "How did you balance this with your own work?",
        "How did you handle the senior engineers who'd been rerouting work around her?",
        "Have you ever tried this and had it backfire?",
    ],
    what_look_for=[
        "Willingness to have the honest conversation early, before it's a formal case",
        "Diagnostic mindset — naming specific behaviours and underlying causes, not general decline",
        "Concrete structure (milestones, check-ins, off-ramp) rather than vague 'support'",
        "Looping in the formal manager rather than running parallel coaching",
        "Discretion — not broadcasting, not making the teammate the subject of team gossip",
        "Crediting the teammate for the actual recovery work",
        "Sustainable behaviour change (the practice stuck, the rerouting reversed itself)",
    ],
    tags=["coaching", "turnaround", "performance", "empathy"],
    categories=["People Development", "Leadership", "Amazon Leadership Principles"],
)
