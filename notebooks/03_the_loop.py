import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 03 · An agent is a while loop

    **This notebook uses `stargate/loop.py`.** It is already in your
    repository: nothing to fetch, nothing to switch.

    If an import fails, you are sitting on a `step-*` branch rather than your
    own — see *cannot import name* in TROUBLESHOOTING.md.

    ---

    In notebook 02 you did one turn by hand: the model asked, you ran the tool,
    you sent the result back.

    Doing that repeatedly, until the model stops asking, is the entire idea. There
    is nothing else in the box.

    By the end of this notebook you will have written an agent. In notebook 04 we
    throw it away and use a framework — and the framework will be less
    interesting than what you wrote, because you will know what it is doing.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The loop, in twelve lines

    Stripped of error handling and bookkeeping, `stargate/loop.py` is this:

    ```python
    messages = [{"role": "user", "content": question}]

    for step in range(max_steps):
        reply = model.reply(messages, tool_schemas)

        if not reply.tool_calls:          # the model answered
            return reply.text

        messages.append(assistant_turn(reply))
        for call in reply.tool_calls:
            result = tools[call.name](**call.arguments)
            messages.append(tool_turn(call, result))

    return None                            # ran out of steps
    ```

    Three things are worth stopping on.

    **`messages` is the entire memory.** The model remembers nothing between
    calls. Anything not in that list did not happen.

    **You execute the tool.** `tools[call.name](...)` is your code, on your
    machine. This is the line that people think the model performs.

    **`max_steps` exists because otherwise it might not stop.** A model that keeps
    requesting tools produces a loop that keeps paying for them. Every framework
    has this ceiling; most hide it from you.
    """)
    return


@app.cell
def _():
    from stargate.loop import run_agent_loop, transcript
    from stargate.providers import GeminiClient
    from stargate.tools import SCHEMAS, TOOLS

    model = GeminiClient()
    return SCHEMAS, TOOLS, model, run_agent_loop, transcript


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Run it
    """)
    return


@app.cell
def _(SCHEMAS, TOOLS, model, run_agent_loop, transcript):
    result = run_agent_loop(
        model,
        "How many UFO sightings were reported in 1952?",
        tools=TOOLS,
        tool_schemas=SCHEMAS,
    )

    print(transcript(result))
    return (result,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Read the transcript rather than the answer. You should see four turns: your
    question, the model asking for a tool, the result you fed back, and only then
    the answer.

    **Two model calls for one question.** Remember that number.
    """)
    return


@app.cell
def _(result):
    print("answer:      ", result.answer)
    print("model calls: ", result.llm_calls)
    print("tools run:   ", [c.name for c in result.tool_calls_made])
    print("stopped:     ", result.stop_reason.value)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## A question that needs two tools

    Now the loop earns its keep: several turns, and the model deciding each time
    whether it has enough.
    """)
    return


@app.cell
def _(SCHEMAS, TOOLS, model, run_agent_loop, transcript):
    multi = run_agent_loop(
        model,
        "Compare how many sightings were reported in 1952 and in 1997, "
        "then give me a target coordinate for a session about the difference.",
        tools=TOOLS,
        tool_schemas=SCHEMAS,
    )
    print(transcript(multi))
    return (multi,)


@app.cell
def _(multi):
    print(f"{multi.llm_calls} model calls for one question")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## What happens without a stop condition

    Set `max_steps=1` and the loop is cut off before the model can use anything it
    asked for.
    """)
    return


@app.cell
def _(SCHEMAS, TOOLS, model, run_agent_loop):
    truncated = run_agent_loop(
        model,
        "How many sightings were reported in 1952?",
        tools=TOOLS,
        tool_schemas=SCHEMAS,
        max_steps=1,
    )
    print("answer:  ", truncated.answer)
    print("stopped: ", truncated.stop_reason.value)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    `answer` is `None` and the reason is `max_steps`.

    That is a real failure mode with a real cost attached, and in notebook 08 you
    will find it in your own traces. An agent that hits its ceiling has spent
    every one of those calls and produced nothing.

    ## What you just built

    - A conversation as a list you own
    - A model that requests rather than acts
    - A dispatch table from names to your functions
    - A ceiling

    That is an agent. Everything after this is ergonomics: retries, streaming,
    memory, tracing, multi-agent routing. Useful ergonomics — but if you ever
    find yourself unsure what a framework is doing, it is doing this.

    ---

    ### Checkpoint

    Reference state: **`step-03`**

    ```
    git diff origin/step-03 -- stargate/
    uv run pytest tests/test_loop.py -v
    ```

    Next: `notebooks/04_agno_agent.py` — the same thing, in six lines.

    To get there: go back to marimo's home page in your browser, shut
    **this** notebook down (**Running notebooks** → the round Shutdown
    button on its row), then click the next one in the list.

    Launched marimo on this single file instead? `Ctrl+C` in its terminal,
    then `uv run marimo edit notebooks/04_agno_agent.py`.

    See *Running the notebooks* in the README if this is the first time.
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


if __name__ == "__main__":
    app.run()
