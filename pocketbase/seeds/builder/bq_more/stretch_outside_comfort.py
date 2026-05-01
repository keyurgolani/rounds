"""Learn and Be Curious — stretched significantly outside comfort zone."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Stretched Outside Comfort — Learning a New Domain",
    "Tell me about a time you took on something significantly outside your comfort zone.",
    situation=(
        "I was a backend engineer with 6 years of Java/Go services experience and almost no "
        "frontend background beyond toy HTML. Our company decided to rewrite the customer-facing "
        "dashboard from a legacy AngularJS app to React/TypeScript. The original frontend tech "
        "lead left mid-project; the team was 3 frontend engineers without a senior. My manager "
        "asked if I'd lead the rewrite — not because I knew the stack, but because the project "
        "needed someone who could plan, sequence work, and hold the line on architecture."
    ),
    task=(
        "Lead a 4-month React/TypeScript rewrite I'd never written professionally — own the "
        "architecture, the migration plan, and the technical decisions — without faking expertise "
        "to the engineers who actually knew the stack better than I did."
    ),
    action=(
        "I named the gap on day one in a 1:1 with the team: 'I'm the architect and project lead; "
        "you three are the React experts. I'll be wrong about idioms; tell me when I am.' Then I "
        "built an explicit 6-week learning plan. Week 1-2: I worked through the official React, "
        "TypeScript, and Redux Toolkit docs end-to-end, ~1.5h per evening, and ported a small "
        "internal tool as a sandbox. Week 3-4: I paired daily with each of the three frontend "
        "engineers — 90 minutes, them driving, me asking 'why this pattern?' I kept a running "
        "doc of every idiom that surprised me (hooks closure pitfalls, why Context isn't a state "
        "manager, when memo helps and when it hurts). Week 5-6: I wrote the architecture proposal "
        "— state shape, routing, data-fetching layer — and explicitly asked the team to red-team "
        "it; they pushed back on three decisions and I changed two. I also found an external "
        "mentor (a senior frontend engineer from another team) for a weekly 30-min sanity check "
        "throughout the project. I shipped my own code in small PRs first — a settings page, then "
        "a list view — so the team could review my code as a peer, not as someone unaccountable. "
        "I made a point of merging their critical feedback visibly."
    ),
    result=(
        "We shipped the rewrite on time (4 months) with zero customer-visible regressions in "
        "the first month. Bundle size dropped 38%, p99 page-load from 3.2s to 1.1s. Two of the "
        "three frontend engineers told me in retros that having a non-frontend lead who "
        "explicitly deferred on idioms made the project the most collaborative they'd been on. "
        "I came out of it as a credible full-stack engineer — six months later I led a "
        "follow-up project end-to-end without a frontend co-lead. I learned that the unlock "
        "wasn't 'fake confidence' — it was naming the gap explicitly, then closing it with a "
        "deliberate plan rather than osmosis."
    ),
    key_strengths=["Curiosity", "Adaptability", "Self-driven learning", "Intellectual honesty"],
    framework_tips=[
        "Name the gap explicitly to the team — it earns trust and unblocks honest feedback",
        "Build a written learning plan with weekly milestones, not 'I'll pick it up as I go'",
        "Pair with the experts in your environment AND find an outside mentor for an unbiased view",
        "Ship code in small PRs early so the team reviews you as a peer, not as a manager-from-above",
    ],
    tips=[
        "Show a concrete learning plan — hours per week, sources, milestones — not 'I read some blogs.'",
        "Distinguish 'stretch' from 'reckless' — the stretch should have a credible path to competence.",
        "Show how you handled the dependency on people who knew the domain better than you.",
        "Quantify the outcome — what did the stretch produce, and what new capability do you carry forward?",
    ],
    common_pitfalls=[
        "'I just figured it out' — no visible learning structure",
        "Faking expertise to the team instead of naming the gap",
        "No follow-through — the stretch was a one-off, not a durable capability",
        "Picking a story where the stretch was actually well within your comfort zone",
    ],
    follow_up_questions=[
        "What did you do when the team disagreed with one of your architectural calls?",
        "How did you decide what to learn deeply vs. defer to the experts?",
        "What would you do differently if you had to do it again?",
        "Have you sought out a stretch like this since?",
    ],
    what_look_for=[
        "Deliberate learning structure vs. osmosis",
        "Intellectual honesty about the gap",
        "Use of mentors / pairing without dependency",
        "Durable capability gain, not a one-off",
    ],
    tags=["learn", "stretch", "new-domain", "growth"],
    categories=["Growth", "Adaptability", "Amazon Leadership Principles"],
)
