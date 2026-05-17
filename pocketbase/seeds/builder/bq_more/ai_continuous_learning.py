"""BQ: Continuous AI Learning — adopted a new tool or workflow recently."""
from builder.bq_questions import _bq


PAYLOAD = _bq(
    "Continuous AI Learning — Adopted a New Tool or Workflow",
    "Tell me about a tool or workflow you adopted in the last six months. What changed in how you work?",
    situation=(
        "About four months ago I was the lead on a perf-engineering project — getting our "
        "checkout API's p99 from 480ms down to under 250ms. The work was bottlenecked on profile "
        "analysis: we'd capture a flame graph, I'd spend an hour or two reading it, propose a "
        "hypothesis, the team would prototype a fix, we'd re-profile. The cycle was 1-2 days per "
        "hypothesis. We had a quarter to ship; at that cycle time we'd test maybe six hypotheses, "
        "not enough."
    ),
    task=(
        "I wanted to compress the hypothesis cycle. There were two ways to do it: (a) become "
        "faster at reading flame graphs (years of practice, no help available), or (b) find a "
        "tool that did the first-pass analysis for me so I spent my hour on the second-order "
        "questions, not on visually pattern-matching wide bars."
    ),
    action=(
        "I tried Claude Code with the Anthropic flame-graph plugin specifically for profile "
        "analysis. It was new to me — I'd used Claude for code-writing tasks but not for "
        "analyzing visual / structured profiling artifacts. "
        "First week I deliberately overlapped my work with the tool. I'd read the flame graph "
        "myself, write down my three top hypotheses, then ask Claude to do the same independently. "
        "I compared every time. Claude was right on 7 of 10 hypotheses, partially right on 2, and "
        "wrong on 1 (it proposed a fix that would have helped throughput but hurt p99 — exactly "
        "the metric we were optimizing). I learned the failure mode: Claude was strong at "
        "identifying CPU-bound hotspots but weak at recognizing when a 'small' bar was actually a "
        "latency bottleneck because it was on the critical path of every request. The flame graph "
        "shows time, not latency-criticality. Once I knew this, I learned to pre-filter my prompts: "
        "'analyze this flame graph for p99 latency impact, paying particular attention to small "
        "bars on the critical path' — that single sentence raised the hit rate substantially. "
        "Second, I built a workflow around the tool rather than just using it ad-hoc. The cycle "
        "became: capture profile → run Claude analysis with the prompt template I'd developed → "
        "read its output critically while overlaying it on the actual flame graph → write up my "
        "own three-hypothesis ranking → discuss with team → prototype. The Claude pass was usually "
        "10-15 minutes; my critical-read pass was 20-30 minutes; the writeup was 15. Total: about "
        "an hour per profile, down from two. "
        "Third — and this is what I think the round is actually testing — I changed my mind "
        "about something. I'd previously assumed AI was for code generation and that 'reading' "
        "tasks (profile analysis, log analysis, post-mortem synthesis) were inherently "
        "human-only because they required holding context. The flame-graph experiment taught me "
        "that the bottleneck for me wasn't holding context — it was the visual-pattern-matching "
        "step, which the tool was actually better at. The reasoning step (interpreting in the "
        "context of our system and our optimization goal) is still where I add value. So I "
        "updated my heuristic: 'pattern recognition on structured artifacts' is now a default-AI "
        "task; 'reasoning about why a pattern matters' is still a default-human task. "
        "I shared the workflow with two other senior engineers on adjacent teams. One adopted it "
        "for log-anomaly analysis with similar results; one tried it for designing query plans "
        "and found it less useful (the bottleneck there was domain context, not pattern matching)."
    ),
    result=(
        "We shipped p99 at 230ms by the end of the quarter — beat the goal. We tested 14 "
        "hypotheses instead of the projected 6, which is the main reason we landed. The workflow "
        "became part of how I do perf work generally. "
        "What I'd want the interviewer to hear: I'm not adopting tools out of FOMO. I adopted "
        "this one because it changed the math on a specific bottleneck, and I built a calibrated "
        "trust by running the tool against my own analysis until I knew its failure modes. The "
        "broader update is that I'm now more willing to test AI on tasks I'd previously assumed "
        "were 'human-only' because the reasoning was load-bearing — sometimes the bottleneck is "
        "actually the perceptual step, not the reasoning, and AI is great at perception."
    ),
    key_strengths=[
        "Continuous AI Learning",
        "Calibrated trust building",
        "Updating priors based on evidence",
        "Workflow design (not just tool use)",
        "Knowledge sharing",
    ],
    framework_tips=[
        "Pick a tool you adopted in the last 90 days — Meta wants recency, not 'I learned Copilot two years ago'",
        "Show your calibration process — how you learned the tool's failure modes",
        "Name the SPECIFIC belief or heuristic that changed",
        "Quantify the workflow change, not just the tool feature list",
        "Mention sharing the workflow — Meta values multipliers",
    ],
    tips=[
        "Have ONE recent tool adoption story ready — Meta asks this directly, candidates often fumble for an example",
        "Strongest stories pair a tool with a workflow change, not just 'I started using X'",
        "Be specific about the failure mode you discovered — proves you calibrated trust, not just tried it",
        "The 'belief I no longer hold' framing is gold for this question",
        "Mention the case where the tool DIDN'T transfer — proves you didn't generalize too quickly",
    ],
    common_pitfalls=[
        "Mentioning a tool you adopted years ago — Meta wants 'in the last six months'",
        "Listing features without showing how YOUR workflow changed",
        "Skipping the calibration step — sounds like uncritical adoption",
        "No counterexample — sounds like you don't know when the tool doesn't work",
        "Vague 'I read AI papers / follow newsletters' answers — Meta wants concrete adoption, not browsing",
    ],
    follow_up_questions=[
        "What's the failure mode of the tool you'd warn a teammate about?",
        "What's another tool you tried and DIDN'T adopt? Why?",
        "How do you decide what to invest time in vs let slide?",
        "What's the next tool/workflow on your list to try?",
        "How do you stay current — what's your information diet for AI tooling?",
    ],
    what_look_for=[
        "Recent (90-day) adoption with concrete impact",
        "Calibrated trust process — candidate learned the failure mode",
        "Specific belief or heuristic that changed",
        "Workflow design, not just tool usage",
        "Evidence of sharing / spreading the workflow",
    ],
    tags=[
        "continuous-ai-learning",
        "tool-adoption",
        "calibrated-trust",
        "ai-driven-impact",
        "knowledge-sharing",
    ],
    categories=["AI Collaboration", "Learning & Growth"],
)
