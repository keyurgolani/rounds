"""BQ: Decided NOT to use AI when you could have."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Decided NOT to Use AI — Knowing When to Stay Hands-On",
    "Tell me about a time you decided NOT to use AI for something you could have. Why?",
    situation=(
        "Our team owned a billing-event pipeline that handled ~12M transactions a day. We hit a "
        "subtle correctness bug: a small fraction of accounts were getting double-charged when a "
        "specific retry path interacted with a deduplication cache. The bug had been live for "
        "11 days before a customer-success engineer noticed a pattern in refund requests. By the "
        "time it surfaced, we had ~$180K in incorrect charges across 2,400 accounts. My job was "
        "root-cause analysis and remediation. Two of my teammates suggested I have Claude pair on "
        "the investigation — it had been productive for similar bugs that month."
    ),
    task=(
        "I needed to find the root cause definitively, build a refund plan, and ship a fix that "
        "wouldn't introduce a worse bug. There were three pressures: (a) the customer-trust hit "
        "compounding each day the bug stayed live, (b) the temptation to ship a patch fast without "
        "understanding the actual mechanism, and (c) the cultural pressure to 'just use AI' as the "
        "default investigation tool."
    ),
    action=(
        "I deliberately worked through this one without an LLM in the loop. I'll defend the reasoning: "
        "the bug involved state interactions across three services (the event producer, the dedup "
        "cache, and the billing consumer) over a several-second window during retries. To find the "
        "root cause I needed to hold a precise mental model of the timing, what was in the cache "
        "at each step, and which idempotency key was being checked. I'd seen Claude be confidently "
        "wrong about race conditions a few weeks earlier — it generated plausible-sounding "
        "explanations that turned out to be impossible given the actual lock ordering. For a bug "
        "this expensive (real customer money), 'confidently wrong' was the most dangerous failure "
        "mode I could introduce. "
        "I instead worked the problem the slow way: pulled six hours of structured logs around three "
        "confirmed double-charge cases, built a timeline by hand in a spreadsheet, and stared at "
        "it until I saw the pattern — the retry was firing before the dedup cache acknowledged the "
        "first write, so both attempts cleared the dedup check. That took me about four hours; an "
        "LLM might have proposed it in five minutes, but I wouldn't have *trusted* the proposal "
        "enough to act on it without doing the timeline work anyway. "
        "I did use AI for two narrowly-scoped tasks later in the day. First, when I drafted the "
        "customer-facing apology email, I had Claude critique the tone — that was safe because I "
        "was the source of truth on the technical content and just wanted a second read on the "
        "register. Second, when I wrote the post-mortem, I had Claude check that I'd covered the "
        "standard sections (timeline, contributing factors, action items, follow-up owners). I "
        "narrated both of these out loud to my skip-level so it was clear which tasks I'd kept "
        "for myself and which I'd delegated. "
        "On the fix itself I went the conservative route: a two-step idempotency check that "
        "verified both the cache state AND the consumer-side ledger before acknowledging the "
        "transaction. I considered the simpler one-line patch Claude would have proposed, but the "
        "two-step check was easier to reason about under load and gave us a fallback when the "
        "cache was warming."
    ),
    result=(
        "Root cause identified in one day. Refund process for 2,400 accounts ran cleanly the next "
        "day. The fix shipped 36 hours after my investigation started; we verified it against a "
        "replay of the original failure window in staging and saw zero duplicate events. No "
        "recurrences in the 11 weeks since. The post-mortem became a reference doc for the team. "
        "What I'd defend in an interview: this was the right call. The bug demanded a precise "
        "mental model that I needed to hold myself, and the cost of an LLM being plausibly-wrong "
        "was real customer money. AI is a force multiplier on tasks where the verification cost "
        "is low (you can run the code and see if it works) and dangerous on tasks where "
        "verification cost is high (race conditions, distributed-system invariants, financial "
        "correctness under retry). I learned to ask myself before delegating: 'if the model is "
        "confidently wrong here, what does that cost me — and can I detect it?' For this bug, "
        "the answer was 'a lot' and 'not quickly enough.' For the tone of a customer email, "
        "the answer was 'almost nothing' and 'yes.' Different tasks, different defaults."
    ),
    key_strengths=[
        "Judgment on when AI is appropriate",
        "Verification-cost reasoning",
        "Resisting cultural pressure to default to AI",
        "Holding a precise mental model",
        "Narrating AI choices transparently",
    ],
    framework_tips=[
        "Lead with the verification-cost question: if the AI is wrong, can you detect it quickly?",
        "Distinguish tasks where AI is a force multiplier from tasks where it's a risk amplifier",
        "Name the specific failure mode you were avoiding (confidently-wrong race-condition explanation)",
        "Show that you DID use AI elsewhere in the same situation — proves your refusal was reasoned, not reflex",
        "Explicitly tell the interviewer you narrated your choice to your manager",
    ],
    tips=[
        "Have ONE crisp story where you refused AI deliberately — Meta asks this often and candidates fumble it",
        "The strongest framing is 'verification cost was too high', not 'I didn't trust AI'",
        "Pair this story with a counterpart where you DID use AI — shows you have judgment, not bias",
        "Quantify the cost of being wrong (customer money, downtime, compliance) — vague risk doesn't land",
        "Mention you narrated the choice to a peer or manager — Meta values visible judgment",
    ],
    common_pitfalls=[
        "Sounding like a Luddite — 'I don't trust AI' is the wrong frame",
        "Picking a task where AI would clearly have been fine (e.g. naming variables) — the refusal needs to be substantive",
        "Skipping the verification-cost analysis — Meta will probe 'why was this different from a task you DO delegate?'",
        "Not having a paired example of using AI well in the same situation",
        "Framing it as a personal preference instead of an engineering decision",
    ],
    follow_up_questions=[
        "What would have changed your mind and made you delegate this to AI?",
        "Have you ever delegated a task you should have kept and regretted it?",
        "Where DO you default to AI on your current team?",
        "How did you communicate this choice to teammates who wanted you to use AI?",
        "How do you decide the line in general?",
    ],
    what_look_for=[
        "Reasoned framework for delegation, not anti-AI bias",
        "Specific failure mode the candidate was avoiding",
        "Verification-cost reasoning",
        "Evidence the candidate uses AI well elsewhere",
        "Transparent communication of the choice to the team",
    ],
    tags=[
        "ai-judgment",
        "safe-and-responsible-ai",
        "verification-cost",
        "tool-discipline",
        "ai-driven-impact",
    ],
    categories=["AI Collaboration", "Decision Making"],
)
