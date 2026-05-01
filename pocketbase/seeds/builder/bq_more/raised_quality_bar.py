"""LP-07 extra: Insist on Highest Standards — raised the quality bar for the team."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Insist on Highest Standards — Raised the Bar for Quality",
    "Tell me about a time you raised the bar for quality on your team.",
    situation=(
        "I joined a 9-engineer service team where 'done' meant 'merged.' Over the prior two quarters, "
        "we'd had 14 customer-impacting defects, change-failure rate was 22%, and prod rollbacks "
        "averaged 1.6/week. Code reviews were rubber-stamps; tests were optional in practice. The "
        "team was burned out fighting fires and our deploy cadence had slowed to once every 6 days "
        "because every release felt risky."
    ),
    task=(
        "I was a senior engineer, not the manager. I had to raise the quality bar without a mandate "
        "— without slowing feature delivery, without making the team feel policed, and without "
        "becoming a single point of approval."
    ),
    action=(
        "I started by quantifying the problem. I pulled 90 days of incident data, PR review timing, "
        "test coverage per service, and lint failures, and shared a one-pager: 'where our defects "
        "actually come from.' 71% of incidents traced to three causes — missing edge-case tests, "
        "config-drift between staging and prod, and merges that bypassed review with 'LGTM' under "
        "5 minutes. Then I proposed three concrete changes and offered to build each. (1) A "
        "PR-review checklist — 8 items, two minutes to run, covering test additions, error-path "
        "coverage, observability, and a self-review pass. I drafted it, asked two skeptical seniors "
        "for a critique, and folded their pushback in before publishing. (2) Automated gates in "
        "CI — ruff + mypy on changed files, a coverage floor (75% on touched code, not absolute), "
        "and a blocking 'tests-required' check that allowed an explicit override label with a "
        "1-line justification (we measured override frequency). I wrote the GitHub Actions config "
        "myself so adoption cost was zero. (3) A lightweight testing standard — every bug fix ships "
        "with a regression test; every new public function has at least one happy-path + one "
        "error-path test. I framed all three as 'guardrails, not gates,' and committed publicly "
        "that I'd remove anything that hurt velocity after one quarter of data. I also did the "
        "unglamorous part: I personally backfilled tests for the three highest-incident files in "
        "the codebase and did 'review office hours' for four weeks so engineers could pair on "
        "writing better tests without feeling judged."
    ),
    result=(
        "After one quarter: defect rate dropped from 14 customer-impacting issues to 4 (-71%); "
        "change-failure rate fell from 22% to 7%; rollbacks dropped from 1.6/week to 0.3/week. "
        "Counter-intuitively, deploy cadence went UP — from once every 6 days to 2.4 deploys per "
        "week (+340%) — because each change was smaller and trusted. Test coverage on touched "
        "code rose from 41% to 78%. Override-label usage settled at <5% of PRs and was usually "
        "legitimate (docs-only changes, dependency bumps). The checklist was adopted by two "
        "adjacent teams in the next quarter. My manager cited the work in my next promo packet. "
        "What I learned: you raise the bar by making the right thing the easy thing — automation "
        "absorbs the cost of standards, so the team experiences higher quality as less friction, "
        "not more."
    ),
    key_strengths=[
        "Data-driven diagnosis",
        "Influence without authority",
        "Automation as a force multiplier for standards",
        "Quantified outcomes",
    ],
    framework_tips=[
        "Quantify the quality problem before proposing solutions — defect count, CFR, rollback rate",
        "Standards land when automation absorbs the cost — manual checklists alone get bypassed",
        "Frame as 'guardrails, not gates' and commit to remove anything that hurts velocity",
        "Do the unglamorous backfill work yourself to earn the right to ask others to follow",
        "Measure override / escape-hatch usage so you know if the bar is real",
    ],
    tips=[
        "Pick a story where you raised the bar across the TEAM, not just on your own work.",
        "Quantify both directions — defect rate down AND velocity up. Standards that slow delivery don't stick.",
        "Show you got buy-in (skeptical seniors reviewed the checklist) — top-down imposition is fragile.",
        "Show the durable artefact (checklist + CI gates), not a one-time push.",
        "Distinguish raising standards from gatekeeping — escape hatches with measurement matter.",
    ],
    common_pitfalls=[
        "Imposing standards without buy-in — they erode the moment you leave",
        "Quality narrative without velocity data — sounds like you slowed the team down",
        "Vague outcomes ('we wrote more tests') without quantified defect or CFR change",
        "No automation — manual checklists alone get bypassed under deadline pressure",
        "Hero narrative — 'I personally caught every bug in review'",
    ],
    follow_up_questions=[
        "How did you handle engineers who pushed back on the new checks?",
        "What did you remove from the standards after one quarter of data?",
        "How do you decide when a standard is worth the friction it creates?",
        "Have you ever raised the bar TOO high and had to back off?",
    ],
    what_look_for=[
        "Quantified before / after on multiple dimensions (defect rate AND velocity)",
        "Influence-without-authority pattern — buy-in, not mandate",
        "Automation absorbing the cost of standards",
        "Durable artefacts (checklist, CI config, runbook) vs one-time push",
        "Calibration — measured override usage, willingness to remove things that didn't work",
    ],
    tags=["quality", "standards", "engineering-excellence", "review"],
    categories=["Engineering Excellence", "Leadership", "Amazon Leadership Principles"],
)
