"""BQ extra: 'Tell me about a time you influenced people without authority' — Earn Trust.

Distinct from 'disagreed with manager' (vertical disagreement) and 'mentored someone'
(growth coaching). This story emphasises horizontal influence: persuading a sister
team to allocate engineering effort to fix a shared infrastructure issue when you
had no formal power over their roadmap, using data, 1:1 alignment, addressing
concerns head-on, and a small pilot to de-risk the ask."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Influenced Without Authority — Building Coalitions",
    "Tell me about a time you had to influence a team or person without direct authority over them.",
    situation=(
        "Two teams at my company — mine (payments) and a sister team (identity) — shared a "
        "library that handled session-token validation. The library had a known thread-safety "
        "bug that surfaced under load: roughly 1 in 50,000 requests would hit a race that "
        "returned a stale token claim, which on our side meant a customer could occasionally "
        "see another customer's order summary for ~200ms before the page corrected itself. "
        "It was rare, it was scary, and it was firmly in the identity team's code — but it had "
        "been on their backlog for three quarters because their leadership prioritised a big "
        "OAuth migration. My team was eating the support tickets. I had no authority over the "
        "identity team's roadmap and their staff engineer had already told me 'we know, it's "
        "queued, please stop pinging us.'"
    ),
    task=(
        "I needed the identity team to allocate ~2 sprints of engineering effort to fix the "
        "bug. I couldn't escalate over them without burning the relationship, and my own "
        "manager didn't have standing to redirect their roadmap. The fix had to come from "
        "their team owning it; my job was to make 'fix this' the obvious next move for their "
        "tech lead and their EM, not an ask they were dodging."
    ),
    action=(
        "I started by getting the data right rather than louder. I pulled six months of our "
        "support tickets, tagged the ones I could correlate to the race (52 of them), and "
        "matched them against trace IDs to confirm the root cause in 47. I quantified blast "
        "radius: 47 confirmed customer-visible cross-account leaks, average resolution time "
        "18 minutes, three of them had escalated to our VP. I wrote a one-page brief — not a "
        "30-page doc — with the data, the root cause (their library, our reproducer), three "
        "fix options ranked by cost, and the option I thought was cheapest for them. Before "
        "sending it anywhere, I booked a 30-minute 1:1 with their staff engineer, the same "
        "person who had told me to stop pinging. I led with 'I think I owe you better data "
        "than I've given you so far' and walked him through the brief. He pushed back on two "
        "things: (a) he didn't believe the leak count was that high, and (b) he was worried "
        "the fix would slip the OAuth migration. On (a) I gave him the trace IDs and offered "
        "to pair on validation. On (b) I proposed a pilot: my team would write the fix as a "
        "PR against their library, run it in our staging for two weeks, and if it held up "
        "they'd just review-and-merge instead of building it themselves — turning a 2-sprint "
        "ask into a 2-day review. I addressed his concern about ownership directly: I told "
        "him I wasn't trying to grab their library, the PR would carry their code style and "
        "their tests, and a named engineer on their team would be the merger of record. Then "
        "I did the same 1:1 with their EM, leading with 'your staff engineer has reviewed "
        "this and these are the open concerns,' so he heard it second from his own person, "
        "not first from me. I built the PR, it passed our staging soak, they merged it 11 "
        "days after my first 1:1. I sent a thank-you in their team channel naming the "
        "specific engineers who reviewed it, not me."
    ),
    result=(
        "The race was eliminated; we tracked zero further cross-account leak tickets in the "
        "following two quarters (down from ~8/month). Their OAuth migration didn't slip — the "
        "fix consumed about 3 engineer-days of their time vs the 2 sprints they had feared. "
        "The bigger durable outcome was the relationship: their staff engineer pinged me "
        "three months later about a different shared concern and opened with 'figured I'd "
        "lead with data this time,' which I took as the actual win. I learned that influence "
        "without authority is mostly about lowering the cost of saying yes — show up with "
        "data instead of urgency, propose the path that's cheapest for the other team, "
        "address their real concerns (not the ones you wish they had), and let them be the "
        "named owner of the outcome."
    ),
    key_strengths=["Persuasion", "Empathy", "Data-driven thinking", "Coalition-building"],
    framework_tips=[
        "Lead with data, not urgency — quantify blast radius before asking for anything",
        "Do the 1:1 alignment BEFORE sending the doc broadly — surprise = pushback",
        "Address the real objections (cost, ownership, roadmap risk), not the ones you wish they had",
        "De-risk the ask with a pilot or pre-built artifact — make 'yes' the cheap path",
        "Let the other team be the named owner of the outcome; credit them publicly",
    ],
    tips=[
        "Pick a story where you had genuinely zero authority — peer team, sister org, external partner.",
        "Show the failed prior attempt or the resistance you started with — otherwise it's not influence, it's just a request.",
        "Quantify the ask's cost from THEIR perspective, not just the impact from yours.",
        "Show explicit buy-in mechanics: who you talked to first, in what order, and why.",
        "Credit the other team in the result — saviour narratives kill the 'earn trust' signal.",
    ],
    common_pitfalls=[
        "Telling a story where you actually did have authority (your direct report, your team)",
        "Skipping the resistance — making it sound like everyone agreed once you asked nicely",
        "Escalating up your chain instead of building peer alignment",
        "Claiming the outcome as yours rather than the other team's",
        "Ignoring the other team's concerns ('I just kept pushing until they caved')",
        "Vague data ('lots of tickets') instead of specifics (47 confirmed, 3 VP escalations)",
    ],
    follow_up_questions=[
        "What if the staff engineer had still said no after the 1:1?",
        "How did you decide it was worth your time to build their fix vs escalating?",
        "How do you avoid the pattern of always being the one who fixes other teams' bugs?",
        "What would you have done differently if the OAuth migration HAD slipped?",
        "How did you handle the relationship after the merge — any follow-through?",
    ],
    what_look_for=[
        "Genuine peer / cross-team context (no formal authority lever)",
        "Data-driven framing of both impact and cost-to-them",
        "Explicit sequencing of buy-in (1:1 before broadcast, engineer before EM)",
        "Concrete de-risking mechanism (pilot, pre-built PR, soak window)",
        "Empathy for the other team's constraints and priorities",
        "Credit-sharing in the outcome and durable relationship payoff",
    ],
    tags=["influence", "cross-team", "persuasion", "earn-trust"],
    categories=["Communication", "Leadership", "Amazon Leadership Principles"],
)
