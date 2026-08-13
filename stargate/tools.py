"""The two tools the model is offered in notebooks 02 and 03.

There are deliberately two, and they are deliberately unalike, because the
interesting thing to watch is not *whether* the model calls a tool but *which*
one it picks. Tool selection is where the failures live — and the routing
failures students find in session 2's error analysis are the grown-up version
of exactly this.

- `count_sightings` is deterministic and checkable by eye.
- `random_target_coordinate` cannot be guessed, so a model that answers without
  calling it is caught immediately.
"""

from __future__ import annotations

import secrets
from collections.abc import Callable
from typing import Any

from stargate.sightings import SightingsDB

# NUFORC's records start in the 20th century; anything outside this is the
# model inventing a year rather than the user asking about one.
MIN_YEAR = 1900
MAX_YEAR = 2100


def count_sightings(year: int, state: str | None = None, db: SightingsDB | None = None) -> int:
    """How many UFO sightings were reported in a given year, optionally by US state.

    Args:
        year: four-digit year.
        state: two-letter US state code, e.g. "NM". Optional.
        db: injected in tests; defaults to the shipped dataset.
    """
    if not MIN_YEAR <= year <= MAX_YEAR:
        raise ValueError(f"year must be between {MIN_YEAR} and {MAX_YEAR}, got {year}")
    return (db or SightingsDB()).count(year=year, state=state)


def random_target_coordinate() -> str:
    """Issue a fresh eight-digit target coordinate, in the CRV session format.

    Coordinate Remote Viewing sessions gave the viewer a random eight-digit
    number standing in for a location. The model cannot know what this will be,
    which is the point: if it answers without calling this, it made the number up.
    """
    return f"{secrets.randbelow(10_000):04d}-{secrets.randbelow(10_000):04d}"


# --- the registry ----------------------------------------------------------
#
# `TOOLS` is what the loop executes. `SCHEMAS` is what the model is shown.
# Keeping them side by side makes the asymmetry visible: the model receives a
# description, never the function.

TOOLS: dict[str, Callable[..., Any]] = {
    "count_sightings": count_sightings,
    "random_target_coordinate": random_target_coordinate,
}

SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "count_sightings",
        "description": (
            "Count reported UFO sightings in a given year, optionally filtered to a "
            "US state. Use this for any question about how many sightings occurred."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "year": {"type": "integer", "description": "Four-digit year, e.g. 1952."},
                "state": {
                    "type": "string",
                    "description": "Two-letter US state code, e.g. 'NM'. Omit for all states.",
                },
            },
            "required": ["year"],
        },
    },
    {
        "name": "random_target_coordinate",
        "description": (
            "Issue a fresh random eight-digit target coordinate for a remote viewing "
            "session. Takes no arguments. The result cannot be predicted."
        ),
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
]

_BY_NAME: dict[str, dict[str, Any]] = {s["name"]: s for s in SCHEMAS}


def schema_for(name: str) -> dict[str, Any] | None:
    """The JSON description of one tool, or None if it is not registered."""
    return _BY_NAME.get(name)
