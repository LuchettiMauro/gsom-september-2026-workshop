"""Evaluation, in the order session 2 builds it.

1. `deterministic` — cheap code-based checks. Most failure categories fall here.
2. `judge`         — an LLM judge, for the one category nothing cheaper catches.
3. `alignment`     — how much the judge agrees with a human, and humans with
                     each other.

The order is the lesson. Building a judge before doing error analysis means
measuring something you guessed at.
"""

from stargate.evaluators.alignment import Confusion, cohens_kappa, confusion_matrix
from stargate.evaluators.deterministic import (
    ALL_CHECKS,
    EvalResult,
    Trace,
    check_citation,
    check_language,
    check_refusal,
    check_retrieval,
    check_routing,
    run_checks,
)

__all__ = [
    "ALL_CHECKS",
    "Confusion",
    "EvalResult",
    "Trace",
    "check_citation",
    "check_language",
    "check_refusal",
    "check_retrieval",
    "check_routing",
    "cohens_kappa",
    "confusion_matrix",
    "run_checks",
]
