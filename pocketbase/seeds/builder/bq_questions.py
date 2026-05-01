"""Behavioral Questions content. 17 entries covering Amazon's Leadership
Principles. Schema mirrors the existing `content.json` behavioral_questions
entries: title, question_text, star_guide, sample_response, tips,
common_pitfalls, follow_up_questions, what_interviewers_look_for,
tags, category_names."""
from __future__ import annotations


def _bq(title, question_text, *, situation, task, action, result,
        key_strengths, framework_tips, tips, common_pitfalls,
        follow_up_questions, what_look_for, tags, categories):
    return {
        "title": title,
        "question_text": question_text,
        "star_guide": {
            "situation": "Set the scene: project, team, stakes, time pressure.",
            "task": "Your specific responsibility — yours, not the team's.",
            "action": "Walk through what YOU did. Use 'I' not 'we'. Quantify decisions.",
            "result": "Measurable outcome. What changed. What you learned.",
            "framework_tips": framework_tips,
        },
        "sample_response": {
            "situation": situation,
            "task": task,
            "action": action,
            "result": result,
            "key_strengths_shown": key_strengths,
        },
        "tips": tips,
        "common_pitfalls": common_pitfalls,
        "follow_up_questions": follow_up_questions,
        "what_interviewers_look_for": what_look_for,
        "tags": tags,
        "category_names": categories,
    }


# ---------------------------------------------------------------------------
# LP-01: Customer Obsession
# ---------------------------------------------------------------------------
LP_01 = _bq(
    "Customer Obsession — Decision Unpopular with Customers",
    "Tell me about a time you had to make a decision that was not popular with customers.",
    situation=(
        "I led the redesign of our enterprise dashboard's bulk-edit feature. The existing "
        "right-click context menu was loved by power users, but our analytics showed only 4% "
        "of customers ever used it, and new users had a 60% drop-off in the first session because "
        "they couldn't figure out where bulk actions lived."
    ),
    task=(
        "I needed to decide whether to deprecate the right-click menu in favour of a visible toolbar. "
        "Power users would push back hard. New-user activation would likely improve."
    ),
    action=(
        "I dug into the support tickets and noticed two patterns: (1) new users churned because they "
        "couldn't find the feature; (2) power users had memorised it and accepted any change as a "
        "regression. I proposed deprecating the menu but retaining the keyboard shortcut. I wrote a "
        "doc with the activation data, the support-ticket categories, and a 4-week migration plan: "
        "ship the toolbar, deprecate the menu in 3 sprints, communicate via in-product banner. I "
        "presented to the customer council before launch and named the trade-off explicitly: 'we are "
        "trading an 8-second saving for power users for a 30-minute saving for every new user.' We "
        "shipped, fielded the complaints, and stayed the course."
    ),
    result=(
        "First-session activation rose from 40% to 67% within two months. We received 22 angry "
        "tickets in the first week from power users; we replied with the keyboard shortcut and 18 "
        "of them stuck. Three months later, NPS improved 8 points overall. The data drove the "
        "decision; I learned to surface trade-offs explicitly instead of trying to make everyone "
        "happy."
    ),
    key_strengths=["Data-driven decision", "Long-term thinking", "Customer empathy", "Communication"],
    framework_tips=[
        "Quantify the customer impact in both directions",
        "Acknowledge the unhappy segment explicitly",
        "Show the trade-off you made and why",
        "Stay the course — don't waffle when complaints come in",
    ],
    tips=[
        "Pick a real decision, not a 'risky' one that worked out anyway.",
        "Quantify everything — activation %, ticket count, NPS shift.",
        "Show you anticipated the unhappy customers and prepared for them.",
        "Distinguish 'unpopular' (they complained) from 'wrong' (they were right) — this should be the former.",
    ],
    common_pitfalls=[
        "Making the decision sound retroactively obvious",
        "Glossing over the customer pushback",
        "Not showing data-driven reasoning",
        "Choosing a story where you actually flip-flopped under pressure",
    ],
    follow_up_questions=[
        "How did you communicate the change to the unhappy segment?",
        "What would you do differently in hindsight?",
        "How do you decide which complaints to act on vs which to weather?",
    ],
    what_look_for=[
        "Working backwards from customer outcomes (not feature lists)",
        "Data-driven trade-offs with quantification",
        "Conviction in the face of vocal pushback",
        "Long-term customer lens vs short-term complaint volume",
    ],
    tags=["customer-obsession", "decision-making", "data-driven"],
    categories=["Customer & Stakeholder Focus", "Decision Making", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-02: Ownership
# ---------------------------------------------------------------------------
LP_02 = _bq(
    "Ownership — Took on Something Outside Your Area",
    "Tell me about a time you took on something significant outside your area of responsibility.",
    situation=(
        "Our team owned the inventory service. Adjacent to us was the order-routing service, owned "
        "by a different team that had been depleted by a re-org. I noticed orders were getting routed "
        "to the wrong fulfillment centre about 0.5% of the time, costing roughly $200K/month in "
        "shipping. The owning team's PM said it was 'on the backlog.'"
    ),
    task=(
        "Not my team. Not my service. But the cost was real and the owning team didn't have "
        "bandwidth. Someone needed to take it on."
    ),
    action=(
        "I read the routing service's code on my own time over a weekend and found the bug — a cache "
        "TTL was misaligned with the shipping zone update cadence. I wrote a doc explaining the bug "
        "and a proposed fix, ran it past the routing team's tech lead and our director. I asked for "
        "two weeks to fix it, with the routing team reviewing the PR. I wrote the fix, the tests, "
        "and the rollout plan. I worked with the on-call to monitor the rollout. I ALSO wrote a "
        "runbook so the owning team could maintain it after."
    ),
    result=(
        "Misroutes dropped from 0.5% to 0.02% within a week. Recovered ~$190K/month in shipping. "
        "The routing team adopted the runbook and made me an honorary contributor. My director "
        "called this out as a Promotion Justification example in my review. I learned that "
        "'somebody else's job' is rarely a good reason to leave a $200K/month bug unfixed."
    ),
    key_strengths=["Initiative", "Cross-team collaboration", "Business impact", "Long-term thinking"],
    framework_tips=[
        "Show that you cleared the work with the owning team — not a heroics-without-buy-in story",
        "Quantify the business impact",
        "Hand off properly — don't leave a maintenance burden",
        "Anchor on customer/business value, not personal advancement",
    ],
    tips=[
        "Distinguish 'taking on' from 'going rogue.' You should have alignment from the owners.",
        "Show the durable handoff — runbook, docs, transitioned ownership.",
        "Quantify the business impact in dollars or customer-affecting metrics.",
        "Don't pick a story where you stepped on someone's toes.",
    ],
    common_pitfalls=[
        "Hero narrative without buy-in from owners",
        "No measurable outcome",
        "Leaving a maintenance burden on the original team",
        "Picking a 'safe' example that doesn't show real ownership",
    ],
    follow_up_questions=[
        "How did you get buy-in from the owning team?",
        "What if they had said no?",
        "How did you balance this with your day-job responsibilities?",
    ],
    what_look_for=[
        "Initiative without overstepping",
        "Business / customer impact framing",
        "Sustainable handoff vs heroics",
        "Long-term thinking",
    ],
    tags=["ownership", "initiative", "cross-team"],
    categories=["Ownership & Accountability", "Leadership", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-03: Invent and Simplify
# ---------------------------------------------------------------------------
LP_03 = _bq(
    "Invent and Simplify — Simple Solution to Complex Problem",
    "Tell me about a time when you found a simple solution to a complex problem.",
    situation=(
        "Our deploy pipeline had grown to 47 stages over five years — every team had bolted on a "
        "validation step. Deploys took 2.5 hours; engineers ran 'staging deploys' just to fail fast "
        "on quick checks, which in turn loaded staging."
    ),
    task=(
        "I was asked to 'optimise' the pipeline. The expected outcome was to parallelise stages or "
        "trim a few. I thought we could go further."
    ),
    action=(
        "I instrumented the pipeline to log per-stage failure rates and median runtimes over 30 days. "
        "Two facts emerged: (1) 8 stages had never failed in 30 days; (2) 12 stages failed only on "
        "code from teams that had moved on. I proposed a radical simplification: keep the 6 stages "
        "that had caught real bugs in the last quarter, move 8 to async post-deploy verification "
        "(non-blocking), and delete the 12 obsolete ones with sign-off from each owning manager. I "
        "wrote a one-pager naming each removed stage with its 30-day record. I also added a single "
        "'fast checks' stage that ran the most-likely-to-fail checks first."
    ),
    result=(
        "Pipeline dropped from 2.5h to 27 minutes. Failure rate held steady (no regressions). "
        "Engineers stopped using staging-as-CI; staging load dropped 40%. The one-pager became the "
        "policy doc — every new stage now had to justify its own existence with a 30-day failure "
        "record. I learned to count *what's actually doing useful work* before optimising it."
    ),
    key_strengths=["Data-driven thinking", "Willingness to remove rather than add", "Stakeholder management"],
    framework_tips=[
        "Show you measured before optimising",
        "'Removing the unnecessary' is often more powerful than 'optimising the existing'",
        "Communicate trade-offs explicitly with stakeholders",
    ],
    tips=[
        "'Simplification' often means deleting things, not improving them.",
        "Measure first — make data the argument.",
        "Get sign-off explicitly per removal; surprise removals breed enemies.",
        "Show that simplicity didn't sacrifice correctness.",
    ],
    common_pitfalls=[
        "'I rewrote the system' isn't simplification, it's rewriting",
        "Not quantifying the simplification",
        "No data — just gut feeling",
        "Leaving a mess of half-deprecated stages",
    ],
    follow_up_questions=[
        "How did you handle pushback from owners of the removed stages?",
        "What broke after?",
        "How do you decide between 'add' vs 'remove' when both could solve the problem?",
    ],
    what_look_for=[
        "Counter-intuitive simplifications (delete > optimise)",
        "Data-driven justification",
        "Long-term ownership of the change (the policy doc)",
        "Quantified outcome",
    ],
    tags=["invent-and-simplify", "data-driven", "process-improvement"],
    categories=["Innovation & Creativity", "Problem Solving", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-04: Are Right, A Lot
# ---------------------------------------------------------------------------
LP_04 = _bq(
    "Are Right, A Lot — Decision with Limited Information",
    "Tell me about a time you made a difficult decision with limited information.",
    situation=(
        "We had a customer-facing feature that occasionally produced wrong results — about 1 in "
        "10,000 queries returned stale data. Reproducing it was nearly impossible; logs were "
        "scattered. Customer reports were rising and we had a board demo in 4 weeks."
    ),
    task=(
        "I had to choose: spend 2-3 weeks on a deep investigation OR ship a defensive fix that would "
        "cover the most-likely root cause without proof, freeing the team for the demo."
    ),
    action=(
        "I asked three questions: (1) what's the most plausible root cause? (2) what's the worst "
        "case if my guess is wrong? (3) what evidence would change my mind? I sketched a Bayesian "
        "table: 60% likely it was a cache-write race, 20% replication lag, 20% client retry "
        "amplifying staleness. I proposed shipping a fix for the cache race AND adding logging that "
        "would distinguish all three. If the bug recurred, the logs would tell us which guess was "
        "wrong. I sought out the senior engineer who'd built the cache for a sanity check; she "
        "agreed with my analysis. I also asked my PM whether sliding the demo by a week was an "
        "option (it was) — that lowered the stakes."
    ),
    result=(
        "Cache fix shipped, complaints dropped 80% within a week. Logs caught two more cases of "
        "what turned out to be replication lag — small enough that we patched it the following "
        "sprint. Demo went well. I learned to MAKE decisions explicit (probabilities, what would "
        "change my mind) rather than agonise over uncertainty in my head."
    ),
    key_strengths=["Decision quality under uncertainty", "Bayesian reasoning", "Disagree-and-commit prep"],
    framework_tips=[
        "Make your reasoning explicit (probabilities, evidence)",
        "Seek targeted input from one or two experts, not a committee",
        "Identify what would change your mind — and instrument for it",
    ],
    tips=[
        "Show structured reasoning — probabilities, expected value, what-would-change-my-mind.",
        "Don't fake certainty. Express uncertainty quantitatively.",
        "Acknowledge that getting input doesn't mean consensus.",
        "Show you would have changed course on contradictory evidence.",
    ],
    common_pitfalls=[
        "Telling a story where you got lucky, not where you reasoned well",
        "Pretending you had more info than you did",
        "Acting unilaterally without seeking targeted input",
        "Not closing the loop — what did the evidence say?",
    ],
    follow_up_questions=[
        "What if your initial guess had been wrong?",
        "How do you decide when to 'wait for more data' vs 'decide now'?",
        "Have you ever been WRONG with this approach?",
    ],
    what_look_for=[
        "Explicit reasoning frameworks",
        "Calibrated confidence (humble + decisive)",
        "Active disconfirmation seeking",
        "Course correction when evidence arrives",
    ],
    tags=["judgment", "uncertainty", "bayesian-thinking"],
    categories=["Decision Making", "Problem Solving", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-05: Learn and Be Curious
# ---------------------------------------------------------------------------
LP_05 = _bq(
    "Learn and Be Curious — Influenced Change by Asking Questions",
    "Tell me about a time when you influenced a change by only asking questions.",
    situation=(
        "I joined a team that had a 'we always do it this way' for database migrations: every "
        "schema change required a 4-week multi-stage rollout via feature flags. New engineers "
        "complained but acquiesced. The pattern had grown out of a 2018 incident where a migration "
        "went bad."
    ),
    task=(
        "I'd seen migrations done in hours at a previous company. I wanted to understand whether "
        "this was justified before proposing change."
    ),
    action=(
        "Instead of arguing, I asked. To the senior engineer who'd written the original runbook: "
        "'what does the 4-week timeline protect against?' To the SRE: 'have we had migration-"
        "related incidents since 2019?' To the on-call: 'do you actually use the feature flags or "
        "do you immediately ship?' The answers revealed: the original 2018 bug was a backwards-"
        "incompatible column drop that broke a downstream service. Since then, we'd added typed "
        "schema migrations and pre-prod replays — the original risk vector had been mitigated. The "
        "feature flags were rarely used. The 4-week ritual was scar tissue."
    ),
    result=(
        "I wrote up the questions and answers as an FAQ doc and shared with the team. The senior "
        "engineer added: 'huh, you're right, the conditions have changed.' We piloted a 1-week "
        "migration cadence with the SRE on board. After two months without incident, the new "
        "default was 1 week. I learned that questions ('what does this protect against?') often "
        "reveal scar-tissue rituals that everyone privately knows are obsolete."
    ),
    key_strengths=["Inquiry over advocacy", "Respect for institutional knowledge", "Collaborative change"],
    framework_tips=[
        "Ask before advocating; understand the original constraint first",
        "Frame questions as exploration, not as critique",
        "Document the answers — the FAQ becomes the change driver",
    ],
    tips=[
        "The point isn't 'I asked some questions' — it's that the questions led to insight that nobody had explicitly surfaced.",
        "Show genuine respect for why the old process existed.",
        "The change should come from the answers, not from your initial opinion.",
        "Keep the doc — it's both an artefact and a teaching aid.",
    ],
    common_pitfalls=[
        "Pretending you 'didn't have an opinion' when you did",
        "Asking leading questions to confirm a pre-formed opinion",
        "Not crediting the senior person who validated the change",
        "No tangible artefact (doc, change, etc.)",
    ],
    follow_up_questions=[
        "How did you know what questions to ask?",
        "What if the questions had revealed the 4-week process WAS still justified?",
        "Have you used this approach since?",
    ],
    what_look_for=[
        "Curiosity over advocacy",
        "Respect for institutional knowledge",
        "Documented inquiry trail",
        "Collaborative outcomes",
    ],
    tags=["curiosity", "inquiry", "change-management"],
    categories=["Learning & Growth", "Communication", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-06: Hire and Develop the Best
# ---------------------------------------------------------------------------
LP_06 = _bq(
    "Hire and Develop — Mentored Someone",
    "Tell me about a time when you mentored someone.",
    situation=(
        "Our team hired a new grad 3 months in. By month 4, her PRs were getting torn apart in "
        "review — not for correctness, but for missing tests, inconsistent style, and skipping "
        "documentation. Her tech lead was beginning to write her off."
    ),
    task=(
        "She wasn't on my team formally, but we sat near each other and I'd done two pair-programming "
        "sessions with her. I noticed she was a strong engineer with a process gap, not a skill gap. "
        "I asked her if I could mentor her informally."
    ),
    action=(
        "First, I asked HER what she thought was going wrong. She said: 'I just don't know how the "
        "team's standards differ from what I learned in school.' That was the diagnosis — implicit "
        "team norms she hadn't been taught. Together we made a written checklist of pre-PR steps: "
        "tests for new branches, run linter, write docstring for public API, self-review the diff. "
        "I reviewed her next 3 PRs PRIVATELY before submission. After PR 4, she submitted alone and "
        "got clean reviews. We kept doing biweekly 1:1s for a few months — she grew quickly. I "
        "made a point of telling her tech lead what was happening so he didn't think she'd just "
        "magically improved."
    ),
    result=(
        "By month 6 she was a normal contributor with no special handling. Her tech lead later said "
        "the early warning signs would have led to a PIP without intervention. Two years later "
        "she's a senior engineer running the on-call rotation. I learned that what looks like an "
        "ability gap is often a tacit-knowledge gap, and that explicit checklists transfer more "
        "than people realise."
    ),
    key_strengths=["Diagnostic mentoring", "Tacit-knowledge transfer", "Long-term investment"],
    framework_tips=[
        "Diagnose before prescribing — ask what THEY think is going wrong",
        "Make implicit knowledge explicit (checklists, written norms)",
        "Loop in the formal manager so growth is visible",
        "Stay engaged after the immediate problem resolves",
    ],
    tips=[
        "Show you diagnosed the right problem — many candidates jump to prescriptions.",
        "Show measurable growth, not just 'she's better now.'",
        "Show the tactical work (PR review pre-submission) AND the strategic loop (informing her manager).",
        "Don't claim more credit than you deserve — she did the work.",
    ],
    common_pitfalls=[
        "Hero narrative — 'I saved her career'",
        "No diagnosis step — just a generic 'I helped'",
        "No follow-through after the immediate fix",
        "Not crediting the mentee's own effort",
    ],
    follow_up_questions=[
        "How did you balance this with your day job?",
        "What if she hadn't been receptive?",
        "Have you formalised any of this into team practice?",
    ],
    what_look_for=[
        "Diagnostic vs prescriptive mentoring",
        "Sustained engagement vs one-off help",
        "Crediting the mentee",
        "Visible long-term outcome",
    ],
    tags=["mentoring", "developing-others", "tacit-knowledge"],
    categories=["Learning & Growth", "Leadership", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-07: Insist on Highest Standards
# ---------------------------------------------------------------------------
LP_07 = _bq(
    "Insist on Highest Standards — Refused to Compromise",
    "Tell me about a time you refused to compromise your standards.",
    situation=(
        "We were 2 weeks from a major launch when QA found a bug: certain combinations of input "
        "would silently truncate the user's data. It was a 0.1% edge case. The PM proposed shipping "
        "with a known-issue note and fixing in v1.1."
    ),
    task=(
        "I was the tech lead. I had to decide whether to ship as-is, hold the launch, or scope-cut "
        "to ship a degraded but correct version."
    ),
    action=(
        "I held the launch. I wrote a one-pager naming the failure mode in customer-facing terms — "
        "'we silently lose 0.1% of your data' — and shared with the PM, the GM, and our director. "
        "Silent data loss is a different category from a missing feature; one is a feature gap, the "
        "other is a betrayal of customer trust. I proposed a 1-week delay to fix the bug and a "
        "scope-cut on a non-critical feature so we could ship within 1 week of original date. The "
        "GM initially pushed back ('the timeline is fixed'); I respectfully said: 'silent data "
        "loss is the kind of thing that makes the front page of Hacker News.' She agreed."
    ),
    result=(
        "We shipped 1 week late with the bug fixed. The non-critical feature shipped 3 sprints "
        "later. Three weeks after launch, a competitor shipped a similar product WITH a similar "
        "data-loss bug and got hammered in tech press. Our launch was clean. Our director referenced "
        "this as a 'right call' in our team retro. I learned that holding standards isn't free — "
        "it costs schedule, scope, and political capital — but the alternative (a public data-loss "
        "story) is much more expensive."
    ),
    key_strengths=["Quality-as-non-negotiable", "Stakeholder communication", "Risk framing"],
    framework_tips=[
        "Frame the standard in customer-impact terms, not engineer-aesthetics terms",
        "Propose a path forward, not just 'no'",
        "Acknowledge the cost (schedule, scope) — be honest about trade-offs",
    ],
    tips=[
        "Pick a story where 'compromise' would have been a real bad outcome, not a stylistic preference.",
        "Frame the standard in customer terms — silent data loss vs UI inconsistency.",
        "Show you proposed a constructive alternative, not just 'no.'",
        "Quantify the cost of holding the line so it's clear you weren't being precious.",
    ],
    common_pitfalls=[
        "Picking a stylistic-preference story (tabs vs spaces, function naming)",
        "Not naming the specific risk in customer terms",
        "Coming across as inflexible — failing to propose alternatives",
        "Not having a fallback if you'd lost the argument",
    ],
    follow_up_questions=[
        "What if leadership had insisted on shipping?",
        "How do you decide what's a 'standard' vs what's a 'preference'?",
        "Have you ever been wrong about holding the line?",
    ],
    what_look_for=[
        "Quality framed in customer-impact terms",
        "Concrete alternative proposed",
        "Willingness to take political cost",
        "Calibration between standards and preferences",
    ],
    tags=["quality", "standards", "customer-trust"],
    categories=["Customer & Stakeholder Focus", "Leadership", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-08: Think Big
# ---------------------------------------------------------------------------
LP_08 = _bq(
    "Think Big — Proposed a New Business Idea",
    "Tell me about a time you proposed a new business idea. How did you get buy-in?",
    situation=(
        "Our team built internal tools. I noticed our company spent $4M/year on a third-party data "
        "annotation tool with limited customisation. Our annotation needs were 60% standard, 40% "
        "domain-specific. The vendor wouldn't build the domain-specific features."
    ),
    task=(
        "I had a hunch we could build a better tool internally and save money + improve quality. "
        "But it would be a 6-engineer-quarter investment. I had to convince leadership it was worth it."
    ),
    action=(
        "I started by talking to 8 annotators across the company to understand their actual pain. "
        "I built a 2-week prototype focused on the highest-pain workflow (medical-image bounding boxes "
        "with longitudinal context). I demoed it to 3 of the 8 annotators; they were enthusiastic. I "
        "wrote a 4-page proposal with: the prototype demo, projected savings ($4M vendor cost vs ~"
        "$1.5M build + $500K/yr maintain), the timeline (2 quarters, 6 engineers), risk register, "
        "and a phased rollout plan. I named the risks honestly: 'we could be wrong about "
        "maintenance cost; we might lose 2 of 6 engineers; vendor might pivot to match.' I "
        "presented to my director, then to the VP. I asked for a pilot — 2 engineers for one "
        "quarter to build the highest-value workflow."
    ),
    result=(
        "Pilot approved. After Q1, we'd built a tool that 5 of the 8 annotators preferred. Phase 2 "
        "(scaling team to 6 engineers) was approved. By Q4, we'd retired the vendor and were saving "
        "$3.2M/year (vs the projected $2M). Tool is now used across the company by 200+ "
        "annotators. I learned that 'big' ideas land when you start with the smallest-possible "
        "credibility-establishing prototype, and when you name the downside risks before "
        "leadership has to ask."
    ),
    key_strengths=["Strategic thinking", "Prototype-driven proposals", "Risk transparency"],
    framework_tips=[
        "Quantify the opportunity AND the cost in dollars",
        "Lead with a prototype, not a slide deck — credibility",
        "Name the risks before leadership asks",
        "Propose a phased start — pilot, then scale",
    ],
    tips=[
        "Quantify both the opportunity and the cost.",
        "Lead with a prototype — concrete beats abstract every time.",
        "Pre-empt 'what could go wrong?' with your own risk list.",
        "Phase the proposal — pilot → expand → full investment.",
    ],
    common_pitfalls=[
        "Big idea without a small proof-of-concept",
        "No quantification of cost",
        "Not anticipating leadership's risk concerns",
        "Asking for full investment up front instead of a pilot",
    ],
    follow_up_questions=[
        "What if the pilot had failed?",
        "How did you handle internal politics with the vendor's account team?",
        "What did you scope OUT of the pilot to keep it small?",
    ],
    what_look_for=[
        "Quantified opportunity and cost",
        "Concrete prototype",
        "Honest risk framing",
        "Phased approach",
    ],
    tags=["think-big", "strategy", "build-vs-buy"],
    categories=["Innovation & Creativity", "Leadership", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-09: Bias for Action
# ---------------------------------------------------------------------------
LP_09 = _bq(
    "Bias for Action — Took a Calculated Risk",
    "Tell me about a time you took a calculated risk.",
    situation=(
        "We were 1 day from a customer deadline when our deployment system started failing for a "
        "specific service. The build engineer was on vacation. The deploy could be unblocked by "
        "manually editing a config file in production — a procedure officially banned without two "
        "approvers, who were unreachable in different timezones."
    ),
    task=(
        "I had to decide: skip the deadline (lose customer trust + ~$1M annual contract) or "
        "manually unblock and document (violate process)."
    ),
    action=(
        "I looked at what the manual edit would actually do — flip a feature flag from 'staging' to "
        "'prod' that the build engineer normally toggled. The risk: if I got it wrong, the service "
        "would be misrouted but recoverable in <5 minutes. Risk magnitude: low. Reversibility: high. "
        "I made the edit myself, paged the on-call to monitor, and posted in the team channel: "
        "'manual edit applied at HH:MM, here's the diff, here's why, will document fully when "
        "build engineer is back.' Deploy went through. Customer deadline met. I emailed the build "
        "engineer the moment she was online."
    ),
    result=(
        "Deploy succeeded. Customer was happy; contract renewed. The build engineer reviewed my "
        "change, agreed it was the right call, and added 'one-engineer override with channel "
        "post' as an explicit emergency procedure. Our director called this out as 'good judgment "
        "on a two-way door.' I learned to evaluate risk along reversibility — a fast-rollback action "
        "with good monitoring is a different beast than a one-way change."
    ),
    key_strengths=["Calibrated risk-taking", "Two-way-door reasoning", "Transparent communication"],
    framework_tips=[
        "Distinguish two-way doors (reversible) from one-way doors (irreversible)",
        "Communicate the action publicly, not after the fact",
        "Document for the formal process to absorb",
    ],
    tips=[
        "Frame the risk in two-way vs one-way door terms — that's Amazon's specific language.",
        "Show transparency — you didn't sneak; you announced.",
        "Show that the formal process absorbed the lesson (new procedure).",
        "Avoid stories where you cut corners on something irreversible.",
    ],
    common_pitfalls=[
        "Risking a one-way door (irreversible change) without authority",
        "Hiding the action — bias for action ≠ bias for stealth",
        "No monitoring or rollback plan",
        "Not closing the loop with the absent owner",
    ],
    follow_up_questions=[
        "What if the change had broken something irreversibly?",
        "How do you tell two-way from one-way doors?",
        "Have you ever taken a risk that BACKFIRED?",
    ],
    what_look_for=[
        "Reversibility awareness",
        "Calibrated risk-taking with monitoring",
        "Transparency post-action",
        "Process improvement",
    ],
    tags=["bias-for-action", "calculated-risk", "two-way-door"],
    categories=["Decision Making", "Adaptability", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-10: Frugality
# ---------------------------------------------------------------------------
LP_10 = _bq(
    "Frugality — Limited Time or Resources",
    "Tell me about a time you worked with limited time or resources.",
    situation=(
        "Our team needed to build a customer-feedback aggregator for a product launch in 3 weeks. "
        "Initial scope estimate: 8 engineer-weeks. We had 2 engineers (me + one junior) for those "
        "3 weeks — about 6 engineer-weeks of capacity, 25% short."
    ),
    task=(
        "I had to either get more headcount (politically expensive — would slip the launch) or "
        "find a way to get 8 weeks of value out of 6 weeks of work."
    ),
    action=(
        "I broke the scope into MUST, SHOULD, COULD. MUST was 4 weeks of work — feedback collection "
        "and the basic dashboard. SHOULD was 3 weeks — sentiment analysis. COULD was 1 week — "
        "advanced filtering. I cut the SHOULD-tier sentiment analysis: instead of building it, I "
        "integrated an off-the-shelf NLP library that gave us 80% of the value in 0.5 weeks. I cut "
        "advanced filtering entirely; the dashboard would launch with basic filters and we'd add "
        "more in a follow-up. With ~5.5 weeks of work, we had MUST + a SHOULD-substitute. I added "
        "0.5 weeks of buffer. I communicated the cuts to the PM weekly with rationale."
    ),
    result=(
        "Shipped on time. Sentiment analysis via the library was less accurate than custom code "
        "would have been, but customers couldn't tell the difference, and we proved the value "
        "before investing in custom. Three months later, the data showed sentiment analysis was "
        "rarely used; we never built the custom version. Saved 2.5 engineer-weeks. I learned "
        "frugality is mostly about NOT doing things that don't pay back."
    ),
    key_strengths=["Scope discipline", "Off-the-shelf vs build", "Communication of cuts"],
    framework_tips=[
        "Break work into MUST / SHOULD / COULD; cut SHOULD or COULD if needed",
        "Look for off-the-shelf / 80% solutions before building custom",
        "Communicate cuts proactively — surprises destroy trust",
    ],
    tips=[
        "Frugality isn't 'I worked harder.' It's 'I did less but got the same value.'",
        "Show explicit prioritisation — MUST/SHOULD/COULD is the standard.",
        "Off-the-shelf vs custom is a frugality lever; show you considered it.",
        "Quantify the savings.",
    ],
    common_pitfalls=[
        "Heroics narrative — 'I worked 80-hour weeks'",
        "Vague 'we cut scope' without specifics",
        "Not quantifying the savings",
        "No communication trail with stakeholders",
    ],
    follow_up_questions=[
        "How did you handle the PM's pushback on scope cuts?",
        "What did you cut that you regret cutting?",
        "How do you decide between buying / building / not-building?",
    ],
    what_look_for=[
        "Scope discipline (must/should/could)",
        "Buy-vs-build pragmatism",
        "Communication of trade-offs",
        "Quantified savings",
    ],
    tags=["frugality", "scope-cutting", "build-vs-buy"],
    categories=["Time Management & Prioritization", "Decision Making", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-11: Earn Trust
# ---------------------------------------------------------------------------
LP_11 = _bq(
    "Earn Trust — Tough Feedback Received",
    "Give me an example of tough feedback you received. What did you do?",
    situation=(
        "After my first major design doc as a tech lead, my skip-level manager pulled me aside and "
        "said: 'this design is fine, but I noticed you didn't credit Sarah for the prototype she "
        "did. People are noticing.' Sarah had built a small prototype I'd extended; in the doc I'd "
        "framed it as 'I built a prototype, then evolved it.'"
    ),
    task=(
        "Decide whether the feedback was right, what to do about it, and how to prevent it "
        "happening again."
    ),
    action=(
        "First reaction: I felt defensive. The prototype I'd extended WAS substantially different. "
        "Then I sat with it for a day. I went back to the doc and the original prototype. Sarah's "
        "work was a meaningful starting point that saved me ~3 days. By underweighting that, I'd "
        "shifted credit to me. I revised the doc explicitly: 'Building on Sarah's prototype, I "
        "extended it to support …'. I sent Sarah a private message saying I'd realised I'd "
        "underweighted her contribution and was correcting it. I thanked my skip-level for the "
        "feedback. I added 'attribution check' as a step in my own pre-publish doc checklist."
    ),
    result=(
        "Sarah appreciated the correction directly; we worked closely for the next 6 months. My "
        "skip-level noted the doc revision in a 1:1 as 'good response.' The attribution-check "
        "habit prevented a similar mistake later that quarter when I would have under-credited a "
        "colleague's review feedback. I learned that tough feedback often hits because there's a "
        "kernel of truth that I want to dismiss; sitting with it for a day before responding lets "
        "the kernel surface."
    ),
    key_strengths=["Receptiveness to feedback", "Self-awareness", "Behaviour change"],
    framework_tips=[
        "Sit with the feedback before responding — emotion fades, signal stays",
        "Take concrete corrective action in public AND private",
        "Build a habit / system to prevent recurrence",
    ],
    tips=[
        "Don't pick a piece of feedback you instantly knew was right — that's not 'tough.'",
        "Show the actual work of changing your mind, including the initial defensiveness.",
        "Demonstrate concrete behaviour change.",
        "Distinguish 'I felt bad' from 'I did something different next time.'",
    ],
    common_pitfalls=[
        "'Tough feedback' that's actually flattering ('I was told I take on too much')",
        "Saying you accepted the feedback without naming the specific behaviour change",
        "Not acknowledging your initial defensive reaction",
        "No durable habit / system to prevent recurrence",
    ],
    follow_up_questions=[
        "What was your initial reaction?",
        "Did you push back at any point?",
        "Have you given similar tough feedback to someone else?",
    ],
    what_look_for=[
        "Genuine receptiveness vs performative acceptance",
        "Behaviour change vs emotional response",
        "Habit-forming",
        "Public + private correction",
    ],
    tags=["earn-trust", "feedback", "self-awareness"],
    categories=["Learning & Growth", "Communication", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-12: Dive Deep
# ---------------------------------------------------------------------------
LP_12 = _bq(
    "Dive Deep — Used Data to Make a Decision",
    "Tell me about a time you used data to make a decision.",
    situation=(
        "Our team was about to spend a full quarter rewriting our login service for performance. The "
        "argument was 'login is slow, customers complain.' I asked: how slow, what's the p99, and "
        "how often does it actually fail?"
    ),
    task=(
        "Validate the assumption that login was the bottleneck before committing the team to a "
        "quarter of rewrite work."
    ),
    action=(
        "I instrumented the login flow with detailed timing per stage. Over 7 days I captured 50M "
        "login attempts with per-stage durations. Analysis showed: p50 login was 80ms (fine), p99 "
        "was 1.8s (the complaint), and 95% of the p99 latency was in ONE stage — a third-party "
        "fraud-detection callout. Our login code itself was p99 200ms. The rewrite would have "
        "addressed at most 11% of the latency; the remaining 89% was the fraud callout. I went to "
        "the fraud team's tech lead with the data; he confirmed they'd been planning to add "
        "regional caching that would cut their p99 to 300ms. I cancelled the login rewrite and "
        "instead sponsored an integration with the fraud team's caching."
    ),
    result=(
        "Fraud caching shipped 6 weeks later; login p99 dropped from 1.8s to 600ms (67% improvement) "
        "with 0 lines of login code rewritten. Saved a quarter of team capacity, redirected to a "
        "feature that drove $3M in revenue. I learned that 'we should rewrite X' is a hypothesis, "
        "not a conclusion — instrument first, conclude second."
    ),
    key_strengths=["Instrumentation-first mindset", "Cross-team coordination", "Hypothesis testing"],
    framework_tips=[
        "Treat 'we should rewrite X' as a hypothesis, not a conclusion",
        "Instrument before architecting",
        "Localise the actual bottleneck before throwing engineering at the assumed one",
    ],
    tips=[
        "Show specific data — percentile, %, before/after.",
        "Show that data CHANGED your conclusion. Otherwise it's just window dressing.",
        "Quantify the saved investment — capacity, dollars, customer impact.",
        "Credit the partner team that did the actual fix.",
    ],
    common_pitfalls=[
        "Vague data references ('I looked at metrics')",
        "Confirming a pre-formed conclusion (post-hoc data justification)",
        "Not crediting the team that solved the actual problem",
        "Quantification only on inputs, not outcomes",
    ],
    follow_up_questions=[
        "How did you handle pushback from the team that wanted to do the rewrite?",
        "What if the data had said the rewrite WAS justified?",
        "How do you balance 'dive deep' with 'don't ratrhole'?",
    ],
    what_look_for=[
        "Instrumentation-first reflex",
        "Data that changed the conclusion",
        "Quantified savings",
        "Cross-team partnership",
    ],
    tags=["dive-deep", "data-driven", "instrumentation"],
    categories=["Problem Solving", "Decision Making", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-13: Have Backbone; Disagree and Commit
# ---------------------------------------------------------------------------
LP_13 = _bq(
    "Have Backbone — Disagreed Strongly with Manager",
    "Tell me about a time you strongly disagreed with your manager on something important.",
    situation=(
        "My manager wanted us to ship a beta of a new product to 100% of users on day 1. I believed "
        "we should ship to 5%, gather data, and ramp. The product was a major architectural shift "
        "and we'd never tested it under real load."
    ),
    task=(
        "Voice disagreement constructively, then either change his mind or commit to his plan."
    ),
    action=(
        "I scheduled a 1:1 specifically for this. I came with two pages of structured argument: "
        "(1) the architectural risks (3 specific unknowns, with evidence from staging tests), "
        "(2) the data we'd want to see before 100%, (3) a proposed ramp schedule that would still "
        "hit GA within 6 weeks. I led with: 'I disagree with shipping at 100% on day 1; here's why.' "
        "He pushed back: 'we've been delayed twice; leadership is watching.' I acknowledged that "
        "AND named the specific bad outcomes from a 100% rollout failure. He asked for one specific "
        "concession — could we accept 25% on day 1 instead of 5%. I said yes; my objection was to "
        "100%, not specifically to 5%. We agreed on 25% → 100% over 2 weeks."
    ),
    result=(
        "At 25%, we caught a memory leak that would have OOM'd the entire fleet at 100%. We patched "
        "it on day 2 and ramped on schedule. Without the staged rollout, the bug would have caused "
        "a 4-hour outage and a customer-facing incident. My manager later said I'd saved his "
        "promotion and the team's quarter. I learned that 'disagree' lands when you bring "
        "structure, evidence, and acceptable alternatives — not when you bring opposition."
    ),
    key_strengths=["Structured disagreement", "Negotiation", "Commitment after decision"],
    framework_tips=[
        "Lead with 'I disagree' explicitly — not euphemisms",
        "Bring evidence and structure, not just feelings",
        "Propose acceptable alternatives, not just opposition",
        "Commit fully after the decision, even if you didn't get 100% your way",
    ],
    tips=[
        "Pick a substantive disagreement, not a stylistic one.",
        "Show structured argument — 1:1, document, evidence.",
        "Show the negotiation — both sides moved.",
        "Show commitment after the decision (the ramp went smoothly).",
    ],
    common_pitfalls=[
        "Disagreeing in public meetings rather than 1:1",
        "Bringing only opposition, no alternatives",
        "After the decision, half-committing",
        "Disagreeing without evidence",
    ],
    follow_up_questions=[
        "What if your manager had insisted on 100%?",
        "Have you ever disagreed and been wrong?",
        "How do you handle disagreement with peers vs managers?",
    ],
    what_look_for=[
        "Structured argument with evidence",
        "Direct (not euphemistic) disagreement",
        "Compromise vs collapse",
        "Full commitment after",
    ],
    tags=["disagree-and-commit", "conflict", "communication"],
    categories=["Conflict Resolution", "Decision Making", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-14: Deliver Results
# ---------------------------------------------------------------------------
LP_14 = _bq(
    "Deliver Results — Important Project Under Tight Deadline",
    "Tell me about delivering an important project under a tight deadline.",
    situation=(
        "We had to ship a regulatory compliance feature with a hard deadline 8 weeks out — a fine "
        "of $1M/month for late filing. My team was 4 engineers; the work was 12 engineer-weeks "
        "in our initial estimate."
    ),
    task=(
        "Hit the deadline with a working, audit-passing implementation."
    ),
    action=(
        "I broke the work into 4 streams and assigned each engineer a primary stream + secondary "
        "support stream. I instituted daily 15-minute standups with explicit blockers — anything "
        "blocking >24h escalated to me immediately. I built a burndown of 'must-have' tasks (no "
        "scope creep). I held one explicit 'risk review' at week 4: were we on track? We weren't; "
        "we were trending 1 week late. I cut a non-essential audit-trail UI and deferred it to "
        "post-launch (with sign-off from the compliance team that the data was logged and "
        "queryable, just not pretty). I personally took on the integration testing in week 6-7 to "
        "free engineers for last bug fixes. I had the team do dry runs of the audit submission "
        "flow with the compliance team in week 7 to surface any gaps."
    ),
    result=(
        "Shipped on day 56 of 56. Audit passed on first submission. Avoided $1M+ fine. Audit-trail "
        "UI shipped 3 weeks later (wasn't actually needed for audit pass). Team retro: weekly risk "
        "review at week 4 was the unlock — without that explicit checkpoint, we'd have shipped late. "
        "I learned that under tight deadlines, the schedule risk has to be SURFACED EARLY and "
        "trade-offs taken EARLY — not heroically caught at the end."
    ),
    key_strengths=["Project planning", "Risk surfacing", "Scope discipline"],
    framework_tips=[
        "Break work into parallel streams with explicit owners",
        "Build a daily blocker mechanism, not weekly status",
        "Schedule explicit risk-review checkpoints, not 'as needed'",
        "Cut scope early when burndown shows trend slipping",
    ],
    tips=[
        "Quantify the deadline stakes — dollars, customer impact, regulatory.",
        "Show the mechanism for risk-detection (weekly risk review).",
        "Show concrete scope cuts when the data warranted them.",
        "Don't sell the heroics — sell the planning.",
    ],
    common_pitfalls=[
        "Heroics narrative — '80-hour weeks saved the day'",
        "No explicit risk-detection mechanism",
        "Scope cut at the last possible moment vs proactively",
        "Not naming what you cut",
    ],
    follow_up_questions=[
        "What if the risk review had shown you were on track and then you slipped at week 7?",
        "How did you decide what to cut?",
        "What did you learn for the next deadline-driven project?",
    ],
    what_look_for=[
        "Proactive risk detection",
        "Scope discipline under pressure",
        "Calm execution vs heroics",
        "Quantified outcome",
    ],
    tags=["delivery", "deadlines", "scope-management"],
    categories=["Time Management & Prioritization", "Decision Making", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-15: Strive to be Earth's Best Employer
# ---------------------------------------------------------------------------
LP_15 = _bq(
    "Best Employer — Created an Inclusive Environment",
    "Tell me about creating a more inclusive environment.",
    situation=(
        "On our team, I noticed that during design reviews, the same 3 senior voices dominated. "
        "Junior engineers — especially those for whom English was a second language — barely "
        "spoke. The team was technically diverse but discussion-wise wasn't."
    ),
    task=(
        "Increase participation in design reviews without forcing junior engineers into a "
        "spotlight they didn't want."
    ),
    action=(
        "I changed three things in our review process. First: documents were shared 24h before the "
        "meeting (was: 1h before). This gave non-native English speakers time to read and prepare. "
        "Second: I introduced a written-comments-first phase — first 10 minutes of the meeting, "
        "everyone wrote one observation in the doc; then we discussed. This let ideas come from "
        "anyone, not just the fastest talkers. Third: I started rotating the 'design review "
        "facilitator' role; the facilitator's job was to call on people who hadn't spoken yet. I "
        "didn't announce this as a 'diversity initiative'; I framed it as 'we want better "
        "decisions.'"
    ),
    result=(
        "Within two months, the participation distribution flattened — written comments came from "
        "all 12 team members, not the original 3. We caught 2 design issues that quarter that "
        "wouldn't have surfaced under the old format (they came from the most-junior engineer's "
        "written comment). One engineer pulled me aside and said the new format was the first time "
        "she'd felt able to push back on a senior engineer's design. I learned that inclusion "
        "isn't about telling people to speak more; it's about removing structural barriers to "
        "participation."
    ),
    key_strengths=["Process design for inclusion", "Structural thinking", "Outcomes orientation"],
    framework_tips=[
        "Inclusion is a process problem, not a personality problem",
        "Reframe DEI changes as 'better outcomes' to broaden support",
        "Measure participation distribution, not just headcount diversity",
    ],
    tips=[
        "Show specific process changes, not vague 'I tried to be inclusive.'",
        "Reframe the change in outcome terms ('better decisions') — broadens the coalition.",
        "Quantify the participation shift.",
        "Avoid saviour narrative — credit the people who participated.",
    ],
    common_pitfalls=[
        "Saviour narrative",
        "No specific process change",
        "Outcome only measured in 'I felt better'",
        "Not crediting the people whose ideas surfaced",
    ],
    follow_up_questions=[
        "How did the senior engineers react?",
        "What if the process changes didn't work?",
        "How do you sustain inclusion over time as the team turns over?",
    ],
    what_look_for=[
        "Structural / process thinking",
        "Quantified participation shift",
        "Reframing as outcomes (not optics)",
        "Sustainable not heroic",
    ],
    tags=["inclusion", "process-design", "team-culture"],
    categories=["Teamwork & Collaboration", "Leadership", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-16: Success and Scale Bring Broad Responsibility
# ---------------------------------------------------------------------------
LP_16 = _bq(
    "Success and Scale — Considered Broader Impact",
    "Tell me about considering the broader impact of a decision.",
    situation=(
        "Our team built a recommendation feature that was about to ship globally to 80M users. "
        "Internal A/B tests showed +12% engagement. Then I noticed: the engagement lift was "
        "concentrated entirely in users aged 13-17, and a slice of the recommendation pool included "
        "content with weight-loss messaging."
    ),
    task=(
        "The feature met every metric. Should I flag this concern even though no policy was being "
        "violated, no review had raised it, and the launch was 1 week away?"
    ),
    action=(
        "I sat with my discomfort. The metric was clean. But the second-order question — 'are we "
        "making teenagers feel worse about their bodies for 12% engagement?' — wasn't answered. I "
        "wrote a one-pager: 'Pre-launch ethics check: weight-loss content recommendation to "
        "teenagers.' I included the demographic engagement breakdown, the % of recommendations "
        "that fell in the weight-loss bucket, and three options: ship as-is, exclude weight-loss "
        "content for under-18, or delay launch for review. I shared it with my PM, my manager, and "
        "the trust & safety team. T&S thanked me, escalated, and the company's policy team got "
        "involved."
    ),
    result=(
        "The launch was delayed 3 weeks. The final feature excluded weight-loss content from "
        "recommendations for users under 18. Engagement dropped from +12% to +9% (still positive). "
        "Our director cited this as the 'right call to make' in an all-hands. Six months later, "
        "Reuters published a piece about a competitor with a similar feature that hadn't gated for "
        "minors; their stock dropped. I learned that 'no policy violation' isn't the same as "
        "'no responsibility,' especially at scale."
    ),
    key_strengths=["Second-order thinking", "Long-horizon consequences", "Courage to flag"],
    framework_tips=[
        "Distinguish 'allowed' from 'right' — policy is a floor, not a ceiling",
        "Surface concerns to the people who CAN act, not just to peers",
        "Frame in second-order terms (downstream impact)",
        "Be willing to lose a metric for the right reason",
    ],
    tips=[
        "Pick a story where you flagged something that no formal review caught.",
        "Quantify the impact you're concerned about (demographic skew, %, etc).",
        "Show that you proposed alternatives, not just objected.",
        "Show acceptance that the right call cost something measurable.",
    ],
    common_pitfalls=[
        "Generic 'I cared about ethics' without specific facts",
        "Acting alone — not surfacing to people who could act",
        "No cost named — a cost-free ethical stand isn't a stand",
        "Saviour narrative",
    ],
    follow_up_questions=[
        "What if leadership had decided to ship anyway?",
        "How do you decide when to flag vs when to let it go?",
        "Have you been wrong about flagging something?",
    ],
    what_look_for=[
        "Second-order thinking",
        "Willingness to surface uncomfortable issues",
        "Framing in customer / societal impact terms",
        "Acceptance of cost",
    ],
    tags=["ethics", "second-order-thinking", "responsibility"],
    categories=["Decision Making", "Customer & Stakeholder Focus", "Amazon Leadership Principles"],
)


# ---------------------------------------------------------------------------
# LP-17: Deals with Ambiguity
# ---------------------------------------------------------------------------
LP_17 = _bq(
    "Deals with Ambiguity — Project with Minimal Direction",
    "Tell me about a time you worked on a project with minimal information and minimal direction. How did you manage?",
    situation=(
        "I was assigned to 'improve customer onboarding.' That was the entire brief. No metric. No "
        "owner before me. No design doc. The previous person had left two weeks earlier. The new "
        "VP wanted 'something concrete' in 90 days."
    ),
    task=(
        "Define what 'improve onboarding' means, why, what success looks like, and execute."
    ),
    action=(
        "Week 1-2: I read every document and interviewed 12 stakeholders — sales, support, product, "
        "engineering, two recent customers. I asked each: 'what's the single biggest pain in our "
        "onboarding?' The answers clustered around: time-to-first-value (avg 14 days), incomplete "
        "default config, and confusion about feature discoverability. Week 3: I drafted a one-pager "
        "with three problem statements + a metric for each (TTFV, % completed setup, % activated "
        "key features). I shared with the VP and stakeholders for sanity check. Week 4-12: I "
        "executed the highest-leverage one — TTFV — by re-ordering the onboarding flow, eliminating "
        "two friction points, and adding a guided tour. I kept the doc updated weekly with "
        "progress and decisions; surprises were proactively communicated."
    ),
    result=(
        "TTFV dropped from 14 days to 3 days. % activating key features rose from 35% to 58%. The "
        "one-pager became the team's onboarding strategy doc. The VP asked me to write a similar "
        "framing for the broader product team. I learned that 'minimal direction' is rarely "
        "minimal information — it's an ambiguity that becomes specific only after talking to the "
        "right people and writing it down."
    ),
    key_strengths=["Ambiguity decomposition", "Stakeholder synthesis", "Definition-of-done invention"],
    framework_tips=[
        "Talk first, write second, build third",
        "Force ambiguity into specific problem statements with metrics",
        "Communicate the framing back to stakeholders for confirmation before executing",
        "Document decisions weekly — your audit trail",
    ],
    tips=[
        "Show the explicit decomposition: ambiguity → problem statements → metrics → action.",
        "Quantify the outcome.",
        "Show stakeholder confirmation of YOUR framing — you defined the problem, they validated it.",
        "Don't sell heroics; sell structure.",
    ],
    common_pitfalls=[
        "'I just figured it out' without showing the structure",
        "No explicit definition-of-done",
        "Choosing without stakeholder confirmation — easy to choose the wrong problem",
        "No quantified outcome",
    ],
    follow_up_questions=[
        "What if stakeholders had disagreed with your framing?",
        "How do you stay focused when scope keeps shifting?",
        "Have you ever locked in the WRONG framing and had to pivot?",
    ],
    what_look_for=[
        "Decomposition of ambiguity",
        "Stakeholder synthesis (not 1 source)",
        "Definition-of-done invention",
        "Structured execution",
    ],
    tags=["ambiguity", "stakeholder-management", "framing"],
    categories=["Adaptability", "Decision Making", "Amazon Leadership Principles"],
)


# Aggregate
_BASE_BQS = [LP_01, LP_02, LP_03, LP_04, LP_05, LP_06, LP_07, LP_08, LP_09,
             LP_10, LP_11, LP_12, LP_13, LP_14, LP_15, LP_16, LP_17]


def _load_more():
    """Auto-discover extra BQs in `bq_more/`. Each module exports `PAYLOAD`."""
    import importlib
    import pkgutil
    extras = []
    try:
        from . import bq_more as _pkg  # type: ignore
    except Exception:
        return extras
    for mod_info in pkgutil.iter_modules(_pkg.__path__):
        mod = importlib.import_module(f"{_pkg.__name__}.{mod_info.name}")
        payload = getattr(mod, "PAYLOAD", None)
        if isinstance(payload, dict):
            extras.append(payload)
    return extras


ALL_BQS = _BASE_BQS + _load_more()
