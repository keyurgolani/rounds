"""Daily Temperatures — Medium. Monotonic Stack.

The canonical 'next greater element' problem dressed up as weather. The
moment you see 'for each i, find the next index j > i where arr[j] >
arr[i]', reach for a monotonic decreasing stack of *indices*. Pop while
the current value beats the top; each popped index gets its answer
(distance = i - popped). Anything still on the stack at the end has no
warmer day and stays at the default 0.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Daily Temperatures",
    "difficulty": "Medium",
    "description": (
        "Given an array of integers `temperatures` representing the daily temperatures, return an array "
        "`answer` such that `answer[i]` is the number of days you have to wait after the i-th day to get "
        "a warmer temperature. If there is no future day for which this is possible, set `answer[i] = 0`.\n\n"
        "**Example 1:**\n"
        "- Input: `temperatures = [73,74,75,71,69,72,76,73]`\n"
        "- Output: `[1,1,4,2,1,1,0,0]`\n\n"
        "**Example 2:**\n"
        "- Input: `temperatures = [30,40,50,60]`\n"
        "- Output: `[1,1,1,0]`\n\n"
        "**Example 3:**\n"
        "- Input: `temperatures = [30,60,90]`\n"
        "- Output: `[1,1,0]`"
    ),
    "hints": [
        "Brute force: for each i, scan forward until you find a strictly greater value. O(n²). State it; don't ship it.",
        "Reframe: 'next greater element to the right' — a textbook monotonic stack problem.",
        "Maintain a stack of *indices* whose temperatures are in strictly decreasing order. When today's temp beats the top, today is the answer for that popped index.",
        "Distance, not value: `answer[popped] = i - popped`. The stack stores indices specifically so you can compute that distance.",
        "Anything left on the stack at the end never found a warmer day → its answer stays 0 (the array's default).",
    ],
    "constraints": [
        "1 <= temperatures.length <= 10⁵",
        "30 <= temperatures[i] <= 100",
    ],
    "starter_code": {
        "python": "def daily_temperatures(temperatures):\n    # Your code here\n    pass",
        "javascript": "function dailyTemperatures(temperatures) {\n    // Your code here\n}",
        "java": "public int[] dailyTemperatures(int[] temperatures) {\n    // Your code here\n    return new int[0];\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[73,74,75,71,69,72,76,73], [30,40,50,60], [30,60,90]]\n"
            "    for temps in cases:\n"
            "        print(f\"daily_temperatures({temps}) = {daily_temperatures(temps)}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[73,74,75,71,69,72,76,73], [30,40,50,60]].forEach(temps =>\n"
            "    console.log(`dailyTemperatures =`, dailyTemperatures(temps))\n"
            ");"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        System.out.println(java.util.Arrays.toString(\n"
            "            s.dailyTemperatures(new int[]{73,74,75,71,69,72,76,73})));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"temperatures": [73, 74, 75, 71, 69, 72, 76, 73]},
         "expected": [1, 1, 4, 2, 1, 1, 0, 0],
         "description": "Canonical example — mixed waits with two trailing zeros", "tags": ["basic"]},
        {"input": {"temperatures": [30, 40, 50, 60]}, "expected": [1, 1, 1, 0],
         "description": "Strictly increasing — every day waits exactly one", "tags": ["basic"]},
        {"input": {"temperatures": [30, 60, 90]}, "expected": [1, 1, 0],
         "description": "Three-day strict increase", "tags": ["basic"]},
        {"input": {"temperatures": [30]}, "expected": [0],
         "description": "Single day — no future, answer is 0", "tags": ["edge"]},
        {"input": {"temperatures": []}, "expected": [],
         "description": "Empty input — empty output", "tags": ["edge"]},
        {"input": {"temperatures": [50, 50, 50]}, "expected": [0, 0, 0],
         "description": "All equal — equal is not *strictly warmer*, so all zeros", "tags": ["edge"]},
        {"input": {"temperatures": [73, 73, 73, 73, 74]}, "expected": [4, 3, 2, 1, 0],
         "description": "Plateau then a single warmer day — every duplicate must skip past the others",
         "tags": ["tricky"]},
        {"input": {"temperatures": [89, 62, 70, 58, 47, 47, 46, 76, 100, 70]},
         "expected": [8, 1, 5, 4, 3, 2, 1, 1, 0, 0],
         "description": "Mixed peaks and valleys — multiple stack pops in a single step", "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Monotonic Decreasing Stack (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Walk left-to-right. Keep a stack of indices whose temperatures are in strictly decreasing "
                "order. For each new index i, while the current temperature is greater than the temperature "
                "at the stack's top, pop and set `answer[popped] = i - popped`. Then push i. Each index is "
                "pushed and popped at most once → amortized O(n)."
            ),
            "code": {
                "python": (
                    "def daily_temperatures(temperatures):\n"
                    "    n = len(temperatures)\n"
                    "    answer = [0] * n\n"
                    "    stack = []  # indices, temperatures[stack] strictly decreasing\n"
                    "    for i, t in enumerate(temperatures):\n"
                    "        while stack and temperatures[stack[-1]] < t:\n"
                    "            j = stack.pop()\n"
                    "            answer[j] = i - j\n"
                    "        stack.append(i)\n"
                    "    return answer"
                ),
                "javascript": (
                    "function dailyTemperatures(temperatures) {\n"
                    "    const n = temperatures.length;\n"
                    "    const answer = new Array(n).fill(0);\n"
                    "    const stack = [];\n"
                    "    for (let i = 0; i < n; i++) {\n"
                    "        while (stack.length && temperatures[stack[stack.length - 1]] < temperatures[i]) {\n"
                    "            const j = stack.pop();\n"
                    "            answer[j] = i - j;\n"
                    "        }\n"
                    "        stack.push(i);\n"
                    "    }\n"
                    "    return answer;\n"
                    "}"
                ),
                "java": (
                    "public int[] dailyTemperatures(int[] temperatures) {\n"
                    "    int n = temperatures.length;\n"
                    "    int[] answer = new int[n];\n"
                    "    java.util.Deque<Integer> stack = new java.util.ArrayDeque<>();\n"
                    "    for (int i = 0; i < n; i++) {\n"
                    "        while (!stack.isEmpty() && temperatures[stack.peek()] < temperatures[i]) {\n"
                    "            int j = stack.pop();\n"
                    "            answer[j] = i - j;\n"
                    "        }\n"
                    "        stack.push(i);\n"
                    "    }\n"
                    "    return answer;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Brute Force (Baseline)",
            "time_complexity": "O(n²)",
            "space_complexity": "O(1)",
            "description": (
                "For each index i, scan forward until you find a strictly greater value or fall off the end. "
                "Mention as the baseline; never submit for n up to 10⁵."
            ),
            "code": {
                "python": (
                    "def daily_temperatures(temperatures):\n"
                    "    n = len(temperatures)\n"
                    "    answer = [0] * n\n"
                    "    for i in range(n):\n"
                    "        for j in range(i + 1, n):\n"
                    "            if temperatures[j] > temperatures[i]:\n"
                    "                answer[i] = j - i\n"
                    "                break\n"
                    "    return answer"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Restate the problem: for each i, find the smallest j > i with temperatures[j] > temperatures[i], and report j - i (or 0 if no such j).",
        "2. Brute force is the n² double loop. State it as the baseline so the interviewer knows you see the lower bound.",
        "3. Recognise the family: 'next greater element to the right'. That's a monotonic stack problem.",
        "4. Decide what the stack stores. Values aren't enough — you need the *distance*, so store **indices** and look up temperatures by index.",
        "5. Invariant: temperatures at the indices on the stack are strictly decreasing from bottom to top. When a new temp breaks that, you've found the answer for everything you pop.",
        "6. Edges: empty input → empty output. Equal temperatures don't count as warmer → use strict `<` in the while condition. Anything left on the stack at the end already defaults to 0.",
    ],
    "tips": [
        "This is a Next Greater Element variant. Once you see that pattern, the same template works for 'next smaller', 'previous greater', etc. — flip the comparison and/or scan direction.",
        "Walking right-to-left also works: for each i, pop while top temp is ≤ current, then `answer[i] = stack_top_index - i` (or 0 if empty), then push i. Same complexity, slightly different mental model.",
        "Use strict `<` (or `>` walking right-to-left) so equal temperatures aren't treated as warmer — that bug silently breaks the plateau test case.",
        "The stack stores indices, not temperatures. Forgetting that is the most common slip — you can't compute `i - j` from values alone.",
        "Each index is pushed once and popped at most once → the inner while loop is amortized O(1), giving overall O(n) despite the nested loop appearance.",
    ],
    "companies": ["Amazon", "Facebook", "Bloomberg"],
    "topics": ["Array", "Stack", "Monotonic Stack"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(temperatures):
    n = len(temperatures)
    answer = [0] * n
    stack = []
    for i, t in enumerate(temperatures):
        while stack and temperatures[stack[-1]] < t:
            j = stack.pop()
            answer[j] = i - j
        stack.append(i)
    return answer


register(PAYLOAD, REFERENCE)
