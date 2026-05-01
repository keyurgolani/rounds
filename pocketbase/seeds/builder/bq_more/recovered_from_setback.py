from builder.bq_questions import _bq

PAYLOAD = _bq(
    "Resilience — Bounced Back From a Setback",
    "Tell me about a time you bounced back from a setback.",
    situation=(
        "Eight months into leading a 7-engineer effort to build a real-time pricing engine for our "
        "marketplace, the company pivoted away from dynamic pricing after a regulatory inquiry into "
        "an adjacent industry spooked our legal team. The project was canceled with one sprint left "
        "before the planned beta. We'd burned ~$1.2M of eng time, my team was demoralized, two senior "
        "engineers were openly talking about leaving, and I was personally crushed — I'd staked my "
        "promotion case on this launch."
    ),
    task=(
        "As tech lead I had three problems stacked on top of each other: a team in grief, a body of "
        "work that needed to be salvaged or shelved cleanly, and my own morale. I had to figure out "
        "what to do for the team first, the work second, and myself third — in that order — without "
        "letting my disappointment leak into how I led."
    ),
    action=(
        "I gave myself 48 hours to be unproductive. I told my manager I needed two days to process; "
        "I went on long walks, wrote in a private doc what I was actually feeling, and didn't make "
        "any decisions. On day 3 I came back with a plan. First, I held a 1:1 with each of the 7 "
        "engineers — not a group meeting, because group meetings let people hide. I asked each one "
        "two questions: 'what do you want to do next?' and 'what would make you regret leaving?' "
        "The two flight risks both said the same thing: they wanted to feel their 8 months hadn't "
        "been wasted. So I built a salvage plan: I went line-by-line through the codebase and "
        "identified four components that had standalone value — the feature store, the experiment "
        "framework, the streaming aggregator, and the rules engine. I pitched each to a different "
        "team that could absorb it. Three of the four were adopted within a month; I made sure the "
        "engineer who'd built each one was credited and got to do the handoff. Second, I wrote a "
        "post-mortem that was honest about what we'd built well AND what the cancellation taught us "
        "about reading regulatory wind early — I shared it openly so the lessons compounded across "
        "the org instead of dying with the project. Third, I rebuilt my own promo case around "
        "leading-through-cancellation rather than launching-the-thing; my manager helped me reframe "
        "the narrative with concrete artifacts (the salvage plan, the retention outcome, the "
        "post-mortem). Fourth, I asked for and took on a smaller, scoped project — a 6-week "
        "internal-tools cleanup — specifically to give myself a near-term win after the long loss."
    ),
    result=(
        "Both flight-risk engineers stayed; one of them later said the salvage handoff was the "
        "reason. Three of four salvaged components shipped inside other teams' products within a "
        "quarter — the feature store became the foundation for a recommendation system that drove "
        "$2.4M in incremental revenue the following year. My post-mortem was cited in a company-"
        "wide doc on regulatory risk-reading that the legal team co-authored. I was promoted on the "
        "next cycle — not in spite of the cancellation, but because of how I'd handled it; the "
        "promo committee specifically called out the reframed narrative. Personally, I learned that "
        "resilience isn't 'pushing through' — it's giving yourself permission to be knocked down "
        "for a bounded period, then making deliberate choices about what to rebuild and in what "
        "order. Team first, work second, self third turned out to be the right sequence; if I'd led "
        "with my own ego repair I'd have lost the engineers."
    ),
    key_strengths=[
        "Emotional regulation under loss",
        "Team-first leadership in grief",
        "Salvaging value from canceled work",
        "Narrative reframing for self and stakeholders",
    ],
    framework_tips=[
        "Give yourself a bounded period to feel the loss — don't perform stoicism",
        "Sequence the recovery: team first, work second, self third",
        "Salvage is leadership work — find the standalone value and broker the handoff",
        "Reframe the narrative explicitly with artifacts, not vibes",
        "Engineer a near-term scoped win to break the loss-streak feeling",
    ],
    tips=[
        "Pick a real setback — canceled project, layoff, PIP, missed promo. 'My feature shipped late' isn't a setback.",
        "Show the 48-hour 'allow yourself to be knocked down' beat — interviewers respect honesty over fake stoicism.",
        "Sequence the recovery explicitly: team / work / self. Most candidates lead with self; that's the tell.",
        "Quantify the bounce-back — retention, salvaged value, dollars, promo outcome.",
        "Show the reframe of your own narrative with concrete artifacts, not just 'I changed my mindset.'",
        "Distinguish 'resilience' (bounced back with new structure) from 'grit' (kept doing the same thing harder).",
    ],
    common_pitfalls=[
        "Performative stoicism — 'I wasn't really upset' rings false and hides the actual skill",
        "Self-first sequencing — 'I rebuilt my own confidence and then helped the team' loses interviewers",
        "No salvage work — a canceled project where nothing was rescued shows learned helplessness",
        "Generic 'I learned to be resilient' takeaway with no behavioral change",
        "Picking a setback that's actually a humblebrag ('I didn't get the promo I deserved')",
        "Skipping the team-impact dimension when the setback affected others, not just you",
    ],
    follow_up_questions=[
        "What did you actually do during those 48 hours of being unproductive?",
        "How did you handle the engineer who DID end up leaving — or did everyone really stay?",
        "Have you ever NOT bounced back from a setback? What was different?",
        "How do you tell the difference between 'time to push through' and 'time to let it go'?",
        "What would you do differently if a similar cancellation happened tomorrow?",
    ],
    what_look_for=[
        "Honest acknowledgment of the emotional impact (not performed toughness)",
        "Sequenced recovery showing team-first instinct under pressure",
        "Concrete salvage / value-preservation actions vs passive grief",
        "Durable behavior change — they handle the next setback differently",
        "Calibrated narrative — neither catastrophizing nor minimizing the loss",
    ],
    tags=["resilience", "setback", "grit", "recovery"],
    categories=["Self-Awareness", "Mental Toughness", "Amazon Leadership Principles"],
)
