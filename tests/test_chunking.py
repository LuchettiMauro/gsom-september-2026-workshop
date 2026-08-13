"""Chunking.

Session 1 uses the naive settings on purpose — fixed size, no overlap, no
respect for sentence boundaries — because that is what produces the truncation
failures students find in session 2. The parameters are real parameters
though, so "move one number" at the end of session 2 actually works.
"""

import pytest

from stargate.chunking import chunk_text


def test_short_text_is_one_chunk() -> None:
    chunks = chunk_text("Approved for release.", size=500)
    assert len(chunks) == 1
    assert chunks[0].text == "Approved for release."
    assert chunks[0].index == 0


def test_splits_at_the_given_size() -> None:
    chunks = chunk_text("x" * 250, size=100, overlap=0)
    assert [len(c.text) for c in chunks] == [100, 100, 50]


def test_no_overlap_loses_nothing_and_repeats_nothing() -> None:
    original = "".join(str(i % 10) for i in range(250))
    chunks = chunk_text(original, size=100, overlap=0)
    assert "".join(c.text for c in chunks) == original


def test_overlap_repeats_the_boundary() -> None:
    chunks = chunk_text("abcdefghij", size=5, overlap=2)
    assert chunks[0].text == "abcde"
    assert chunks[1].text == "defgh", "should step forward by size - overlap"


def test_offsets_point_back_into_the_source() -> None:
    """Needed so a retrieved chunk can be shown in context."""
    source = "abcdefghij"
    for chunk in chunk_text(source, size=4, overlap=0):
        assert source[chunk.start : chunk.end] == chunk.text


def test_empty_text_produces_no_chunks() -> None:
    assert chunk_text("", size=100) == []
    assert chunk_text("   \n  ", size=100) == []


def test_overlap_must_be_smaller_than_size() -> None:
    """Otherwise the loop never advances and the notebook hangs forever."""
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("abc", size=5, overlap=5)


def test_size_must_be_positive() -> None:
    with pytest.raises(ValueError, match="size"):
        chunk_text("abc", size=0)


def test_chunks_carry_their_document_id() -> None:
    chunks = chunk_text("hello world", size=5, doc_id="CIA-RDP96-00789R003800440001-2")
    assert all(c.doc_id == "CIA-RDP96-00789R003800440001-2" for c in chunks)
