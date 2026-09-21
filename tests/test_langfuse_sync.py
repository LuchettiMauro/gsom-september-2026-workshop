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


# --- reading tool calls out of a delegated run -----------------------------


class _Tool:
    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name


class _Run:
    def __init__(self, tools: list, member_responses: list | None = None) -> None:
        self.tools = tools
        self.member_responses = member_responses or []


def test_tool_names_reaches_into_the_members_of_a_team() -> None:
    """The router's own tool list says 'delegate' and nothing about SQL."""
    from stargate.evaluators.langfuse_sync import tool_names

    team_run = _Run(
        tools=[_Tool("delegate_task_to_member")],
        member_responses=[_Run(tools=[_Tool("query_sightings")])],
    )
    assert tool_names(team_run) == ["delegate_task_to_member", "query_sightings"]


def test_tool_names_recurses_through_a_nested_team() -> None:
    from stargate.evaluators.langfuse_sync import tool_names

    nested = _Run(
        tools=[],
        member_responses=[_Run(tools=[], member_responses=[_Run(tools=[_Tool("run_sql")])])],
    )
    assert tool_names(nested) == ["run_sql"]


def test_tool_names_of_a_plain_agent_run() -> None:
    from stargate.evaluators.langfuse_sync import tool_names

    assert tool_names(_Run(tools=[_Tool("search_knowledge_base")])) == ["search_knowledge_base"]
    assert tool_names(_Run(tools=[])) == []


def test_a_team_run_passes_the_routing_check() -> None:
    """End to end: delegated SQL has to satisfy check_routing."""
    from stargate.evaluators.langfuse_sync import tool_names

    team_run = _Run(
        tools=[_Tool("delegate_task_to_member")],
        member_responses=[_Run(tools=[_Tool("query_sightings")])],
    )
    routing = next(
        e
        for e in deterministic_evaluator(
            input=ITEM_INPUT,
            output={"answer": "32 sightings.", "tool_calls": tool_names(team_run)},
            expected_output=None,
            metadata=None,
        )
        if e.name == "check_routing"
    )
    assert routing.value == 1.0


# --- a run that never completed is not a failing run -----------------------


class _StatusRun:
    def __init__(self, status, content="answer", tools=None) -> None:
        self.status = status
        self.content = content
        self.tools = tools or []
        self.member_responses = []


class _Brain:
    """Answers with the given statuses in order, one per call."""

    def __init__(self, statuses: list) -> None:
        self.statuses = list(statuses)
        self.calls = 0

    def run(self, _question):
        self.calls += 1
        return _StatusRun(self.statuses.pop(0), tools=[_Tool("query_sightings")])


def test_a_completed_run_is_returned_straight_away() -> None:
    from agno.run.base import RunStatus

    from stargate.evaluators.langfuse_sync import answer_with

    brain = _Brain([RunStatus.completed])
    out = answer_with(brain, "how many?")
    assert brain.calls == 1
    assert out["tool_calls"] == ["query_sightings"]
    assert "error" not in out


def test_a_rate_limited_run_is_retried_then_succeeds(monkeypatch) -> None:
    from agno.run.base import RunStatus

    import stargate.providers as providers
    from stargate.evaluators import langfuse_sync

    monkeypatch.setattr(providers, "RETRY_DELAYS", (0, 0, 0))
    brain = _Brain([RunStatus.error, RunStatus.error, RunStatus.completed])
    out = langfuse_sync.answer_with(brain, "how many?")
    assert brain.calls == 3
    assert "error" not in out


def test_a_run_that_never_completes_is_marked_rather_than_answered(monkeypatch) -> None:
    from agno.run.base import RunStatus

    import stargate.providers as providers
    from stargate.evaluators import langfuse_sync

    monkeypatch.setattr(providers, "RETRY_DELAYS", (0,))
    brain = _Brain([RunStatus.error, RunStatus.error])
    out = langfuse_sync.answer_with(brain, "how many?")
    assert out["error"]
    assert out["answer"] == ""


def test_an_errored_output_produces_no_scores() -> None:
    """The whole point: a quota failure must not read as a routing failure."""
    assert (
        deterministic_evaluator(
            input=ITEM_INPUT,
            output={"answer": "", "tool_calls": [], "error": "run status: error"},
            expected_output=ITEM_EXPECTED,
            metadata=ITEM_METADATA,
        )
        == []
    )


def test_without_the_guard_that_same_item_would_score_zero() -> None:
    """Shows what the guard is preventing, so the test fails if it is removed."""
    scored = deterministic_evaluator(
        input=ITEM_INPUT,
        output={"answer": "", "tool_calls": []},
        expected_output=ITEM_EXPECTED,
        metadata=ITEM_METADATA,
    )
    routing = next(e for e in scored if e.name == "check_routing")
    assert routing.value == 0.0
