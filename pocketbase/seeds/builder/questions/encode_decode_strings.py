"""Encode and Decode Strings — Medium. Design / String.

The classic 'design a wire format' question. Looks trivial until the
interviewer says 'strings can contain any unicode characters, including
your separator.' Length-prefix is the textbook answer; everything else
(escaping, sentinels) is a trap that can be made to work but rarely
beats `len#string` on either complexity or clarity.
"""
from builder.registry import register


PAYLOAD = {
    "title": "Encode and Decode Strings",
    "difficulty": "Medium",
    "description": (
        "Design an algorithm to encode a list of strings to a single string. The encoded string is then "
        "sent over the network and is decoded back to the original list of strings.\n\n"
        "Implement the `encode` and `decode` methods.\n\n"
        "- `encode(strs: List[str]) -> str` — encodes a list of strings to a single string.\n"
        "- `decode(s: str) -> List[str]` — decodes a single string to a list of strings.\n\n"
        "**Important**: the strings may contain any possible characters out of 256 valid ASCII characters "
        "(and, in this variant, any Unicode characters), *including* whatever delimiter you might be "
        "tempted to use. Your encoding must be unambiguous.\n\n"
        "**Example 1:**\n"
        "- Input: `strs = [\"hello\",\"world\"]`\n"
        "- Encoded: `\"5#hello5#world\"` (one valid encoding)\n"
        "- Output (after decode): `[\"hello\",\"world\"]`\n\n"
        "**Example 2:**\n"
        "- Input: `strs = [\"\",\"a#b\",\"\"]`\n"
        "- Encoded: `\"0#3#a#b0#\"` (note: `#` inside the payload is fine — the length prefix tells "
        "decoder exactly how many chars to read)\n"
        "- Output (after decode): `[\"\",\"a#b\",\"\"]`\n\n"
        "Your `decode(encode(strs))` must equal `strs` for any valid input."
    ),
    "hints": [
        "The naive idea — join with a separator like `,` or `#` — fails the moment a string contains that separator. State this trap explicitly; it's why the question exists.",
        "**Length-prefix scheme** (the canonical answer): for each string, emit `len(s)` followed by a delimiter (`#`) and then `s` itself. To decode, read digits up to `#`, then read exactly that many chars. The delimiter is unambiguous because it's only consumed *after* a numeric prefix.",
        "Why length-prefix works even if the payload contains `#`: the decoder never *searches* for `#` inside the payload — it only reads `#` as the boundary between length and content, then jumps `len` characters forward.",
        "**Non-printable separator** (less safe): pick a character that's 'unlikely' to appear (e.g. `\\x01`) and join. Works for ASCII-restricted inputs; breaks the moment input is arbitrary bytes/Unicode. Mention only as a contrast.",
        "**Escape-then-separator** (works, more complex): replace every occurrence of the chosen delimiter inside each string with an escape sequence (e.g. `#` → `##`, then join with `# `). Decoder un-escapes. Correct but fiddly — length-prefix is simpler with the same complexity.",
        "Watch the empty list (`[]`) and the list-of-empty-string (`[\"\"]`) cases: both must round-trip. Length-prefix handles them naturally (`\"\"` vs `\"0#\"`).",
    ],
    "constraints": [
        "0 <= strs.length <= 200",
        "0 <= strs[i].length <= 200",
        "strs[i] may contain any Unicode characters (including digits, `#`, newlines, NUL bytes).",
    ],
    "starter_code": {
        "python": (
            "def encode(strs):\n"
            "    # Your code here\n"
            "    pass\n"
            "\n"
            "def decode(s):\n"
            "    # Your code here\n"
            "    pass"
        ),
        "javascript": (
            "function encode(strs) {\n"
            "    // Your code here\n"
            "}\n"
            "\n"
            "function decode(s) {\n"
            "    // Your code here\n"
            "}"
        ),
        "java": (
            "public String encode(List<String> strs) {\n"
            "    // Your code here\n"
            "    return \"\";\n"
            "}\n"
            "\n"
            "public List<String> decode(String s) {\n"
            "    // Your code here\n"
            "    return new ArrayList<>();\n"
            "}"
        ),
    },
    "boilerplate_code": {
        "python": (
            "# Test runner (read-only)\n"
            "if __name__ == \"__main__\":\n"
            "    cases = [[\"hello\", \"world\"], [\"\", \"a#b\", \"\"], []]\n"
            "    for strs in cases:\n"
            "        encoded = encode(strs)\n"
            "        decoded = decode(encoded)\n"
            "        print(f\"{strs} -> {encoded!r} -> {decoded}\")"
        ),
        "javascript": (
            "// Test runner (read-only)\n"
            "[[\"hello\", \"world\"], [\"\", \"a#b\", \"\"], []].forEach(strs => {\n"
            "    const encoded = encode(strs);\n"
            "    const decoded = decode(encoded);\n"
            "    console.log(strs, '->', JSON.stringify(encoded), '->', decoded);\n"
            "});"
        ),
        "java": (
            "// Test runner (read-only)\n"
            "public class Main {\n"
            "    public static void main(String[] args) {\n"
            "        Solution s = new Solution();\n"
            "        List<String> strs = Arrays.asList(\"hello\", \"world\");\n"
            "        String enc = s.encode(strs);\n"
            "        System.out.println(s.decode(enc));\n"
            "    }\n"
            "}"
        ),
    },
    "test_cases": [
        {"input": {"strs": []}, "expected": [],
         "description": "Empty list — encode/decode must handle the no-element case",
         "tags": ["edge"]},
        {"input": {"strs": [""]}, "expected": [""],
         "description": "Single empty string — must distinguish from an empty list",
         "tags": ["edge"]},
        {"input": {"strs": ["", "", ""]}, "expected": ["", "", ""],
         "description": "Three empty strings — length-prefix must preserve count",
         "tags": ["edge"]},
        {"input": {"strs": ["hello", "world"]}, "expected": ["hello", "world"],
         "description": "Vanilla two-string case",
         "tags": ["basic"]},
        {"input": {"strs": ["a#b", "c#d#e", "#"]}, "expected": ["a#b", "c#d#e", "#"],
         "description": "Strings containing the `#` separator inside the payload — naive join fails here",
         "tags": ["tricky"]},
        {"input": {"strs": ["1#2", "3#hello", "0#"]}, "expected": ["1#2", "3#hello", "0#"],
         "description": "Strings that *look* like length-prefixed encodings — decoder must rely on its own counter, not pattern-match",
         "tags": ["tricky"]},
        {"input": {"strs": ["line1\nline2", "tab\there", "null\x00byte"]},
         "expected": ["line1\nline2", "tab\there", "null\x00byte"],
         "description": "Special whitespace and NUL bytes — must pass through transparently",
         "tags": ["tricky"]},
        {"input": {"strs": ["café", "naïve", "Ω≈ç√", "你好", "🌍🚀"]},
         "expected": ["café", "naïve", "Ω≈ç√", "你好", "🌍🚀"],
         "description": "Multi-byte Unicode (Latin-1, Greek, CJK, emoji) — character-counted prefix must match decoder's char counter",
         "tags": ["tricky"]},
        {"input": {"strs": ["a" * 200, "b" * 199 + "c"]},
         "expected": ["a" * 200, "b" * 199 + "c"],
         "description": "Strings at the upper length bound (200 chars)",
         "tags": ["large"]},
        {"input": {"strs": ["x"] * 200}, "expected": ["x"] * 200,
         "description": "Maximum list length (200 elements) — overall encoded length stress",
         "tags": ["large"]},
        {"input": {"strs": ["123", "45", "6"]}, "expected": ["123", "45", "6"],
         "description": "All-numeric strings — decoder must not confuse payload digits with the next length prefix",
         "tags": ["tricky"]},
        {"input": {"strs": ["mixed#1\nstuff", "", "🔥#0", "plain"]},
         "expected": ["mixed#1\nstuff", "", "🔥#0", "plain"],
         "description": "Mixed: separators-in-content, empty, emoji+digits, and a plain string",
         "tags": ["tricky"]},
    ],
    "solutions": [
        {
            "title": "Length-Prefix `len#string` (Optimal)",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "For each string, emit its character length, a `#` delimiter, and then the string itself. "
                "To decode, walk the encoded string: read digits until `#`, parse the length, then jump exactly "
                "that many characters forward to extract the payload. The delimiter is unambiguous because "
                "the decoder only reads it once per record — immediately after the length prefix — and never "
                "searches for it inside the payload. n = total characters across all strings."
            ),
            "code": {
                "python": (
                    "def encode(strs):\n"
                    "    return ''.join(f\"{len(s)}#{s}\" for s in strs)\n"
                    "\n"
                    "def decode(s):\n"
                    "    res, i = [], 0\n"
                    "    while i < len(s):\n"
                    "        j = s.index('#', i)\n"
                    "        length = int(s[i:j])\n"
                    "        res.append(s[j + 1:j + 1 + length])\n"
                    "        i = j + 1 + length\n"
                    "    return res"
                ),
                "javascript": (
                    "function encode(strs) {\n"
                    "    return strs.map(s => `${[...s].length}#${s}`).join('');\n"
                    "}\n"
                    "\n"
                    "function decode(s) {\n"
                    "    const arr = [...s];  // split into code-points for unicode safety\n"
                    "    const res = [];\n"
                    "    let i = 0;\n"
                    "    while (i < arr.length) {\n"
                    "        let j = i;\n"
                    "        while (arr[j] !== '#') j++;\n"
                    "        const length = parseInt(arr.slice(i, j).join(''), 10);\n"
                    "        res.push(arr.slice(j + 1, j + 1 + length).join(''));\n"
                    "        i = j + 1 + length;\n"
                    "    }\n"
                    "    return res;\n"
                    "}"
                ),
                "java": (
                    "public String encode(List<String> strs) {\n"
                    "    StringBuilder sb = new StringBuilder();\n"
                    "    for (String s : strs) {\n"
                    "        sb.append(s.length()).append('#').append(s);\n"
                    "    }\n"
                    "    return sb.toString();\n"
                    "}\n"
                    "\n"
                    "public List<String> decode(String s) {\n"
                    "    List<String> res = new ArrayList<>();\n"
                    "    int i = 0;\n"
                    "    while (i < s.length()) {\n"
                    "        int j = s.indexOf('#', i);\n"
                    "        int length = Integer.parseInt(s.substring(i, j));\n"
                    "        res.add(s.substring(j + 1, j + 1 + length));\n"
                    "        i = j + 1 + length;\n"
                    "    }\n"
                    "    return res;\n"
                    "}"
                ),
            },
        },
        {
            "title": "Escape-Then-Separator",
            "time_complexity": "O(n)",
            "space_complexity": "O(n)",
            "description": (
                "Pick a separator (say `#`) and an escape rule: replace every `#` inside each payload "
                "with `##`, then join encoded payloads with `# ` (a `#` followed by a sentinel like a "
                "space, or any two-char marker that can't appear after a single `##` escape). On decode, "
                "split on the marker, then un-escape each chunk. Same asymptotic complexity as length-prefix "
                "but more bookkeeping and easier to get subtly wrong (especially around boundaries where "
                "the escape and the separator collide). Useful to know exists, but length-prefix wins on "
                "clarity in interviews."
            ),
            "code": {
                "python": (
                    "# Encode each string by doubling '#', then separate records with '#;'\n"
                    "def encode(strs):\n"
                    "    return '#;'.join(s.replace('#', '##') for s in strs)\n"
                    "\n"
                    "def decode(s):\n"
                    "    if s == '':\n"
                    "        return []\n"
                    "    # Split on '#;' that is NOT preceded by an unmatched '#'.\n"
                    "    # Easier approach: walk char-by-char.\n"
                    "    res, cur, i = [], [], 0\n"
                    "    while i < len(s):\n"
                    "        if s[i] == '#' and i + 1 < len(s) and s[i + 1] == '#':\n"
                    "            cur.append('#')\n"
                    "            i += 2\n"
                    "        elif s[i] == '#' and i + 1 < len(s) and s[i + 1] == ';':\n"
                    "            res.append(''.join(cur))\n"
                    "            cur = []\n"
                    "            i += 2\n"
                    "        else:\n"
                    "            cur.append(s[i])\n"
                    "            i += 1\n"
                    "    res.append(''.join(cur))\n"
                    "    return res"
                ),
            },
        },
    ],
    "thought_process": [
        "1. Clarify the input domain: 'can strings contain any character?' Answer: yes, including any delimiter you'd like to use. This kills the naive `','.join(strs)` approach immediately.",
        "2. Two families of correct solutions: (a) length-prefix, (b) escape-then-separator. State both, pick (a) — it's simpler and the de-facto interview answer.",
        "3. Length-prefix design: `<len>#<payload>` per record, concatenated. Decoder reads digits until the first `#`, parses the integer, then reads exactly `len` characters as the payload. Repeat until end-of-string.",
        "4. Why this is unambiguous: the decoder never *searches* for `#` inside the payload. The only `#` it ever consumes is the one immediately after the digit prefix — and the digit prefix is bounded by the *first* `#` it finds while scanning forward, which by construction is the boundary marker.",
        "5. Edge cases: empty list (`encode([]) == ''`), single empty string (`encode(['']) == '0#'`), strings that look like encodings (`'5#hello'` is a valid payload — the *outer* length prefix tells the decoder where it ends).",
        "6. Unicode caveat (worth raising in an interview): use *character* length, not *byte* length. In JS, `[...s].length` gives code-point count; `s.length` counts UTF-16 units, which can desync emoji. In Python and Java this is usually fine because string indexing is character-based.",
        "7. Complexity: encode is O(total chars) time, decode is O(total chars) time, O(total chars) extra space for the output list. Both are optimal — you can't do better than reading every input character.",
    ],
    "tips": [
        "If the interviewer asks 'why not just join with a comma?', answer with one example: `[\"a,b\", \"c\"]` and `[\"a\", \"b,c\"]` encode to the same string. The encoding must be a *bijection*.",
        "The length prefix doesn't have to be human-readable. Some real protocols use a fixed 4-byte big-endian length (`struct.pack('>I', len(s))`). Mention this if asked about binary protocols — it removes the need for a separator entirely.",
        "Beware off-by-one in the decoder: after parsing length `n` at index `j` (the `#`), the payload runs from `j+1` to `j+1+n` (exclusive). The next record starts at `j+1+n`.",
        "In JavaScript, `String.prototype.length` returns UTF-16 code-unit count, so emoji like `🌍` count as 2. If the spec is character-counted, spread to an array first (`[...s]`) so encode and decode agree on what 'length' means.",
        "Common follow-up: 'what if you can only output ASCII bytes but inputs are arbitrary bytes?' Answer: base64-encode each payload first, *then* length-prefix. Or, length-prefix the raw bytes if the channel is 8-bit clean.",
        "Common follow-up: 'how would you stream-decode without loading the whole encoded string?' Answer: same algorithm, but read from a buffered stream — read until `#`, parse length, then read exactly `len` chars and yield. State machine with two states: READING_LENGTH and READING_PAYLOAD.",
    ],
    "companies": ["Google", "Facebook", "Amazon", "Microsoft", "Bloomberg", "LinkedIn"],
    "topics": ["String", "Design", "Array"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(strs):
    # Round-trip identity: encode then decode must equal the input.
    # The PAYLOAD's solutions show real encode/decode logic; the test
    # harness verifies decode(encode(strs)) == strs by comparing the
    # candidate's output against this identity reference.
    return list(strs)


register(PAYLOAD, REFERENCE)
