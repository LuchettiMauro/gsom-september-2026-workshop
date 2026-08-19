import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 05 · Giving it something to read

    **Behind? Start here.** In a terminal, in the repository root — not in a
    cell of this notebook, and not in the terminal marimo is running in:

    ```
    git add -A && git commit -m "my work so far"
    git fetch origin
    git switch -c mywork-04 origin/step-04
    ```

    ---

    The agent can count sightings. It knows nothing about the documents.

    This notebook fixes that: 42 declassified files from the CIA's STARGATE
    programme, chunked, embedded, and searchable.

    At the end of it you have a working agent — and the homework for next week is
    to use it and find out what is wrong with it.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The corpus

    Real OCR of real scans. Broken words, page furniture, declassification stamps
    in the middle of sentences. This is what retrieval material actually looks
    like, and it is why retrieval is harder than the demos suggest.
    """)
    return


@app.cell
def _():
    from stargate.knowledge import document_paths

    paths = document_paths()
    print(f"{len(paths)} documents\n")
    for _p in paths[:5]:
        print(" ", _p.stem)
    return (paths,)


@app.cell
def _(paths):
    _mars = next(p for p in paths if "001900760001" in p.stem)
    print(_mars.read_text(encoding="utf-8")[:700])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Chunking

    A document is too big to hand a model, and too big to embed as one vector. So
    it gets cut up.

    We cut at a fixed 500 characters with no overlap. Look at what that does to a
    sentence.
    """)
    return


@app.cell
def _(paths):
    from stargate.chunking import chunk_text

    _text = paths[0].read_text(encoding="utf-8")
    chunks = chunk_text(_text, size=500, overlap=0, doc_id=paths[0].stem)

    print(f"{len(chunks)} chunks from {len(_text)} characters\n")
    print("--- end of chunk 1 ---")
    print(repr(chunks[1].text[-120:]))
    print("\n--- start of chunk 2 ---")
    print(repr(chunks[2].text[:120]))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    The boundary lands wherever character 500 happens to fall — mid-word, mid-
    sentence, mid-number. Nothing joins those two pieces back together at
    retrieval time.

    Remember that you saw this.

    ## Embedding, locally

    Text goes in, a 384-dimensional vector comes out. Similar text lands nearby.

    This runs on your CPU, through FastEmbed, which matters for a practical
    reason: Google's free embedding tier allows about 27,000 tokens a minute and
    1,000 requests a day. Embedding this corpus through it would take roughly half
    an hour, and running it twice would lock you out until tomorrow.
    """)
    return


@app.cell
def _():
    from fastembed import TextEmbedding

    from stargate.config import DEFAULT_EMBEDDER

    embedder = TextEmbedding(model_name=DEFAULT_EMBEDDER)
    _vector = next(iter(embedder.embed(["a disk-shaped object over the Capitol"])))
    print(f"{len(_vector)} dimensions")
    print(_vector[:6])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Watch it index

    Six documents, so you can see the whole cycle happen: read, chunk, embed,
    write. Should take under a minute.
    """)
    return


@app.cell
def _():
    from stargate.knowledge import build_knowledge

    demo = build_knowledge(uri="lancedb_demo", limit=6, recreate=True)
    print("\nchunks indexed:", demo.vector_db.table.count_rows())
    return (demo,)


@app.cell
def _(demo):
    for _hit in demo.vector_db.search("psychic experiments in the Soviet Union", limit=3):
        print(f"[{_hit.meta_data.get('doc_id')}]")
        print(" ", _hit.content[:130].replace("\n", " "), "\n")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The full index

    All 42 documents is about 1,100 chunks, and several minutes of the same thing
    — one embedding per chunk, one write per document. So it ships prebuilt.

    Worth holding on to, because it comes back next week:

    > **DuckDB loads 60,000 sighting records in about 0.2 seconds. Embedding 42
    > documents takes minutes.**

    That asymmetry is why a well-built agent sends *"how many sightings in 1952?"*
    to SQL and only sends *"what did they say about Mars?"* to the vector store.
    Routing is an economic decision before it is an architectural one.
    """)
    return


@app.cell
def _():
    from stargate.knowledge import knowledge_from_existing, restore_prebuilt_index

    restore_prebuilt_index()
    knowledge = knowledge_from_existing()
    print("chunks:", knowledge.vector_db.table.count_rows())
    return (knowledge,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The agent, with documents
    """)
    return


@app.cell
def _(knowledge):
    from stargate.agents import archivist
    from stargate.observability import enable_tracing

    enable_tracing()
    agent = archivist(knowledge)
    return (agent,)


@app.cell
def _(agent):
    agent.print_response("What was the Grill Flame programme?")
    return


@app.cell
def _(agent):
    agent.print_response("What did the remote viewers report about Mars?")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Poke at it

    Try a few of these before you go. Read the answers properly rather than
    skimming them.

    - `"How many sightings were reported in 1952?"` — it has no SQL. What does it do?
    - `"What happened at Roswell?"` — not in this corpus. What does it say?
    - `"Did remote viewing work?"` — read that answer *very* carefully.
    - `"Cosa dicono i documenti sul programma Grill Flame?"`
    """)
    return


@app.cell
def _(agent):
    agent.print_response("Did remote viewing actually work?")
    return


@app.cell
def _():
    from stargate.observability import flush

    flush()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ---

    ## Homework, before session 2

    **Use the agent. Don't fix it.**

    Ask it **25 questions** you actually find interesting. Mix easy ones with
    nasty ones. Ask a few in Italian. Ask about things you suspect are not in the
    corpus.

    Then do nothing about what you see. Do not improve the prompt, do not change
    the chunk size, do not add instructions. If an answer is wrong, note it in one
    sentence and move on.

    Every conversation is traced. Next week we open those traces, work out what
    is actually wrong, and build the measurements that would have caught it.

    A first draft is supposed to be bad. The interesting question is whether you
    can tell *how*.

    > Ask it about UFOs rather than about yourself — you'll be comparing findings
    > with the room.

    ---

    ### Checkpoint

    Reference state: **`step-05`** — end of session 1.

    ```
    git diff origin/step-05 -- stargate/
    ```

    Next week: `notebooks/06_teams.py`

    To get there: go back to marimo's home page in your browser, shut
    **this** notebook down (**Running notebooks** → the round Shutdown
    button on its row), then click the next one in the list.

    Launched marimo on this single file instead? `Ctrl+C` in its terminal,
    then `uv run marimo edit notebooks/06_teams.py`.

    See *Running the notebooks* in the README if this is the first time.
    """)
    return


@app.cell
def _():
    import marimo as mo

    return (mo,)


if __name__ == "__main__":
    app.run()
