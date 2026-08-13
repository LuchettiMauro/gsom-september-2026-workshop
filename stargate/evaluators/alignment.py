"""How well does the judge agree with a human? How well do humans agree?

Session 2's last two beats live here. The order matters: you measure the judge
against human labels, discover the numbers are mediocre, and only then ask
whether the humans agreed with each other in the first place.

Throughout, the positive class is **"this trace has the defect"**. A true
positive is the judge correctly catching a real failure.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


def _safe_ratio(numerator: int, denominator: int) -> float:
    """Rates over an empty class are undefined; report 0.0 and let `n` explain."""
    return numerator / denominator if denominator else 0.0


@dataclass(frozen=True)
class Confusion:
    """A 2x2 confusion matrix, with the rates that matter for a judge."""

    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def n(self) -> int:
        return self.tp + self.fp + self.tn + self.fn

    @property
    def positives(self) -> int:
        """How many real failures the humans found.

        Printed alongside every rate, because a TPR computed from three
        positives is not a measurement, it is an anecdote.
        """
        return self.tp + self.fn

    @property
    def tpr(self) -> float:
        """Of the real failures, what fraction did the judge catch? (Recall.)"""
        return _safe_ratio(self.tp, self.tp + self.fn)

    @property
    def tnr(self) -> float:
        """Of the good traces, what fraction did the judge leave alone?"""
        return _safe_ratio(self.tn, self.tn + self.fp)

    @property
    def precision(self) -> float:
        return _safe_ratio(self.tp, self.tp + self.fp)

    @property
    def accuracy(self) -> float:
        return _safe_ratio(self.tp + self.tn, self.n)

    @property
    def f1(self) -> float:
        p, r = self.precision, self.tpr
        return 2 * p * r / (p + r) if (p + r) else 0.0

    def __str__(self) -> str:
        return (
            f"n={self.n} (positives={self.positives})  "
            f"TPR={self.tpr:.2f}  TNR={self.tnr:.2f}  "
            f"precision={self.precision:.2f}  F1={self.f1:.2f}\n"
            f"    tp={self.tp}  fp={self.fp}  fn={self.fn}  tn={self.tn}"
        )


def _validate(a: Sequence[bool], b: Sequence[bool]) -> None:
    if len(a) != len(b):
        raise ValueError(f"label sets must be the same length, got {len(a)} and {len(b)}")
    if not a:
        raise ValueError("cannot measure agreement on an empty label set")


def confusion_matrix(human: Sequence[bool], judge: Sequence[bool]) -> Confusion:
    """Compare judge verdicts against human labels, element by element.

    Args:
        human: ground truth. True means the human marked the trace as failing.
        judge: the judge's verdicts, in the same order.
    """
    _validate(human, judge)
    tp = sum(1 for h, j in zip(human, judge, strict=True) if h and j)
    fp = sum(1 for h, j in zip(human, judge, strict=True) if not h and j)
    tn = sum(1 for h, j in zip(human, judge, strict=True) if not h and not j)
    fn = sum(1 for h, j in zip(human, judge, strict=True) if h and not j)
    return Confusion(tp=tp, fp=fp, tn=tn, fn=fn)


def cohens_kappa(a: Sequence[bool], b: Sequence[bool]) -> float:
    """Agreement between two annotators, corrected for agreement by chance.

    Raw agreement flatters everyone: if 90% of traces are fine, two annotators
    who both say "fine" every time agree 90% of the time while having done no
    work. Kappa subtracts that.

    Returns 1.0 for perfect agreement, 0.0 for chance-level, negative for
    systematic disagreement.
    """
    _validate(a, b)
    n = len(a)
    observed = sum(1 for x, y in zip(a, b, strict=True) if x == y) / n

    p_a_true = sum(a) / n
    p_b_true = sum(b) / n
    expected = p_a_true * p_b_true + (1 - p_a_true) * (1 - p_b_true)

    if expected >= 1.0:
        # Both annotators used a single label throughout, so chance agreement is
        # total and kappa is undefined. Report the honest extremes instead.
        return 1.0 if observed == 1.0 else 0.0
    return (observed - expected) / (1 - expected)
