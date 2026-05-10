import json, pathlib

# A trivial hidden assertion to verify the hidden-test pipeline. The
# real critical-verification round (async-bugs-py, Task 1.4) is where
# this matters.
def test_discounts_file_present():
    root = pathlib.Path(__file__).resolve().parents[2]  # workdir root
    data = json.loads((root / "discounts.json").read_text())
    assert "BLACKFRIDAY50" in data
