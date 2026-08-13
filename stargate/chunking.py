"""Splitting documents into retrievable pieces.

Notebook 05 uses `NAIVE` — fixed 500 characters, no overlap, no regard for
where a sentence ends. That is not an oversight. It is the setting a
reasonable person picks first, and it produces the truncated-context failures
that show up in session 2's error analysis.

At the end of session 2, changing `overlap` and re-running is the "move one
number and watch the score shift" exercise.
"""

from __future__ import annotations

from dataclasses import dataclass

NAIVE_SIZE = 500
NAIVE_OVERLAP = 0


@dataclass(frozen=True)
class Chunk:
    """One piece of a document, plus enough metadata to cite it."""

    text: str
    index: int
    start: int
    end: int
    doc_id: str | None = None


def chunk_text(
    text: str,
    *,
    size: int = NAIVE_SIZE,
    overlap: int = NAIVE_OVERLAP,
    doc_id: str | None = None,
) -> list[Chunk]:
    """Split `text` into fixed-width chunks.

    Args:
        text: the document.
        size: characters per chunk.
        overlap: characters repeated between consecutive chunks. Zero in
            session 1, which is why answers sometimes stop mid-sentence.
        doc_id: carried onto every chunk so retrieved text can be attributed.

    Raises:
        ValueError: if `size` is not positive, or `overlap` is not smaller than
            `size` — that combination makes the window stop advancing, and the
            notebook would hang rather than fail.
    """
    if size < 1:
        raise ValueError(f"size must be at least 1, got {size}")
    if overlap >= size:
        raise ValueError(f"overlap ({overlap}) must be smaller than size ({size})")
    if overlap < 0:
        raise ValueError(f"overlap must not be negative, got {overlap}")

    if not text.strip():
        return []

    step = size - overlap
    chunks: list[Chunk] = []
    start = 0
    index = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(Chunk(text=text[start:end], index=index, start=start, end=end, doc_id=doc_id))
        if end == len(text):
            break
        start += step
        index += 1
    return chunks
