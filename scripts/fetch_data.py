"""Fetch the two halves of the corpus. Run once, during phase 0.

    uv run python scripts/fetch_data.py

Writes:
    data/docs/*.md        42 declassified documents, as text
    data/nuforc.parquet   ~80k UFO sighting reports, structured

Both sources are public. The documents are US Government works in the public
domain; the sightings are a teaching dataset derived from NUFORC reports.

Re-running is cheap: anything already on disk is skipped unless --force.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
DOCS = DATA / "docs"
MANIFEST = DATA / "corpus_manifest.json"
PARQUET = DATA / "nuforc.parquet"

SIGHTINGS_CSV = "https://corgis-edu.github.io/corgis/datasets/csv/ufo_sightings/ufo_sightings.csv"
USER_AGENT = "polimi-workshop/0.1 (teaching material)"
TIMEOUT = 60

# corgis column -> ours. Anything not listed is dropped.
COLUMNS = {
    "Location.City": "city",
    "Location.State": "state",
    "Location.Country": "country",
    "Data.Shape": "shape",
    "Data.Encounter duration": "duration_seconds",
    "Data.Description excerpt": "description",
    "Location.Coordinates.Latitude ": "latitude",
    "Location.Coordinates.Longitude ": "longitude",
    "Dates.Sighted.Year": "year",
    "Dates.Sighted.Month": "month",
    "Date.Sighted.Day": "day",
    "Dates.Sighted.Hour": "hour",
    "Dates.Sighted.Minute": "minute",
}
NUMERIC = {"duration_seconds", "latitude", "longitude"}
INTEGER = {"year", "month", "day", "hour", "minute"}


def get(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        return bytes(response.read())


# --- documents -------------------------------------------------------------


def fetch_one(entry: dict[str, object], template: str, force: bool) -> tuple[str, str]:
    doc_id = str(entry["id"])
    target = DOCS / f"{doc_id}.md"
    if target.exists() and not force:
        return doc_id, "skip"
    try:
        raw = get(template.format(id=doc_id)).decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as exc:
        return doc_id, f"FAILED ({exc})"

    body = "\n".join(line.rstrip() for line in raw.splitlines()).strip()
    target.write_text(
        f"# {entry['title']}\n\n"
        f"Document id: {doc_id}\n"
        f"Theme: {entry['theme']}\n"
        f"Source: https://archive.org/details/{doc_id}\n\n"
        f"---\n\n{body}\n",
        encoding="utf-8",
    )
    return doc_id, "ok"


def fetch_documents(force: bool) -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    template = manifest["text_url_template"]
    entries = manifest["documents"]
    DOCS.mkdir(parents=True, exist_ok=True)

    print(f"Documents: {len(entries)} in the manifest")
    failures = 0
    with ThreadPoolExecutor(max_workers=6) as pool:
        for doc_id, status in pool.map(lambda e: fetch_one(e, template, force), entries):
            if status.startswith("FAILED"):
                failures += 1
                print(f"  {doc_id}: {status}")
    written = len(list(DOCS.glob("*.md")))
    print(f"  {written} documents on disk at {DOCS.relative_to(REPO_ROOT)}")
    return failures


# --- sightings -------------------------------------------------------------


def coerce(field: str, value: str) -> object:
    value = value.strip()
    if value in {"", "NA", "unknown"}:
        return None
    try:
        if field in INTEGER:
            return int(float(value))
        if field in NUMERIC:
            return float(value)
    except ValueError:
        return None
    return value


def fetch_sightings(force: bool) -> int:
    if PARQUET.exists() and not force:
        print(f"Sightings: already at {PARQUET.relative_to(REPO_ROOT)} (use --force to refetch)")
        return 0

    print("Sightings: downloading...")
    try:
        raw = get(SIGHTINGS_CSV).decode("utf-8", errors="replace")
    except (urllib.error.URLError, OSError) as exc:
        print(f"  FAILED: {exc}")
        return 1

    reader = csv.DictReader(io.StringIO(raw))
    rows: list[dict[str, object]] = []
    for source_row in reader:
        row = {
            ours: coerce(ours, source_row.get(theirs, "") or "") for theirs, ours in COLUMNS.items()
        }
        if row.get("year") is None:
            continue
        rows.append(row)

    if not rows:
        print("  FAILED: no usable rows; the upstream schema may have changed.")
        return 1

    import pandas as pd

    frame = pd.DataFrame(rows, columns=list(COLUMNS.values()))
    DATA.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(PARQUET, index=False)
    size_mb = PARQUET.stat().st_size / 1_048_576
    print(
        f"  {len(frame):,} sightings, {frame['year'].min()}-{frame['year'].max()}, "
        f"{size_mb:.1f} MB parquet"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="refetch everything")
    parser.add_argument("--docs-only", action="store_true")
    parser.add_argument("--sightings-only", action="store_true")
    args = parser.parse_args()

    failures = 0
    if not args.sightings_only:
        failures += fetch_documents(args.force)
    if not args.docs_only:
        failures += fetch_sightings(args.force)

    if failures:
        print(f"\n{failures} download(s) failed. Re-run to retry just those.")
        return 1
    print("\nDone. Next: uv run python scripts/check.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
