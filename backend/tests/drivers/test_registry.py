import pytest
from drivers import get_driver, LANGUAGES, KINDS


def test_unknown_language_raises():
    with pytest.raises(KeyError, match="ruby"):
        get_driver("ruby", "function")


def test_unknown_kind_raises():
    with pytest.raises(KeyError, match="quantum"):
        get_driver("python", "quantum")


def test_known_kinds_return_modules_with_validate_and_wrapper():
    for lang in LANGUAGES:
        for kind in KINDS:
            driver = get_driver(lang, kind)
            assert callable(driver.validate)
            assert callable(driver.wrapper_snippet)


def test_entry_model_accepts_known_kind():
    from schemas import Entry
    e = Entry.model_validate({"kind": "function", "name": "twoSum"})
    assert e.kind == "function"


def test_entry_model_rejects_unknown_kind():
    from schemas import Entry
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        Entry.model_validate({"kind": "ruby", "name": "x"})


def test_entry_model_preserves_extra_fields():
    from schemas import Entry
    e = Entry.model_validate({"kind": "class_ops", "class": "LRUCache",
                              "methods": [{"name": "get"}]})
    assert e.model_extra.get("class") == "LRUCache"
    assert e.model_extra.get("methods") == [{"name": "get"}]


def test_entry_kinds_match_registry_kinds():
    import typing
    from schemas import Entry
    from drivers import KINDS
    literal_args = set(typing.get_args(Entry.model_fields["kind"].annotation))
    assert literal_args == set(KINDS)
