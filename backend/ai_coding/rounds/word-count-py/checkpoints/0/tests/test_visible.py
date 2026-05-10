from wordcount import count


# These tests pass against the starter — they cover the
# already-working baseline (whitespace split + lowercase). They stay
# passing after the feature is added.
def test_basic_frequency():
    assert count("hello world hello") == {"hello": 2, "world": 1}


def test_lowercase_normalization():
    assert count("Hello hello HELLO") == {"hello": 3}


# This test FAILS against the starter — it's the feature-add the
# candidate must implement. The visible suite is intentionally red on
# this entry until the work is done.
def test_strips_leading_and_trailing_punctuation():
    assert count("hello, world! hello.") == {"hello": 2, "world": 1}
