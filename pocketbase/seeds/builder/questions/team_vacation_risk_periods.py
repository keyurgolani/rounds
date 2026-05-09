"""Team Vacation Overlap — Risk Periods. Hard. Sweep Line / Intervals.

The 'merge intervals with optimization' extension that gets asked once
the basic merge is done. Given each teammate's vacation intervals and
a 'minimum percentage available' threshold, identify the contiguous
date ranges when the team is below threshold. Sweep line on
(start, +1) / (end+1, -1) events, tracked by a running absent-count.
The fence-post bug — using `(end, -1)` for inclusive intervals —
is the single biggest senior-signal trap in this problem."""
from builder.registry import register


PAYLOAD = {
    "title": "Team Vacation Overlap — Risk Periods",
    "difficulty": "Hard",
    "description": (
        "You manage a team and want to know when too many teammates will be on vacation at once.\n\n"
        "Given:\n"
        "- `team_size` — total number of people on the team.\n"
        "- `threshold` — the **minimum fraction** of the team that must be available. A threshold of "
        "`0.6` means a date is *risky* whenever **strictly less than 60%** of the team is present.\n"
        "- `vacations` — a list (one entry per teammate) of vacation intervals `[start_day, end_day]` "
        "(both inclusive, integer day-of-year, 1–366).\n\n"
        "Return the merged, sorted list of contiguous risk periods `[start, end]` (inclusive). A risk "
        "period is a maximal run of consecutive days where strictly less than `threshold * team_size` "
        "teammates are available.\n\n"
        "**Example:**\n"
        "```\n"
        "team_size = 5\n"
        "threshold = 0.6   # we want at least 60% available; flag when fewer\n"
        "vacations = [\n"
        "    [[1, 3], [8, 10]],   # Member 1\n"
        "    [[2, 6]],            # Member 2\n"
        "    [[3, 7], [9, 11]],   # Member 3\n"
        "    [[2, 4]],            # Member 4\n"
        "    [[5, 7], [10, 12]],  # Member 5\n"
        "]\n"
        "Output: [[2, 6], [10, 10]]\n"
        "```\n\n"
        "Day-by-day absent count: `1 3 4 3 3 3 2 1 2 3 2 1`. Risk (absent ≥ 3) on days 2–6 and 10."
    ),
    "hints": [
        "Pure brute force: for every day in the span, count how many teammates have any interval covering it. O(D · M · K) where D is span length, M members, K average intervals per member. Fine for small inputs and easy to get right; document this as your 'first cut'.",
        "Sweep-line is the canonical optimisation. Convert each `[start, end]` into two events: `(start, +1)` and `(end + 1, -1)` — note the `+1` because the interval is *inclusive*. Sort by date.",
        "Running count of absent teammates: walk the events, apply ALL deltas at the same date before deciding. Start a risk period when the count first crosses above the threshold, end it when it drops back.",
        "The threshold-to-absent-count conversion: 'at least `threshold` fraction available' ↔ 'at most `team_size * (1 - threshold)` absent'. Risk = `absent > team_size * (1 - threshold)`. Mind whether the comparison is strict.",
        "Fence-post trap: using `(end, -1)` instead of `(end + 1, -1)` removes the teammate ON their last day, off-by-one on every period boundary. Use a closed-interval convention end-to-end OR convert to half-open at the boundary, but pick one and stick with it.",
        "Don't accumulate floating-point error. With small team sizes the math stays exact, but if you'd rather not depend on that, multiply both sides: `absent * 100 > (100 - threshold_pct) * team_size` keeps everything in integers.",
        "Two events on the same day: a teammate ends a vacation (release) and another starts (acquire). Apply BOTH deltas before evaluating the threshold for that date — otherwise you'll record a transient false-negative.",
    ],
    "constraints": [
        "1 <= team_size <= 10⁵",
        "0.0 <= threshold <= 1.0",
        "0 <= len(vacations) <= team_size",
        "Each member contributes 0+ intervals; total intervals across all members <= 10⁵",
        "Each interval is `[start, end]` with `1 <= start <= end <= 366` (inclusive day-of-year)",
        "Multiple intervals per member may overlap each other (don't assume non-overlap).",
    ],
    "starter_code": {
        "python": (
            "def find_risk_periods(team_size, threshold, vacations):\n"
            "    # Your code here\n"
            "    pass"
        ),
        "javascript": (
            "function findRiskPeriods(teamSize, threshold, vacations) {\n"
            "    // Your code here\n"
            "}"
        ),
        "java": (
            "public int[][] findRiskPeriods(int teamSize, double threshold, int[][][] vacations) {\n"
            "    // Your code here\n"
            "    return new int[][]{};\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(find_risk_periods(5, 0.6, [\n"
            "        [[1,3],[8,10]], [[2,6]], [[3,7],[9,11]], [[2,4]], [[5,7],[10,12]]\n"
            "    ]))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "console.log(findRiskPeriods(5, 0.6, [\n"
            "    [[1,3],[8,10]], [[2,6]], [[3,7],[9,11]], [[2,4]], [[5,7],[10,12]]\n"
            "]));"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        int[][] r = s.findRiskPeriods(5, 0.6, new int[][][]{\n"
            "            {{1,3},{8,10}}, {{2,6}}, {{3,7},{9,11}}, {{2,4}}, {{5,7},{10,12}}\n"
            "        });\n"
            "        for (int[] iv : r) System.out.println(iv[0] + \",\" + iv[1]);\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"team_size": 5, "threshold": 0.6,
                    "vacations": [[[1, 3], [8, 10]], [[2, 6]], [[3, 7], [9, 11]], [[2, 4]], [[5, 7], [10, 12]]]},
         "expected": [[2, 6], [10, 10]],
         "description": "Canonical example — risk on 2–6 and 10",
         "tags": ["basic"]},
        {"input": {"team_size": 3, "threshold": 0.5, "vacations": []},
         "expected": [],
         "description": "No vacations → no risk",
         "tags": ["edge"]},
        {"input": {"team_size": 4, "threshold": 0.5,
                    "vacations": [[[1, 5]], [[1, 5]], [[1, 5]]]},
         "expected": [[1, 5]],
         "description": "Three of four out for the same span — one continuous risk",
         "tags": ["basic"]},
        {"input": {"team_size": 4, "threshold": 1.0,
                    "vacations": [[[10, 12]]]},
         "expected": [[10, 12]],
         "description": "Threshold 100% — any absence is risk",
         "tags": ["edge"]},
        {"input": {"team_size": 4, "threshold": 0.0,
                    "vacations": [[[1, 5]], [[1, 5]], [[1, 5]], [[1, 5]]]},
         "expected": [],
         "description": "Threshold 0% — never risk, even when everyone is out",
         "tags": ["edge"]},
        {"input": {"team_size": 5, "threshold": 0.6,
                    "vacations": [[[1, 1]], [[3, 3]], [[5, 5]]]},
         "expected": [],
         "description": "Single-day vacations, never enough simultaneous absentees",
         "tags": ["basic"]},
        {"input": {"team_size": 3, "threshold": 0.5,
                    "vacations": [[[1, 2]], [[2, 3]], [[2, 2]]]},
         "expected": [[2, 2]],
         "description": "Same-day boundary — multiple events on day 2 must be applied together",
         "tags": ["tricky"]},
        {"input": {"team_size": 4, "threshold": 0.6,
                    "vacations": [[[1, 3], [7, 9]], [[2, 5]], [[3, 4], [8, 10]]]},
         "expected": [[2, 4], [8, 9]],
         "description": "Two disjoint risk periods, each with multiple absentees",
         "tags": ["basic"]},
        {"input": {"team_size": 2, "threshold": 0.6,
                    "vacations": [[[1, 5]], [[3, 7]]]},
         "expected": [[1, 7]],
         "description": "Two-person team — a single absence is risk under 60% threshold (50% < 60%)",
         "tags": ["tricky"]},
        {"input": {"team_size": 5, "threshold": 0.8,
                    "vacations": [[[1, 10]], [[3, 5]]]},
         "expected": [[3, 5]],
         "description": "Threshold 80% — 1 absent OK, 2 absent triggers risk only on overlap",
         "tags": ["basic"]},
        {"input": {"team_size": 3, "threshold": 0.5,
                    "vacations": [[[1, 5]], [[1, 5]], [[1, 5]]]},
         "expected": [[1, 5]],
         "description": "Whole team out — risk for entire span",
         "tags": ["edge"]},
        {"input": {"team_size": 5, "threshold": 0.6,
                    "vacations": [[[1, 3], [2, 4]]]},
         "expected": [],
         "description": "Self-overlapping intervals on one member still count as one absentee per day",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Sweep Line on Inclusive Intervals (Optimal)",
            "time_complexity": "O((I + D) log I) — sort dominated; D is the unique-event count",
            "space_complexity": "O(I) for the events buffer",
            "description": (
                "Convert each interval `[s, e]` into two events: `(s, +1)` and `(e + 1, -1)`. The `+1` "
                "is the fence-post: an inclusive interval ends *after* day `e`, so the decrement fires "
                "on day `e + 1`. Sort events by date. Walk them, applying ALL deltas at the current "
                "date before deciding the threshold — otherwise a release-then-acquire on the same "
                "day creates a phantom dip. Risk fires when the running count crosses the absent "
                "limit; resolves on the day it crosses back. Self-overlapping intervals from one "
                "member must be normalised first (or we double-count them) — the simplest fix is to "
                "merge each member's intervals before generating events."
            ),
            "code": {
                "python": (
                    "def find_risk_periods(team_size, threshold, vacations):\n"
                    "    events = []\n"
                    "    for member in vacations:\n"
                    "        # Merge per-member self-overlaps first so each absent-day counts once.\n"
                    "        intervals = sorted(member)\n"
                    "        merged = []\n"
                    "        for s, e in intervals:\n"
                    "            if merged and s <= merged[-1][1] + 1:\n"
                    "                merged[-1] = (merged[-1][0], max(merged[-1][1], e))\n"
                    "            else:\n"
                    "                merged.append((s, e))\n"
                    "        for s, e in merged:\n"
                    "            events.append((s, 1))\n"
                    "            events.append((e + 1, -1))\n"
                    "    events.sort()\n"
                    "    \n"
                    "    # Strict comparison: risk when absent > limit (so absent=2 with limit=2 is NOT risk).\n"
                    "    # 'less than threshold available' means available < threshold * team_size,\n"
                    "    # i.e. absent > team_size - threshold * team_size = team_size * (1 - threshold).\n"
                    "    limit = team_size - team_size * threshold\n"
                    "    \n"
                    "    out = []\n"
                    "    count = 0\n"
                    "    risk_start = None\n"
                    "    i = 0\n"
                    "    while i < len(events):\n"
                    "        d = events[i][0]\n"
                    "        while i < len(events) and events[i][0] == d:\n"
                    "            count += events[i][1]\n"
                    "            i += 1\n"
                    "        if count > limit and risk_start is None:\n"
                    "            risk_start = d\n"
                    "        elif count <= limit and risk_start is not None:\n"
                    "            out.append([risk_start, d - 1])\n"
                    "            risk_start = None\n"
                    "    return out"
                ),
                "javascript": (
                    "function findRiskPeriods(teamSize, threshold, vacations) {\n"
                    "    const events = [];\n"
                    "    for (const member of vacations) {\n"
                    "        const intervals = [...member].sort((a, b) => a[0] - b[0]);\n"
                    "        const merged = [];\n"
                    "        for (const [s, e] of intervals) {\n"
                    "            if (merged.length && s <= merged[merged.length - 1][1] + 1) {\n"
                    "                merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], e);\n"
                    "            } else {\n"
                    "                merged.push([s, e]);\n"
                    "            }\n"
                    "        }\n"
                    "        for (const [s, e] of merged) {\n"
                    "            events.push([s, 1]);\n"
                    "            events.push([e + 1, -1]);\n"
                    "        }\n"
                    "    }\n"
                    "    events.sort((a, b) => a[0] - b[0]);\n"
                    "    const limit = teamSize - teamSize * threshold;\n"
                    "    const out = [];\n"
                    "    let count = 0;\n"
                    "    let riskStart = null;\n"
                    "    let i = 0;\n"
                    "    while (i < events.length) {\n"
                    "        const d = events[i][0];\n"
                    "        while (i < events.length && events[i][0] === d) {\n"
                    "            count += events[i][1];\n"
                    "            i++;\n"
                    "        }\n"
                    "        if (count > limit && riskStart === null) riskStart = d;\n"
                    "        else if (count <= limit && riskStart !== null) {\n"
                    "            out.push([riskStart, d - 1]);\n"
                    "            riskStart = null;\n"
                    "        }\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Per-Day Brute Force",
            "time_complexity": "O(D · I) where D is the calendar span and I total intervals",
            "space_complexity": "O(1) extra (besides the output)",
            "description": (
                "For every day in the active span, count how many teammates have any interval covering "
                "it; emit a risk run when the count crosses the limit. Easy to write under pressure and "
                "obviously correct, but blows up linearly with the calendar span. Useful as the warm-up "
                "answer or the oracle to validate an optimised version against."
            ),
            "code": {
                "python": (
                    "def find_risk_periods(team_size, threshold, vacations):\n"
                    "    if not vacations or not any(vacations):\n"
                    "        return []\n"
                    "    spans = [iv for member in vacations for iv in member]\n"
                    "    if not spans:\n"
                    "        return []\n"
                    "    lo = min(s for s, _ in spans)\n"
                    "    hi = max(e for _, e in spans)\n"
                    "    limit = team_size - team_size * threshold\n"
                    "    out = []\n"
                    "    risk_start = None\n"
                    "    for d in range(lo, hi + 2):  # one past for the closing edge\n"
                    "        absent = sum(\n"
                    "            1 for member in vacations\n"
                    "            if any(s <= d <= e for s, e in member)\n"
                    "        )\n"
                    "        if absent > limit and risk_start is None:\n"
                    "            risk_start = d\n"
                    "        elif absent <= limit and risk_start is not None:\n"
                    "            out.append([risk_start, d - 1])\n"
                    "            risk_start = None\n"
                    "    return out"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate. We have intervals per teammate; we want days when the *count of overlapping intervals across teammates* is too high. The per-teammate granularity matters — overlapping intervals on the SAME teammate should still count as one absentee.",
        "2. Choose representation. Brute force per day is fine for small inputs but blows up if days are large; events (sweep line) are O(I log I).",
        "3. Inclusive vs half-open. The intervals are inclusive on both ends. Use `(end + 1, -1)` so the decrement happens AFTER the last absent day.",
        "4. Threshold semantics. 'At least 60% available' = 'absent < 40% of team'. 'Less than 60% available' = 'absent ≥ 40%'? Or `>` 40%? Pin this down explicitly with the interviewer; the tests assume strict inequality (`absent > limit`) so 40% absent with limit=40% is NOT risk.",
        "5. Same-day events. If a teammate ends and another starts on day D, apply both deltas before evaluating — otherwise you'll record a phantom non-risk minute.",
        "6. Per-member overlaps. If a member has [1,3] and [2,4], they're absent on days 1–4 as one person, not two. Merge per-member intervals first.",
        "7. Output format. Inclusive `[start, end]`. The end is the day BEFORE the count drops back below the limit — careful with the `d - 1`.",
        "8. Edge cases. No vacations → []. One member, threshold=1.0 → entire union of their absences. Threshold=0.0 → never risk regardless.",
    ],
    "tips": [
        "Pin the threshold semantics at the start. 'Less than 60%' is strict; 'at most 60%' is not. The tests use strict.",
        "The fence-post `(end + 1, -1)` is the #1 bug. Write it once, comment it, never touch it.",
        "Per-member merge is the #2 bug. Without it, [1,3] + [2,4] from one teammate counts as 2 absentees on day 2.",
        "When applying events, batch by date. Don't decide the threshold mid-batch — only after every delta on that date is applied.",
        "The brute force version is a great oracle. Keep it around in scratch space; randomise inputs and assert the optimised version agrees.",
        "Common follow-up: 'now teammates can also be on parental leave with a different multiplier.' Generalise the `+1 / -1` deltas to weighted; everything else stays the same.",
        "Common follow-up: 'tell me which teammate caused the risk to start.' Tag each event with the member id; track the last-acquired set.",
        "Common follow-up: 'which date has the most simultaneous vacations?' Same sweep, just track max(count) and the date(s) achieving it.",
    ],
    "companies": ["Amazon", "Microsoft", "Google", "Bloomberg", "LinkedIn"],
    "topics": ["Array", "Sorting", "Greedy", "Sweep Line", "Intervals"],
    "time_complexity": "O(I log I)",
    "space_complexity": "O(I)",
    "entry": {
        "kind": "function",
        "name": "find_risk_periods",
        "params": [
            {"name": "team_size", "type": "int"},
            {"name": "threshold", "type": "float"},
            {"name": "vacations", "type": "list"},
        ],
    },
}


def REFERENCE(team_size, threshold, vacations):
    events = []
    for member in vacations:
        intervals = sorted(member)
        merged = []
        for s, e in intervals:
            if merged and s <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], e))
            else:
                merged.append((s, e))
        for s, e in merged:
            events.append((s, 1))
            events.append((e + 1, -1))
    events.sort()

    # Float-stable limit: team_size - team_size * threshold avoids the
    # (1 - threshold) decomposition that introduces float drift on
    # 'round' thresholds like 0.8 (where 1 - 0.8 != 0.2 in IEEE-754).
    limit = team_size - team_size * threshold

    out = []
    count = 0
    risk_start = None
    i = 0
    while i < len(events):
        d = events[i][0]
        while i < len(events) and events[i][0] == d:
            count += events[i][1]
            i += 1
        if count > limit and risk_start is None:
            risk_start = d
        elif count <= limit and risk_start is not None:
            out.append([risk_start, d - 1])
            risk_start = None
    return out


register(PAYLOAD, REFERENCE)
