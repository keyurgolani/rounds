"""BQ extra: 'Tell me about a time you drove change in your organization' —
Bias for Action / Earn Trust.

Distinct from 'influenced without authority' (peer-team ask) and 'disagreed with
manager' (vertical disagreement). This one emphasises org-wide momentum: noticing
a status quo people had quietly accepted, building a coalition, running a small
credibility-establishing pilot, measuring adoption, and scaling the change so it
becomes the new default — not a one-off heroics moment."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Drove Change — Building Momentum",
    "Tell me about a time you championed a change across your org.",
    situation=(
        "When I joined as a senior engineer, my org of ~120 engineers across 14 teams was on a "
        "long-lived-feature-branch model. Branches typically lived 2-4 weeks before merging, "
        "merge conflicts ate ~15% of engineering time (we'd measured it in a prior retro), and "
        "release cadence was a painful biweekly 'integration train' that slipped about 40% of "
        "the time. Everyone privately complained — I'd heard 'integration week is the worst' "
        "from at least eight different engineers in my first month — but the consensus was "
        "'this is just how big orgs work.' Two prior attempts to push trunk-based development "
        "had stalled: one had been a top-down mandate that teams quietly ignored, the other a "
        "Slack rant from a staff engineer that produced strong opinions and zero behaviour "
        "change. The status quo had inertia AND scar tissue around it."
    ),
    task=(
        "I wasn't a manager and I didn't own the build system. I wanted the org to move to "
        "trunk-based development with feature flags, short-lived branches (<24h), and a "
        "continuous release model. But I'd just watched two attempts fail, so I knew that "
        "'announcing the change' was the wrong move. My real task was to make trunk-based "
        "development the obvious next step rather than a top-down ask — which meant building "
        "a coalition, proving the model on one team first, and letting the data and the "
        "happier engineers do the persuading."
    ),
    action=(
        "I started by talking, not pitching. Over three weeks I had 1:1 coffees with engineers "
        "and tech leads on six different teams and asked one question: 'what part of "
        "integration week do you most want to never do again?' The answers clustered tightly: "
        "merge conflicts, bisecting old commits, and weekend release rollbacks. I wrote a "
        "two-page memo titled 'Why integration week hurts and what we could do about it' — "
        "framed in their words, with their numbers, not as 'trunk-based development is "
        "industry best practice.' I shared the memo with three tech leads I trusted to push "
        "back honestly; two pointed out real concerns (test flakiness would block trunk; we "
        "had no feature-flag system). I added their concerns to the memo as 'prerequisites' "
        "rather than dismissing them. Then I asked the EM of one mid-sized team — the one "
        "with the loudest pain and a tech lead who was already on board — if their team "
        "would pilot the new model for one quarter. I committed to doing the prerequisite "
        "work myself: I built a lightweight feature-flag library on my Friday-afternoon "
        "time, partnered with the platform team to triage the worst test flakiness (their "
        "manager said yes once I framed it as 'we'll do the triage, you review the fixes'), "
        "and wrote a one-page playbook for the pilot team covering branch lifetime, flag "
        "lifecycle, and rollback. I addressed the obvious objection head-on: I told the "
        "pilot team's EM that if the experiment hurt their delivery I would be the one to "
        "tell our director it had failed, not him. During the pilot I sat in their standup "
        "twice a week, captured friction in real time, and shipped fixes within 24 hours. "
        "After 8 weeks the pilot team's data was striking enough to do the work for me: I "
        "wrote it up — not as a victory lap, but as 'here's what we learned, here's what "
        "still hurts' — and the pilot team's tech lead presented it at the org all-hands, "
        "not me. Three more teams asked to onboard within the week. I put together a "
        "lightweight onboarding checklist and a Slack channel where adopters could trade "
        "fixes. By the end of the next quarter, eight teams were on trunk; I made a point "
        "of crediting the pilot team and the platform team in every forum, and pushed back "
        "when leadership tried to label it 'my' initiative."
    ),
    result=(
        "Within nine months, 13 of 14 teams had moved to trunk-based development; the last "
        "team had a legitimate constraint (a regulated codebase with mandatory pre-merge "
        "review) and we kept them on a modified model rather than forcing a fit. Median "
        "branch lifetime fell from 18 days to 9 hours. Merge-conflict time dropped from ~15% "
        "of engineering time to ~2% (re-measured the same way). Release cadence moved from "
        "biweekly-and-slipping to roughly daily, with no increase in production incident "
        "rate (we tracked it specifically because that was the loudest fear). The feature-"
        "flag library I'd built on Fridays got adopted as the org-standard tool and was "
        "later taken over by the platform team — exactly the durable handoff I wanted. The "
        "more lasting outcome was cultural: 'have we tried this on one team first?' became "
        "a common phrase in roadmap reviews. I learned that driving change is mostly about "
        "lowering the activation energy for the second adopter — the first team is "
        "persuasion, the rest is making it easy and visible to follow. And I learned that "
        "you drive change faster by handing the credit away than by holding onto it."
    ),
    key_strengths=["Initiative", "Persuasion", "Persistence", "Coalition-building", "Credit-sharing"],
    framework_tips=[
        "Listen before pitching — frame the change in the org's own words and pain, not industry best-practice language",
        "Do the prerequisite work yourself instead of waiting for someone to authorise it",
        "Pilot on ONE team that has the pain AND the willingness — don't try to convince everyone at once",
        "Make the pilot data, not your opinion, do the persuading — let the pilot team present the result",
        "Lower the cost of being the second adopter (playbook, channel, named contact)",
        "Hand off ownership of the durable artefacts (tools, docs) to the right org-permanent team",
        "Credit others publicly and consistently — you accelerate adoption by giving the win away",
    ],
    tips=[
        "Pick a story where you DID NOT have formal authority to mandate the change — that's where 'driving' is real.",
        "Show the prior failed attempts (or the inertia) so the change isn't trivial.",
        "Quantify both before and after — branch lifetime, merge-conflict time, release cadence, adoption count.",
        "Show the pilot-then-scale pattern explicitly; 'I convinced everyone at once' is a red flag.",
        "Show how you addressed the real objections (test flakiness, no feature-flag tooling), not strawmen.",
        "Demonstrate durable handoff — who owns the artefacts a year later? Not you, ideally.",
        "Don't take all the credit; explicitly name the pilot team / platform team / others.",
    ],
    common_pitfalls=[
        "Top-down mandate framing — 'I told everyone we were doing X' isn't change leadership",
        "No measured baseline — 'things felt better' isn't a result",
        "Skipping the resistance — every real org change has scar tissue and prior failures",
        "Hero narrative where you single-handedly converted the org",
        "No pilot — boiling the ocean instead of proving on one team",
        "Leaving a maintenance burden — building a tool you still own a year later",
        "Hoarding credit — claiming it as 'my' initiative kills the next change you try to drive",
        "Vague adoption metrics ('most teams adopted it') vs specific (13 of 14, by month 9)",
    ],
    follow_up_questions=[
        "What did the team that DIDN'T adopt teach you?",
        "What if the pilot team had failed — what would you have told the org?",
        "How did you handle the engineers who actively pushed back?",
        "How did you avoid burning out as the de facto owner before the handoff?",
        "Have you driven a change since that DID fail? What was different?",
        "How did you decide which team to pilot on, and what would you have done if no team volunteered?",
    ],
    what_look_for=[
        "Real org-wide scope (not just your team) without formal authority",
        "Acknowledgement of prior failed attempts or genuine inertia",
        "Coalition-building before announcement — 1:1s, listening, framing in their words",
        "Pilot-then-scale pattern with measured baseline and outcome",
        "Concrete prerequisite work the candidate did themselves",
        "Durable handoff to a permanent owner (not still owned by the candidate)",
        "Quantified adoption (count of teams, time-to-adoption) AND quantified outcome (the actual metric that improved)",
        "Credit-sharing — the candidate names other people doing the work",
        "Cultural durability — did the change stick, and did it shift how the org operates beyond this one initiative?",
    ],
    tags=["change", "initiative", "drive", "org", "bias-for-action", "earn-trust", "coalition"],
    categories=["Leadership", "Initiative", "Amazon Leadership Principles"],
)
