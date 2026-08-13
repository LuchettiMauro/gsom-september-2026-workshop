"""The agents.

`archivist` searches the declassified documents. `analyst` writes SQL against
the sightings table. Notebook 06 puts a team around both.

Two sets of instructions live here. `INSTRUCTIONS` is what session 1 builds and
what generates the traces you analyse a week later. `INSTRUCTIONS_GROUNDED` is
introduced at the end of session 2, once you have measurements that say what
was actually wrong — the difference between them is the exercise.
"""

from __future__ import annotations

from typing import Any

from stargate.config import SESSION_DB, settings
from stargate.sightings import SightingsDB

# --- instructions ----------------------------------------------------------

INSTRUCTIONS = [
    "You answer questions about declassified US government files on remote viewing "
    "and UFO sightings.",
    "Search your knowledge base before answering.",
    "Be concise.",
]

INSTRUCTIONS_GROUNDED = [
    "You answer questions about declassified US government files on remote viewing "
    "and UFO sightings.",
    "Search your knowledge base before answering.",
    "Cite the document id for every claim you make, like this: (CIA-RDP96-...).",
    "These documents record what researchers claimed at the time. Report claims as "
    "claims: write 'a 1979 SRI report concluded X', never 'X is true'.",
    "If the documents do not contain the answer, say you don't know. Do not fill "
    "the gap from general knowledge.",
    "Answer in the same language the question was asked in.",
    "Be concise.",
]

ANALYST_INSTRUCTIONS = [
    "You answer questions about UFO sighting statistics by querying a DuckDB table.",
    "The table is called `sightings`. Call describe_sightings() first if you are "
    "unsure of the columns.",
    "Always answer numeric questions by running a query. Never estimate.",
    "The connection is read-only: only SELECT and WITH are permitted.",
]


# --- the model -------------------------------------------------------------


def model(model_id: str | None = None) -> Any:
    from agno.models.google import Gemini

    cfg = settings()
    return Gemini(id=model_id or cfg.model, api_key=cfg.require_google())


def _db() -> Any:
    """Session storage, so the agent remembers earlier turns of a conversation."""
    from agno.db.sqlite import SqliteDb

    return SqliteDb(db_file=str(SESSION_DB))


# --- the document agent ----------------------------------------------------


def archivist(
    knowledge: Any = None,
    *,
    instructions: list[str] | None = None,
    with_memory: bool = True,
    **kwargs: Any,
) -> Any:
    """An agent over the declassified document corpus.

    Args:
        knowledge: an Agno `Knowledge`. Built by `stargate.knowledge.build_knowledge`.
        instructions: defaults to `INSTRUCTIONS`. Pass `INSTRUCTIONS_GROUNDED`
            to see what changes.
        with_memory: keep conversation history across turns.
    """
    from agno.agent import Agent

    return Agent(
        name="Archivist",
        model=model(),
        knowledge=knowledge,
        search_knowledge=knowledge is not None,
        instructions=instructions or INSTRUCTIONS,
        db=_db() if with_memory else None,
        add_history_to_context=with_memory,
        num_history_runs=3,
        markdown=True,
        **kwargs,
    )


# --- the SQL agent ---------------------------------------------------------


def sightings_tools(db: SightingsDB | None = None) -> list[Any]:
    """Read-only SQL tools for the analyst.

    Note what is *not* here: Agno ships `DuckDbTools`, which would let the model
    run any statement it likes. `SightingsDB` refuses everything except SELECT,
    which is the version you want when a language model is writing the SQL.
    """
    database = db or SightingsDB()

    def query_sightings(sql: str) -> str:
        """Run a read-only SQL query against the `sightings` table and return rows."""
        rows = database.query(sql)
        if not rows:
            return "No rows."
        preview = rows[:50]
        body = "\n".join(" | ".join(str(v) for v in row) for row in preview)
        suffix = f"\n... ({len(rows)} rows total)" if len(rows) > len(preview) else ""
        return body + suffix

    def describe_sightings() -> str:
        """List the columns and types of the `sightings` table."""
        return "\n".join(f"{name}: {dtype}" for name, dtype in database.schema())

    return [query_sightings, describe_sightings]


def analyst(db: SightingsDB | None = None, *, with_memory: bool = True, **kwargs: Any) -> Any:
    """An agent that answers statistical questions by writing SQL."""
    from agno.agent import Agent

    return Agent(
        name="Analyst",
        model=model(),
        tools=sightings_tools(db),
        instructions=ANALYST_INSTRUCTIONS,
        db=_db() if with_memory else None,
        add_history_to_context=with_memory,
        num_history_runs=3,
        markdown=True,
        **kwargs,
    )
