from wordcount import count


def test_empty_string_returns_empty():
    assert count("") == {}


def test_token_that_is_only_punctuation_is_dropped():
    # "..." strips to "" — must NOT appear as an empty-string key.
    assert count("hello ... world") == {"hello": 1, "world": 1}


def test_internal_apostrophe_preserved():
    assert count("don't can't don't") == {"don't": 2, "can't": 1}


def test_mixed_case_and_punctuation():
    out = count("Foo, BAR! foo? bar.")
    assert out == {"foo": 2, "bar": 2}
