import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 07 · When you don't want an agent deciding

    **This notebook uses `stargate/sightings.py` and `stargate/knowledge.py`.**
    They are already in your repository: nothing to fetch, nothing to switch.

    If an import fails, you are sitting on a `step-*` branch rather than your
    own — see *cannot import name* in TROUBLESHOOTING.md.

    ---

    Every notebook so far has handed control to a model. It chose the tool, it
    chose when to stop, and in notebook 06 it chose which colleague to ask.

    That is the right design when you genuinely do not know in advance what the
    steps are. It is the wrong one when you do.

    A workflow is the other option: **you** write the control flow, and the model
    only fills in the parts that need language.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The case for giving up the flexibility

    Take a concrete job: produce a short briefing on a year of sightings, using
    both halves of the corpus.

    The steps never vary.

    1. Count the sightings that year (SQL — always)
    2. Find the most common shapes (SQL — always)
    3. Search the documents for that period (vector — always)
    4. Write it up (language — genuinely needs a model)

    Handing that to an agent means paying a model to rediscover the same four
    steps every time, and occasionally getting three of them.

    | | Agent | Workflow |
    |---|---|---|
    | Who picks the steps | the model, each run | you, once |
    | Same input, same path | not guaranteed | guaranteed |
    | Model calls | 6-10 | 1 |
    | Fails by | doing something unexpected | raising an exception |
    | Debugging | read the trace, infer | read the code |

    The honest summary: **an agent is a workflow you were not able to write down.**
    Whenever you can write it down, do.
    """)
    return


@app.cell
def _():
    from stargate.knowledge import knowledge_from_existing
    from stargate.observability import enable_tracing
    from stargate.sightings import SightingsDB

    enable_tracing()
    db = SightingsDB()
    knowledge = knowledge_from_existing()
    return db, knowledge


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Steps 1-3: no model involved at all
    """)
    return


@app.cell
def _(db, knowledge):
    def gather(year: int) -> dict:
        """Deterministic. Same year in, same facts out, every time."""
        return {
            "year": year,
            "total": db.count(year=year),
            "shapes": db.shapes(year=year, limit=5),
            "passages": [
                hit.content[:400]
                for hit in knowledge.vector_db.search(f"sightings and reports from {year}", limit=3)
            ],
        }

    facts = gather(1952)
    print(f"{facts['total']} sightings in {facts['year']}")
    print("shapes:", facts["shapes"])
    print(f"{len(facts['passages'])} passages retrieved")
    return facts, gather


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Run that cell twice. Identical output. No model has been called, nothing has
    been decided, and nothing can drift.

    ## Step 4: the one part that needs language
    """)
    return


@app.cell
def _(facts):
    from google import genai

    from stargate.config import settings
    from stargate.providers import with_backoff

    _cfg = settings()
    _client = genai.Client(api_key=_cfg.require_google())

    def write_briefing(f: dict) -> str:
        _prompt = f"""Write a short briefing on UFO sightings in {f["year"]}.

    Use only these facts.

    Total sightings reported: {f["total"]}
    Most common shapes: {f["shapes"]}

    Passages from the declassified files:
    {chr(10).join(f["passages"])}

    Three paragraphs. Attribute anything from the passages to the documents
    rather than stating it as fact. Do not add figures that are not above.
    """
        return with_backoff(
            _client.models.generate_content, model=_cfg.model, contents=_prompt
        ).text

    briefing = write_briefing(facts)
    print(briefing)
    return (write_briefing,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **One model call.** The agent in notebook 06 would have spent eight or nine on
    the same question, and might still have skipped the SQL.

    ## The whole thing
    """)
    return


@app.cell
def _(gather, write_briefing):
    def briefing_workflow(year: int) -> str:
        return write_briefing(gather(year))

    print(briefing_workflow(1997)[:600])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Agno's version

    Agno ships a `Workflow` type with named steps, so the structure shows up in
    your traces as steps rather than as one opaque call. Same idea, better
    observability: <https://docs.agno.com/concepts/workflows/overview>

    The concept matters more than the API. You can write this with three functions
    and no framework at all — which is rather the point.

    ## How to choose

    Reach for a **workflow** when the steps are known, the order is fixed, and you
    want the same answer twice. Most production "AI features" are this and are
    built as agents by mistake.

    Reach for an **agent** when the steps genuinely depend on the input, or when
    the space of possible requests is too large to enumerate.

    Reach for a **team** when the work splits across genuinely different
    capabilities — as it did in the notebook before this one, where the corpus
    really was two shapes.

    You now have all three shapes in front of you, which is the point of taking
    them in this order: the same briefing question, answered by one agent, by a
    team, and by four lines of Python. The differences between them are
    architectural choices you make deliberately, and the next notebook is about
    the only thing that tells you whether you chose well.

    Because whichever you pick, none of it tells you the thing that matters: you
    do not know whether it works until you have looked at a hundred of its
    outputs and written down what was wrong.

    ---

    ### Checkpoint

    Reference state: **`step-07`**

    Nothing new lands in `stargate/` here: a workflow is control flow you write
    in the notebook, which is rather the point. `step-07` is `step-06` plus this
    notebook, so the diff is empty and that is the confirmation:

    ```
    git diff origin/step-07 -- stargate/
    ```

    Broke something beyond repair? `git switch -c mywork2 origin/step-07` puts
    you back on your feet here.

    Next: `notebooks/08_evals.py` — the part that matters.

    To get there: go back to marimo's home page in your browser, shut
    **this** notebook down (**Running notebooks** → the round Shutdown
    button on its row), then click the next one in the list.

    Launched marimo on this single file instead? `Ctrl+C` in its terminal,
    then `uv run marimo edit --no-token notebooks/08_evals.py`.

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
