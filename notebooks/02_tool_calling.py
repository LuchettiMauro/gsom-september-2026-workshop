import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 02 · The model does not call anything

    **Behind? Start here.** In a terminal, in the repository root — not in a
    cell of this notebook, and not in the terminal marimo is running in:

    ```
    git add -A && git commit -m "my work so far"
    git fetch origin
    git switch -c mywork-01 origin/step-01
    ```

    ---

    "Tool calling" is the worst-named idea in this field.

    The model cannot reach your machine. It has no network, no filesystem, no
    ability to execute anything. What it can do is emit a **structured request**
    and stop — and then it is your problem.

    This notebook is about looking at that request directly, before any library
    hides it from you.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Two tools

    We give the model two, deliberately unalike, because the interesting question
    is not *whether* it asks for a tool but *which* one it picks.
    """)
    return


@app.cell
def _():
    from stargate import tools

    for _name, _schema in ((n, tools.schema_for(n)) for n in tools.TOOLS):
        print(f"{_name}({', '.join(_schema['parameters']['properties'])})")
        print(f"    {_schema['description']}\n")
    return (tools,)


@app.cell
def _(tools):
    # These are ordinary Python functions. Nothing magic.
    print("1952 sightings:", tools.count_sightings(year=1952))
    print("a coordinate:  ", tools.random_target_coordinate())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## What the model is actually sent

    Not the functions. A **description** of the functions. This is the whole of
    what it knows about your code.
    """)
    return


@app.cell
def _(tools):
    import json

    print(json.dumps(tools.SCHEMAS[0], indent=2))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Ask it something it cannot know

    The model was trained long before you ran this notebook. It has no way to
    know how many sightings are in *your* copy of the data.

    One line below matters more than the rest:

    ```python
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
    ```

    Left on, the SDK would run the tool for you behind the scenes and hand back a
    finished answer — convenient in production, and fatal here, because the entire
    point is to see the request before anything executes it.
    """)
    return


@app.cell
def _(cfg, tools):
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=cfg.require_google())

    declarations = [
        types.FunctionDeclaration(
            name=t["name"], description=t["description"], parameters_json_schema=t["parameters"]
        )
        for t in tools.SCHEMAS
    ]

    config = types.GenerateContentConfig(
        tools=[types.Tool(function_declarations=declarations)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )

    response = client.models.generate_content(
        model=cfg.model,
        contents="How many UFO sightings were reported in 1952?",
        config=config,
    )
    return client, config, response, types


@app.cell
def _():
    from stargate.config import settings

    cfg = settings()
    return (cfg,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### The reply

    Look at `.text` first — the thing you would normally print.
    """)
    return


@app.cell
def _(response):
    print("text:", repr(response.text))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Empty, or nearly. The answer is not there because the model did not answer.

    Here is what it actually returned.
    """)
    return


@app.cell
def _(response):
    _part = response.candidates[0].content.parts[0]
    _fc = _part.function_call

    print("finish_reason:", response.candidates[0].finish_reason)
    print()
    print("function_call.name:", _fc.name)
    print("function_call.args:", dict(_fc.args))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **That is the whole mechanism.**

    The model produced a name and some arguments. Nothing ran. Nothing counted
    anything. There is no result anywhere in that object, and there never will be
    unless you produce one.

    ### Now do the part the model cannot do
    """)
    return


@app.cell
def _(response, tools):
    _call = response.candidates[0].content.parts[0].function_call
    _fn = tools.TOOLS[_call.name]
    result = _fn(**dict(_call.args))

    print(f"you ran: {_call.name}({dict(_call.args)})")
    print(f"result:  {result}")
    return (result,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### And hand it back

    The model has no memory. It will not recall asking. To let it use the answer
    you must send the whole conversation again, with the result appended as a
    `function_response` part.
    """)
    return


@app.cell
def _(cfg, client, config, response, result, types):
    followup = client.models.generate_content(
        model=cfg.model,
        contents=[
            types.Content(
                role="user",
                parts=[types.Part(text="How many UFO sightings were reported in 1952?")],
            ),
            response.candidates[0].content,
            types.Content(
                role="user",
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            name="count_sightings", response={"result": result}
                        )
                    )
                ],
            ),
        ],
        config=config,
    )
    print(followup.text)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Try the other tool

    Ask for a target coordinate. The model has no way to guess it — so if it
    answers without asking for the tool, you have caught it inventing one.
    """)
    return


@app.cell
def _(cfg, client, config):
    coord_response = client.models.generate_content(
        model=cfg.model,
        contents="Give me a fresh target coordinate for a remote viewing session.",
        config=config,
    )

    for _p in coord_response.candidates[0].content.parts:
        if _p.function_call:
            print("asked for:", _p.function_call.name)
        if _p.text:
            print("said:", _p.text.strip()[:200])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Where this is going

    You have now done, by hand, one turn of the cycle:

    ```
    ask  ->  model requests a tool  ->  you run it  ->  you send the result  ->  answer
    ```

    An agent is that cycle in a `while` loop, with something to stop it.

    That is the next notebook, and it is the most important one in the course.

    ---

    ### Checkpoint

    Reference state: **`step-02`**

    ```
    git diff origin/step-02 -- stargate/
    ```

    Next: `notebooks/03_the_loop.py`

    To get there: go back to marimo's home page in your browser, shut
    **this** notebook down (**Running notebooks** → the round Shutdown
    button on its row), then click the next one in the list.

    Launched marimo on this single file instead? `Ctrl+C` in its terminal,
    then `uv run marimo edit notebooks/03_the_loop.py`.

    See *Running the notebooks* in the README if this is the first time.
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


if __name__ == "__main__":
    app.run()
