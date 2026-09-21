"""Evaluators that are just code.

Every check here corresponds to a failure category that shows up in error
analysis. They cost nothing, run in milliseconds, and never disagree with
themselves — which is exactly why you build these before reaching for a judge.

Each check returns `passed=None` when it does not apply to a given trace. That
distinction matters: "this check found nothing wrong" and "this check had
nothing to look at" are different facts, and averaging them together is how
eval dashboards start lying to you.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field

# Tools that constitute "asked the database". A counting question answered
# without one of these went to the wrong half of the corpus, and the check says
# so whether the answer was an invented number or an honest "I don't know" —
# a refusal is cheaper to read and no more correct.
SQL_TOOLS = frozenset({"count_sightings", "query_sightings", "duckdb", "run_sql"})

_COUNTING = re.compile(
    r"\b(how many|how much|count|number of|total|quante|quanti|numero di)\b",
    re.IGNORECASE,
)
# Document ids look like CIA-RDP96-00789R003800440001-2.
_DOC_ID = re.compile(r"\bCIA-RDP\d{2}-\d{5}[A-Z]\d+-\d\b", re.IGNORECASE)
# ...or a human-written attribution such as [source: ...] or (document: ...).
_ATTRIBUTION = re.compile(r"[\[(]\s*(source|document|doc|from)\s*:", re.IGNORECASE)

_REFUSALS = (
    "i don't know",
    "i do not know",
    "i cannot find",
    "not in these documents",
    "not in the documents",
    "no information",
    "non lo so",
    "non è nei documenti",
    "non ho trovato",
)

# Below this many characters, language detection is guessing.
MIN_CHARS_FOR_LANGUAGE = 25


@dataclass(frozen=True)
class Trace:
    """One agent interaction, flattened into the fields evaluators need.

    The optional fields are ground truth. A trace without them can still be
    checked by the reference-free evaluators.
    """

    question: str
    answer: str
    tool_calls: list[str] = field(default_factory=list)
    retrieved_ids: list[str] = field(default_factory=list)
    trace_id: str | None = None
    gold_doc_id: str | None = None
    expects_refusal: bool | None = None


@dataclass(frozen=True)
class EvalResult:
    name: str
    passed: bool | None
    detail: str = ""

    @property
    def applicable(self) -> bool:
        return self.passed is not None


def looks_like_a_counting_question(question: str) -> bool:
    """Does this question have a number for an answer?

    Deliberately a regex rather than a model. It is wrong sometimes; it is also
    free, instant, and inspectable, which for a routing check is the better trade.
    """
    return bool(_COUNTING.search(question))


# --- the checks ------------------------------------------------------------


def check_routing(trace: Trace) -> EvalResult:
    """Was a counting question answered with SQL rather than from a memo?"""
    if not looks_like_a_counting_question(trace.question):
        return EvalResult("check_routing", None, "not a counting question")
    used = SQL_TOOLS.intersection(trace.tool_calls)
    if used:
        return EvalResult("check_routing", True, f"used {sorted(used)}")
    called = ", ".join(trace.tool_calls) or "no tools"
    return EvalResult("check_routing", False, f"counting question answered with: {called}")


def check_citation(trace: Trace) -> EvalResult:
    """Did the answer say where it got this from?"""
    if _DOC_ID.search(trace.answer) or _ATTRIBUTION.search(trace.answer):
        return EvalResult("check_citation", True, "attribution present")
    return EvalResult("check_citation", False, "no document reference in the answer")


def check_refusal(trace: Trace) -> EvalResult:
    """When the answer isn't in the corpus, did the agent say so?"""
    if trace.expects_refusal is None:
        return EvalResult("check_refusal", None, "no expectation recorded")
    refused = any(marker in trace.answer.lower() for marker in _REFUSALS)
    if trace.expects_refusal:
        return EvalResult(
            "check_refusal",
            refused,
            "declined as expected" if refused else "answered a question it cannot know",
        )
    return EvalResult(
        "check_refusal",
        not refused,
        "declined a question it should have answered" if refused else "answered, as expected",
    )


def check_retrieval(trace: Trace) -> EvalResult:
    """Was the document that holds the answer among the ones retrieved?"""
    if trace.gold_doc_id is None:
        return EvalResult("check_retrieval", None, "no gold document recorded")
    hit = trace.gold_doc_id in trace.retrieved_ids
    return EvalResult(
        "check_retrieval",
        hit,
        f"gold {trace.gold_doc_id} {'found in' if hit else 'missing from'} "
        f"{len(trace.retrieved_ids)} retrieved",
    )


def check_language(trace: Trace) -> EvalResult:
    """Did the agent reply in the language it was asked in?"""
    if len(trace.question) < MIN_CHARS_FOR_LANGUAGE or len(trace.answer) < MIN_CHARS_FOR_LANGUAGE:
        return EvalResult("check_language", None, "too short to classify reliably")
    try:
        from langdetect import DetectorFactory, detect

        DetectorFactory.seed = 0  # langdetect is stochastic unless seeded
        asked, answered = detect(trace.question), detect(trace.answer)
    except Exception as exc:
        return EvalResult("check_language", None, f"detection failed: {exc}")
    return EvalResult(
        "check_language",
        asked == answered,
        f"asked in {asked}, answered in {answered}",
    )


ALL_CHECKS: tuple[Callable[[Trace], EvalResult], ...] = (
    check_routing,
    check_citation,
    check_refusal,
    check_retrieval,
    check_language,
)


def run_checks(
    trace: Trace, checks: tuple[Callable[[Trace], EvalResult], ...] = ALL_CHECKS
) -> list[EvalResult]:
    """Run every check over one trace.

    A check that raises is reported as not-applicable rather than allowed to
    abort the run: these execute unattended over hundreds of student traces,
    and one malformed answer must not take the batch down.
    """
    results: list[EvalResult] = []
    for check in checks:
        try:
            results.append(check(trace))
        except Exception as exc:
            results.append(EvalResult(check.__name__, None, f"check errored: {exc}"))
    return results
