"""Micro-Service Availability Monitor — Medium. Sliding Window.

Stream of availability samples. Notify on K-in-a-row failures; reset
state on K-in-a-row successes. Sliding window or finite state machine."""
from builder.registry import register


PAYLOAD = {
    "title": "Micro-Service Availability Alarm",
    "difficulty": "Medium",
    "description": (
        "Given a stream of availability samples (each `1` = up, `0` = down) for a single service, return "
        "the indices at which the alarm SHOULD FIRE.\n\n"
        "Rules:\n"
        "- Alarm enters 'firing' state when **K** consecutive `0`s are observed.\n"
        "- Alarm leaves 'firing' state (returns to 'normal') when **K** consecutive `1`s are observed.\n"
        "- Alarm fires once when entering firing state — that's the index returned.\n"
        "- Re-entering firing after a recovery counts as another fire event.\n\n"
        "**Example:**\n"
        "- Input: `samples = [1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0]`, `k = 3`\n"
        "- Output: `[3, 10]`\n"
        "- Reasoning: indices 1-3 are three 0s → fire at index 3. Indices 5-7 are three 1s → recover. "
        "Indices 8-10 are three 0s → fire at index 10."
    ),
    "hints": [
        "Track two counters: consecutive 0s and consecutive 1s. Reset the other when one increments.",
        "When consecutive 0s hits K AND alarm isn't already firing → fire (record the index, set firing=True).",
        "When consecutive 1s hits K AND alarm IS firing → recover (set firing=False).",
        "Edge case: stream starts with K 0s — alarm fires at index K-1 immediately.",
        "Edge cases: K = 1 (every transition fires), empty stream, all 0s, all 1s, K > stream length.",
    ],
    "constraints": [
        "0 <= |samples| <= 10⁵",
        "1 <= k <= 10⁴",
    ],
    "starter_code": {
        "python": "def alarm_indices(samples, k):\n    # Your code here\n    pass",
        "javascript": "function alarmIndices(samples, k) {\n    // Your code here\n}",
        "java": "public List<Integer> alarmIndices(int[] samples, int k) {\n    // Your code here\n    return new ArrayList<>();\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(alarm_indices([1,0,0,0,0,1,1,1,0,0,0], 3))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"samples": [1, 0, 0, 0, 0, 1, 1, 1, 0, 0, 0], "k": 3},
         "expected": [3, 10],
         "description": "Two firing intervals", "tags": ["basic"]},
        {"input": {"samples": [], "k": 3}, "expected": [],
         "description": "Empty stream", "tags": ["edge"]},
        {"input": {"samples": [1, 1, 1, 1], "k": 2}, "expected": [],
         "description": "All up — never fires", "tags": ["edge"]},
        {"input": {"samples": [0, 0, 0, 0, 0], "k": 3}, "expected": [2],
         "description": "Stream starts with K 0s — fires at index K-1, no further re-fires",
         "tags": ["edge"]},
        {"input": {"samples": [0, 1, 0, 1, 0], "k": 3}, "expected": [],
         "description": "Flapping below threshold — never fires", "tags": ["tricky"]},
        {"input": {"samples": [0, 0, 0, 1, 0, 0, 0], "k": 3}, "expected": [2],
         "description": "Single 1 isn't enough to recover — still in firing state",
         "tags": ["tricky"]},
        {"input": {"samples": [1, 0], "k": 1}, "expected": [1],
         "description": "k=1 — first 0 fires immediately", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Two Counters + Boolean State (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(1)",
            "description": (
                "Walk the samples once. Maintain `zeros`, `ones` consecutive counters and a `firing` "
                "boolean. On 0: zeros++, ones = 0. On 1: ones++, zeros = 0. Fire when zeros == k and not "
                "firing. Recover when ones == k and firing."
            ),
            "code": {
                "python": (
                    "def alarm_indices(samples, k):\n"
                    "    out = []\n"
                    "    zeros = ones = 0\n"
                    "    firing = False\n"
                    "    for i, v in enumerate(samples):\n"
                    "        if v == 0:\n"
                    "            zeros += 1; ones = 0\n"
                    "            if zeros >= k and not firing:\n"
                    "                out.append(i)\n"
                    "                firing = True\n"
                    "        else:\n"
                    "            ones += 1; zeros = 0\n"
                    "            if ones >= k and firing:\n"
                    "                firing = False\n"
                    "    return out"
                ),
                "javascript": (
                    "function alarmIndices(samples, k) {\n"
                    "    const out = [];\n"
                    "    let zeros = 0, ones = 0, firing = false;\n"
                    "    for (let i = 0; i < samples.length; i++) {\n"
                    "        if (samples[i] === 0) {\n"
                    "            zeros++; ones = 0;\n"
                    "            if (zeros >= k && !firing) { out.push(i); firing = true; }\n"
                    "        } else {\n"
                    "            ones++; zeros = 0;\n"
                    "            if (ones >= k && firing) firing = false;\n"
                    "        }\n"
                    "    }\n"
                    "    return out;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Read the rules carefully. K-in-a-row 0s → fire. K-in-a-row 1s → recover. Mind the 'enter firing' vs 'continue firing' distinction.",
        "2. Two counters track current run lengths. Reset on direction change.",
        "3. Boolean tracks current alarm state. Fire is the transition normal→firing; recover is firing→normal.",
        "4. Single stream, single index — only fire once when entering firing.",
        "5. Edge cases: K=1 (instant), empty, single transition, flapping below threshold, ends mid-firing.",
        "6. Discuss back-pressure / configurable thresholds as the production hardening step.",
    ],
    "tips": [
        "Don't forget to reset the OTHER counter when the current sample changes direction. `zeros = 0` on a 1, and vice versa.",
        "If you check `zeros == k` (exact equality) the alarm fires only on the first hit; `zeros >= k` is fine but redundant since `firing` blocks re-fire.",
        "Common follow-up: 'percentage threshold instead of strict K.' Sliding window of N samples, count zeros, fire when count > p · N.",
        "Common follow-up: 'transient flicker tolerance' — require K consecutive 1s INTERSPERSED among more than K 1s before recovery. Adjust thresholds independently.",
        "Common follow-up: 'multiple services.' Per-service state machine; same logic, parameterised.",
    ],
    "companies": ["Amazon", "Datadog", "Splunk"],
    "topics": ["Sliding Window", "State Machine", "Streaming"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(samples, k):
    out = []
    zeros = ones = 0
    firing = False
    for i, v in enumerate(samples):
        if v == 0:
            zeros += 1
            ones = 0
            if zeros >= k and not firing:
                out.append(i)
                firing = True
        else:
            ones += 1
            zeros = 0
            if ones >= k and firing:
                firing = False
    return out


register(PAYLOAD, REFERENCE)
