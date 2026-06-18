"""Tests for the brace-matching JSON extractor."""

from __future__ import annotations

from aco_runtime_lib.agents._json_extract import (
    extract_all_json_objects,
    extract_last_json_object,
    iter_top_level_objects,
)


def test_extracts_single_object() -> None:
    text = '{"a": 1, "b": 2}'
    assert extract_all_json_objects(text) == [{"a": 1, "b": 2}]


def test_extracts_multiple_objects() -> None:
    text = 'first thing {"a": 1}\n' 'second thing {"b": 2, "c": 3}\n' "done"
    assert extract_all_json_objects(text) == [{"a": 1}, {"b": 2, "c": 3}]


def test_handles_nested_objects() -> None:
    text = '{"outer": {"inner": 1, "deeper": {"x": 2}}}'
    assert extract_all_json_objects(text) == [{"outer": {"inner": 1, "deeper": {"x": 2}}}]


def test_ignores_braces_in_strings() -> None:
    text = '{"a": "json with { and } in it"}'
    assert extract_all_json_objects(text) == [{"a": "json with { and } in it"}]


def test_ignores_escaped_quotes_in_strings() -> None:
    text = r'{"a": "she said \"hi { there }\""}'
    assert extract_all_json_objects(text) == [{"a": 'she said "hi { there }"'}]


def test_skips_invalid_json() -> None:
    text = 'not json {"a":} more text {"b": 2}'
    assert extract_all_json_objects(text) == [{"b": 2}]


def test_extract_last_returns_most_recent() -> None:
    text = '{"first": 1} {"second": 2} {"third": 3}'
    assert extract_last_json_object(text) == {"third": 3}


def test_iter_handles_empty_string() -> None:
    assert list(iter_top_level_objects("")) == []


def test_iter_handles_unclosed_brace() -> None:
    text = '{"a": 1, "b": 2'
    assert list(iter_top_level_objects(text)) == []


def test_iter_handles_extra_closing_brace() -> None:
    text = '}} {"a": 1}'
    assert list(iter_top_level_objects(text)) == ['{"a": 1}']


def test_handles_code_block_wrapping() -> None:
    text = (
        "Here's a result:\n"
        "```json\n"
        '{"verdict": "PASS", "confidence": 0.9}\n'
        "```\n"
        "And another:\n"
        "```\n"
        '{"verdict": "REPAIR", "issues": []}\n'
        "```\n"
    )
    objs = extract_all_json_objects(text)
    assert len(objs) == 2
    assert objs[0]["verdict"] == "PASS"
    assert objs[1]["verdict"] == "REPAIR"
