"""Measuring the judge against humans, and humans against each other.

The positive class throughout is "this trace has the defect". So a true
positive is the judge correctly catching a real failure.
"""

import pytest

from stargate.evaluators.alignment import (
    Confusion,
    cohens_kappa,
    confusion_matrix,
)

#            human:  T  T  T  F  F  F  F
#            judge:  T  T  F  T  F  F  F
HUMAN = [True, True, True, False, False, False, False]
JUDGE = [True, True, False, True, False, False, False]


def test_confusion_counts() -> None:
    c = confusion_matrix(HUMAN, JUDGE)
    assert (c.tp, c.fn, c.fp, c.tn) == (2, 1, 1, 3)


def test_rates() -> None:
    c = confusion_matrix(HUMAN, JUDGE)
    assert c.tpr == pytest.approx(2 / 3), "caught 2 of the 3 real failures"
    assert c.tnr == pytest.approx(3 / 4), "correctly cleared 3 of the 4 good traces"
    assert c.precision == pytest.approx(2 / 3)
    assert c.accuracy == pytest.approx(5 / 7)


def test_f1() -> None:
    c = confusion_matrix(HUMAN, JUDGE)
    assert c.f1 == pytest.approx(2 / 3)


def test_perfect_judge() -> None:
    c = confusion_matrix(HUMAN, HUMAN)
    assert c.tpr == 1.0 and c.tnr == 1.0


def test_rates_are_zero_when_there_is_nothing_to_measure() -> None:
    """No actual failures means TPR is undefined; report 0.0 rather than crash."""
    c = confusion_matrix([False, False], [False, True])
    assert c.tpr == 0.0
    assert c.tnr == pytest.approx(0.5)


def test_mismatched_lengths_are_rejected() -> None:
    with pytest.raises(ValueError, match="same length"):
        confusion_matrix([True], [True, False])


def test_empty_input_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        confusion_matrix([], [])


def test_sample_size_is_reported() -> None:
    """So the notebook can print 'TPR 0.67 (from 3 positives)' rather than '0.67'."""
    c = confusion_matrix(HUMAN, JUDGE)
    assert c.n == 7
    assert c.positives == 3


# --- inter-annotator agreement --------------------------------------------


def test_kappa_is_one_for_total_agreement() -> None:
    assert cohens_kappa(HUMAN, HUMAN) == pytest.approx(1.0)


def test_kappa_is_zero_for_chance_agreement() -> None:
    a = [True, True, False, False]
    b = [True, False, True, False]
    assert cohens_kappa(a, b) == pytest.approx(0.0)


def test_kappa_is_negative_for_systematic_disagreement() -> None:
    a = [True, True, False, False]
    b = [False, False, True, True]
    assert cohens_kappa(a, b) < 0


def test_kappa_when_both_annotators_only_ever_say_one_thing() -> None:
    """Chance agreement is 1.0 here, so the usual formula divides by zero."""
    assert cohens_kappa([True, True], [True, True]) == pytest.approx(1.0)
    assert cohens_kappa([True, True], [False, False]) == pytest.approx(0.0)


def test_kappa_known_value() -> None:
    # 20 items: 8 both-yes, 4 a-yes/b-no, 3 a-no/b-yes, 5 both-no.
    a = [True] * 12 + [False] * 8
    b = [True] * 8 + [False] * 4 + [True] * 3 + [False] * 5
    # po = (8 + 5) / 20 = 0.65
    # pe = (12/20)(11/20) + (8/20)(9/20) = 0.33 + 0.18 = 0.51
    assert cohens_kappa(a, b) == pytest.approx((0.65 - 0.51) / (1 - 0.51))


def test_confusion_is_printable() -> None:
    """It gets shown in the notebook, so it must render without extra work."""
    assert "TPR" in str(Confusion(tp=1, fp=1, tn=1, fn=1))
