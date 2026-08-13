"""An agent, written out by hand.

This module is the destination of notebook 03. There is no framework here and
nothing clever: an agent is a loop that calls a model, executes whatever the
model asked for, feeds the result back, and repeats until the model stops
asking for things.

Everything Agno does in notebook 04 is a more careful version of this file.

The one design decision worth noticing is `ModelClient`: the loop does not know
which provider it is talking to. That is what makes it testable without a
network, and it is the same abstraction a framework sells you.
"""

from __future__ import annotations

import enum
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

Message = dict[str, Any]
ToolFn = Callable[..., Any]

DEFAULT_MAX_STEPS = 6


@dataclass(frozen=True)
class ToolCall:
    """A request from the model to run one tool.

    Note what this is not: it is not a tool being called. The model cannot
    reach your machine. It can only emit a structured request and wait.
    """

    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelReply:
    """One turn from the model: either prose, or a request for tools, or both."""

    text: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def wants_tools(self) -> bool:
        return bool(self.tool_calls)


class ModelClient(Protocol):
    """Anything that can turn a conversation into a reply.

    Notebook 01 builds three of these — one per provider — and discovers they
    differ only in wire format.
    """

    def reply(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelReply: ...


class StopReason(enum.Enum):
    """Why the loop ended. There are only ever two answers."""

    MODEL_ANSWERED = "model_answered"
    MAX_STEPS = "max_steps"


@dataclass
class LoopResult:
    answer: str | None
    messages: list[Message]
    steps: int
    llm_calls: int
    tool_calls_made: list[ToolCall]
    stop_reason: StopReason


def _run_one_tool(tools: dict[str, ToolFn], call: ToolCall) -> str:
    """Execute a single tool request and return what the model should be told.

    Both failure modes below get *reported to the model* rather than raised.
    A model that hallucinates a tool name, or a tool that throws, is an
    ordinary event in agent-land: the model usually recovers if you tell it
    what happened. Raising would end the conversation instead.
    """
    fn = tools.get(call.name)
    if fn is None:
        known = ", ".join(sorted(tools)) or "none"
        return f"Error: unknown tool {call.name!r}. Available tools: {known}."
    try:
        return str(fn(**call.arguments))
    except Exception as exc:
        return f"Error: tool {call.name!r} failed: {exc}"


def run_agent_loop(
    model: ModelClient,
    user_message: str,
    tools: dict[str, ToolFn],
    *,
    tool_schemas: list[dict[str, Any]] | None = None,
    max_steps: int = DEFAULT_MAX_STEPS,
) -> LoopResult:
    """Run the agent loop until the model stops asking for tools.

    Args:
        model: anything implementing `ModelClient`.
        user_message: the question.
        tools: name -> callable. The loop executes these; the model never does.
        tool_schemas: the JSON descriptions sent to the model. Defaults to
            whatever `stargate.tools` has registered for these names.
        max_steps: hard ceiling on model calls.

    Why `max_steps` exists: a model that keeps requesting tools produces a loop
    that keeps paying for them. Every agent framework has this ceiling; most
    hide it. Notebook 03 makes students choose the number themselves.
    """
    if max_steps < 1:
        raise ValueError(f"max_steps must be at least 1, got {max_steps}")

    schemas = tool_schemas if tool_schemas is not None else _default_schemas(tools)

    messages: list[Message] = [{"role": "user", "content": user_message}]
    made: list[ToolCall] = []

    for step in range(1, max_steps + 1):
        reply = model.reply(messages, schemas)

        if not reply.wants_tools:
            messages.append({"role": "assistant", "content": reply.text})
            return LoopResult(
                answer=reply.text,
                messages=messages,
                steps=step,
                llm_calls=step,
                tool_calls_made=made,
                stop_reason=StopReason.MODEL_ANSWERED,
            )

        # The model asked for tools. Record the request, run them, and put the
        # results back into the conversation — the model has no memory of its
        # own, so anything not in `messages` did not happen as far as it knows.
        messages.append(
            {
                "role": "assistant",
                "content": reply.text,
                "tool_calls": [
                    {"id": c.id, "name": c.name, "arguments": c.arguments} for c in reply.tool_calls
                ],
            }
        )
        for call in reply.tool_calls:
            made.append(call)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": call.name,
                    "content": _run_one_tool(tools, call),
                }
            )

    return LoopResult(
        answer=None,
        messages=messages,
        steps=max_steps,
        llm_calls=max_steps,
        tool_calls_made=made,
        stop_reason=StopReason.MAX_STEPS,
    )


def _default_schemas(tools: dict[str, ToolFn]) -> list[dict[str, Any]]:
    """Look up JSON schemas for the given tool names, skipping unknown ones."""
    from stargate.tools import schema_for

    out: list[dict[str, Any]] = []
    for name in tools:
        schema = schema_for(name)
        if schema is not None:
            out.append(schema)
    return out


def transcript(result: LoopResult) -> str:
    """Pretty-print a loop result. Used in notebook 03 to show the conversation."""
    lines: list[str] = []
    for msg in result.messages:
        role = str(msg.get("role", "?")).upper()
        if msg.get("tool_calls"):
            for tc in msg["tool_calls"]:
                lines.append(f"{role:>9} -> wants {tc['name']}({json.dumps(tc['arguments'])})")
        elif msg.get("content") is not None:
            lines.append(f"{role:>9} | {msg['content']}")
    lines.append("")
    lines.append(f"{'':>9}   {result.llm_calls} model calls, stopped: {result.stop_reason.value}")
    return "\n".join(lines)
