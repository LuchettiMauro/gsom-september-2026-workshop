"""One LLM judge, for the one thing code cannot check.

Error analysis produces roughly six failure categories. Five of them fall to
the deterministic checks next door. The sixth — did the agent report what the
document *claims*, or assert it as *fact*? — needs a reader.

This file is deliberately not a wrapper around a managed evaluator. A judge is
a prompt, a rubric, and an alignment measurement; hiding those behind a
configuration form is how teams end up trusting a number nobody can explain.
Notebook 08 shows the managed version afterwards, once students know what is
inside it.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

_JSON_OBJECT = re.compile(r"\{.*?\}", re.DOTALL)
_TRUEISH = {"true", "yes", "y", "1", "grounded"}
_FALSEISH = {"false", "no", "n", "0", "ungrounded"}


@dataclass(frozen=True)
class Verdict:
    """What the judge decided. `None` means it failed to decide."""

    grounded: bool | None
    reason: str

    @property
    def is_failure(self) -> bool | None:
        """Translate into the convention the other evaluators use.

        Elsewhere in this package, True means *the trace has the defect*. Here
        True means *the answer was fine*. Getting that backwards silently
        inverts every metric in the notebook, so the conversion lives in one
        place with a test on it.
        """
        if self.grounded is None:
            return None
        return not self.grounded


def _coerce(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in _TRUEISH:
            return True
        if low in _FALSEISH:
            return False
    return None


def parse_verdict(raw: str) -> Verdict:
    """Pull a boolean out of whatever the model actually returned.

    Models wrap JSON in code fences, prefix it with "Sure!", and occasionally
    just write a paragraph. An unparseable reply is recorded as undecided —
    never as a pass, because "the judge broke" and "nothing was wrong" are
    different facts and only one of them is good news.
    """
    if not raw or not raw.strip():
        return Verdict(None, "judge returned nothing")

    for candidate in _JSON_OBJECT.findall(raw):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if not isinstance(data, dict) or "grounded" not in data:
            continue
        grounded = _coerce(data["grounded"])
        reason = str(data.get("reason", "")).strip() or "no reason given"
        if grounded is None:
            return Verdict(None, f"unrecognised verdict value: {data['grounded']!r}")
        return Verdict(grounded, reason)

    return Verdict(None, f"could not parse a verdict from: {raw.strip()[:120]!r}")


RUBRIC = """\
You are checking one thing only: whether an answer is GROUNDED in the source \
material it was given.

An answer is grounded when every factual claim it makes is supported by the \
context, AND when claims made *by* the documents are reported as claims rather \
than restated as established fact.

These documents are declassified reports about experimental programmes. They \
record what researchers claimed at the time. Reporting "a 1979 report concluded \
X" is grounded. Stating "X is true" because a document says so is NOT grounded, \
even if the document really says it.

Answer with JSON only: {"grounded": true|false, "reason": "<one short sentence>"}\
"""

_EXAMPLES = """\
Example 1
CONTEXT: "The 1979 SRI final report concluded that the viewer's description \
matched the target site."
ANSWER: "Remote viewing works — a viewer correctly described a target site."
VERDICT: {"grounded": false, "reason": "restates a study's claim as established fact"}

Example 2
CONTEXT: "The 1979 SRI final report concluded that the viewer's description \
matched the target site."
ANSWER: "A 1979 SRI report concluded that a viewer's description matched the target."
VERDICT: {"grounded": true, "reason": "attributes the claim to the report"}\
"""


def build_judge_prompt(question: str, answer: str, context: str, examples: str = _EXAMPLES) -> str:
    """Assemble the judge prompt.

    `examples` is a parameter because the few-shot cases should come from the
    students' own labelled traces. The default pair is a starting point, not
    the answer.
    """
    return f"""{RUBRIC}

{examples}

Now assess this one.

QUESTION: {question}

CONTEXT GIVEN TO THE AGENT:
{context}

ANSWER TO ASSESS:
{answer}

VERDICT:"""
