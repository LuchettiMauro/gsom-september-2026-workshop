"""Instructor script: build the vector index and package it for the repo.

    uv run python scripts/build_index.py

Students do not run this. It indexes all 42 documents (a few minutes) and
writes data/lancedb_prebuilt.tar.gz, which notebook 05 unpacks in seconds.

Re-run it whenever the corpus manifest or the chunking defaults change.
"""

from __future__ import annotations

import argparse
import logging
import sys
import tarfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from stargate.chunking import NAIVE_OVERLAP, NAIVE_SIZE  # noqa: E402
from stargate.config import LANCEDB_DIR  # noqa: E402
from stargate.knowledge import PREBUILT, build_knowledge  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--size", type=int, default=NAIVE_SIZE)
    parser.add_argument("--overlap", type=int, default=NAIVE_OVERLAP)
    parser.add_argument("--quiet", action="store_true", help="silence Agno's INFO logs")
    args = parser.parse_args()

    if args.quiet:
        logging.disable(logging.INFO)

    print(f"Building index (chunk size {args.size}, overlap {args.overlap})...")
    knowledge = build_knowledge(size=args.size, overlap=args.overlap, recreate=True)

    rows = knowledge.vector_db.table.count_rows()
    print(f"{rows} chunks indexed.")

    PREBUILT.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(PREBUILT, "w:gz") as archive:
        archive.add(LANCEDB_DIR, arcname=LANCEDB_DIR.name)
    size_mb = PREBUILT.stat().st_size / 1_048_576
    print(f"Packaged {PREBUILT.relative_to(REPO_ROOT)} ({size_mb:.1f} MB). Commit it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
