from matchers import match


def test_literal_expected_uses_exact_equality():
    assert match([0, 1], [0, 1], None) == (True, None)
    assert match([0, 1], [1, 0], None) == (False, None)
    assert match({"a": 1}, {"a": 1}, None) == (True, None)
    assert match(42, 42, None) == (True, None)
    assert match(42, 43, None) == (False, None)


def test_tagged_exact_matches_literal_behavior():
    expected = {"$match": "exact", "value": [0, 1]}
    assert match(expected, [0, 1], None) == (True, None)
    assert match(expected, [1, 0], None) == (False, None)


def test_unknown_matcher_returns_error():
    expected = {"$match": "no_such_matcher", "value": 1}
    passed, err = match(expected, 1, None)
    assert passed is False
    assert err is not None
    assert "no_such_matcher" in err


def test_unordered_passes_on_permutation():
    expected = {"$match": "unordered", "value": [0, 1]}
    assert match(expected, [1, 0], None) == (True, None)
    assert match(expected, [0, 1], None) == (True, None)


def test_unordered_fails_on_duplicate_count_mismatch():
    expected = {"$match": "unordered", "value": [1, 1, 2]}
    assert match(expected, [1, 2, 2], None) == (False, None)


def test_unordered_fails_on_non_list_output():
    expected = {"$match": "unordered", "value": [1, 2]}
    assert match(expected, "not a list", None) == (False, None)


def test_unordered_handles_nested_list_elements_as_whole_values():
    expected = {"$match": "unordered", "value": [[1, 2], [3, 4]]}
    assert match(expected, [[3, 4], [1, 2]], None) == (True, None)
    assert match(expected, [[2, 1], [4, 3]], None) == (False, None)


def test_unordered_deep_recurses_into_nested_lists():
    expected = {"$match": "unordered_deep", "value": [[1, 2], [3, 4]]}
    assert match(expected, [[2, 1], [4, 3]], None) == (True, None)
    assert match(expected, [[4, 3], [2, 1]], None) == (True, None)
    assert match(expected, [[1, 2], [3, 5]], None) == (False, None)


def test_any_of_passes_when_first_matches():
    expected = {"$match": "any_of", "values": [[0, 4], [2, 3]]}
    assert match(expected, [0, 4], None) == (True, None)


def test_any_of_passes_when_last_matches():
    expected = {"$match": "any_of", "values": [[0, 4], [2, 3]]}
    assert match(expected, [2, 3], None) == (True, None)


def test_any_of_fails_when_none_match():
    expected = {"$match": "any_of", "values": [[0, 4], [2, 3]]}
    assert match(expected, [1, 5], None) == (False, None)


def test_any_of_with_empty_values_fails():
    expected = {"$match": "any_of", "values": []}
    assert match(expected, [0, 1], None) == (False, None)


def test_contains_substring():
    expected = {"$match": "contains", "value": "foo"}
    assert match(expected, "the foo bar", None) == (True, None)
    assert match(expected, "the bar baz", None) == (False, None)


def test_contains_single_element_in_list():
    expected = {"$match": "contains", "value": 7}
    assert match(expected, [1, 2, 7, 9], None) == (True, None)
    assert match(expected, [1, 2, 9], None) == (False, None)


def test_contains_all_listed_elements_in_list():
    expected = {"$match": "contains", "value": [2, 7]}
    assert match(expected, [1, 2, 7, 9], None) == (True, None)
    assert match(expected, [1, 2, 9], None) == (False, None)


def test_subset_of_passes_when_every_output_element_is_in_value():
    expected = {"$match": "subset_of", "value": [1, 2, 3, 4]}
    assert match(expected, [1, 2], None) == (True, None)
    assert match(expected, [2, 2, 1], None) == (True, None)
    assert match(expected, [1, 5], None) == (False, None)


def test_superset_of_passes_when_every_value_element_is_in_output():
    expected = {"$match": "superset_of", "value": [1, 2]}
    assert match(expected, [1, 2, 3, 4], None) == (True, None)
    assert match(expected, [1, 3, 4], None) == (False, None)


def test_approx_scalar_within_abs_tol():
    expected = {"$match": "approx", "value": 3.14, "abs_tol": 1e-2}
    assert match(expected, 3.135, None) == (True, None)
    assert match(expected, 3.16, None) == (False, None)


def test_approx_scalar_within_rel_tol():
    expected = {"$match": "approx", "value": 1000.0, "rel_tol": 1e-3}
    assert match(expected, 1000.5, None) == (True, None)
    assert match(expected, 1002.0, None) == (False, None)


def test_approx_default_zero_tolerance_is_strict_equality():
    expected = {"$match": "approx", "value": 1.0}
    assert match(expected, 1.0, None) == (True, None)
    assert match(expected, 1.0000001, None) == (False, None)


def test_approx_recurses_into_same_shape_nested_lists():
    expected = {
        "$match": "approx",
        "value": [[1.0, 2.0], [3.0, 4.0]],
        "abs_tol": 0.05,
    }
    assert match(expected, [[1.01, 1.99], [3.04, 4.0]], None) == (True, None)
    assert match(expected, [[1.0, 2.0], [3.0, 4.5]], None) == (False, None)


def test_approx_shape_mismatch_fails():
    expected = {"$match": "approx", "value": [1.0, 2.0], "abs_tol": 0.1}
    assert match(expected, [1.0, 2.0, 3.0], None) == (False, None)
    assert match(expected, 1.5, None) == (False, None)


def test_validator_passes_when_predicate_returns_true():
    expected = {
        "$match": "validator",
        "code": "lambda inp, out: out == [inp['a'], inp['b']]",
    }
    assert match(expected, [1, 2], {"a": 1, "b": 2}) == (True, None)


def test_validator_fails_when_predicate_returns_false():
    expected = {
        "$match": "validator",
        "code": "lambda inp, out: out == [inp['a'], inp['b']]",
    }
    assert match(expected, [1, 3], {"a": 1, "b": 2}) == (False, None)


def test_validator_two_sum_predicate_accepts_either_valid_pair():
    code = (
        "lambda inp, out: isinstance(out, list) and len(out) == 2 "
        "and out[0] != out[1] "
        "and 0 <= out[0] < len(inp['nums']) "
        "and 0 <= out[1] < len(inp['nums']) "
        "and inp['nums'][out[0]] + inp['nums'][out[1]] == inp['target']"
    )
    expected = {"$match": "validator", "code": code}
    inp = {"nums": [1, 5, 6, 9, 14], "target": 15}
    assert match(expected, [0, 4], inp) == (True, None)
    assert match(expected, [4, 0], inp) == (True, None)
    assert match(expected, [2, 3], inp) == (True, None)
    assert match(expected, [0, 1], inp) == (False, None)


def test_validator_exception_becomes_error_string():
    expected = {"$match": "validator", "code": "lambda inp, out: out[99]"}
    passed, err = match(expected, [1, 2], None)
    assert passed is False
    assert err is not None
    assert "Validator error" in err


def test_validator_coerces_non_bool_truthy_to_pass():
    expected = {"$match": "validator", "code": "lambda inp, out: out"}
    assert match(expected, [1], None) == (True, None)
    assert match(expected, [], None) == (False, None)


def test_validator_cannot_import_os():
    expected = {"$match": "validator", "code": "lambda inp, out: __import__('os').getcwd()"}
    passed, err = match(expected, None, None)
    assert passed is False
    assert err is not None
    assert "Validator error" in err
