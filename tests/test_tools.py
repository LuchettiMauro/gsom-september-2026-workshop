"""The tools the model is offered in notebooks 02 and 03."""

from pathlib import Path

import pandas as pd
import pytest

from stargate import tools
from stargate.sightings import SightingsDB


@pytest.fixture
def db(tmp_path: Path) -> SightingsDB:
    frame = pd.DataFrame(
        [(1952, "DC", "disk"), (1952, "NM", "disk"), (1973, "MS", "oval")],
        columns=["year", "state", "shape"],
    )
    path = tmp_path / "n.parquet"
    frame.to_parquet(path)
    return SightingsDB(path)


# --- schemas ---------------------------------------------------------------


def test_every_registered_tool_has_a_schema() -> None:
    """A tool with no schema is invisible to the model."""
    for name in tools.TOOLS:
        assert tools.schema_for(name) is not None, f"{name} has no schema"


def test_schema_shape_matches_what_providers_expect() -> None:
    schema = tools.schema_for("count_sightings")
    assert schema is not None
    assert schema["name"] == "count_sightings"
    assert schema["description"].strip()
    assert schema["parameters"]["type"] == "object"
    assert "year" in schema["parameters"]["properties"]
    assert schema["parameters"]["required"] == ["year"]


def test_optional_parameters_are_not_required() -> None:
    schema = tools.schema_for("count_sightings")
    assert schema is not None
    assert "state" in schema["parameters"]["properties"]
    assert "state" not in schema["parameters"]["required"]


def test_schema_for_unknown_tool_is_none() -> None:
    assert tools.schema_for("teleport") is None


# --- count_sightings -------------------------------------------------------


def test_count_sightings_reads_the_database(db: SightingsDB) -> None:
    assert tools.count_sightings(year=1952, db=db) == 2
    assert tools.count_sightings(year=1952, state="NM", db=db) == 1


def test_count_sightings_rejects_absurd_years(db: SightingsDB) -> None:
    """The model will occasionally ask about the year 20252. Say no clearly."""
    with pytest.raises(ValueError, match="year"):
        tools.count_sightings(year=99999, db=db)


# --- the unfakeable tool ---------------------------------------------------


def test_target_coordinate_has_the_documented_shape() -> None:
    """Real CRV sessions used eight-digit target coordinates."""
    coord = tools.random_target_coordinate()
    assert len(coord) == 9 and coord[4] == "-"
    assert coord.replace("-", "").isdigit()


def test_target_coordinate_is_not_something_the_model_could_have_known() -> None:
    """The point of this tool: two calls disagree, so a guessed answer is caught."""
    seen = {tools.random_target_coordinate() for _ in range(50)}
    assert len(seen) > 40, "should be effectively unpredictable"
