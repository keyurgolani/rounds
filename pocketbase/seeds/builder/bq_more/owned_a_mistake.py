"""BQ: Owned a costly mistake — missed feature flag caused a customer-facing
outage. Maps to Ownership / Earn Trust."""
from __future__ import annotations

from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Ownership — A Mistake You Made and How You Handled It",
    "Tell me about a mistake you made and how you handled it.",
    situation=(
        "I was the on-call engineer rolling out a new pricing engine for our marketplace. The new "
        "engine was behind a feature flag with two scopes: a 'dark-launch' flag that ran the new "
        "engine alongside the old one for shadow comparisons, and a 'serve' flag that actually "
        "returned the new engine's prices to customers. The plan was to dark-launch for 2 weeks, "
        "diff outputs, then flip 'serve' to true for 5% of traffic. I'd written the runbook myself."
    ),
    task=(
        "Flip the dark-launch flag at 9pm on a Wednesday — quiet traffic window — and verify diffs "
        "in the shadow logs the next morning."
    ),
    action=(
        "I flipped the wrong flag. Instead of toggling the dark-launch flag, I toggled the 'serve' "
        "flag to 100%. The new engine started returning prices to every customer. Within 4 minutes, "
        "alerts fired: ~12% of items showed prices that were off by an order of magnitude because "
        "the new engine had a currency-conversion edge case my shadow tests would have caught. "
        "Customers were buying mispriced items in real time. My first reaction was to stare at the "
        "console and silently look for a way to make the bad number not be there. I caught myself "
        "doing that and stopped. Within 90 seconds I (1) rolled back by flipping 'serve' back to "
        "false — which was the right two-way-door action since the old engine was still warm; (2) "
        "paged my manager and the on-call SRE and posted in #incidents: 'I flipped the wrong "
        "flag at 21:04, mispriced traffic for ~6 minutes, rolled back at 21:10, will lead the "
        "post-mortem.' I named it as my error in the first sentence — not 'a flag was flipped' but "
        "'I flipped.' Then I pulled the order log and identified all 847 affected orders. I worked "
        "with finance and customer support overnight to (a) honor the lower prices customers had "
        "already paid (~$11K cost to the company), (b) proactively refund the ~30 customers who'd "
        "been overcharged before they noticed, and (c) draft a customer-facing email I sent the "
        "next morning that said plainly 'we made a mistake, here's what happened, here's what we "
        "did.' For the post-mortem I refused to let it be framed as a 'process gap.' The process "
        "gap was real, but I'd had the runbook open and still picked the wrong flag — that was a "
        "human error I owned. I proposed three durable fixes: rename the flags so 'serve' became "
        "'CUSTOMER_FACING_SERVE_DO_NOT_TOGGLE_WITHOUT_TICKET' and required a typed confirmation; "
        "added a one-line preflight script that printed which flag was about to be toggled and "
        "required y/N; and wrote a checklist for the runbook that required reading the flag name "
        "aloud on a recorded incident bridge before flipping anything customer-facing."
    ),
    result=(
        "Total cost: ~$11K honored prices, ~$3K refunds, 6 minutes of bad pricing for 847 "
        "customers, one apology email. The customer-facing email received a surprising number of "
        "kind replies — 'thanks for being upfront' was a common theme. None of the affected "
        "customers churned in the following quarter (we tracked this). The renamed-flag + "
        "preflight-script change was adopted across the team and prevented at least two similar "
        "near-misses I know of in the following 6 months. My manager's feedback in the next 1:1 "
        "was: 'you owned it before anyone could blame you, and the post-mortem made the team "
        "safer — that's the right pattern.' I learned three things: (1) the instinct to silently "
        "fix-and-hope is real and has to be actively overridden — out-loud comms first, fixing "
        "second; (2) ownership in writing (the email, the post-mortem, the #incidents post) is "
        "what builds trust, not ownership in your own head; (3) the durable fix isn't 'be more "
        "careful' — it's making the wrong action structurally harder."
    ),
    key_strengths=[
        "Immediate ownership without blame-shifting",
        "Transparent customer + internal communication",
        "Root-cause action vs willpower-based fixes",
        "Behavior change that outlasted the incident",
    ],
    framework_tips=[
        "Name the mistake as YOURS in the first sentence — 'I' not 'a flag was'",
        "Communicate before you finish fixing — silence reads as cover-up",
        "Refuse the comfortable framing ('process gap') if the truth is 'I made an error'",
        "Make the wrong action structurally harder — willpower doesn't scale",
        "Close the loop with affected customers explicitly, not just internally",
    ],
    tips=[
        "Pick a real mistake with a real cost — dollars, customers, downtime. 'I once misnamed a variable' is not the question being asked.",
        "Show the immediate emotional reaction (the urge to silently fix) AND the override.",
        "Distinguish ownership-in-comms (visible) from ownership-in-head (invisible). Interviewers want the former.",
        "Show that the durable fix changed the system, not just your resolve.",
        "Don't end on 'I learned to be more careful' — that's not a fix, that's a feeling.",
    ],
    common_pitfalls=[
        "Choosing a 'mistake' that was actually someone else's fault you generously absorbed",
        "Choosing a mistake with no real cost ('a typo in a doc')",
        "Framing the fix as 'I'm more careful now' instead of a structural change",
        "Glossing over the customer-facing communication",
        "Hiding the initial instinct to cover it up — interviewers know you had it; admitting it shows self-awareness",
        "Blaming the runbook / process / tooling instead of yourself",
    ],
    follow_up_questions=[
        "What was your first instinct when you realized what you'd done?",
        "How did you decide what to tell customers vs handle silently?",
        "Have you made the same kind of mistake since?",
        "What would you have done if your manager had wanted to keep it quiet?",
        "Was the cost worth the lessons, or could you have learned them more cheaply?",
    ],
    what_look_for=[
        "Genuine ownership — 'I' language, not 'we' or passive voice",
        "Transparency reflex — proactive comms before being asked",
        "Structural fix vs willpower fix",
        "Customer-trust orientation — proactive refunds, honest email",
        "Self-awareness about the urge to hide and the override",
        "Behavior change that persisted, not a one-time apology",
    ],
    tags=["mistake", "ownership", "accountability", "earn-trust"],
    categories=["Self-Awareness", "Integrity", "Amazon Leadership Principles"],
)
