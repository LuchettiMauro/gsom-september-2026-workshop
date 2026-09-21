"""The adapter between the local checks and a Langfuse dataset run.

Nothing here talks to Langfuse. What is worth testing is the translation:
a dataset item plus a task's output has to come back out as the same `Trace`
the notebook's own checks were written against, and an inapplicable check has
to disappear rather than score zero.
"""

from __future__ import annotations

import pytest

pytest.importorskip("langfuse", reason="needs the langfuse SDK")

from stargate.evaluators.langfuse_sync import (
    deterministic_evaluator,
    pass_rate,
    trace_from_experiment,
)

ITEM_INPUT = {"question": "How many sightings were reported in 1952?"}
ITEM_METADATA = {
    "recorded_answer": "Well over a thousand.",
    "recorded_tool_calls": ["search_knowledge"],
    "recorded_retrieved_ids": ["CIA-RDP96-00788R002000160001-3"],
}
ITEM_EXPECTED = {"gold_doc_id": "CIA-RDP96-00788R002000160001-3", "expects_refusal": None}


# --- rebuilding a Trace ----------------------------------------------------


def test_a_replayed_answer_takes_its_tool_calls_from_the_item() -> None:
    trace = trace_from_experiment(
        input=ITEM_INPUT,
        output="Well over a thousand.",
        expected_output=ITEM_EXPECTED,
        metadata=ITEM_METADATA,
    )
    assert trace.question == ITEM_INPUT["question"]
    assert trace.tool_calls == ["search_knowledge"]
    assert trace.gold_doc_id == ITEM_EXPECTED["gold_doc_id"]


def test_a_live_run_takes_its_tool_calls_from_the_output() -> None:
    """The whole point of the fallback: one evaluator scores both kinds of run."""
    trace = trace_from_experiment(
        input=ITEM_INPUT,
        output={"answer": "32 sightings.", "tool_calls": ["query_sightings"]},
        expected_output=ITEM_EXPECTED,
        metadata=ITEM_METADATA,
    )
    assert trace.tool_calls == ["query_sightings"]
    assert trace.answer == "32 sightings."


def test_a_bare_string_output_is_accepted() -> None:
    trace = trace_from_experiment(
        input=ITEM_INPUT, output="anything", expected_output=None, metadata=None
    )
    assert trace.answer == "anything"
    assert trace.tool_calls == []


# --- turning verdicts into scores ------------------------------------------


def test_an_inapplicable_check_produces_no_score_at_all() -> None:
    """Scoring it zero would drag the run's average down over nothing."""
    names = {
        e.name
        for e in deterministic_evaluator(
            input=ITEM_INPUT, output="short", expected_output=None, metadata=None
        )
    }
    # No ground truth was supplied, so the reference-based checks have nothing
    # to look at and must be absent rather than failing.
    assert "check_retrieval" not in names
    assert "check_refusal" not in names


def test_scores_are_one_or_zero_and_carry_the_detail() -> None:
    evaluations = deterministic_evaluator(
        input=ITEM_INPUT,
        output={"answer": "Well over a thousand.", "tool_calls": ["search_knowledge"]},
        expected_output=ITEM_EXPECTED,
        metadata=ITEM_METADATA,
    )
    assert evaluations, "a counting question answered without SQL must be scored"
    assert all(e.value in (0.0, 1.0) for e in evaluations)
    assert all(isinstance(e.comment, str) for e in evaluations)
    routing = next(e for e in evaluations if e.name == "check_routing")
    assert routing.value == 0.0


# --- the run-level number --------------------------------------------------


class _Result:
    def __init__(self, evaluations: list) -> None:
        self.evaluations = evaluations


def test_pass_rate_reads_a_generator_once() -> None:
    from langfuse.experiment import Evaluation

    def results():
        yield _Result([Evaluation(name="a", value=1.0), Evaluation(name="b", value=0.0)])
        yield _Result([Evaluation(name="a", value=1.0)])

    score = pass_rate(item_results=results())
    assert score.value == pytest.approx(2 / 3)
    assert "3 applicable checks across 2 items" in (score.comment or "")


def test_pass_rate_says_so_when_nothing_applied() -> None:
    score = pass_rate(item_results=[_Result([])])
    assert score.value == 0.0
    assert "no check applied" in (score.comment or "")
