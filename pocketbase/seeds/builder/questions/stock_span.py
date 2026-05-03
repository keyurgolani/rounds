"""Stock Span — Medium. Stack / Monotonic Stack.

The span problem is the canonical motivation for a decreasing stack.
Each day's span depends on how many consecutive previous days had a
lower-or-equal price, which is exactly the distance back to the nearest
strictly-greater price. The stack tracks those greater prices so each
index is pushed and popped at most once.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Stock Span",
    "difficulty": "Medium",
    "description": (
        "Given daily stock `prices`, return the span for each day. A day's span is the number of consecutive "
        "days ending today where the price was less than or equal to today's price.\n\n"
        "For `prices = [8, 6, 2, 4, 2, 5, 7]`, the spans are `[1, 1, 1, 2, 1, 4, 6]`."
    ),
    "hints": [
        "Brute force scans backward from each day until it finds a greater price, which is O(n^2).",
        "The useful question is: where is the nearest previous day with price greater than today's price?",
        "Maintain a stack of indices whose prices are strictly greater than future spans can cross.",
        "Pop while `prices[stack[-1]] <= prices[i]`; those days are covered by today's span and will never block a later higher price.",
        "If the stack is empty, today's span reaches back to day 0; otherwise it starts after `stack[-1]`.",
    ],
    "constraints": ["0 <= prices.length <= 10^5", "0 <= prices[i] <= 10^9"],
    "starter_code": {
        "python": "def stock_span(prices):\n    # Your code here\n    pass",
        "javascript": "function stockSpan(prices) {\n    // Your code here\n}",
        "java": "public int[] stockSpan(int[] prices) {\n    // Your code here\n    return new int[]{};\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(stock_span([8, 6, 2, 4, 2, 5, 7]))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "console.log(stockSpan([8, 6, 2, 4, 2, 5, 7]));"
        ),
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"prices": [8, 6, 2, 4, 2, 5, 7]}, "expected": [1, 1, 1, 2, 1, 4, 6],
         "description": "Standard example", "tags": ["basic"]},
        {"input": {"prices": [100, 60, 70, 65, 80, 85]}, "expected": [1, 1, 2, 1, 4, 5],
         "description": "Classic stock span example", "tags": ["basic"]},
        {"input": {"prices": [10, 20, 30, 40]}, "expected": [1, 2, 3, 4],
         "description": "Strictly increasing", "tags": ["edge"]},
        {"input": {"prices": [40, 30, 20, 10]}, "expected": [1, 1, 1, 1],
         "description": "Strictly decreasing", "tags": ["edge"]},
        {"input": {"prices": [5, 5, 5]}, "expected": [1, 2, 3],
         "description": "Equal prices count in the span", "tags": ["tricky"]},
        {"input": {"prices": []}, "expected": [],
         "description": "Empty input", "tags": ["edge"]},
    ],
    "solutions": [{
        "title": "Monotonic Decreasing Stack",
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "description": "Keep indices of previous greater prices. Each index is pushed and popped at most once.",
        "code": {
            "python": (
                "def stock_span(prices):\n"
                "    spans = []\n"
                "    stack = []\n"
                "    for i, price in enumerate(prices):\n"
                "        while stack and prices[stack[-1]] <= price:\n"
                "            stack.pop()\n"
                "        spans.append(i + 1 if not stack else i - stack[-1])\n"
                "        stack.append(i)\n"
                "    return spans"
            ),
            "javascript": (
                "function stockSpan(prices) {\n"
                "    const spans = [];\n"
                "    const stack = [];\n"
                "    for (let i = 0; i < prices.length; i++) {\n"
                "        while (stack.length && prices[stack[stack.length - 1]] <= prices[i]) stack.pop();\n"
                "        spans.push(stack.length === 0 ? i + 1 : i - stack[stack.length - 1]);\n"
                "        stack.push(i);\n"
                "    }\n"
                "    return spans;\n"
                "}"
            ),
        },
    }],
    "thought_process": [
        "1. Define span as a consecutive block ending today; older non-consecutive lower prices do not count.",
        "2. State the brute-force backward scan and its O(n^2) worst case.",
        "3. Reframe the task as finding the nearest previous greater price for each day.",
        "4. Use a decreasing stack of indices and pop smaller-or-equal prices before computing today's span.",
        "5. Explain amortized O(n): every index is pushed once and popped once.",
    ],
    "tips": [
        "Use `<=` in the pop condition because equal prices are included in the span.",
        "Store indices, not prices, because span length depends on distance.",
        "This is the same monotonic-stack pattern as next greater element and daily temperatures, but the output is a distance backward.",
    ],
    "companies": [],
    "topics": ["Array", "Stack", "Monotonic Stack"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(prices):
    spans = []
    stack = []
    for i, price in enumerate(prices):
        while stack and prices[stack[-1]] <= price:
            stack.pop()
        spans.append(i + 1 if not stack else i - stack[-1])
        stack.append(i)
    return spans


register(PAYLOAD, REFERENCE)
