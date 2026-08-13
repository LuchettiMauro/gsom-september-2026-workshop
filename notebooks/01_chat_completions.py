import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 01 · One question, three providers

    **Behind? Start here.**

    ```
    git add -A && git commit -m "my work so far"
    git fetch origin
    git switch -c mywork-00 origin/step-00
    ```

    ---

    We are going to build an agent. Before that, the thing an agent is built out
    of: a single call to a language model.

    There is no framework in this notebook and no agent. Just an HTTP request
    with a list of messages in it, sent to three different companies, so you can
    see what actually differs between them.

    Spoiler: less than you would think.
    """)
    return


@app.cell
def _():

    from stargate.config import settings

    cfg = settings()
    print(f"Model: {cfg.model}")
    print(f"Google key:    {'set' if cfg.google_api_key else 'MISSING — see PHASE0.md'}")
    print(f"OpenAI key:    {'set' if cfg.openai_api_key else 'not set (optional)'}")
    print(f"Anthropic key: {'set' if cfg.anthropic_api_key else 'not set (optional)'}")
    return (cfg,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Google — `generate_content`

    The one everybody has. Note the shape: a list of `contents`, each with a
    `role` and a list of `parts`. A message is not a string, it is a list of
    pieces.
    """)
    return


@app.cell
def _(cfg):
    from google import genai

    google_client = genai.Client(api_key=cfg.require_google())

    google_response = google_client.models.generate_content(
        model=cfg.model,
        contents="In one sentence: what was the CIA's STARGATE programme?",
    )
    print(google_response.text)
    return (google_response,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Now look at what came back, rather than at the text. This is the object the
    text was pulled out of.
    """)
    return


@app.cell
def _(google_response):
    _candidate = google_response.candidates[0]
    print("finish_reason:", _candidate.finish_reason)
    print("parts:", len(_candidate.content.parts))
    print("usage:", google_response.usage_metadata.total_token_count, "tokens")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## OpenAI — `chat.completions.create`

    **You do not need an OpenAI key.** The output is reproduced below so you can
    read the comparison either way. If you do have one in `.env`, the next cell
    runs for real.

    The differences worth noticing:

    - Messages are `{"role", "content"}` dicts, and `content` is a plain string.
    - The system prompt is a *message* with `role: "system"`.
    - The reply is at `choices[0].message.content`.
    """)
    return


@app.cell
def _(cfg):
    if cfg.openai_api_key:
        from openai import OpenAI

        _client = OpenAI(api_key=cfg.openai_api_key)
        _completion = _client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are terse."},
                {
                    "role": "user",
                    "content": "In one sentence: what was the CIA's STARGATE programme?",
                },
            ],
        )
        openai_text = _completion.choices[0].message.content
    else:
        openai_text = (
            "[not run — no OPENAI_API_KEY]\n\n"
            "STARGATE was a US government programme that from the 1970s to 1995 "
            "investigated whether 'remote viewing' could be used for intelligence "
            "gathering."
        )
    print(openai_text)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Anthropic — `messages.create`

    Different again:

    - The system prompt is **not** a message. It is a top-level `system=` argument.
    - `max_tokens` is required, not optional.
    - The reply is a list of content blocks: `content[0].text`.
    """)
    return


@app.cell
def _(cfg):
    if cfg.anthropic_api_key:
        import anthropic

        _client = anthropic.Anthropic(api_key=cfg.anthropic_api_key)
        _message = _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            system="You are terse.",
            messages=[
                {
                    "role": "user",
                    "content": "In one sentence: what was the CIA's STARGATE programme?",
                }
            ],
        )
        anthropic_text = _message.content[0].text
    else:
        anthropic_text = (
            "[not run — no ANTHROPIC_API_KEY]\n\n"
            "STARGATE was a classified US programme, running from the 1970s until "
            "1995, that studied psychic phenomena — principally remote viewing — "
            "for possible intelligence applications."
        )
    print(anthropic_text)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## So what actually differs?

    | | Google | OpenAI | Anthropic |
    |---|---|---|---|
    | Method | `models.generate_content` | `chat.completions.create` | `messages.create` |
    | Conversation | `contents=[Content(role, parts)]` | `messages=[{role, content}]` | `messages=[{role, content}]` |
    | System prompt | `config.system_instruction` | a message with `role: "system"` | top-level `system=` |
    | Message body | list of `Part` | a string | list of blocks |
    | Reply | `candidates[0].content.parts` | `choices[0].message.content` | `content[0].text` |
    | Token limit | optional | optional | **required** |

    Three vocabularies for the same idea: *here is a conversation, produce the
    next turn*.

    None of that difference is interesting. It is packaging. And it is why the
    framework we pick up in notebook 04 can swap providers with a one-line change
    — there is nothing deeper to abstract over.

    What **is** interesting is what happens when the model wants something from
    you before it can answer. That is notebook 02.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---

    ### Checkpoint

    Reference state for what you just built: **`step-01`**

    ```
    git diff origin/step-01 -- stargate/
    ```

    Next: `notebooks/02_tool_calling.py`
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


if __name__ == "__main__":
    app.run()
