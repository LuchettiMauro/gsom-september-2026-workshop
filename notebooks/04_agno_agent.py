import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 04 · The same thing, in six lines

    **Start here.** This notebook needs `stargate/agents.py` and
    `stargate/observability.py`, which arrive on `step-04`. Run this in a
    terminal, in the repository root — not in a cell of this notebook, and
    not in the terminal marimo is running in:

    ```
    git add -A && git commit -m "my work so far"
    git fetch origin
    git switch -c mywork-04 origin/step-04
    ```

    Then shut this notebook down from marimo's home page and open it again, so
    the kernel picks up the files that just appeared.

    ---

    You have written an agent. Now throw it away.

    Not because it was wrong — because you now know what a framework replaces,
    which is the only useful way to evaluate one.

    We also switch tracing on in this notebook. Everything you do from here to the
    end of the course gets recorded, and next week that recording is the material
    you work on.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Tracing first

    Three lines. Every agent run from now on appears in your Langfuse project.

    This goes at the *start* of the course rather than the end on purpose. By
    session 2 you will have a week of real traces from questions you actually
    cared about — which is a far better dataset than anything produced in the last
    ten minutes of a lab.
    """)
    return


@app.cell
def _():
    from stargate.observability import enable_tracing, flush

    langfuse = enable_tracing()
    return flush, langfuse


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The agent
    """)
    return


@app.cell
def _():
    from agno.agent import Agent
    from agno.models.google import Gemini

    from stargate.config import settings
    from stargate.tools import count_sightings, random_target_coordinate

    _cfg = settings()

    agent = Agent(
        model=Gemini(id=_cfg.model, api_key=_cfg.require_google()),
        tools=[count_sightings, random_target_coordinate],
        instructions=["You answer questions about UFO sighting records."],
        markdown=True,
    )
    return (agent,)


@app.cell
def _(agent):
    agent.print_response("How many UFO sightings were reported in 1952?")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## What did it do?

    The same loop. Compare against notebook 03: a tool request, an execution, a
    result fed back, an answer.

    Agno wrote the schema from your function signature and docstring — which is
    why `count_sightings` has type hints and a real docstring. It did not read
    your mind; it read your annotations.
    """)
    return


@app.cell
def _(agent):
    response = agent.run("How many sightings were reported in 1997 in Arizona?")

    for _message in response.messages or []:
        _role = _message.role
        if getattr(_message, "tool_calls", None):
            for _tc in _message.tool_calls:
                print(
                    f"{_role:>9} -> wants {_tc['function']['name']}({_tc['function']['arguments']})"
                )
        elif _message.content:
            print(f"{_role:>9} | {str(_message.content)[:110]}")
    return (response,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## What one question costs

    You saw two model calls in notebook 03. It is worth watching this number,
    because it is the number that gets you rate-limited — and, outside a
    workshop, billed.
    """)
    return


@app.cell
def _(response):
    _calls = sum(1 for m in (response.messages or []) if m.role == "assistant")
    print(f"assistant turns: {_calls}")
    if response.metrics:
        print(f"tokens:          {response.metrics.total_tokens}")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## What the framework actually bought

    | You wrote in 03 | Agno gives you |
    |---|---|
    | `ModelClient` protocol | any provider, one-line swap |
    | hand-written JSON schemas | generated from signatures and docstrings |
    | `tools[name](**args)` | dispatch, plus errors reported back to the model |
    | `max_steps` | the same ceiling, named differently |
    | `messages` list | sessions, persisted across runs |
    | nothing | streaming, structured output, retries, tracing |

    Ergonomics. Real ones — but the loop underneath is the one you wrote.

    ## Memory

    Your loop forgot everything between calls. Give the agent a database and it
    stops forgetting.
    """)
    return


@app.cell
def _():
    from stargate.agents import archivist

    remembering = archivist(knowledge=None)
    remembering.print_response("My name is Mauro and I'm interested in the 1952 wave.")
    return (remembering,)


@app.cell
def _(remembering):
    remembering.print_response("Which year did I say I was interested in?")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    That answer came out of a SQLite file, not the model. The conversation was
    replayed into the prompt — which means memory costs tokens on every turn, and
    is a thing you are choosing to pay for.

    ## Go and look at your traces
    """)
    return


@app.cell
def _(flush, langfuse):
    flush()
    if langfuse:
        print("Open https://cloud.langfuse.com and look at the traces you just made.")
        print("Every run above is there: prompts, tool calls, timings, tokens.")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Spend a minute in there. Open one trace, expand the tool call, read what was
    actually sent to the model.

    Next week you will be doing that for an hour, with a purpose.

    ---

    ### Checkpoint

    Reference state: **`step-04`**

    ```
    git diff origin/step-04 -- stargate/
    ```

    Next: `notebooks/05_knowledge.py` — giving it documents to read.

    To get there: go back to marimo's home page in your browser, shut
    **this** notebook down (**Running notebooks** → the round Shutdown
    button on its row), then click the next one in the list.

    Launched marimo on this single file instead? `Ctrl+C` in its terminal,
    then `uv run marimo edit notebooks/05_knowledge.py`.

    See *Running the notebooks* in the README if this is the first time.
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


if __name__ == "__main__":
    app.run()
