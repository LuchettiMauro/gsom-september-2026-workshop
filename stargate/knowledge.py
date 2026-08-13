"""The unstructured half of the corpus: declassified documents, in a vector store.

Embeddings run locally through FastEmbed rather than through an API. That is
not a stylistic preference — Gemini's free embedding tier allows roughly 27k
tokens/minute and 1000 requests/day, which works out at about 28 minutes to
embed this corpus and a hard lockout for any student who runs it twice.
Locally it takes about a minute and cannot be rate limited.

The chunking here is deliberately naive: fixed-width, no overlap, no regard for
where a sentence ends. Changing `size` and `overlap` and re-measuring is the
closing exercise of session 2.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from stargate.chunking import NAIVE_OVERLAP, NAIVE_SIZE
from stargate.config import DATA_DIR, DEFAULT_EMBEDDER, DOCS_DIR, LANCEDB_DIR

TABLE_NAME = "declassified"
PREBUILT = DATA_DIR / "lancedb_prebuilt.tar.gz"


def _embedder() -> Any:
    from agno.knowledge.embedder.fastembed import FastEmbedEmbedder

    return FastEmbedEmbedder(id=DEFAULT_EMBEDDER)


def vector_db(uri: Path | str = LANCEDB_DIR, table_name: str = TABLE_NAME) -> Any:
    """The LanceDB table the agent searches. Embedded, file-based, no server."""
    from agno.vectordb.lancedb import LanceDb, SearchType

    return LanceDb(
        uri=str(uri),
        table_name=table_name,
        search_type=SearchType.vector,
        embedder=_embedder(),
    )


def document_paths(docs_dir: Path = DOCS_DIR) -> list[Path]:
    """The curated corpus on disk."""
    if not docs_dir.exists():
        raise FileNotFoundError(
            f"No corpus at {docs_dir}. Run `uv run python scripts/fetch_data.py` first."
        )
    paths = sorted(docs_dir.glob("*.md"))
    if not paths:
        raise FileNotFoundError(
            f"{docs_dir} exists but holds no .md files. Re-run scripts/fetch_data.py."
        )
    return paths


def build_knowledge(
    docs_dir: Path = DOCS_DIR,
    uri: Path | str = LANCEDB_DIR,
    *,
    size: int = NAIVE_SIZE,
    overlap: int = NAIVE_OVERLAP,
    recreate: bool = False,
    limit: int | None = None,
    verbose: bool = True,
) -> Any:
    """Chunk, embed and index the corpus. Returns an Agno `Knowledge`.

    One `add_content` call per *document*, not per chunk. Agno chunks and
    inserts each document in one pass; adding chunks individually means one
    LanceDB write per chunk, which turns a one-minute build into a nine-minute
    one. Worth knowing before you index anything larger than this.

    Args:
        size / overlap: chunking parameters, naive by default.
        recreate: drop and rebuild. Required after changing the chunking,
            since otherwise the old vectors are still in the table.
        limit: index only the first N documents. Useful for a quick smoke test.
    """
    from agno.knowledge.chunking.fixed import FixedSizeChunking
    from agno.knowledge.knowledge import Knowledge
    from agno.knowledge.reader.markdown_reader import MarkdownReader

    db = vector_db(uri)
    if recreate and db.exists():
        db.drop()

    knowledge = Knowledge(name="Declassified files", vector_db=db, max_results=5)

    if db.exists() and not recreate:
        if verbose:
            print(f"Using the existing index at {uri}. Pass recreate=True to rebuild.")
        return knowledge

    reader = MarkdownReader(chunking_strategy=FixedSizeChunking(chunk_size=size, overlap=overlap))
    paths = document_paths(docs_dir)[:limit]

    if verbose:
        print(f"Indexing {len(paths)} documents (chunk size {size}, overlap {overlap})...")
    for n, path in enumerate(paths, start=1):
        knowledge.add_content(
            name=path.stem,
            path=path,
            reader=reader,
            metadata={"doc_id": path.stem},
            skip_if_exists=False,
        )
        if verbose and n % 10 == 0:
            print(f"  {n}/{len(paths)}")

    if verbose:
        print(f"Done. Index at {uri}")
    return knowledge


# --- the prebuilt index ----------------------------------------------------
#
# Indexing all 42 documents takes several minutes: FastEmbed embeds one chunk
# at a time and LanceDB writes once per document. That is fine to *watch* on a
# handful of documents, and much too slow to sit through on all of them, so the
# finished index ships with the repo.


def restore_prebuilt_index(uri: Path | str = LANCEDB_DIR, *, force: bool = False) -> bool:
    """Unpack the index that ships with the repo. Returns True if it was written.

    Args:
        force: replace an existing index rather than leaving it alone.
    """
    import shutil
    import tarfile

    target = Path(uri)
    if target.exists() and not force:
        print(f"An index already exists at {target}. Pass force=True to replace it.")
        return False
    if not PREBUILT.exists():
        raise FileNotFoundError(
            f"No prebuilt index at {PREBUILT}. Build one with "
            "`uv run python scripts/build_index.py`, or index the corpus yourself "
            "with build_knowledge(recreate=True)."
        )
    if target.exists():
        shutil.rmtree(target)
    with tarfile.open(PREBUILT, "r:gz") as archive:
        archive.extractall(target.parent, filter="data")
    print(f"Restored the prebuilt index to {target}")
    return True


def knowledge_from_existing(uri: Path | str = LANCEDB_DIR) -> Any:
    """Wrap an index that is already on disk, without touching the documents."""
    from agno.knowledge.knowledge import Knowledge

    db = vector_db(uri)
    if not db.exists():
        raise FileNotFoundError(
            f"No index at {uri}. Run restore_prebuilt_index() or build_knowledge()."
        )
    return Knowledge(name="Declassified files", vector_db=db, max_results=5)
