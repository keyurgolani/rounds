"""BQ: Said no to a stakeholder — defending engineering quality."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Said No — Defending Engineering Quality",
    "Tell me about a time you had to say no to a stakeholder. How did you handle it?",
    situation=(
        "Our PM wanted to ship a new internal-data export feature in 2 weeks for a customer pilot. "
        "The feature would expose tenant-scoped CSV exports of usage data. The catch: the proposed "
        "first version would skip authentication and rely on 'unguessable' signed URLs because adding "
        "authn 'would slip the pilot by 3 weeks.' Five customers were waiting; the PM had already "
        "named a date externally."
    ),
    task=(
        "I was the tech lead on the service. I had to decide whether to build what the PM asked for "
        "or push back, knowing he'd already committed a date and that 'no' would create real "
        "friction with both him and his customer relationships."
    ),
    action=(
        "I declined to ship it without authn, but I did not just say no. First I named the trade-off "
        "explicitly in writing: 'unguessable URLs' is security-by-obscurity; logs, browser history, "
        "Slack pastes, and proxy caches all leak them, and the export contains tenant-identifiable "
        "data — a single leak is a customer-trust incident, not a bug. I framed the cost in the "
        "PM's terms: 'one leaked URL is a worse outcome for these five pilot customers than a 3-"
        "week slip.' Second, I proposed an alternative phased rollout: week 1-2, ship the export "
        "engine behind our existing authn with a CLI-only interface for the pilot customers (they "
        "already had API tokens); week 3-5, ship the UI on top with proper session auth; week 6, "
        "open to GA. That collapsed his slip from 3 weeks to ~1 week and kept all five pilots on "
        "track. Third, I went to the PM 1:1 BEFORE the team standup so he didn't feel cornered in "
        "front of engineers. I said: 'I'm going to push back on shipping without authn — here's why "
        "and here's what I'm proposing instead.' He pushed back hard initially. I held the line on "
        "authn-from-day-1 but conceded on UI scope and on shipping CLI-first to pilots. We brought "
        "the proposal to our director together; I let the PM present the timeline, I presented the "
        "security framing. Director backed the phased plan."
    ),
    result=(
        "We shipped CLI export with authn at week 2 (1 week late vs the original promise). All five "
        "pilots onboarded successfully — 4 of 5 used the CLI from day 1; only 1 needed the UI. UI "
        "shipped at week 5. Six weeks post-launch, our security team ran a routine audit; one of "
        "the things they specifically called out as 'done right' was that exports had been authn-"
        "gated from launch, because two competitor products had had signed-URL leak incidents in "
        "that window. The PM later told me he'd been wrong on this one and added me to the "
        "spec-review list for future data-export features. I learned that 'no' lands when you "
        "name the trade-off in the stakeholder's own units (customer trust, not 'security'), "
        "propose a credible alternative, and protect the stakeholder's social position while "
        "holding the technical line."
    ),
    key_strengths=[
        "Backbone",
        "Trade-off thinking",
        "Stakeholder management",
        "Constructive alternative",
    ],
    framework_tips=[
        "Name the trade-off in the stakeholder's own units, not engineering jargon",
        "Always pair 'no' with a concrete alternative path",
        "Push back 1:1 before going public — protect the stakeholder's social position",
        "Hold the line on the principle; concede on scope/timeline where you can",
    ],
    tips=[
        "Pick a story where 'yes' would have been a real bad outcome, not a stylistic preference.",
        "Show you talked to the stakeholder privately first — not blindsided in a meeting.",
        "Show the alternative you proposed; 'no' without an alternative is just opposition.",
        "Include a follow-up signal that your call was right (audit, incident in industry, etc).",
    ],
    common_pitfalls=[
        "'No' without a constructive alternative — sounds like blocking, not leadership",
        "Embarrassing the stakeholder publicly instead of aligning 1:1 first",
        "Picking a stylistic 'no' (code style, framework choice) instead of a quality/trust 'no'",
        "Not naming the trade-off in business or customer terms",
        "Conceding on the principle to keep the relationship — that's not backbone",
    ],
    follow_up_questions=[
        "What if the PM had escalated and leadership had overruled you?",
        "How do you decide which 'no's are worth fighting and which to let go?",
        "How did you rebuild the relationship with the PM afterwards?",
        "Have you ever said no and later realised you were wrong?",
    ],
    what_look_for=[
        "Trade-off framed in customer / business terms, not engineering aesthetics",
        "Concrete alternative proposed alongside the no",
        "Stakeholder relationship preserved — 1:1 first, joint presentation",
        "Willingness to concede on scope while holding on principle",
        "Evidence the call was right (post-hoc validation)",
    ],
    tags=["no", "backbone", "scope", "stakeholder"],
    categories=["Communication", "Decision Making", "Amazon Leadership Principles"],
)
