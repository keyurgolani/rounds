"""Word-frequency counter.

Spec:
  count(text) returns a dict mapping each lowercased word to its
  count. Words are split on whitespace, lowercased, then stripped of
  any leading/trailing punctuation (use string.punctuation). Empty
  tokens after stripping are NOT included in the result. Internal
  characters (e.g. apostrophes in "don't") are preserved verbatim.
"""


def count(text: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for w in text.split():
        key = w.lower()
        out[key] = out.get(key, 0) + 1
    return out
