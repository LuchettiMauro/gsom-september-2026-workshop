import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 01 · One question, three providers

    **Nothing to set up.** Phase 0 left you on your own branch with the whole
    repository in it — every module these notebooks use is already there.

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
    ### What actually came back

    `.text` is a convenience. It walks into the response, finds the first
    candidate, keeps the parts that are text, and joins them — throwing away
    everything else on the way. That "everything else" is most of what you need
    once you stop writing demos: why the model stopped, what it cost, whether it
    was censored, whether it wants a tool.

    So before we go anywhere near an agent, print the whole envelope once.
    """)
    return


@app.cell
def _(google_response):
    import json as _json

    _envelope = google_response.to_json_dict()
    _envelope.pop("sdk_http_response", None)  # HTTP plumbing — separate cell below
    print(_json.dumps(_envelope, indent=2, default=str))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    That is the whole response. It is shorter than you might expect because the
    SDK drops every field it did not receive — so what you see printed is
    exactly what Google sent, and everything discussed below that is missing
    from the dump simply was not set on this call.

    Now the same thing one layer at a time, with what each layer is for.

    #### Layer 1 — the envelope

    Metadata about the *request*, not about the answer. Nothing here depends on
    what the model said.

    - **`response_id`** — the server's id for this call. This is what you quote
      to Google when a response is wrong or a bill looks odd. Worth logging in
      production; we log it for free once tracing arrives in notebook 04.
    - **`model_version`** — the model that actually served you, which is not the
      string you asked for. Ask for `gemini-3.1-flash-lite` and you get a dated
      build. When answers change overnight without your code changing, this is
      the field that tells you why.
    - **`create_time`** — server-side timestamp.
    - **`candidates`** — a *list*. You can ask for several independent answers to
      the same prompt (`config={"candidate_count": n}`). You almost never do, and
      the whole industry has quietly collapsed this list to `[0]`.
    - **`prompt_feedback`** — set when the *input* was rejected. If Google blocks
      your prompt you get `block_reason` here and **no candidates at all**, which
      is the case where `.text` returns `None` and naive code raises
      `AttributeError` in production at 3am.
    - **`parsed`** — populated only when you asked for structured output with a
      schema; then it holds real Python objects instead of a string.
    - **`function_calls`** — a shortcut that collects the tool requests out of
      the parts. `None` here, because we gave the model no tools. Notebook 02 is
      entirely about making it not-`None`.
    """)
    return


@app.cell
def _(google_response):
    print("response_id:    ", google_response.response_id)
    print("model_version:  ", google_response.model_version)
    print("create_time:    ", google_response.create_time)
    print("candidates:     ", len(google_response.candidates or []))
    print("prompt_feedback:", google_response.prompt_feedback)
    print("parsed:         ", google_response.parsed)
    print("function_calls: ", google_response.function_calls)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Layer 2 — the candidate

    One possible answer.

    - **`finish_reason`** — *the* field to check. `STOP` means the model decided
      it was done. `MAX_TOKENS` means you truncated it mid-sentence and the text
      you got is a fragment that will still look plausible. `SAFETY` /
      `PROHIBITED_CONTENT` mean it was cut off on the way out. Code that reads
      `.text` without reading this will happily hand a half-answer to a user.
    - **`safety_ratings`** — per-category scores on the *output*. Often `None`
      when nothing tripped.
    - **`citation_metadata`** — populated when the output reproduces recognised
      source material.
    - **`avg_logprobs`** — mean log-probability of the tokens chosen. A crude
      confidence signal, and a tempting one; notebook 08 is about why you should
      not trust it as an eval.
    - **`content.role`** — `"model"`. The same envelope shape you send back as
      conversation history, which is exactly what makes the loop in notebook 03
      possible.
    """)
    return


@app.cell
def _(google_response):
    _candidate = google_response.candidates[0]
    print("index:            ", _candidate.index)
    print("finish_reason:    ", _candidate.finish_reason)
    print("finish_message:   ", _candidate.finish_message)
    print("safety_ratings:   ", _candidate.safety_ratings)
    print("citation_metadata:", _candidate.citation_metadata)
    print("avg_logprobs:     ", _candidate.avg_logprobs)
    print("token_count:      ", _candidate.token_count)
    print("content.role:     ", _candidate.content.role)
    print("content.parts:    ", len(_candidate.content.parts or []))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Layer 3 — the parts

    A message is not a string; it is a list of pieces, and each piece has a
    *kind*. A `Part` has a field for every kind it could be — `text`,
    `function_call`, `inline_data` (images, audio), `executable_code`,
    `thought` — and exactly one of them is set.

    This is the single most important thing in the notebook. The reason
    "tool calling" works at all is that a `function_call` arrives through the
    same channel as prose, as just another kind of part. Nothing special
    happens at the protocol level. The model emits a different-shaped part, and
    the rest is your problem.

    The cell below prints, for every part, which fields are actually populated.
    """)
    return


@app.cell
def _(google_response):
    for _i, _part in enumerate(google_response.candidates[0].content.parts or []):
        _populated = sorted(k for k, v in _part.model_dump().items() if v is not None)
        print(f"part[{_i}]  populated: {_populated}")
        if _part.thought:
            print("           ^ reasoning, not the answer — usually hidden from users")
        if _part.text:
            print(f"           text ({len(_part.text)} chars): {_part.text[:160]}")
        if _part.function_call:
            print(f"           function_call: {_part.function_call}")
        if _part.inline_data:
            print(f"           inline_data: {_part.inline_data.mime_type}")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Layer 4 — usage

    What it cost. Every one of these is billed, and the ones that surprise people
    are the last two.

    - **`prompt_token_count`** — everything you sent: system prompt, tool
      schemas, and the entire conversation so far. In an agent loop this grows on
      every turn, so turn 8 costs several times what turn 1 did.
    - **`candidates_token_count`** — the visible answer.
    - **`thoughts_token_count`** — reasoning tokens. Billed as output, and you
      never see them.
    - **`cached_content_token_count`** — prompt tokens served from cache, at a
      discount. The lever you pull when a long system prompt is re-sent on every
      turn.
    - **`tool_use_prompt_token_count`** — what the tool schemas cost you. Adding
      a tenth tool is not free, even on the calls where it goes unused.

    Read this table again after notebook 03, once a single question costs six
    calls instead of one.
    """)
    return


@app.cell
def _(google_response):
    _usage = google_response.usage_metadata
    print("prompt_token_count:         ", _usage.prompt_token_count)
    print("candidates_token_count:     ", _usage.candidates_token_count)
    print("thoughts_token_count:       ", _usage.thoughts_token_count)
    print("cached_content_token_count: ", _usage.cached_content_token_count)
    print("tool_use_prompt_token_count:", _usage.tool_use_prompt_token_count)
    print("total_token_count:          ", _usage.total_token_count)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    #### Layer 0 — the HTTP response underneath

    None of the above is special. It is one JSON body over one HTTPS POST, and
    the SDK keeps the raw exchange attached. The headers are where you find the
    rate-limit state that produces the `429`s in TROUBLESHOOTING.md.
    """)
    return


@app.cell
def _(google_response):
    _http = google_response.sdk_http_response
    if _http is None:
        print("no sdk_http_response on this object")
    else:
        for _key, _value in sorted((_http.headers or {}).items()):
            print(f"{_key}: {_value}")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    So `google_response.text` is shorthand for:

    ```python
    "".join(
        part.text
        for part in response.candidates[0].content.parts
        if part.text is not None
    )
    ```

    Which is fine, right up until there are no candidates (blocked prompt), or
    the finish reason was `MAX_TOKENS` (truncated), or the part you wanted was a
    `function_call` rather than text (notebook 02). Every framework in the rest
    of this course is, at bottom, code that handles those three cases for you.
    """)
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

    To get there: go back to marimo's home page in your browser, shut
    **this** notebook down (**Running notebooks** → the round Shutdown
    button on its row), then click the next one in the list.

    Launched marimo on this single file instead? `Ctrl+C` in its terminal,
    then `uv run marimo edit --no-token notebooks/02_tool_calling.py`.

    See *Running the notebooks* in the README if this is the first time.
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


if __name__ == "__main__":
    app.run()
