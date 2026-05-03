"""RNA Transcription — Easy. String, Hash Table.

A single-pass character mapping using a four-entry lookup table.
Each nucleotide transforms independently, so no state or look-ahead
is needed.
"""
from builder.registry import register


PAYLOAD = {
    "title": "RNA Transcription",
    "difficulty": "Easy",
    "description": (
        "Given a DNA strand, return its RNA complement. Transcribe each nucleotide with these pairs: "
        "`G -> C`, `C -> G`, `T -> A`, and `A -> U`."
    ),
    "hints": [
        "Use a small lookup table for the four nucleotide mappings; this avoids a branch per nucleotide.",
        "Build a new string from left to right; do not mutate the input.",
        "The output length should always equal the input length for valid DNA.",
        "Decide how invalid nucleotides should behave before coding. These app tests use valid DNA strands, but the Exercism version raises on invalid input.",
    ],
    "constraints": ["0 <= dna.length <= 10^5", "dna contains only A, C, G, and T"],
    "starter_code": {
        "python": "def to_rna(dna):\n    # Your code here\n    pass",
        "javascript": "function toRna(dna) {\n    // Your code here\n}",
        "java": "public String toRna(String dna) {\n    // Your code here\n    return \"\";\n}",
    },
    "boilerplate_code": {
        "python": "# Test runner (read-only)\nif __name__ == \"__main__\":\n    print(to_rna(\"ACGTGGTCTTAA\"))",
        "javascript": "// Test runner (read-only)\nconsole.log(toRna(\"ACGTGGTCTTAA\"));",
        "java": "// Test runner (read-only)",
    },
    "test_cases": [
        {"input": {"dna": "C"}, "expected": "G", "description": "Cytosine to guanine", "tags": ["basic"]},
        {"input": {"dna": "G"}, "expected": "C", "description": "Guanine to cytosine", "tags": ["basic"]},
        {"input": {"dna": "T"}, "expected": "A", "description": "Thymine to adenine", "tags": ["basic"]},
        {"input": {"dna": "A"}, "expected": "U", "description": "Adenine to uracil", "tags": ["basic"]},
        {"input": {"dna": "ACGTGGTCTTAA"}, "expected": "UGCACCAGAAUU", "description": "Full Exercism sample", "tags": ["basic"]},
        {"input": {"dna": ""}, "expected": "", "description": "Empty strand", "tags": ["edge"]},
    ],
    "solutions": [{
        "title": "Lookup Table",
        "time_complexity": "O(n)",
        "space_complexity": "O(n)",
        "description": "Map each DNA nucleotide to its RNA complement and join the results.",
        "code": {
            "python": "def to_rna(dna):\n    pairs = {'G': 'C', 'C': 'G', 'T': 'A', 'A': 'U'}\n    return ''.join(pairs[ch] for ch in dna)",
            "javascript": "function toRna(dna) {\n    const pairs = { G: 'C', C: 'G', T: 'A', A: 'U' };\n    return [...dna].map((ch) => pairs[ch]).join('');\n}",
        },
    }],
    "thought_process": [
        "1. State the nucleotide mapping table before writing code.",
        "2. Explain that each character transforms independently, so a single pass is sufficient.",
        "3. Append or map each complement into a new sequence.",
        "4. Join the mapped characters and return the RNA strand.",
    ],
    "tips": [
        "This is a good place to mention input validation as a follow-up, not the core algorithm.",
        "Do not reverse the string; transcription preserves order.",
        "Use `ACGTGGTCTTAA -> UGCACCAGAAUU` as the full sanity check.",
    ],
    "companies": [],
    "topics": ["String", "Hash Table"],
    "time_complexity": "O(n)",
    "space_complexity": "O(n)",
}


def REFERENCE(dna):
    return "".join({"G": "C", "C": "G", "T": "A", "A": "U"}[ch] for ch in dna)


register(PAYLOAD, REFERENCE)
