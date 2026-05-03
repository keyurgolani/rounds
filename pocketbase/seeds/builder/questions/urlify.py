"""URLify — Easy. String / Two Pointers.

The in-place backward scan is the canonical solution. Counting spaces
first determines the final write position, then two pointers walk from
the end of the true content and the end of the expanded buffer
simultaneously. The trap is treating trailing buffer spaces as content.
"""
from builder.registry import register


PAYLOAD = {
    "title": "URLify",
    "difficulty": "Easy",
    "description": (
        "Replace every space in the true portion of a character array with `%20`. The array has enough trailing "
        "space to hold the extra characters, and `true_length` gives the length before padding. Return the transformed string."
    ),
    "hints": [
        "Only inspect the first `true_length` characters; trailing spaces are buffer, not content.",
        "Count spaces in the true portion to know the final write index.",
        "Work backward so moving characters does not overwrite data you still need to read.",
        "When you see a space, write `0`, `2`, `%` backward into the destination positions.",
    ],
    "constraints": ["0 <= true_length <= chars.length", "chars has enough trailing buffer for replacements"],
    "starter_code": {
        "python": "def urlify(chars, true_length):\n    # Your code here\n    pass",
        "javascript": "function urlify(chars, trueLength) {\n    // Your code here\n}",
        "java": "public String urlify(char[] chars, int trueLength) {\n    // Your code here\n    return \"\";\n}",
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    print(urlify(list(\"Mr John Smith    \"), 13))"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "console.log(urlify(Array.from(\"Mr John Smith    \"), 13));"
        ),
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"chars": list("Mr John Smith    "), "true_length": 13}, "expected": "Mr%20John%20Smith",
         "description": "Classic example with two spaces", "tags": ["basic"]},
        {"input": {"chars": list("HelloWorld"), "true_length": 10}, "expected": "HelloWorld",
         "description": "No spaces", "tags": ["edge"]},
        {"input": {"chars": list("a b  "), "true_length": 3}, "expected": "a%20b",
         "description": "Single middle space", "tags": ["basic"]},
        {"input": {"chars": list(" a  "), "true_length": 2}, "expected": "%20a",
         "description": "Leading space in true content", "tags": ["tricky"]},
        {"input": {"chars": list("a   "), "true_length": 2}, "expected": "a%20",
         "description": "Trailing true-content space", "tags": ["tricky"]},
        {"input": {"chars": [], "true_length": 0}, "expected": "",
         "description": "Empty input", "tags": ["edge"]},
    ],
    "solutions": [{
        "title": "Backward In-Place Write",
        "time_complexity": "O(n)",
        "space_complexity": "O(1)",
        "description": "Use two pointers from the end: one reads true content, the other writes into the padded buffer.",
        "code": {
            "python": (
                "def urlify(chars, true_length):\n"
                "    space_count = sum(1 for i in range(true_length) if chars[i] == ' ')\n"
                "    write = true_length + space_count * 2 - 1\n"
                "    for read in range(true_length - 1, -1, -1):\n"
                "        if chars[read] == ' ':\n"
                "            chars[write - 2:write + 1] = ['%', '2', '0']\n"
                "            write -= 3\n"
                "        else:\n"
                "            chars[write] = chars[read]\n"
                "            write -= 1\n"
                "    return ''.join(chars[:true_length + space_count * 2])"
            ),
            "javascript": (
                "function urlify(chars, trueLength) {\n"
                "    let spaces = 0;\n"
                "    for (let i = 0; i < trueLength; i++) if (chars[i] === ' ') spaces++;\n"
                "    let write = trueLength + spaces * 2 - 1;\n"
                "    for (let read = trueLength - 1; read >= 0; read--) {\n"
                "        if (chars[read] === ' ') {\n"
                "            chars[write--] = '0';\n"
                "            chars[write--] = '2';\n"
                "            chars[write--] = '%';\n"
                "        } else {\n"
                "            chars[write--] = chars[read];\n"
                "        }\n"
                "    }\n"
                "    return chars.slice(0, trueLength + spaces * 2).join('');\n"
                "}"
            ),
        },
    }],
    "thought_process": [
        "1. Separate true content from buffer; `true_length` controls what must be transformed.",
        "2. Count true-content spaces so the final output length is `true_length + 2 * spaces`.",
        "3. Walk backward to avoid clobbering unread characters while expanding spaces.",
        "4. Return only the transformed output length, not the original padded buffer.",
    ],
    "tips": [
        "Forward replacement is simple for immutable strings but misses the in-place intent.",
        "Trailing spaces after `true_length` are not real spaces to encode; they are just capacity.",
        "If the input language uses immutable strings, clarify whether returning a new string is acceptable.",
    ],
    "companies": [],
    "topics": ["String", "Two Pointers", "Array"],
    "time_complexity": "O(n)",
    "space_complexity": "O(1)",
}


def REFERENCE(chars, true_length):
    if not chars:
        return ""
    space_count = sum(1 for i in range(true_length) if chars[i] == " ")
    write = true_length + space_count * 2 - 1
    for read in range(true_length - 1, -1, -1):
        if chars[read] == " ":
            chars[write - 2:write + 1] = ["%", "2", "0"]
            write -= 3
        else:
            chars[write] = chars[read]
            write -= 1
    return "".join(chars[:true_length + space_count * 2])


register(PAYLOAD, REFERENCE)
