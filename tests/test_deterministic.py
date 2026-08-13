"""The cheap evaluators.

Five of the six failure categories students find in error analysis are
catchable with code like this. That ratio is the point of the exercise, so
these checks have to actually work.
"""

import pytest

from stargate.evaluators.deterministic import (
    ALL_CHECKS,
    Trace,
    check_citation,
    check_language,
    check_refusal,
    check_retrieval,
    check_routing,
    looks_like_a_counting_question,
    run_checks,
)

DOC = "CIA-RDP96-00789R003800440001-2"


def trace(**kw: object) -> Trace:
    base: dict[str, object] = {"question": "q", "answer": "a"}
    base.update(kw)
    return Trace(**base)  # type: ignore[arg-type]


# --- routing ---------------------------------------------------------------


@pytest.mark.parametrize(
    "question",
    [
        "How many sightings were there in 1952?",
        "how many ufo reports in New Mexico",
        "Count the disk-shaped sightings in 1973",
        "What is the number of sightings in 1997?",
        "Quante segnalazioni ci sono state nel 1952?",
    ],
)
def test_recognises_counting_questions(question: str) -> None:
    assert looks_like_a_counting_question(question)


@pytest.mark.parametrize(
    "question",
    [
        "What was the Gateway Process?",
        "Describe the Iran hostage remote viewing sessions.",
        "Who was Edwin May?",
    ],
)
def test_does_not_flag_narrative_questions(question: str) -> None:
    assert not looks_like_a_counting_question(question)


def test_routing_fails_when_a_counting_question_never_touched_sql() -> None:
    """The funniest failure: answering 'how many' from the vibes of a memo."""
    result = check_routing(
        trace(question="How many sightings in 1952?", tool_calls=["search_knowledge"])
    )
    assert result.passed is False
    assert "search_knowledge" in result.detail


def test_routing_passes_when_sql_was_used() -> None:
    result = check_routing(
        trace(question="How many sightings in 1952?", tool_calls=["count_sightings"])
    )
    assert result.passed is True


def test_routing_is_not_applicable_to_narrative_questions() -> None:
    result = check_routing(trace(question="What was Grill Flame?", tool_calls=[]))
    assert result.passed is None, "not applicable should be distinct from passing"


# --- citation --------------------------------------------------------------


def test_citation_found_in_document_id_form() -> None:
    assert check_citation(trace(answer=f"According to {DOC}, the programme ended.")).passed


def test_citation_missing() -> None:
    result = check_citation(trace(answer="The programme ended in 1995."))
    assert result.passed is False


def test_citation_accepts_bracketed_form() -> None:
    assert check_citation(trace(answer="It ended in 1995 [source: SUN STREAK 1990 report].")).passed


# --- refusal ---------------------------------------------------------------


def test_refusal_expected_and_given() -> None:
    result = check_refusal(
        trace(answer="I don't know — that isn't in these documents.", expects_refusal=True)
    )
    assert result.passed is True


def test_refusal_expected_but_answered_anyway() -> None:
    """Out-of-corpus hallucination: the model answers a question it cannot know."""
    result = check_refusal(
        trace(answer="Roswell involved a weather balloon from Project Mogul.", expects_refusal=True)
    )
    assert result.passed is False


def test_refusal_not_applicable_without_a_label() -> None:
    assert check_refusal(trace(answer="anything")).passed is None


def test_refusal_recognises_italian() -> None:
    result = check_refusal(trace(answer="Non lo so, non è nei documenti.", expects_refusal=True))
    assert result.passed is True


# --- retrieval -------------------------------------------------------------


def test_retrieval_hit() -> None:
    result = check_retrieval(trace(retrieved_ids=["other", DOC], gold_doc_id=DOC))
    assert result.passed is True


def test_retrieval_miss() -> None:
    result = check_retrieval(trace(retrieved_ids=["other"], gold_doc_id=DOC))
    assert result.passed is False


def test_retrieval_not_applicable_without_ground_truth() -> None:
    assert check_retrieval(trace(retrieved_ids=["x"])).passed is None


# --- language --------------------------------------------------------------


def test_language_drift_is_caught() -> None:
    result = check_language(
        trace(
            question="Quante segnalazioni ci sono state nel 1952 secondo questi documenti?",
            answer="There were three sightings reported in that year according to the records.",
        )
    )
    assert result.passed is False


def test_matching_language_passes() -> None:
    result = check_language(
        trace(
            question="Quante segnalazioni ci sono state nel 1952 secondo questi documenti?",
            answer="Nel 1952 sono state registrate tre segnalazioni secondo questi documenti.",
        )
    )
    assert result.passed is True


def test_language_check_skips_text_too_short_to_classify() -> None:
    """langdetect on three words is a coin flip; do not report a coin flip."""
    assert check_language(trace(question="ok", answer="3")).passed is None


# --- the suite -------------------------------------------------------------


def test_run_checks_returns_one_result_per_check() -> None:
    results = run_checks(trace(question="How many in 1952?", answer="Three."))
    assert len(results) == len(ALL_CHECKS)
    assert {r.name for r in results} == {c.__name__ for c in ALL_CHECKS}


def test_run_checks_never_raises_on_odd_input() -> None:
    """These run over hundreds of student traces unattended."""
    for weird in ["", "?" * 500, "🛸🛸🛸", "SELECT 1"]:
        run_checks(trace(question=weird, answer=weird))
