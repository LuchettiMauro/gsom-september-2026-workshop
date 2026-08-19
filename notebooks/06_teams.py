import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 06 · Two specialists and a router

    **Start here.** This notebook needs `stargate/teams.py`, which arrives
    on `step-06`. Run this in a terminal, in the repository root — not in a
    cell of this notebook, and not in the terminal marimo is running in:

    ```
    git add -A && git commit -m "my work so far"
    git fetch origin
    git switch -c mywork-06 origin/step-06
    ```

    Then shut this notebook down from marimo's home page and open it again, so
    the kernel picks up the files that just appeared.

    ---

    Welcome back. Before anything else, ask last week's agent a counting question.
    """)
    return


@app.cell
def _():
    from stargate.agents import archivist
    from stargate.knowledge import knowledge_from_existing
    from stargate.observability import enable_tracing

    enable_tracing()
    knowledge = knowledge_from_existing()
    documents_only = archivist(knowledge)
    return documents_only, knowledge


@app.cell
def _(documents_only):
    documents_only.print_response("How many UFO sightings were reported in 1952?")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Check that number.

    It has no access to the sightings table. Whatever it said came from a
    retrieved memo, or from nothing at all — and it very likely said it with
    complete confidence.

    Hold on to this. It is going to show up as a failure category in the next
    notebook, and it is the most common one in the room.

    ## The data was never one shape

    | | Shape | Belongs in |
    |---|---|---|
    | 42 declassified memos | narrative prose | a vector store |
    | 60,632 sighting records | rows and columns | SQL |

    Embedding a table would be silly and slow. Vector-searching for a `COUNT(*)`
    is what you just watched fail.

    So: two agents, and something to choose between them.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The analyst

    An agent that writes its own SQL. Note what it is *not* given: Agno ships
    `DuckDbTools`, which would let the model run any statement it likes. This one
    gets a connection that refuses everything except `SELECT`.

    A language model that can `DROP TABLE` is one bad completion away from
    ruining your afternoon.
    """)
    return


@app.cell
def _():
    from stargate.sightings import SightingsDB

    db = SightingsDB()
    print("columns:", [c for c, _ in db.schema()])
    print("rows:   ", f"{db.count():,}")
    return (db,)


@app.cell
def _(db):
    try:
        db.query("DROP TABLE sightings")
    except PermissionError as exc:
        print("refused:", exc)
    return


@app.cell
def _():
    from stargate.agents import analyst

    sql_agent = analyst()
    sql_agent.print_response("How many sightings were reported in 1952?")
    return (sql_agent,)


@app.cell
def _(sql_agent):
    sql_agent.print_response(
        "Which three shapes were reported most often in the 1990s, and how many of each?"
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Open that trace in Langfuse and read the SQL it wrote. It is usually
    reasonable, occasionally wrong in an interesting way, and always inspectable —
    which is more than can be said for a number that came out of an embedding.

    ## The team

    A router plus the two specialists. The router's only job is to decide who
    should answer.
    """)
    return


@app.cell
def _(knowledge):
    from stargate.teams import research_team

    team = research_team(knowledge)
    return (team,)


@app.cell
def _(team):
    team.print_response("How many sightings were reported in 1952?")
    return


@app.cell
def _(team):
    team.print_response("What did the remote viewers claim to see on Mars?")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The one that needs both
    """)
    return


@app.cell
def _(team):
    team.print_response(
        "How many sightings were reported in 1952, and what did the "
        "declassified files say about that period?"
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## What it cost

    Look at the trace for that last question. The router consulted both members;
    each member ran its own loop.

    One question, easily eight or nine model calls. On a free tier that allows
    fifteen a minute, a five-member team would be roughly one question per minute
    — which is why this team has two members and not five.

    Routing is not free. Neither is delegation. Both are worth it *when the
    alternative is a confidently invented number*, and not otherwise.

    ---

    ### Checkpoint

    Reference state: **`step-06`**

    ```
    git diff origin/step-06 -- stargate/
    ```

    Next: `notebooks/07_telegram.py`

    To get there: go back to marimo's home page in your browser, shut
    **this** notebook down (**Running notebooks** → the round Shutdown
    button on its row), then click the next one in the list.

    Launched marimo on this single file instead? `Ctrl+C` in its terminal,
    then `uv run marimo edit notebooks/07_telegram.py`.

    See *Running the notebooks* in the README if this is the first time.
    """)
    return


@app.cell
def _():
    from stargate.observability import flush

    flush()
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


if __name__ == "__main__":
    app.run()
