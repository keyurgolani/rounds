"""BQ: Frugality — accomplishing more with less by reusing existing infrastructure."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Frugality - Doing More With Less",
    "Tell me about a time you achieved a major outcome with very limited resources.",
    situation=(
        "Our platform team was running 14 production services with no unified observability. "
        "Pages were noisy, on-call burnout was real, and dashboards were scattered across three "
        "internal tools that none of us trusted. Engineering leadership asked me to scope a "
        "monitoring solution for the org. The vendor shortlist had landed on a popular SaaS "
        "observability product quoted at $50K/year for our seat count plus an estimated $15K/year "
        "in ingestion overage based on our log volume. At the same time, we were one approved "
        "headcount short of hiring a senior SRE the team had been waiting on for two quarters — "
        "and the budget envelope was effectively zero-sum: the SaaS spend would come out of the "
        "headcount line. I had a hard constraint of about six engineer-weeks of my own time and "
        "no incremental budget to spend."
    ),
    task=(
        "I had to deliver unified, trustworthy monitoring for the 14 services without spending "
        "the $50K/year that would block the SRE hire. The bar wasn't 'cheaper than the SaaS' — "
        "it was 'good enough that the team would actually use it,' because a monitoring tool that "
        "people don't trust is worse than no tool at all. My goal was to deliver this with what we "
        "already had, in a timeframe that didn't push out the rest of the roadmap."
    ),
    action=(
        "I started by listing what we already paid for. We were on AWS and already had CloudWatch "
        "metrics emitting from every service, CloudWatch Logs ingesting from our containers, and "
        "an existing Lambda fleet for various automation jobs. The SaaS pitch had been 'one place "
        "for everything,' but I noticed the underlying signals were already in our account — we "
        "just had no consolidated view. "
        "I scoped a 5-week build with explicit cuts. Week 1: I interviewed the four most-frequent "
        "on-call engineers and asked exactly two questions — 'what's the first dashboard you open "
        "during an incident?' and 'what alert wakes you up that you wish was filtered?' Their "
        "answers gave me a tight scope: a single per-service dashboard with five panels (error "
        "rate, p99 latency, saturation, dependency health, recent deploys) and three alert "
        "categories that mattered. Everything else could wait. "
        "Week 2-3: I built the dashboard generator as a Lambda. It read service metadata from our "
        "existing service registry, queried CloudWatch metrics, and rendered a CloudWatch dashboard "
        "per service via the AWS SDK. Treating dashboards as code meant adding a service was a "
        "one-line change — no manual UI clicks. I used CloudWatch Composite Alarms to roll up the "
        "noisy individual alerts into a single 'service unhealthy' signal per service, which cut "
        "page volume dramatically without losing fidelity. "
        "Week 4: I added the deploy-correlation overlay. We already emitted deploy events to an SNS "
        "topic; I subscribed a Lambda that wrote them as CloudWatch metric annotations. Now every "
        "dashboard showed deploy markers next to the latency lines — the single feature engineers "
        "told me later they used most. "
        "Week 5: I wrote a one-page runbook, ran a 30-minute walkthrough with each on-call rotation, "
        "and shipped a Slack bot (40 lines, also a Lambda) that posted the relevant dashboard link "
        "into the incident channel when a Composite Alarm fired. "
        "I deliberately did NOT build: log search (CloudWatch Logs Insights was already there, just "
        "underused — I documented it instead), distributed tracing (we'd revisit if the SaaS gap "
        "showed up in real incidents), or custom anomaly detection (the SaaS's headline feature, "
        "but our incidents were almost all caught by simple thresholds). I framed the cuts honestly "
        "in a one-pager to my director: 'this won't match the SaaS feature-for-feature; here are "
        "the three gaps and the cost of buying them later if we need to.'"
    ),
    result=(
        "Page volume dropped by roughly 60% in the first month, mostly from the Composite Alarm "
        "rollups. Mean time to dashboard during an incident went from 'whichever tool we remember' "
        "to ~10 seconds via the Slack bot link. Direct savings on the SaaS line: $50K/year in "
        "subscription plus the ~$15K/year overage we'd projected — about $65K/year. Build cost: "
        "~5 engineer-weeks of my time and about $40/month in Lambda + CloudWatch dashboard charges. "
        "The freed budget covered the senior SRE hire we'd been waiting on; she joined the following "
        "quarter and is now the on-call lead. Six months in, two of the three deferred features "
        "(tracing, anomaly detection) still hadn't surfaced as real gaps in post-incident reviews; "
        "we revisited tracing for one specific service and added it narrowly with AWS X-Ray rather "
        "than buying it broadly. The dashboard generator was adopted by two adjacent teams and is "
        "now the org default. "
        "I learned three things. First, frugality is mostly about noticing what you already pay "
        "for — the CloudWatch signals had been there the whole time; the gap was a consolidating "
        "view, not the underlying data. Second, the strongest argument against an expensive tool "
        "is a working alternative, not a spreadsheet — the dashboard generator was the proposal. "
        "Third, naming the deferred features explicitly (with cost-to-add-later) made the trade-off "
        "honest and made the decision easy to revisit if the gaps turned real."
    ),
    key_strengths=["Resourcefulness", "Creativity", "Pragmatism", "Scope discipline", "Build-vs-buy judgment"],
    framework_tips=[
        "Inventory what you already pay for before proposing new spend — the signal is often already there",
        "Frame the build as 'consolidating existing infrastructure,' not 'replacing the vendor'",
        "Cut features explicitly and name the deferred ones with cost-to-add-later",
        "Quantify both the savings AND the build cost — frugality stories need both numbers",
        "Tie the savings to a concrete reallocation (a hire, a project) — dollars in a budget feel abstract",
        "Show the working alternative IS the proposal — concrete beats spreadsheet",
    ],
    tips=[
        "Frugality isn't 'I worked harder' or 'I bought the cheap option' — it's 'I got the same outcome from less.'",
        "Quantify in dollars AND in opportunity cost (the hire, the deferred project).",
        "Name what you cut and why those cuts were safe — not naming the cuts hides the trade-offs.",
        "Show off-the-shelf reuse (CloudWatch + Lambda) over custom code — that IS the frugality.",
        "Pick a story where the deferred features stayed deferred — proves the cuts were right, not lucky.",
        "Don't pretend the build was free — show the engineer-weeks honestly.",
    ],
    common_pitfalls=[
        "Heroics narrative — '80-hour weeks built it cheap'",
        "No quantified savings — 'we saved a lot' isn't a number",
        "Not naming what was cut — hides whether the trade-off was real",
        "Building custom when an existing tool would have done the job — that's the opposite of frugality",
        "Saving money on something that mattered (data loss, security) — frugality on the wrong axis",
        "No reallocation story — saved dollars that just sat in the budget aren't a result",
    ],
    follow_up_questions=[
        "How would you have argued for the SaaS if the in-house build had failed?",
        "What if one of the deferred features (tracing, anomaly detection) had turned into a real incident?",
        "How do you decide when to build vs buy in general?",
        "Have you ever been frugal in a way that backfired?",
        "How did you handle pushback from people who wanted the SaaS?",
        "What would you do differently if you ran this again?",
    ],
    what_look_for=[
        "Inventory of existing resources before proposing new spend",
        "Explicit scope cuts with named trade-offs",
        "Quantified savings tied to concrete reallocation (hire, project)",
        "Off-the-shelf reuse over custom code",
        "Honest accounting of build cost (engineer-weeks, ongoing ops)",
        "Durable adoption beyond the original team",
    ],
    tags=["frugality", "resourceful", "cost", "creativity", "build-vs-buy", "cloudwatch", "lambda"],
    categories=["Cost Awareness", "Innovation", "Amazon Leadership Principles"],
)
