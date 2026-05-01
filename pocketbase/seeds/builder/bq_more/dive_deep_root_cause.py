"""Behavioral Question: Dive Deep — Tracking Down a Subtle Bug.

Story: a 0.1% checkout failure rate that nobody could reproduce, traced via
custom logging to thread-pool exhaustion in a shared library.
"""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Dive Deep — Tracking Down a Subtle Bug",
    "Tell me about a time you debugged a difficult problem that others had given up on.",
    situation=(
        "Our checkout service had a 0.1% failure rate that two engineers had spent a sprint each "
        "investigating and bounced off. The errors were 'connection timed out' from a downstream "
        "payment-tokenisation call, but the downstream team's metrics were green. The bug was "
        "intermittent, never reproduced in staging or load tests, and was distributed across "
        "regions and customer cohorts — no obvious pattern. The official call was 'flaky network, "
        "accept the SLA.' At our scale, 0.1% was about 4,000 lost checkouts per day."
    ),
    task=(
        "Nobody had assigned it to me — the previous owners had moved on and the ticket was tagged "
        "'wontfix.' I didn't believe 'flaky network' for a bug this consistent in shape. I asked my "
        "manager for two weeks to take another pass; if I didn't find anything actionable, we'd "
        "close it for real."
    ),
    action=(
        "I treated it as a scientific-method problem rather than a 'try things' problem. Step 1: "
        "I wrote down every fact we knew (failure shape, distribution, what was green) and every "
        "hypothesis (network, downstream, our code, infrastructure, client retry). Step 2: I ranked "
        "hypotheses by 'what observation would falsify this?' — network flake should correlate with "
        "TCP retransmits (our metrics showed none), downstream issue should show in their p99 "
        "(didn't), client retry should show in request-id duplication (didn't). The remaining "
        "candidates were OUR code or OUR infrastructure. Step 3: existing logs were too coarse — "
        "they recorded the timeout but not the state of the calling process. I added custom "
        "instrumentation: thread-pool occupancy at the moment of timeout, in-flight call count per "
        "thread, time spent waiting for a thread vs in the network call. Deployed to 2% of fleet, "
        "waited 36 hours. Step 4: the data was striking — 100% of timeouts happened when the shared "
        "HTTP-client thread pool was at 100% occupancy. The 'network timeout' was actually a "
        "thread-acquisition timeout that the client library was reporting as a connection timeout. "
        "Step 5: I traced the thread starvation to a shared library used by checkout AND by an "
        "unrelated background reconciliation job that ran every 10 minutes and held threads for "
        "long-running queries. Two services, one thread pool, no isolation. Step 6: I wrote up the "
        "root cause with the data, proposed a fix (separate thread pools per logical workload + a "
        "real timeout on the reconciliation job), and ran it past the library's owners before "
        "writing the patch."
    ),
    result=(
        "Fix shipped in week 3. Checkout failure rate dropped from 0.1% to 0.003% (the residual was "
        "actual network noise). Recovered roughly 4,000 checkouts/day — at our average order value "
        "this was meaningful seven-figure annual revenue. The misleading error message was fixed in "
        "the shared library so future debuggers wouldn't be sent down the same wrong path. I wrote a "
        "post-mortem and a runbook for 'when a metric says network, double-check the thread pool.' "
        "Two unrelated teams later cited the runbook for similar bugs in their services. I learned "
        "that 'flaky' is almost never the real answer — it's the label we put on bugs we haven't "
        "instrumented well enough to see."
    ),
    key_strengths=[
        "Persistence",
        "Methodical thinking",
        "Curiosity",
        "Instrumentation-first debugging",
        "Cross-team root-cause ownership",
    ],
    framework_tips=[
        "List facts and hypotheses explicitly before touching code — debugging is a science problem",
        "For each hypothesis, name the observation that would falsify it",
        "When existing logs aren't enough, add targeted instrumentation rather than guessing",
        "Distinguish the symptom (the error message) from the actual failure mode",
        "Fix the misleading observability too, so the next person isn't misled",
    ],
    tips=[
        "Pick a bug that was genuinely hard — others gave up, the symptom was misleading, the root cause was non-obvious.",
        "Show methodology, not heroics — list of hypotheses, falsifiability, instrumentation, narrowing.",
        "Quantify the impact of finding the root cause (revenue recovered, failure rate before/after).",
        "Show the systemic improvement — a runbook, a fixed error message, a shared learning — not just a one-time patch.",
        "Credit the prior engineers honestly; you had the benefit of their failed attempts narrowing the space.",
    ],
    common_pitfalls=[
        "Hero narrative — 'I worked nights for two weeks and finally cracked it'",
        "Lucky-guess narrative — no method, just intuition",
        "Stopping at the first plausible cause without falsifying alternatives",
        "Fixing the bug but not fixing the misleading signal that caused others to give up",
        "Not quantifying the customer / business impact",
    ],
    follow_up_questions=[
        "What if your two-week timebox had run out without a finding?",
        "How did you decide which hypothesis to instrument for first?",
        "Have you been wrong about a root cause and had to backtrack?",
        "How do you balance 'dive deep' with 'don't ratrhole on a low-priority bug'?",
        "What systemic change came out of this beyond the immediate fix?",
    ],
    what_look_for=[
        "Scientific method — hypotheses with falsification criteria, not guess-and-check",
        "Instrumentation-first reflex when existing data is insufficient",
        "Distinguishing symptom from root cause",
        "Quantified outcome (failure rate before/after, revenue impact)",
        "Systemic improvement that helps future debuggers, not just a point fix",
        "Persistence calibrated to impact — willing to dig where others stopped, but with a timebox",
    ],
    tags=["debugging", "root-cause", "deep-dive", "persistence", "instrumentation", "dive-deep"],
    categories=["Problem Solving", "Technical Excellence", "Amazon Leadership Principles"],
)
