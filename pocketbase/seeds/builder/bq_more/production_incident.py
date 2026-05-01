"""BQ: Production incident response — calm under fire."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Production Incident — Calm Under Fire",
    "Tell me about a time you handled a high-severity production incident. Walk me through what you did.",
    situation=(
        "On a Tuesday at 14:07 UTC, our checkout service started returning 503s for ~40% of "
        "requests. We were a payments platform processing roughly $2.1M/hour at peak; the "
        "incident hit during the lunch-rush traffic ramp. PagerDuty paged me as the on-call "
        "for the checkout service. Initial signal: write latency to our primary Postgres had "
        "spiked from 8ms p99 to 4.5s, and connection-pool saturation was causing the API "
        "tier to time out. A read-replica had also stopped catching up. Twelve enterprise "
        "customers were already in our support queue."
    ),
    task=(
        "I was the incident commander by rotation. My job: stop the bleeding, coordinate "
        "the responders, own external comms, and make the call on whether to fail over to "
        "the standby Postgres in our DR region — a one-way-ish door because failover "
        "burns ~15 minutes of write availability and replays can lose in-flight transactions."
    ),
    action=(
        "I declared SEV-1 at 14:11 and opened the incident bridge. I assigned roles "
        "explicitly: one engineer on Postgres diagnostics, one on the API tier, one as "
        "scribe in the incident doc. I told the rest of the responders to mute and watch — "
        "five voices on a bridge is noise. I posted a holding statement to the public "
        "status page within 4 minutes ('investigating elevated checkout errors') so "
        "customers knew we'd seen it. Then I ran a tight comms loop: every 10 minutes I "
        "either posted an update or said 'no new information, next update in 10.' That "
        "predictability was deliberate — silence from incident commanders is what makes "
        "customer-success teams panic. "
        "On diagnostics, the Postgres engineer found a runaway analytical query from a "
        "newly-onboarded internal BI tool; it had table-scanned a 400M-row transactions "
        "table with no index hint and had taken an exclusive lock that was queueing "
        "writes. I made three decisions in the first 20 minutes: "
        "(1) kill the query immediately (`pg_terminate_backend`) — fast, reversible; "
        "(2) DON'T fail over yet — the bottleneck was a single query, not the database; "
        "failover would have caused more pain than the bug; "
        "(3) put the BI tool's database user behind a statement_timeout of 30 seconds so "
        "this couldn't recur in the next hour. "
        "Killing the query dropped p99 write latency from 4.5s back to 12ms within 90 "
        "seconds. Connection pools drained. Error rate dropped below 1% by 14:34. I kept "
        "the bridge open for another 30 minutes to confirm stability and then formally "
        "closed the SEV-1 at 15:05. I personally drafted the customer-facing update and "
        "the internal exec summary before logging off — I didn't want a tired engineer "
        "writing those at midnight."
    ),
    result=(
        "MTTR was 27 minutes from page to recovery; total customer-impact window was 58 "
        "minutes including elevated error rate before recovery completed. ~$340K of "
        "transaction volume was deferred or retried; we proactively credited the 12 "
        "enterprise customers who'd opened tickets. In the postmortem (blameless, run by "
        "me 48 hours later) we landed five durable actions: enforced statement_timeout on "
        "all non-OLTP database users, mandatory query review for any new BI integration "
        "touching the transactions table, an automated query-killer for queries holding "
        "exclusive locks > 60s, a runbook entry for 'symptom: write latency spike + "
        "single-query lock' so the next on-call would diagnose in minutes instead of "
        "fifteen, and a quarterly DR-failover drill so the failover decision wasn't "
        "loaded with unfamiliarity. I also coached the BI team's lead on the right way "
        "to onboard analytical workloads — they weren't villains, they hadn't been told "
        "the rules. Eight months on, none of those failure modes have recurred. I "
        "learned that incident command is mostly about making the bridge calm, "
        "predictable, and small — and that the right call is often the most-reversible "
        "one, not the most-aggressive one."
    ),
    key_strengths=["Composure", "Customer Obsession", "Dive Deep", "Communication"],
    framework_tips=[
        "Assign roles on the bridge explicitly; mute everyone else",
        "Set a comms cadence and stick to it — 'no update' is still an update",
        "Prefer reversible mitigations before irreversible ones (kill query > failover)",
        "Don't make the postmortem about the person who wrote the bad query",
        "Land durable actions, not just 'we'll be more careful'",
    ],
    tips=[
        "Pick a real SEV-1 with a measurable customer impact — not a flaky test or a near-miss.",
        "Show the decision to NOT do the dramatic thing (failover, rollback) when it wasn't warranted.",
        "Quantify everything: MTTR, error rate, dollars, number of customers affected.",
        "Show the comms loop explicitly — interviewers care about how you handle stakeholders, not just the bug.",
        "The postmortem actions should be systemic (timeouts, runbooks, drills), not 'I'll be more careful.'",
    ],
    common_pitfalls=[
        "Hero narrative — 'I single-handedly fixed it' (you ran the bridge; the team fixed it)",
        "No comms / customer-impact framing",
        "Postmortem actions limited to 'we added a monitor' with no systemic change",
        "Conflating root cause with blame ('the BI team broke prod')",
        "Picking a story where the right call was obvious — interviewers want to see judgment under pressure",
    ],
    follow_up_questions=[
        "Walk me through how you decided NOT to fail over.",
        "What did you tell customers, and when?",
        "How did you keep the bridge from devolving into chaos?",
        "What was the hardest call you made during the incident?",
        "What did the postmortem reveal that surprised you?",
    ],
    what_look_for=[
        "Calm, structured incident command (roles, cadence, scribe)",
        "Bias toward reversible mitigations under uncertainty",
        "Customer-facing comms as a first-class workstream, not an afterthought",
        "Blameless postmortem with systemic, durable corrective actions",
        "Quantified impact (MTTR, error rate, dollars, customers)",
    ],
    tags=["incident", "oncall", "sev1", "postmortem", "reliability"],
    categories=["Crisis Management", "Operational Excellence", "Amazon Leadership Principles"],
)
