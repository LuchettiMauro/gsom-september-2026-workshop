"""Talking to a model provider directly, with no framework in the way.

Notebook 01 uses these to show that the three big providers differ in wire
format and almost nothing else. Notebook 03 plugs `GeminiClient` into the
hand-written agent loop.

The single most important line in this file is `disable=True` on automatic
function calling. Left on, the SDK executes tools for you behind the scenes —
which is convenient in production and fatal in a lesson whose whole point is
that **the model does not call anything; it asks you to**.
"""

from __future__ import annotations

import time
from typing import Any

from stargate.config import settings
from stargate.loop import Message, ModelReply, ToolCall

# Free-tier Gemini allows ~15 requests/minute. Rather than let students stare
# at a 429, back off and tell them what is happening.
RETRY_DELAYS = (2, 5, 12, 30)


class RateLimited(RuntimeError):
    pass


def _is_rate_limit(exc: Exception) -> bool:
    text = f"{type(exc).__name__} {exc}".lower()
    return "429" in text or "resource_exhausted" in text or "rate limit" in text


def with_backoff(fn: Any, *args: Any, **kwargs: Any) -> Any:
    """Call `fn`, retrying on rate limits with increasing delays.

    Worth reading rather than skipping: an agent makes several model calls per
    question, so on a free tier the rate limit is a design constraint and not
    an annoyance. Notebook 04 makes students look at the call count for this
    reason.
    """
    last: Exception | None = None
    for delay in (*RETRY_DELAYS, None):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            if not _is_rate_limit(exc):
                raise
            last = exc
            if delay is None:
                break
            print(f"  rate limited; waiting {delay}s before retrying...")
            time.sleep(delay)
    raise RateLimited(
        "Still rate limited after several retries. Free-tier Gemini allows about "
        "15 requests/minute and 1000/day. Wait a minute, or switch STARGATE_MODEL."
    ) from last


class GeminiClient:
    """A `ModelClient` for the hand-written loop in notebook 03."""

    def __init__(self, model: str | None = None, system: str | None = None) -> None:
        from google import genai

        self.model = model or settings().model
        self.system = system
        self._client = genai.Client(api_key=settings().require_google())
        self.call_count = 0

    # -- conversion between our loop's message format and Gemini's ----------

    @staticmethod
    def _to_contents(messages: list[Message]) -> list[Any]:
        """Our messages -> Gemini `contents`.

        Gemini has no "tool" role: a tool result is a *user* turn carrying a
        `function_response` part. That mismatch is exactly the kind of thing
        notebook 01 is about.
        """
        from google.genai import types

        contents: list[Any] = []
        for msg in messages:
            role = msg.get("role")
            if role == "user":
                contents.append(
                    types.Content(role="user", parts=[types.Part(text=str(msg["content"]))])
                )
            elif role == "assistant":
                parts: list[Any] = []
                if msg.get("content"):
                    parts.append(types.Part(text=str(msg["content"])))
                for call in msg.get("tool_calls", []):
                    parts.append(
                        types.Part(
                            function_call=types.FunctionCall(
                                id=call["id"], name=call["name"], args=call["arguments"]
                            )
                        )
                    )
                if parts:
                    contents.append(types.Content(role="model", parts=parts))
            elif role == "tool":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    id=msg.get("tool_call_id"),
                                    name=str(msg.get("name")),
                                    response={"result": str(msg.get("content"))},
                                )
                            )
                        ],
                    )
                )
        return contents

    def reply(self, messages: list[Message], tools: list[dict[str, Any]]) -> ModelReply:
        from google.genai import types

        declarations = [
            types.FunctionDeclaration(
                name=t["name"],
                description=t.get("description", ""),
                parameters_json_schema=t.get("parameters"),
            )
            for t in tools
        ]
        config = types.GenerateContentConfig(
            system_instruction=self.system,
            tools=[types.Tool(function_declarations=declarations)] if declarations else None,
            # THE important line. With automatic function calling left enabled,
            # the SDK would run the tools itself and the loop below would never
            # see a `function_call` part at all.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        response = with_backoff(
            self._client.models.generate_content,
            model=self.model,
            contents=self._to_contents(messages),
            config=config,
        )
        self.call_count += 1
        return self._to_reply(response)

    @staticmethod
    def _to_reply(response: Any) -> ModelReply:
        text_parts: list[str] = []
        calls: list[ToolCall] = []
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            for part in getattr(content, "parts", None) or []:
                if getattr(part, "text", None):
                    text_parts.append(part.text)
                fc = getattr(part, "function_call", None)
                if fc is not None:
                    calls.append(
                        ToolCall(
                            id=fc.id or f"call_{len(calls)}",
                            name=fc.name or "",
                            arguments=dict(fc.args or {}),
                        )
                    )
        return ModelReply(text="".join(text_parts) or None, tool_calls=calls)
