import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 06 · Two specialists and a router

    **This notebook uses `stargate/teams.py`.** It is already in your
    repository: nothing to fetch, nothing to switch.

    If an import fails, you are sitting on a `step-*` branch rather than your
    own — see *cannot import name* in TROUBLESHOOTING.md.

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

    ## Don't take that on trust

    You have just been *told* what this agent can and cannot reach. Read it off
    the object instead. An agent is three things: a model, a system prompt, and
    a list of tools. All three are inspectable before you spend a single call.
    """)
    return


@app.cell
def _():
    from agno.session.agent import AgentSession
    from agno.session.team import TeamSession

    def tool_names(agent):
        """Every tool the model is offered, including the ones Agno adds itself."""
        names = [
            getattr(t, "__name__", None) or getattr(t, "name", None) or repr(t)
            for t in (agent.tools or [])
        ]
        if getattr(agent, "members", None) is not None:
            names.append(
                "delegate_task_to_members"
                if agent.delegate_to_all_members
                else "delegate_task_to_member"
            )
        if getattr(agent, "knowledge", None) is not None and agent.search_knowledge:
            names.append("search_knowledge_base")
        return names

    def roster(*agents):
        """Name, instructions and tools for each agent, without calling anything."""
        print("Agents available:", ", ".join(a.name for a in agents))
        for a in agents:
            print(f"\n{a.name}")
            for line in a.instructions or []:
                print(f"    · {line}")
            print(f"  tools: {', '.join(tool_names(a)) or 'none'}")

    def system_prompt(agent):
        """The system message Agno will actually send, assembled without a call."""
        session = (
            TeamSession(session_id="inspect", team_id=agent.id)
            if getattr(agent, "members", None) is not None
            else AgentSession(session_id="inspect", agent_id=agent.id)
        )
        message = agent.get_system_message(session=session)
        return message.content if message else ""

    return roster, system_prompt


@app.cell
def _(documents_only, roster):
    roster(documents_only)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    One tool, and it searches documents. There is no path from here to the
    sightings table, so the number you just read was invented.

    `instructions` is the part *we* wrote. What the model actually receives is
    a little more than that, because Agno assembles the rest:
    """)
    return


@app.cell
def _(documents_only, system_prompt):
    print(system_prompt(documents_only))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Note the `<knowledge_base>` block at the bottom. Nobody wrote it: Agno adds
    it because `search_knowledge=True`, and it is the reason the agent knows the
    tool exists at all. This is the whole prompt, and it is worth re-reading
    whenever an agent behaves in a way your instructions do not explain.

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
    return (sql_agent,)


@app.cell
def _(roster, sql_agent):
    roster(sql_agent)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Two tools this time, and neither of them can reach a document. The
    read-only rule is stated in the instructions *and* enforced in
    `SightingsDB` — instructions alone are a request, not a guarantee.
    """)
    return


@app.cell
def _(sql_agent):
    sql_agent.print_response("How many sightings were reported in 1952?")
    return


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
def _(roster, team):
    roster(team, *team.members)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Three agents now, and the router's only tool is `delegate_task_to_member`.
    It cannot query, it cannot search, it can only pick someone. That is why
    *"Never answer a numeric question yourself"* is in its instructions: it is
    the one failure mode its tools do not already prevent.

    Now read what the router is actually sent:
    """)
    return


@app.cell
def _(system_prompt, team):
    print(system_prompt(team))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Look at the `<team_members>` block: two names, and nothing else. Agno passes
    no description of what either member does, so every routing decision the
    model makes rests on the strings *"Archivist"* and *"Analyst"* plus the five
    lines we wrote. That is a thin basis for a decision, and it is worth
    remembering when the router sends a question to the wrong specialist.
    """)
    return


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

    Next: `notebooks/07_workflows.py` — the case for not using an agent
    at all.

    To get there: go back to marimo's home page in your browser, shut
    **this** notebook down (**Running notebooks** → the round Shutdown
    button on its row), then click the next one in the list.

    Launched marimo on this single file instead? `Ctrl+C` in its terminal,
    then `uv run marimo edit --no-token notebooks/07_workflows.py`.

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
