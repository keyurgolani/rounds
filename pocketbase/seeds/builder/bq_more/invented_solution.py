"""BQ: Invent and Simplify — invented a solution / simplified a process."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Invented Solution — Simplifying What Was Complex",
    "Tell me about a time you simplified a process or invented a new approach to a problem.",
    situation=(
        "Our team's production deploy ran on a 4-hour Friday-afternoon checklist. It was a shared "
        "Google Doc with 38 manual steps: copy this hash, run that script, paste the output into "
        "Slack, wait for two approvals, edit a config in the bastion host, run smoke tests by "
        "clicking through the UI. Three engineers needed to be on the call — a deployer, a reviewer, "
        "and an SRE. We deployed twice a week; that was ~24 engineer-hours/week of toil. Worse, "
        "newer engineers were terrified of running it, so the same two senior engineers were on "
        "every deploy. Step 17 had been wrong for 6 months — everyone privately corrected it on the "
        "fly because nobody owned the doc."
    ),
    task=(
        "Officially I owned a different service. But I'd been the deployer six times in two months "
        "and watched two near-misses (someone almost ran the prod migration against staging). I "
        "decided to invent a better way rather than file another 'please fix the checklist' ticket "
        "that wouldn't move."
    ),
    action=(
        "I started by instrumenting reality: I shadowed the next 4 deploys with a stopwatch and "
        "logged where the time actually went. 70% was waiting (CI runs, approval pings, smoke "
        "tests); 20% was copy-paste between tools; only 10% was decisions a human needed to make. "
        "That reframed the problem — the checklist was mostly a glue script in human form. I built "
        "a CLI prototype over a weekend: `deploy <service>` orchestrated the existing scripts, "
        "fetched the right hash from CI, posted the approval request to Slack with a one-click "
        "approve button, ran smoke tests headlessly, and printed a single GO/NO-GO at the end. "
        "First version covered our 3 most-deployed services. I demoed it on a Wednesday lunch in "
        "10 minutes — the deploy that had taken 4 hours the week before took 11 minutes live. I "
        "did NOT pitch 'replace the checklist'; I pitched 'opt-in for service owners who want it.' "
        "I sought out the SREs and asked them to break it: they found two real bugs (a race in the "
        "approval poll, a missing rollback path) which I fixed before broader rollout. I wrote a "
        "one-page runbook so other teams could self-serve onboarding, plus a 'how to add your "
        "service' doc. Adoption was voluntary; I did office hours twice a week for a month."
    ),
    result=(
        "Within 8 weeks all 11 services in our org were on the CLI. Average deploy went from "
        "~4 hours / 3 engineers to ~10 minutes / 1 engineer — roughly a 95% reduction in deploy "
        "toil, ~22 engineer-hours/week recovered. Junior engineers started running deploys; the "
        "'only two seniors can deploy' bottleneck disappeared. Step 17 (the silently-wrong one) "
        "got fixed because the CLI's source-of-truth was code that ran, not prose that drifted. "
        "Six months later the platform team adopted the CLI as the org-wide standard and added "
        "two more orchestration backends. The bigger lesson for me: the checklist had grown for "
        "good reasons (each step solved a past incident), but nobody had ever measured where the "
        "TIME actually went — once I did, the answer was obvious. I also learned that voluntary "
        "adoption + a real demo beats top-down mandates; service owners migrated themselves once "
        "they saw a peer's deploy go from hours to minutes."
    ),
    key_strengths=[
        "Simplification",
        "Initiative",
        "First-principles thinking",
        "Adoption-as-product",
    ],
    framework_tips=[
        "Measure where time actually goes before you redesign — assumptions are usually wrong",
        "Build a real prototype on the highest-frequency workflow; demo beats deck",
        "Make adoption voluntary — let early users pull others in",
        "Encode the checklist in code so it can't silently drift",
    ],
    tips=[
        "Quantify the BEFORE rigorously — toil hours, headcount required, error rate.",
        "Show that you measured, not just guessed, where the complexity lived.",
        "Frame the invention as 'replacing glue work,' not 'replacing judgment.'",
        "Show adoption strategy — a tool nobody uses isn't a simplification.",
        "Credit the SREs / reviewers who broke your prototype; that's where trust came from.",
    ],
    common_pitfalls=[
        "Inventing a tool nobody adopted (no adoption story = no result)",
        "Skipping the measurement step — 'I just knew it was slow'",
        "Top-down mandate instead of voluntary opt-in (creates resistance)",
        "Not naming the cost of the OLD system in concrete units (hours, dollars, errors)",
        "Replacing a checklist with a black box that hides decisions humans should still make",
    ],
    follow_up_questions=[
        "How did you handle the team that liked the old process?",
        "What was the riskiest part of the rollout, and how did you de-risk it?",
        "What would you do differently if you started over?",
        "How did you decide what to AUTOMATE vs what to leave as a human decision?",
        "How did you sustain the tool — who maintains it now?",
    ],
    what_look_for=[
        "Measurement-driven invention (instrument before building)",
        "Prototype-first credibility — concrete demo, not slideware",
        "Voluntary adoption strategy",
        "Quantified before/after with adoption rate",
        "Sustainable handoff (runbook, ownership, second team adopting)",
    ],
    tags=["invent", "simplify", "automation", "process", "tooling", "deploy"],
    categories=[
        "Innovation & Creativity",
        "Process Improvement",
        "Amazon Leadership Principles",
    ],
)
