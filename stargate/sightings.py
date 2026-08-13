"""Read-only SQL over the UFO sighting reports.

The unstructured half of the corpus (declassified memos) goes into a vector
store in notebook 05. This is the other half: 148k rows of structured sighting
reports, which belong in SQL and emphatically not in an embedding.

Notebook 06 hands this to an agent that writes its own queries, which is why
`query()` refuses anything that is not a read. An agent that can `DROP TABLE`
is one bad completion away from ruining your afternoon.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

DEFAULT_PARQUET = Path(__file__).resolve().parent.parent / "data" / "nuforc.parquet"

# Only these may start a statement. Everything else — including DDL, COPY,
# ATTACH and PRAGMA — is refused before it reaches DuckDB. DESCRIBE is here
# because the SQL agent needs to read the schema before it can query it.
_ALLOWED_START = re.compile(r"^\s*(select|with|describe)\b", re.IGNORECASE)
_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)


class SightingsDB:
    """A tiny read-only wrapper over the sightings parquet.

    Args:
        path: parquet file. Defaults to the one `scripts/fetch_data.py` writes.
    """

    def __init__(self, path: Path | str = DEFAULT_PARQUET) -> None:
        self.path = Path(path)

    # --- plumbing ----------------------------------------------------------

    def _connect(self) -> Any:
        import duckdb

        if not self.path.exists():
            raise FileNotFoundError(
                f"No sightings data at {self.path}. "
                "Run `uv run python scripts/fetch_data.py` first."
            )
        con = duckdb.connect(database=":memory:")
        # Built through the relational API rather than an f-string: DuckDB cannot
        # prepare a CREATE VIEW, and interpolating a path into SQL is how you get
        # an injection bug in the one place you were not expecting one.
        con.read_parquet(str(self.path)).create_view("sightings")
        return con

    @staticmethod
    def _reject_writes(sql: str) -> None:
        stripped = _COMMENT.sub(" ", sql)
        if ";" in stripped.rstrip().rstrip(";"):
            raise PermissionError("Only one statement at a time. Stacked statements are refused.")
        if not _ALLOWED_START.match(stripped):
            raise PermissionError(
                f"This connection is read-only; only SELECT/WITH is allowed. Got: {sql.strip()[:60]!r}"
            )

    # --- the API the agent and the notebooks use ---------------------------

    def query(self, sql: str, params: list[Any] | None = None) -> list[tuple[Any, ...]]:
        """Run a read-only query and return rows as tuples."""
        self._reject_writes(sql)
        con = self._connect()
        try:
            return [tuple(r) for r in con.execute(sql, params or []).fetchall()]
        finally:
            con.close()

    def count(self, year: int | None = None, state: str | None = None) -> int:
        """How many sightings match. This is the tool notebook 02 hands the model."""
        clauses: list[str] = []
        params: list[Any] = []
        if year is not None:
            clauses.append("year = ?")
            params.append(year)
        if state is not None:
            clauses.append("upper(state) = upper(?)")
            params.append(state)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self.query(f"SELECT count(*) FROM sightings{where}", params)
        return int(rows[0][0])

    def shapes(self, year: int | None = None, limit: int = 10) -> list[tuple[str, int]]:
        """Reported shapes, most common first."""
        where, params = ("WHERE year = ?", [year]) if year is not None else ("", [])
        rows = self.query(
            f"SELECT shape, count(*) AS n FROM sightings {where} "
            f"GROUP BY shape ORDER BY n DESC, shape ASC LIMIT {int(limit)}",
            params,
        )
        return [(str(s), int(n)) for s, n in rows]

    def schema(self) -> list[tuple[str, str]]:
        """Column names and types — what the SQL agent needs in its prompt."""
        return [(str(r[0]), str(r[1])) for r in self.query("DESCRIBE SELECT * FROM sightings")]
