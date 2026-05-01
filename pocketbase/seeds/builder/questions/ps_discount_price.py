"""Discount Price — Medium. String / Regex.

Apply a percentage discount to every price token in a sentence.
The L&M signal: support i18n (multiple currency symbols) cleanly via
a per-currency handler map."""
from builder.registry import register


PAYLOAD = {
    "title": "Discount Prices in a Sentence",
    "difficulty": "Medium",
    "description": (
        "Given a sentence and a discount fraction (e.g. `0.20` for 20% off), find every PRICE in the "
        "sentence and replace it with the discounted value. A price is a `$` followed by a positive "
        "decimal number (no thousands separators).\n\n"
        "Round the discounted value to TWO decimal places. Strip trailing zero decimals (`$8.00` → `$8`, "
        "but `$7.99` × 0.20 = `$6.39` stays `$6.39`).\n\n"
        "**Examples:**\n"
        "- `'Echos are $50 today.'` × 0.20 → `'Echos are $40 today.'`\n"
        "- `'Buy 3 shirts for $9.99'` × 0.20 → `'Buy 3 shirts for $7.99'`\n"
        "- `'No price here'` → `'No price here'`\n"
        "- `'Buy 3 shirts for $10 or 5 shirts for $15'` → `'Buy 3 shirts for $8 or 5 shirts for $12'`"
    ),
    "hints": [
        "Regex: `\\$(\\d+(?:\\.\\d+)?)` matches a dollar sign followed by a decimal.",
        "Use `re.sub` with a callback to compute the discounted price per match.",
        "Format: `f\"${val:.2f}\"` then strip trailing zeros and the trailing `.`.",
        "The 'Ke$ha' edge case: `$h` is not a price (there's no digit). The regex handles this via the digit lookahead.",
        "i18n follow-up: pull formatting + currency symbol into a Locale handler. Don't hardcode `$`.",
    ],
    "constraints": [
        "0 <= |sentence| <= 10⁴",
        "0 <= discount < 1",
    ],
    "starter_code": {
        "python": "def discount_prices(sentence, discount):\n    # Your code here\n    pass",
        "javascript": "function discountPrices(sentence, discount) {\n    // Your code here\n}",
        "java": "public String discountPrices(String sentence, double discount) {\n    // Your code here\n    return sentence;\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(discount_prices('Echos are $50 today.', 0.20))"
        ),
        "javascript": "// Test runner (read-only)",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"sentence": "Echos are $50 today.", "discount": 0.20},
         "expected": "Echos are $40 today.",
         "description": "Round number, integer result", "tags": ["basic"]},
        {"input": {"sentence": "Buy 3 shirts for $9.99", "discount": 0.20},
         "expected": "Buy 3 shirts for $7.99",
         "description": "Decimal price", "tags": ["basic"]},
        {"input": {"sentence": "No price here.", "discount": 0.20},
         "expected": "No price here.",
         "description": "No match — passthrough", "tags": ["edge"]},
        {"input": {"sentence": "Buy 3 shirts for $10 or 5 shirts for $15", "discount": 0.20},
         "expected": "Buy 3 shirts for $8 or 5 shirts for $12",
         "description": "Multiple matches", "tags": ["basic"]},
        {"input": {"sentence": "Buy the Ke$ha album for $13.", "discount": 0.20},
         "expected": "Buy the Ke$ha album for $10.4.",
         "description": "$h doesn't match (no digit); $13 does",
         "tags": ["tricky"]},
        {"input": {"sentence": "$1.00 or $2.00", "discount": 0.50},
         "expected": "$0.5 or $1",
         "description": "Trim trailing zeros (.50 → .5; .00 → strip)", "tags": ["edge"]},
        {"input": {"sentence": "", "discount": 0.20}, "expected": "",
         "description": "Empty input", "tags": ["edge"]},
    ],
    "solutions": [
        {
            "title": "Regex with Callback (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n) for the output",
            "description": (
                "Match `\\$\\d+(?:\\.\\d+)?` and rewrite each match. Callback parses, applies discount, "
                "formats with two decimals and strips trailing zeros. Single linear pass."
            ),
            "code": {
                "python": (
                    "import re\n\n"
                    "def discount_prices(sentence, discount):\n"
                    "    factor = 1 - discount\n"
                    "    pattern = re.compile(r'\\$(\\d+(?:\\.\\d+)?)')\n"
                    "    def repl(m):\n"
                    "        val = float(m.group(1)) * factor\n"
                    "        s = f\"{val:.2f}\"\n"
                    "        if '.' in s:\n"
                    "            s = s.rstrip('0').rstrip('.')\n"
                    "        return f\"${s}\"\n"
                    "    return pattern.sub(repl, sentence)"
                ),
                "javascript": (
                    "function discountPrices(sentence, discount) {\n"
                    "    const factor = 1 - discount;\n"
                    "    return sentence.replace(/\\$(\\d+(?:\\.\\d+)?)/g, (_, num) => {\n"
                    "        let val = (parseFloat(num) * factor).toFixed(2);\n"
                    "        if (val.includes('.')) val = val.replace(/0+$/, '').replace(/\\.$/, '');\n"
                    "        return `$${val}`;\n"
                    "    });\n"
                    "}"
                ),
                "java": (
                    "public String discountPrices(String sentence, double discount) {\n"
                    "    double factor = 1 - discount;\n"
                    "    Matcher m = Pattern.compile(\"\\\\$(\\\\d+(?:\\\\.\\\\d+)?)\").matcher(sentence);\n"
                    "    StringBuffer sb = new StringBuffer();\n"
                    "    while (m.find()) {\n"
                    "        double val = Double.parseDouble(m.group(1)) * factor;\n"
                    "        String s = String.format(\"%.2f\", val);\n"
                    "        if (s.contains(\".\")) s = s.replaceAll(\"0+$\", \"\").replaceAll(\"\\\\.$\", \"\");\n"
                    "        m.appendReplacement(sb, \"\\\\$\" + s);\n"
                    "    }\n"
                    "    m.appendTail(sb);\n"
                    "    return sb.toString();\n"
                    "}"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Regex-match price tokens. Lock down the rule: `$` followed by a digit (not just any character).",
        "2. Replace each match using a callback that computes and formats the discounted value.",
        "3. Format: `.2f` then strip trailing zeros and trailing `.` so `$8.00 → $8`.",
        "4. Edge cases: no match (passthrough), `$h` (not a price), multiple matches, leading $0.",
        "5. i18n: pull formatting + symbol into a Locale handler. Per-currency rules (decimal separator, symbol position) live there.",
    ],
    "tips": [
        "Floats around money are fine for one operation but not for accumulating sums. For 'apply 20% off then 10% off', do the math in cents-as-int.",
        "Don't hardcode `.2f` everywhere — pull formatting into a helper. JPY uses 0 decimals; BHD uses 3.",
        "Common follow-up: 'apply different rules per currency.' Map symbol → handler; default to a generic handler.",
        "Common follow-up: 'apply discount only to certain product categories.' Tokenise the sentence into 'price + nearby words' and gate on a category dictionary.",
        "Common follow-up: 'support European format ($9,99).' Replace the regex; handlers parse comma as decimal.",
    ],
    "companies": ["Amazon", "Microsoft", "Bloomberg"],
    "topics": ["String", "Regex", "Strategy Pattern"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(sentence, discount):
    import re
    factor = 1 - discount
    pattern = re.compile(r"\$(\d+(?:\.\d+)?)")

    def repl(m):
        val = float(m.group(1)) * factor
        s = f"{val:.2f}"
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return f"${s}"

    return pattern.sub(repl, sentence)


register(PAYLOAD, REFERENCE)
