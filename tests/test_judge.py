"""The LLM judge for groundedness.

The prompt itself can only be evaluated against human labels (that is what
session 2 does). What *can* be unit-tested is the part that always breaks in
practice: getting a reliable boolean out of a model that likes to chat.
"""

import pytest

from stargate.evaluators.judge import Verdict, build_judge_prompt, parse_verdict


def test_parses_clean_json() -> None:
    v = parse_verdict('{"grounded": true, "reason": "supported by the retrieved memo"}')
    assert v.grounded is True
    assert "supported" in v.reason


def test_parses_json_in_a_code_fence() -> None:
    raw = '```json\n{"grounded": false, "reason": "asserted as fact"}\n```'
    assert parse_verdict(raw).grounded is False


def test_parses_json_buried_in_prose() -> None:
    raw = 'Sure! Here is my assessment:\n\n{"grounded": false, "reason": "no support"}\n\nHope that helps!'
    assert parse_verdict(raw).grounded is False


def test_unparseable_output_is_not_silently_a_pass() -> None:
    """A judge that failed to answer must not be recorded as 'no problem found'."""
    v = parse_verdict("I'm not sure how to assess this one.")
    assert v.grounded is None
    assert v.reason


def test_empty_output_is_undecided() -> None:
    assert parse_verdict("").grounded is None


@pytest.mark.parametrize("value", ["true", "True", "yes"])
def test_tolerates_common_boolean_spellings(value: str) -> None:
    assert parse_verdict(f'{{"grounded": "{value}", "reason": "x"}}').grounded is True


def test_verdict_converts_to_the_failure_convention() -> None:
    """Evaluators speak in failures; the judge speaks in groundedness."""
    assert Verdict(grounded=False, reason="r").is_failure is True
    assert Verdict(grounded=True, reason="r").is_failure is False
    assert Verdict(grounded=None, reason="r").is_failure is None


# --- the prompt ------------------------------------------------------------


def test_prompt_contains_the_material_being_judged() -> None:
    prompt = build_judge_prompt(
        question="Did remote viewing work?",
        answer="Remote viewing worked.",
        context="A 1979 SRI report claims positive results.",
    )
    assert "Did remote viewing work?" in prompt
    assert "Remote viewing worked." in prompt
    assert "1979 SRI report" in prompt


def test_prompt_demands_a_binary_verdict() -> None:
    """Binary, not a 1-5 scale: adjacent points on a Likert scale mean nothing."""
    prompt = build_judge_prompt(question="q", answer="a", context="c")
    assert "grounded" in prompt.lower()
    assert "true" in prompt.lower() and "false" in prompt.lower()


def test_prompt_includes_worked_examples() -> None:
    """Few-shot examples come from the students' own labels; ship a default pair."""
    prompt = build_judge_prompt(question="q", answer="a", context="c")
    assert prompt.lower().count("example") >= 1
