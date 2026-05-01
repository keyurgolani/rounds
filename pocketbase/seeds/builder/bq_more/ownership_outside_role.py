"""BQ: Ownership — Took on something outside your role."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Ownership Outside Role — Stepping Up",
    "Tell me about a time you saw a problem outside your scope and stepped up to fix it.",
    situation=(
        "Our team owned the checkout service. The CI pipeline — owned by a sibling Platform team — "
        "had been increasingly flaky for 6 weeks: ~22% of main-branch runs failed on unrelated "
        "tests, blocking deploys for every team in the org. Engineers had started rerunning "
        "until-green, which masked real failures and once let a bad commit reach prod. The "
        "Platform team had it on their backlog behind two larger projects."
    ),
    task=(
        "Not my pipeline. Not my team. But every deploy I tried to ship was paying the flakiness "
        "tax, and the until-green workaround had become a real correctness risk. Someone needed "
        "to organise a fix without stepping on the Platform team's toes."
    ),
    action=(
        "I started by quantifying the problem so the conversation wasn't anecdotal: I scraped 30 "
        "days of CI runs and produced a per-test failure-rate table. Eight tests accounted for "
        "78% of the flakiness. I shared the data with the Platform team's tech lead and proposed "
        "a 2-week 'flake strike force' — one engineer per affected team for two hours a day, "
        "Platform team coordinating but not staffing. I got buy-in from my manager (clearing it "
        "with him so my day-job didn't slip) and from the Platform tech lead. I volunteered as "
        "the coordinator: ran a daily 15-minute standup, owned a shared tracker, and personally "
        "fixed the two flakes attributable to our checkout team. I wrote a 'how to triage a "
        "flake' runbook so the work outlived the strike force, and added a CI dashboard the "
        "Platform team could own afterward."
    ),
    result=(
        "By end of week 2, 7 of 8 top flakes were fixed; main-branch failure rate dropped from "
        "22% to 3%. Until-green reruns dropped 90%. The Platform team adopted the dashboard and "
        "made flake-triage a recurring rotation across contributing teams — so the fix became a "
        "process, not a one-off heroics. My checkout work didn't slip; I traded ~6 hours/week "
        "of coordination for the deploy-time I was already losing to flakes. My director cited "
        "this in calibration as a cross-team-impact example. I learned that 'not my job' is "
        "fine until the cost of inaction starts paying itself out of your own time."
    ),
    key_strengths=["Ownership", "Initiative", "Cross-team thinking", "Sustainable handoff"],
    framework_tips=[
        "Quantify the problem before you propose action — data wins arguments anecdotes can't",
        "Get explicit buy-in from the owning team AND your manager — not heroics-without-alignment",
        "Coordinate, don't conquer — the owning team should still own it after",
        "Leave a durable artefact (runbook, dashboard, rotation) so the fix doesn't depend on you",
    ],
    tips=[
        "Show that you cleared the work with the owning team — this is ownership, not invasion.",
        "Quantify the cost of the unowned problem (deploy-time, dollars, incidents).",
        "Show you protected your day-job — the interviewer is checking you didn't drop primary responsibilities.",
        "Show the durable handoff: who owns it now, what they own, and what artefact carries the practice.",
    ],
    common_pitfalls=[
        "Hero narrative without alignment from the formal owners",
        "Dropping your primary responsibilities to chase the side problem",
        "No durable handoff — leaving a maintenance burden on the original team",
        "Picking a 'safe' example where nobody actually owned the problem (then it's just unclaimed work, not outside-your-role)",
    ],
    follow_up_questions=[
        "How did you get buy-in from the Platform team — what if they had said no?",
        "How did you balance this with your checkout responsibilities?",
        "What if the strike force hadn't worked — what was your fallback?",
        "How do you decide when to step in vs when to leave it for the owners?",
    ],
    what_look_for=[
        "Initiative without overstepping — alignment from the owning team",
        "Quantified business / engineering cost",
        "Sustainable handoff (runbook, rotation) vs heroics",
        "Honest accounting of how the candidate protected day-job responsibilities",
    ],
    tags=["ownership", "initiative", "scope", "cross-team"],
    categories=["Leadership", "Initiative", "Amazon Leadership Principles"],
)
