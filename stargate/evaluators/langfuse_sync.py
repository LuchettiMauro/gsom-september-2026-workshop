"""The local evaluators, pushed to Langfuse.

Everything else in this package runs on a laptop and leaves nothing behind.
That is the right way to *build* an evaluator and the wrong way to *keep* one:
a number printed in a notebook cell is a number nobody else sees, nobody
compares against last week, and nobody notices regressing.

Three things move across, and no more:

    push_dataset            the testset, as a dataset the whole room can open
    deterministic_evaluator run_checks(), in the shape run_experiment() wants
    pass_rate               one run-level number, so two runs compare at a glance

The dataset is the part worth being careful about. Items are created with an
explicit id derived from the trace, so re-running the cell updates the testset
instead of growing a second copy of it — which matters in a notebook, where
every cell gets run four times.

Nothing here decides anything. The checks are the same functions notebook 08
already built by hand; this only changes where their results end up.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from stargate.evaluators.deterministic import Trace, run_checks

DATASET_NAME = "stargate-eval"
DATASET_DESCRIPTION = (
    "Traces from session 1, labelled during error analysis in notebook 08. "
    "Inputs are the questions; metadata carries what the agent did at the time."
)


# --- the testset -----------------------------------------------------------


def push_dataset(
    traces: Sequence[Trace],
    *,
    name: str = DATASET_NAME,
    description: str = DATASET_DESCRIPTION,
) -> int:
    """Create or update the dataset and its items. Returns the item count.

    `create_dataset` and `create_dataset_item` are both upserts, the first on
    name and the second on id, so this is safe to run repeatedly.
    """
    from langfuse import get_client

    client = get_client()
    client.create_dataset(name=name, description=description)

    for position, trace in enumerate(traces):
        client.create_dataset_item(
            dataset_name=name,
            id=f"{name}:{trace.trace_id or position:02}",
            input={"question": trace.question},
            # Ground truth, and only ground truth. What the agent happened to
            # answer last week is evidence, not an expectation.
            expected_output={
                "gold_doc_id": trace.gold_doc_id,
                "expects_refusal": trace.expects_refusal,
            },
            metadata={
                "recorded_answer": trace.answer,
                "recorded_tool_calls": list(trace.tool_calls),
                "recorded_retrieved_ids": list(trace.retrieved_ids),
            },
        )

    client.flush()
    return len(traces)


# --- reading what a run actually did ---------------------------------------


def tool_names(run_output: Any) -> list[str]:
    """Every tool called during a run, the members' own included.

    A Team's own `tools` holds `delegate_task_to_member` and nothing else: the
    SQL call happened one level down, inside the member the router picked.
    Reading only the top level is how an evaluator concludes that a team which
    routed perfectly never touched the database, and `check_routing` then
    reports a failure that did not happen.

    Recursive, because a member can itself be a team.
    """
    names = [
        tool.tool_name
        for tool in (getattr(run_output, "tools", None) or [])
        if getattr(tool, "tool_name", None)
    ]
    for member in getattr(run_output, "member_responses", None) or []:
        names.extend(tool_names(member))
    return names


# --- turning a task's output back into something the checks understand -----


def _fields(output: Any) -> dict[str, Any]:
    """A task may return a bare string, or the three fields the checks want."""
    if isinstance(output, dict):
        return output
    return {"answer": "" if output is None else str(output)}


def trace_from_experiment(
    *,
    input: Any,
    output: Any,
    expected_output: Any,
    metadata: dict[str, Any] | None,
) -> Trace:
    """Rebuild a `Trace` from what run_experiment hands an evaluator.

    Tool calls and retrieved ids are read from the *output* when the task
    produced them, and from the item's metadata otherwise. That is what lets
    the same evaluator score a live agent run and a replay of last week's
    recorded answer, which is the comparison the whole exercise is for.
    """
    fields = _fields(output)
    meta = metadata or {}
    expected = expected_output if isinstance(expected_output, dict) else {}
    question = input.get("question", "") if isinstance(input, dict) else str(input or "")

    return Trace(
        question=question,
        answer=str(fields.get("answer") or ""),
        tool_calls=list(fields.get("tool_calls") or meta.get("recorded_tool_calls") or []),
        retrieved_ids=list(fields.get("retrieved_ids") or meta.get("recorded_retrieved_ids") or []),
        gold_doc_id=expected.get("gold_doc_id"),
        expects_refusal=expected.get("expects_refusal"),
    )


# --- the evaluators --------------------------------------------------------


def deterministic_evaluator(
    *,
    input: Any,
    output: Any,
    expected_output: Any = None,
    metadata: dict[str, Any] | None = None,
    **_: Any,
) -> list[Any]:
    """Every cheap check, as one Langfuse score each.

    A check that does not apply is dropped rather than scored zero. Langfuse
    averages what you give it, and a check with nothing to look at must not
    drag a run's number down — the same distinction the `of` column makes in
    the notebook, enforced here so the dashboard cannot quietly lose it.
    """
    from langfuse.experiment import Evaluation

    trace = trace_from_experiment(
        input=input, output=output, expected_output=expected_output, metadata=metadata
    )
    return [
        Evaluation(
            name=result.name,
            value=1.0 if result.passed else 0.0,
            comment=result.detail,
            data_type="NUMERIC",
        )
        for result in run_checks(trace)
        if result.passed is not None
    ]


def pass_rate(*, item_results: Iterable[Any], **_: Any) -> Any:
    """One number for the whole run: the share of applicable checks that passed.

    Deliberately not a per-check average of averages. Every check that had
    something to look at counts once, so a run where more checks applied is
    compared on more evidence rather than on a tidier number.
    """
    from langfuse.experiment import Evaluation

    # Materialised once: run_evaluators may be handed a generator, and reading
    # it twice would silently report zero items.
    results = list(item_results)
    values = [
        evaluation.value
        for result in results
        for evaluation in (getattr(result, "evaluations", None) or [])
        if isinstance(evaluation.value, int | float)
    ]
    if not values:
        return Evaluation(name="pass_rate", value=0.0, comment="no check applied to any item")
    return Evaluation(
        name="pass_rate",
        value=sum(values) / len(values),
        comment=f"{len(values)} applicable checks across {len(results)} items",
        data_type="NUMERIC",
    )
