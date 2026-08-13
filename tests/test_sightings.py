"""The structured half of the corpus: UFO sightings, queried with SQL.

These tests build their own tiny parquet file, so they run without the real
148k-row dataset having been fetched.
"""

from pathlib import Path

import pandas as pd
import pytest

from stargate.sightings import SightingsDB

ROWS = [
    # year month day hour minute city         state shape      dur   desc
    (1952, 7, 19, 23, 40, "washington", "DC", "disk", 300.0, "Lights over the Capitol."),
    (1952, 7, 26, 22, 30, "washington", "DC", "light", 120.0, "Radar returns again."),
    (1952, 8, 1, 21, 0, "roswell", "NM", "disk", 60.0, "A disk, briefly."),
    (1973, 10, 11, 21, 0, "pascagoula", "MS", "oval", 900.0, "Two men, one boat."),
    (1997, 3, 13, 20, 15, "phoenix", "AZ", "triangle", 1800.0, "The lights, in a V."),
]


@pytest.fixture
def db(tmp_path: Path) -> SightingsDB:
    frame = pd.DataFrame(
        ROWS,
        columns=[
            "year",
            "month",
            "day",
            "hour",
            "minute",
            "city",
            "state",
            "shape",
            "duration_seconds",
            "description",
        ],
    )
    path = tmp_path / "nuforc.parquet"
    frame.to_parquet(path)
    return SightingsDB(path)


def test_counts_by_year(db: SightingsDB) -> None:
    assert db.count(year=1952) == 3
    assert db.count(year=1973) == 1
    assert db.count(year=1800) == 0


def test_counts_by_year_and_state(db: SightingsDB) -> None:
    assert db.count(year=1952, state="DC") == 2
    assert db.count(year=1952, state="NM") == 1


def test_state_matching_is_case_insensitive(db: SightingsDB) -> None:
    """Students will type 'nm'. The agent will pass through whatever they typed."""
    assert db.count(year=1952, state="nm") == db.count(year=1952, state="NM") == 1


def test_counts_everything_when_no_filter(db: SightingsDB) -> None:
    assert db.count() == len(ROWS)


def test_shape_breakdown_is_ordered_by_frequency(db: SightingsDB) -> None:
    assert db.shapes(year=1952) == [("disk", 2), ("light", 1)]


def test_arbitrary_read_only_sql(db: SightingsDB) -> None:
    rows = db.query("SELECT city, shape FROM sightings WHERE state = 'AZ'")
    assert rows == [("phoenix", "triangle")]


@pytest.mark.parametrize(
    "sql",
    [
        "DELETE FROM sightings",
        "DROP TABLE sightings",
        "UPDATE sightings SET city = 'x'",
        "INSERT INTO sightings VALUES (1)",
        "  create table evil as select 1  ",
        "ATTACH 'evil.db'",
        "COPY sightings TO 'out.csv'",
    ],
)
def test_rejects_anything_that_is_not_a_read(db: SightingsDB, sql: str) -> None:
    """The SQL agent in notebook 06 writes these queries. It gets read-only access.

    An LLM that can write to your database is a bad afternoon.
    """
    with pytest.raises(PermissionError):
        db.query(sql)


def test_rejects_stacked_statements(db: SightingsDB) -> None:
    with pytest.raises(PermissionError):
        db.query("SELECT 1; DROP TABLE sightings")


def test_schema_lists_columns_and_types(db: SightingsDB) -> None:
    """The SQL agent needs this in its prompt, so DESCRIBE must be permitted."""
    columns = dict(db.schema())
    assert "year" in columns
    assert "city" in columns
    assert columns["duration_seconds"].upper().startswith("DOUBLE")


def test_describe_is_allowed_but_still_read_only(db: SightingsDB) -> None:
    assert db.query("DESCRIBE SELECT * FROM sightings")
    with pytest.raises(PermissionError):
        db.query("DESCRIBE; DROP TABLE sightings")


def test_missing_parquet_gives_an_actionable_error(tmp_path: Path) -> None:
    db = SightingsDB(tmp_path / "absent.parquet")
    with pytest.raises(FileNotFoundError, match="fetch_data"):
        db.count(year=1952)
