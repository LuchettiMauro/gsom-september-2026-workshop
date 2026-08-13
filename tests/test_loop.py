"""The manual agent loop from notebook 03.

This is the conceptual core of session 1, so it gets the most careful tests:
the whole point of the notebook is that an agent is a loop with a stop
condition, and a loop with a broken stop condition is an agent that costs you
money forever.
"""

import pytest

from stargate.loop import LoopResult, ModelReply, StopReason, ToolCall, run_agent_loop


class ScriptedModel:
    """A model that replies from a fixed script, recording what it was sent.

    Lets us test the loop without a network, a key, or a rate limit.
    """

    def __init__(self, script: list[ModelReply]) -> None:
        self.script = list(script)
        self.seen_messages: list[list[dict[str, object]]] = []

    def reply(
        self, messages: list[dict[str, object]], tools: list[dict[str, object]]
    ) -> ModelReply:
        self.seen_messages.append([dict(m) for m in messages])
        if not self.script:
            raise AssertionError("model called more times than the script allows")
        return self.script.pop(0)


def text(t: str) -> ModelReply:
    return ModelReply(text=t, tool_calls=[])


def call(name: str, **kwargs: object) -> ModelReply:
    return ModelReply(text=None, tool_calls=[ToolCall(id="c1", name=name, arguments=kwargs)])


# --- the happy path --------------------------------------------------------


def test_answers_directly_without_calling_a_tool() -> None:
    model = ScriptedModel([text("42 sightings.")])

    result = run_agent_loop(model, "how many?", tools={})

    assert isinstance(result, LoopResult)
    assert result.answer == "42 sightings."
    assert result.steps == 1
    assert result.stop_reason is StopReason.MODEL_ANSWERED


def test_executes_a_tool_then_answers() -> None:
    model = ScriptedModel([call("count_sightings", year=1952), text("There were 3 in 1952.")])
    calls: list[int] = []

    def count_sightings(year: int) -> int:
        calls.append(year)
        return 3

    result = run_agent_loop(model, "how many in 1952?", tools={"count_sightings": count_sightings})

    assert calls == [1952], "the loop, not the model, must execute the tool"
    assert result.answer == "There were 3 in 1952."
    assert result.steps == 2


def test_tool_result_is_appended_to_the_conversation() -> None:
    """The lesson of notebook 03: the model only sees what you put back in."""
    model = ScriptedModel([call("count_sightings", year=1952), text("done")])

    run_agent_loop(model, "q", tools={"count_sightings": lambda year: 7})

    second_turn = model.seen_messages[1]
    tool_messages = [m for m in second_turn if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert "7" in str(tool_messages[0]["content"])


def test_handles_several_tool_calls_in_one_reply() -> None:
    model = ScriptedModel(
        [
            ModelReply(
                text=None,
                tool_calls=[
                    ToolCall(id="a", name="count_sightings", arguments={"year": 1952}),
                    ToolCall(id="b", name="count_sightings", arguments={"year": 1953}),
                ],
            ),
            text("done"),
        ]
    )
    seen: list[int] = []

    run_agent_loop(model, "q", tools={"count_sightings": lambda year: seen.append(year) or 1})

    assert seen == [1952, 1953]


# --- the parts that stop it running forever --------------------------------


def test_stops_at_max_steps() -> None:
    """A model that always wants another tool call must not loop forever."""
    model = ScriptedModel([call("noop") for _ in range(10)])

    result = run_agent_loop(model, "q", tools={"noop": lambda: "ok"}, max_steps=3)

    assert result.steps == 3
    assert result.stop_reason is StopReason.MAX_STEPS
    assert result.answer is None


def test_unknown_tool_is_reported_to_the_model_not_raised() -> None:
    """A hallucinated tool name is a normal event, not a crash."""
    model = ScriptedModel([call("teleport", to="mars"), text("sorry, I cannot")])

    result = run_agent_loop(model, "q", tools={})

    assert result.answer == "sorry, I cannot"
    tool_msg = next(m for m in model.seen_messages[1] if m.get("role") == "tool")
    assert "teleport" in str(tool_msg["content"])
    assert "unknown" in str(tool_msg["content"]).lower()


def test_tool_that_raises_is_reported_to_the_model() -> None:
    def explode(**_: object) -> str:
        raise ValueError("database is on fire")

    model = ScriptedModel([call("explode"), text("I hit an error")])

    result = run_agent_loop(model, "q", tools={"explode": explode})

    assert result.answer == "I hit an error"
    tool_msg = next(m for m in model.seen_messages[1] if m.get("role") == "tool")
    assert "database is on fire" in str(tool_msg["content"])


def test_max_steps_must_be_positive() -> None:
    with pytest.raises(ValueError, match="max_steps"):
        run_agent_loop(ScriptedModel([]), "q", tools={}, max_steps=0)


# --- what students inspect -------------------------------------------------


def test_result_exposes_the_full_transcript_and_call_count() -> None:
    model = ScriptedModel([call("count_sightings", year=1952), text("3")])

    result = run_agent_loop(model, "how many in 1952?", tools={"count_sightings": lambda year: 3})

    assert result.messages[0] == {"role": "user", "content": "how many in 1952?"}
    assert result.llm_calls == 2, "one question cost two model calls — this is the point"
    assert [t.name for t in result.tool_calls_made] == ["count_sightings"]
