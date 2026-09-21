"""A team, in notebook 06.

Two members and a router. The team is kept small for a reason that is not
aesthetic: free-tier Gemini allows about 15 requests per minute, and every
member the router consults costs calls. A five-member team is roughly one
question per minute, which is not a workshop.

The team exists because the corpus genuinely has two shapes. Narrative memos
belong in a vector store; 60,632 structured sighting records belong in SQL.
Asking "how many sightings in 1952?" of a vector store gets you one of two
answers, and they are the same failure: a confidently invented number, or a
correct refusal to answer a question the repository can in fact answer. The
truth is 32, and it is in the table the vector store cannot reach. Which of
the two you get depends on the model; that the question went to the wrong half
of the corpus does not. It is the most common failure category students find
in session 2.
"""

from __future__ import annotations

from typing import Any

from stargate.agents import analyst, archivist, model
from stargate.config import SESSION_DB

TEAM_INSTRUCTIONS = [
    "You route questions about declassified UFO and remote-viewing files to the right specialist.",
    "Send anything that counts, totals, ranks or aggregates sightings to the Analyst — "
    "it has SQL access to the full sightings table.",
    "Send anything about what the documents say, or about the remote viewing "
    "programme itself, to the Archivist.",
    "If a question needs both, ask both and combine the answers.",
    "Never answer a numeric question yourself. Delegate it.",
]


def research_team(
    knowledge: Any = None,
    *,
    instructions: list[str] | None = None,
    with_memory: bool = True,
    **kwargs: Any,
) -> Any:
    """A router plus the two specialists.

    Args:
        knowledge: passed to the Archivist. Without it the Archivist has no
            documents to search and will fall back on the model's own memory —
            which is itself an instructive thing to watch happen.
        instructions: defaults to `TEAM_INSTRUCTIONS`. Notebook 08 passes a
            version with the delegation line removed, to measure what that one
            sentence is worth.
    """
    from agno.db.sqlite import SqliteDb
    from agno.team import Team

    return Team(
        name="Research Team",
        model=model(),
        members=[
            archivist(knowledge, with_memory=False),
            analyst(with_memory=False),
        ],
        instructions=instructions or TEAM_INSTRUCTIONS,
        db=SqliteDb(db_file=str(SESSION_DB)) if with_memory else None,
        show_members_responses=True,
        markdown=True,
        **kwargs,
    )
