"""Maximum Profitable Windows — Medium. Array, Window, Divide and Conquer.

Count contiguous subarrays whose maximum sits at either endpoint.
Brute force enumerates O(n^2) windows; the insight is that windows
crossing a maximum without touching it are the only ones that fail.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Maximum Profitable Windows",
    "difficulty": "Medium",
    "description": (
        "Given an array `stock_prices`, count how many contiguous windows are maximum profitable. "
        "A window is maximum profitable when either its first element or its last element is the "
        "maximum value inside that window.\n\n"
        "For `stock_prices = [2, 3, 2]`, every window except `[2, 3, 2]` qualifies, so the answer is `5`."
    ),
    "hints": [
        "Start from the definition: a window qualifies when the maximum appears at its left edge or right edge.",
        "Brute force is enough to prove correctness: enumerate each `[left, right]` window, compute its maximum, then test both endpoints.",
        "Single-element windows always qualify because their only value is both endpoints and the maximum.",
        "For a stronger solution, split around the maximum element. Windows that cross the maximum but do not start or end there are the ones that fail.",
        "Ties matter: if the maximum value appears at an endpoint, the window qualifies even when the same maximum appears inside the window.",
    ],
    "constraints": [
        "0 <= stock_prices.length <= 2000",
        "0 <= stock_prices[i] <= 10^9",
    ],
    "starter_code": {
        "python": "def max_profitable_window_count(stock_prices):\n    # Your code here\n    pass",
        "javascript": "function maxProfitableWindowCount(stockPrices) {\n    // Your code here\n}",
        "java": "public int maxProfitableWindowCount(int[] stockPrices) {\n    // Your code here\n    return 0;\n}",
    },
    "boilerplate_code": {
        "python": "# Test runner (read-only)\nif __name__ == \"__main__\":\n    print(max_profitable_window_count([2, 3, 2]))",
        "javascript": "// Test runner (read-only)\nconsole.log(maxProfitableWindowCount([2, 3, 2]));",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"stock_prices": [2, 3, 2]}, "expected": 5, "description": "Source example", "tags": ["basic"]},
        {"input": {"stock_prices": [1, 2, 3, 4, 5]}, "expected": 15, "description": "Strictly increasing", "tags": ["edge"]},
        {"input": {"stock_prices": [5, 4, 3, 2, 1]}, "expected": 15, "description": "Strictly decreasing", "tags": ["edge"]},
        {"input": {"stock_prices": [1, 2, 3, 4, 5, 4, 3, 2, 1]}, "expected": 29, "description": "Source regression case", "tags": ["tricky"]},
        {"input": {"stock_prices": [3, 2, 3]}, "expected": 6, "description": "Tied maxima at both ends", "tags": ["tricky"]},
        {"input": {"stock_prices": []}, "expected": 0, "description": "Empty input", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Enumerate Windows",
            "time_complexity": "O(n^3)",
            "space_complexity": "O(1)",
            "description": "Check every contiguous window and count it if either endpoint equals that window's maximum value.",
            "code": {
                "python": (
                    "def max_profitable_window_count(stock_prices):\n"
                    "    count = 0\n"
                    "    for left in range(len(stock_prices)):\n"
                    "        for right in range(left, len(stock_prices)):\n"
                    "            window_max = max(stock_prices[left:right + 1])\n"
                    "            if stock_prices[left] == window_max or stock_prices[right] == window_max:\n"
                    "                count += 1\n"
                    "    return count"
                ),
                "javascript": (
                    "function maxProfitableWindowCount(stockPrices) {\n"
                    "    let count = 0;\n"
                    "    for (let left = 0; left < stockPrices.length; left++) {\n"
                    "        for (let right = left; right < stockPrices.length; right++) {\n"
                    "            const windowMax = Math.max(...stockPrices.slice(left, right + 1));\n"
                    "            if (stockPrices[left] === windowMax || stockPrices[right] === windowMax) count++;\n"
                    "        }\n"
                    "    }\n"
                    "    return count;\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Repeat the predicate in your own words: each subarray is valid if its maximum is visible from at least one endpoint.",
        "2. Establish the exhaustive baseline: there are O(n^2) windows and each can be checked by scanning for its maximum.",
        "3. Explain why every one-element window is valid and why monotonic arrays produce every possible window.",
        "4. If asked to optimize, pivot to structure: choose the maximum, count windows ending or starting at it, then solve the left and right partitions.",
        "5. Call out duplicate maxima before coding. `max == left` or `max == right` is the condition, not unique maximum at an endpoint.",
    ],
    "tips": [
        "Do not confuse this with maximum subarray sum; no values are accumulated.",
        "Use very small examples while explaining: `[2, 3, 2]` has exactly one failing window, the full array.",
        "The common off-by-one bug is excluding the right endpoint when slicing or scanning the window.",
        "If constraints are large, precomputing range maximums can speed up the brute-force check, but it still leaves O(n^2) windows.",
        "A monotonic stack can also count invalid windows by nearest-greater boundaries; mention it only if the interviewer pushes beyond divide-and-conquer.",
    ],
    "companies": [],
    "topics": ["Array", "Window", "Divide and Conquer"],
    "time_complexity": "O(n^3)",
    "space_complexity": "O(1)",
}


def REFERENCE(stock_prices):
    count = 0
    for left in range(len(stock_prices)):
        for right in range(left, len(stock_prices)):
            window_max = max(stock_prices[left:right + 1])
            if stock_prices[left] == window_max or stock_prices[right] == window_max:
                count += 1
    return count


register(PAYLOAD, REFERENCE)
