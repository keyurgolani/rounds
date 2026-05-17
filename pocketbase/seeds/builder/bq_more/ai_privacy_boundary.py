"""BQ: Privacy boundary — deciding what's safe to send to an external model."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Privacy Boundary — What's Safe to Send to an External Model",
    "How do you decide what's safe to send to an external AI model and what isn't? Walk me through a recent decision.",
    situation=(
        "Two months ago, my team — payments infrastructure at a fintech — was rolling out an "
        "internal AI assistant for debugging production incidents. The pitch was straightforward: "
        "engineers paste a stack trace, a few log lines, and a hypothesis; the assistant searches "
        "internal runbooks, recent post-mortems, and similar past incidents, then suggests the "
        "next debugging step. The proposed implementation routed everything through Claude's "
        "public API. The platform team had already done a security review and approved it for the "
        "infrastructure-engineering org. I was asked to approve rollout to my payments team."
    ),
    task=(
        "I owned the call on whether my team could use this assistant during production "
        "debugging. The platform-team approval was real but generic — they hadn't analyzed "
        "payments-specific data. My job was to figure out whether the data flow as designed was "
        "safe for OUR domain, where 'a few log lines' might contain customer payment metadata, "
        "merchant identifiers, or fragments of card-related context."
    ),
    action=(
        "I worked through a concrete data-flow analysis before approving anything. "
        "First, I enumerated what payments engineers actually paste into a debugging tool in "
        "practice. I asked five engineers to send me a sanitized example of the last log "
        "snippet they'd pasted into a Slack channel for help. Three of the five contained merchant "
        "IDs (PII under our agreements). One contained a truncated card-token (not PAN, but "
        "considered sensitive under our customer contracts because the truncation pattern was "
        "reversible against an internal ledger). One was clean. So the realistic data flow wasn't "
        "'stack traces' — it was 'stack traces plus whatever context the engineer pasted to make "
        "the model actually useful.' "
        "Second, I mapped the contractual and regulatory constraints. Merchant IDs and card "
        "tokens were both in the 'must not leave first-party infrastructure' category in our "
        "vendor agreements. The proposed flow would have violated those contracts. The platform "
        "team's review hadn't surfaced this because their team didn't handle either category. "
        "Third, I proposed an alternative rather than just blocking. I drafted three options for "
        "my team: (a) opt out entirely, (b) run the assistant only against fully-redacted snippets "
        "(engineer responsibility, easy to violate accidentally), (c) deploy a payments-specific "
        "version that routed through our internal LLM proxy, which already had a PII scrubber and "
        "would have logged every call for audit. I pushed for (c) and got buy-in from my skip-level "
        "and the platform-team lead. We held my team out of the rollout for three weeks while the "
        "proxy work shipped. "
        "Fourth, I named what I would NOT do: I would not approve 'engineers please remember to "
        "redact before pasting.' Human-redaction-as-a-control is a known-broken pattern under "
        "deadline pressure. The control had to be technical or it didn't exist. "
        "I documented the decision in a one-page memo so the next person facing the same question "
        "didn't have to redo the analysis. The memo named the three data categories, the contract "
        "clauses they implicated, and the criteria a proposed flow had to meet to be approvable."
    ),
    result=(
        "Three weeks later my team came online via the proxy. Zero PII-exfiltration incidents in "
        "the 11 weeks since. Two other teams (treasury, fraud) reused the same decision memo to "
        "make their own approval calls — both ended up needing the proxy route too. The platform "
        "team folded the memo's criteria into their default rollout checklist so new teams "
        "couldn't get approved without explicit data-category analysis. "
        "What I'd defend in an interview: the right framing for AI privacy isn't 'is this model "
        "secure?' but 'what data am I actually committing to send, given how engineers will use "
        "this tool under real-world pressure?' The hard part is being honest about the *realistic* "
        "data flow, not the *advertised* one. I learned to start every AI integration review with "
        "'show me five real examples of the input,' not 'show me the architecture diagram.' I also "
        "learned that 'just remind people to redact' is not a control — it's an aspiration."
    ),
    key_strengths=[
        "Safe & responsible AI use",
        "Concrete data-flow analysis",
        "Distinguishing advertised flow from realistic flow",
        "Proposing alternatives, not just blocking",
        "Systemic documentation that scaled the decision",
    ],
    framework_tips=[
        "Lead with the REAL data flow (what engineers actually paste), not the architecture diagram",
        "Map data categories to contracts/regulations explicitly — don't hand-wave 'sensitive data'",
        "Reject human-redaction-as-a-control — the control has to be technical to count",
        "Propose alternatives so you're not just the 'no' person",
        "Write the decision down so others don't redo the analysis",
    ],
    tips=[
        "Have a story where the privacy concern was REAL but the AI use case was legitimate — Meta is testing judgment, not paranoia",
        "Name the specific data category (PII, PHI, card data, IP) and the constraint that applied",
        "Show that you proposed a path to YES, not just a block",
        "Mention the documentation/memo so the decision scales beyond your team",
        "Be ready for 'where do you draw the line?' — have a framework, not anecdotes",
    ],
    common_pitfalls=[
        "Sounding maximalist — 'never send anything external' isn't a position Meta will reward",
        "Missing the 'realistic flow vs advertised flow' gap — Meta engineers see this gap constantly",
        "Approving human-redaction as a control",
        "Not having an alternative path — pure blocking is weak leadership signal",
        "Vague references to 'compliance' or 'security' without naming the specific constraint",
    ],
    follow_up_questions=[
        "Where in your current workflow do you allow external models, and where don't you?",
        "How would you train a new engineer to make this decision themselves?",
        "What's a case where you said yes to an external model that you later regretted?",
        "How do you handle the gray-area cases (e.g. internal docs that might contain customer names)?",
        "Have you ever caught a teammate sending data they shouldn't have? What did you do?",
    ],
    what_look_for=[
        "Realistic data-flow analysis (what engineers actually paste)",
        "Specific data category and constraint named",
        "Technical control rather than aspirational policy",
        "Constructive alternative proposed, not pure block",
        "Documentation that scales the decision",
    ],
    tags=[
        "safe-and-responsible-ai",
        "privacy",
        "ai-judgment",
        "data-flow-analysis",
        "ai-driven-impact",
    ],
    categories=["AI Collaboration", "Decision Making"],
)
