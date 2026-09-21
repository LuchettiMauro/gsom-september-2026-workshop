import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 08 · How bad is it?

    **This notebook uses the `stargate/evaluators/` package.** It is already
    in your repository: nothing to fetch, nothing to switch.

    If an import fails, you are sitting on a `step-*` branch rather than your
    own — see *cannot import name* in TROUBLESHOOTING.md.

    ---

    You have an agent. You have a week of traces. You have no idea whether it
    works.

    The order of this notebook matters more than any individual step in it:

    1. **Look at your own traces** and write down what went wrong, in your words
    2. **Group** those notes into categories, and count them
    3. **Write cheap code** for every category code can catch
    4. **Write one LLM judge**, for the category nothing cheaper catches
    5. **Measure the judge** against human labels
    6. **Change one thing** and watch a number move

    The tempting shortcut is to skip to step 3 or 4 — pick some metrics that sound
    sensible and start scoring. Don't. You would be measuring problems you
    imagined instead of the ones you have, and a dashboard full of those is worse
    than no dashboard, because it looks like knowledge.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 1 · Open coding

    Go to **your Langfuse project** and pull up the traces from last week.

    For each of about twenty of them, record two things:

    - a **binary** judgement: is this answer acceptable, yes or no
    - **one sentence**, in your own words, about the first thing that is wrong

    Two rules that matter more than they look.

    **Write free text, not a category.** The moment you pick from a list you stop
    seeing anything that is not on it.

    **Record only the first failure.** If retrieval pulled the wrong chunk, and
    *therefore* the answer was wrong, and *therefore* the citation was bogus, that
    is **one** failure — a retrieval failure. Counting the downstream symptoms
    separately is how you end up building a citation evaluator to fix a chunking
    bug.

    Use Langfuse's annotation queue, or a text file. The tool does not matter.

    > **No traces of your own?** Run `uv run python scripts/seed_traces.py` and
    > work on the fallback set. Your own would have been better.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 2 · Axial coding

    Now cluster your twenty sentences. Merge the ones that say the same thing
    differently, name each group, and **count** them.

    Then, as a room, merge everyone's groups into one taxonomy.

    Twenty-five people × twenty traces is five hundred traces — past the point
    where new categories keep appearing, and far more than any one of you could
    read.

    Typical result:

    | Failure category | n | Catchable by |
    |---|---|---|
    | Wrong retrieval route — a counting question answered without SQL | 31 | code |
    | Unattributed claim — no document id | 24 | code |
    | **Source/claim conflation** — *doc says X* asserted as *X* | 19 | **a judge** |
    | Out-of-corpus hallucination — no "I don't know" | 14 | code |
    | Retrieval miss / chunk truncation | 11 | code |
    | Language drift — Italian question, English answer | 5 | code |

    Look at that last column before going on.

    **Five of six fall to ordinary code.** One needs a language model. That ratio
    is the finding, and you derived it from data rather than being told it.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 3 · The cheap evaluators

    Five checks, no model calls, milliseconds. Read them — they are about forty
    lines in total and there is nothing clever in any of them.
    """)
    return


@app.cell
def _():
    import inspect

    from stargate.evaluators import deterministic

    print(inspect.getsource(deterministic.check_routing))
    print(inspect.getsource(deterministic.check_citation))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Run them over the traces
    """)
    return


@app.cell
def _():
    import json

    from stargate.config import DATA_DIR
    from stargate.evaluators import Trace, run_checks

    _payload = json.loads((DATA_DIR / "example_traces.json").read_text(encoding="utf-8"))
    traces = [
        Trace(
            question=t["question"],
            answer=t["answer"],
            tool_calls=t.get("tool_calls", []),
            retrieved_ids=t.get("retrieved_ids", []),
            gold_doc_id=t.get("gold_doc_id"),
            expects_refusal=t.get("expects_refusal"),
            trace_id=f"example-{i:02d}",
        )
        for i, t in enumerate(_payload["traces"])
    ]
    print(f"{len(traces)} traces loaded")
    return DATA_DIR, run_checks, traces


@app.cell
def _(run_checks, traces):
    from collections import Counter

    failed = Counter()
    checked = Counter()

    for _t in traces:
        for _r in run_checks(_t):
            if _r.passed is None:
                continue
            checked[_r.name] += 1
            if not _r.passed:
                failed[_r.name] += 1

    print(f"{'check':<20} {'failed':>7} {'of':>5}")
    for _name in sorted(checked):
        print(f"{_name:<20} {failed[_name]:>7} {checked[_name]:>5}")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Note the `of` column. Some checks apply to every trace; others only apply when
    there is ground truth to compare against.

    That distinction is deliberate. "This check found nothing wrong" and "this
    check had nothing to look at" are different facts, and averaging them together
    is the first step towards a dashboard that lies.
    """)
    return


@app.cell
def _(run_checks, traces):
    for _t in traces[:4]:
        print(f"Q: {_t.question}")
        for _r in run_checks(_t):
            _mark = {True: "pass", False: "FAIL", None: " -- "}[_r.passed]
            print(f"   {_mark}  {_r.name:<18} {_r.detail}")
        print()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 4 · One judge

    Now the category nothing cheaper catches: did the agent report what the
    document **claims**, or restate it as **fact**?

    On this corpus that distinction is unmissable. *"Remote viewing worked"* and
    *"a 1979 SRI report concluded that a viewer's description matched the target"*
    are both faithful to the same document and only one of them is honest.

    A judge is three things and no more: a prompt, a rubric, and — later — a
    measurement of how much it agrees with you.
    """)
    return


@app.cell
def _():
    from stargate.evaluators.judge import RUBRIC

    print(RUBRIC)
    return


@app.cell
def _():
    from stargate.evaluators.judge import build_judge_prompt, parse_verdict

    print(
        build_judge_prompt(
            question="Did remote viewing work?",
            answer="Remote viewing worked.",
            context="The 1979 SRI final report concluded that the viewer's description matched.",
        )[-700:]
    )
    return build_judge_prompt, parse_verdict


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Run it

    One model call per trace, so this is the slow and expensive part of the
    notebook — which is itself the argument for doing step 3 first.
    """)
    return


@app.cell
def _(build_judge_prompt, parse_verdict, traces):
    from google import genai

    from stargate.config import settings
    from stargate.providers import with_backoff

    _cfg = settings()
    _client = genai.Client(api_key=_cfg.require_google())

    def judge(trace):
        _prompt = build_judge_prompt(
            question=trace.question,
            answer=trace.answer,
            context=" ".join(trace.retrieved_ids) or "(nothing retrieved)",
        )
        _response = with_backoff(
            _client.models.generate_content, model=_cfg.model, contents=_prompt
        )
        return parse_verdict(_response.text or "")

    verdicts = [judge(t) for t in traces]
    print(f"{sum(1 for v in verdicts if v.grounded is False)} judged ungrounded")
    print(f"{sum(1 for v in verdicts if v.grounded is None)} undecided")
    return (verdicts,)


@app.cell
def _(traces, verdicts):
    for _t, _v in list(zip(traces, verdicts, strict=True))[:6]:
        print(f"{'GROUNDED' if _v.grounded else 'ungrounded':<12} {_t.question[:58]}")
        print(f"             {_v.reason}\n")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 5 · Judge the judge

    You now have a number. The obvious question, and the one most people skip:
    **is the judge right?**

    An unaligned judge is worse than no judge, because it produces a confident
    number that nobody checks.
    """)
    return


@app.cell
def _(DATA_DIR):
    import csv
    from collections import defaultdict

    labels = defaultdict(dict)
    with (DATA_DIR / "eval_labels_multi.csv").open(encoding="utf-8") as _f:
        for _row in csv.DictReader(_f):
            labels[_row["annotator"]][_row["trace_ref"]] = _row["grounded"] == "true"

    print("annotators:", list(labels))
    print("labels each:", {a: len(v) for a, v in labels.items()})
    return (labels,)


@app.cell
def _(labels, traces, verdicts):
    from stargate.evaluators import confusion_matrix

    _annotator = next(iter(labels))
    _human, _judged = [], []
    for _t, _v in zip(traces, verdicts, strict=True):
        _label = labels[_annotator].get(_t.trace_id)
        if _label is None or _v.grounded is None:
            continue
        # Positive class is "has the defect", so both get inverted.
        _human.append(not _label)
        _judged.append(not _v.grounded)

    matrix = confusion_matrix(_human, _judged)
    print(f"judge vs {_annotator}:\n{matrix}")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Now read that number properly

    Look at `positives`. If the TPR came out of five or six real failures, then a
    single relabelled trace swings it by fifteen or twenty points.

    **That is not a measurement. It is an anecdote with a decimal point.**

    Which raises the more uncomfortable question.
    """)
    return


@app.cell
def _(labels):
    from stargate.evaluators import cohens_kappa

    if len(labels) < 2:
        print(
            "Only one annotator in eval_labels_multi.csv.\n\n"
            "Inter-annotator agreement needs at least two people labelling the same\n"
            "traces independently. That file has not been filled in yet — see\n"
            "data/README.md.\n\n"
            "The disagreement is deliberately not simulated: invented disagreement\n"
            "would produce a number that teaches nothing."
        )
    else:
        _names = list(labels)[:2]
        _shared = sorted(set(labels[_names[0]]) & set(labels[_names[1]]))
        _a = [labels[_names[0]][r] for r in _shared]
        _b = [labels[_names[1]][r] for r in _shared]
        _raw = sum(1 for x, y in zip(_a, _b, strict=True) if x == y) / len(_shared)
        print(f"{_names[0]} vs {_names[1]} over {len(_shared)} traces")
        print(f"  raw agreement: {_raw:.2f}")
        print(f"  Cohen's kappa: {cohens_kappa(_a, _b):.2f}")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Raw agreement flatters everyone. If nine traces in ten are fine, two people who
    both say "fine" every time agree ninety per cent of the time having done no
    work at all. Kappa subtracts that.

    When humans disagree on what "grounded" means, a judge that scores 0.7 against
    one of them is not obviously worse than one scoring 0.9 — you have simply
    measured which human it imitates.

    **Fix the rubric before you fix the judge.** Almost always, disagreement
    between annotators is a disagreement about the definition, not about the trace.

    ## Step 6 · Move one number

    You have measurements. Now change exactly one thing.

    The obvious candidate: the instructions. Last week's agent was never told to
    cite anything, never told to distinguish a claim from a fact, never told to
    admit ignorance.
    """)
    return


@app.cell
def _():
    from stargate.agents import INSTRUCTIONS, INSTRUCTIONS_GROUNDED

    print("Session 1:")
    for _i in INSTRUCTIONS:
        print("  -", _i)
    print("\nWhat the measurements argue for:")
    for _i in INSTRUCTIONS_GROUNDED:
        print("  -", _i)
    return (INSTRUCTIONS_GROUNDED,)


@app.cell
def _(INSTRUCTIONS_GROUNDED):
    from stargate.agents import archivist
    from stargate.knowledge import knowledge_from_existing
    from stargate.observability import enable_tracing

    enable_tracing()
    improved = archivist(knowledge_from_existing(), instructions=INSTRUCTIONS_GROUNDED)
    improved.print_response("Did remote viewing actually work?")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Compare that against the same question in notebook 05.

    Then re-run the cheap checks over the new answers. If `check_citation` does not
    move, the instruction did not work — and you would never have known without
    the evaluator.

    Other single changes worth trying, one at a time:

    - `chunk_text(..., overlap=100)` and rebuild the index — does retrieval improve?
    - Route counting questions to the team from notebook 06 — does `check_routing`
      go to zero?
    - Raise `max_results` on the knowledge base — better recall, or just more noise?

    **One change, re-measure, keep or discard.** That loop is the entire job.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 7 · Get it out of the notebook

    Everything so far printed to a cell. That was right for building and is wrong
    for keeping: a number in a notebook is one nobody else sees, nobody compares
    against last week, and nobody notices regressing.

    Three things move to Langfuse, and no more.

    **The testset becomes a dataset.** Twenty questions with their ground truth,
    in one place the whole room can open, version and add to.

    **The checks become scores on a run.** Same functions, same verdicts, now
    attached to a dataset run instead of a `Counter`.

    **The run becomes comparable.** Which is the only reason to do any of this:
    two runs side by side is what turns *"I changed the instructions"* into
    *"I changed the instructions and citation went from 0.15 to 0.80"*.

    The plumbing is one small module. Read it — it decides nothing, it only
    changes where the results end up.
    """)
    return


@app.cell
def _():
    import inspect as _inspect

    from stargate.evaluators import langfuse_sync

    print(_inspect.getsource(langfuse_sync.deterministic_evaluator))
    return (langfuse_sync,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Note the last line: a check that does not apply is **dropped**, never scored
    zero. Langfuse averages what you hand it, so scoring an inapplicable check
    zero would quietly turn the `of` column from earlier into a lie that now has
    a dashboard behind it.

    ### Push the testset
    """)
    return


@app.cell
def _(langfuse_sync, traces):
    from stargate.observability import enable_tracing as _enable_tracing

    _client = _enable_tracing()
    if _client is None:
        print("No Langfuse keys in .env — the rest of this step needs them.")
    else:
        _n = langfuse_sync.push_dataset(traces)
        print(f"{_n} items in dataset '{langfuse_sync.DATASET_NAME}'")
        print("Langfuse sidebar → Datasets. It is there now.")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Open it. Every item carries the question as input, the ground truth as
    expected output, and what the agent did last week in metadata.

    Run that cell twice and the dataset stays at twenty items: `push_dataset`
    gives each item an id derived from its trace, and Langfuse upserts on it.
    The alternative, which everyone writes first, is a testset that doubles
    every time somebody re-runs a cell.

    ### Run one: last week, scored

    The first run replays the answers the session-1 agent actually gave. **No
    model is called** — the answers already exist, and this is what puts last
    week's failures on the board as a baseline.
    """)
    return


@app.cell
def _(langfuse_sync):
    from langfuse import get_client

    dataset = get_client().get_dataset(langfuse_sync.DATASET_NAME)

    def replay(*, item, **_):
        """Hand back what the agent said at the time. Costs nothing."""
        return {
            "answer": item.metadata["recorded_answer"],
            "tool_calls": item.metadata["recorded_tool_calls"],
            "retrieved_ids": item.metadata["recorded_retrieved_ids"],
        }

    baseline = dataset.run_experiment(
        name="session-1 instructions",
        # Without run_name Langfuse builds one from the experiment name, an ISO
        # timestamp and the description, which is unreadable in the Runs list.
        # A fixed name also means re-running this cell updates the same run
        # instead of leaving a trail of near-identical ones.
        run_name="session-1",
        task=replay,
        evaluators=[langfuse_sync.deterministic_evaluator],
        run_evaluators=[langfuse_sync.pass_rate],
    )
    print(baseline.format())
    return (dataset,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    That prints the run, and the numbers are the whole error analysis in five
    lines:

    ```
    check_routing:    0.000      check_language:  0.950
    check_citation:   0.050      check_retrieval: 0.889
    check_refusal:    0.000      pass_rate:       0.519
    ```

    Every counting question was answered without touching SQL. One answer in
    twenty cited anything. The agent never once said it did not know. None of
    that is a surprise by now, and that is the point: you found it by reading
    traces in step 1, and the dashboard is only agreeing with you.

    Now the screen that matters: **Datasets → `stargate-eval` → Runs**. One row,
    with `pass_rate` and one column per check. Click into it and every item shows
    its own scores with the `detail` string as the comment, which is the same
    text the notebook printed earlier.

    ### Run two: change one thing

    Same dataset, same evaluators, one difference — the agent answers now, with
    the instructions the measurements argued for.

    **This one costs model calls**, one agent run per item, so budget a few
    minutes. `max_concurrency=2` keeps it under the free tier's fifteen requests
    a minute.
    """)
    return


@app.cell
def _(INSTRUCTIONS_GROUNDED, dataset, langfuse_sync):
    from stargate.agents import archivist as _archivist
    from stargate.knowledge import knowledge_from_existing as _knowledge

    _agent = _archivist(_knowledge(), instructions=INSTRUCTIONS_GROUNDED, with_memory=False)

    def answer_now(*, item, **_):
        _out = _agent.run(item.input["question"])
        return {
            "answer": _out.content or "",
            "tool_calls": [_t.tool_name for _t in (_out.tools or [])],
            # Deliberately empty. The ids in the answer are the ones it *cited*,
            # and scoring those as "retrieved" would let a confident citation
            # pass a retrieval check. An inapplicable check is the honest result.
            "retrieved_ids": [],
        }

    grounded = dataset.run_experiment(
        name="grounded instructions",
        run_name="grounded",
        task=answer_now,
        evaluators=[langfuse_sync.deterministic_evaluator],
        run_evaluators=[langfuse_sync.pass_rate],
        max_concurrency=2,
    )
    print(grounded.format())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Back to **Datasets → `stargate-eval` → Runs**, where there are now two rows.
    Tick both and Langfuse puts them side by side, per check and per item.

    Read `check_citation` first. Session 1 was never told to cite anything, so
    the baseline is close to zero and the new run should not be. If it did not
    move, the instruction did not work, and you would never have known.

    Then read `check_retrieval` and notice it is empty for the live run. That is
    the comment in the task cell doing its job: the run had nothing to look at,
    and it says so rather than inventing a pass.

    ## Postscript: the button

    Langfuse will run a judge for you on every trace, forever, configured through
    a form. You have earned the right to read that form properly, so go and fill
    it in: **Evaluators → + New evaluator** in the sidebar.

    | The form asks for | You built it in |
    |---|---|
    | a prompt with `{{input}}` / `{{output}}` variables | `build_judge_prompt` |
    | the scoring scale and what each value means | `RUBRIC` |
    | a model and its temperature | the `genai` call in step 4 |
    | how to parse the reply into a score | `parse_verdict` |
    | which traces to run on, and on what share of them | the loop in step 4 |

    Configure it against the **source/claim conflation** category, because that
    is the one your error analysis said code cannot catch. Point it at this
    project's traces, set the sampling low to start with, and give the score the
    same name your local judge uses so the two are comparable.

    Then do the thing almost nobody does: **run it on the twenty traces you
    labelled by hand**, and put its numbers through step 5. You already have the
    labels and you already have `confusion_matrix`. A configured judge is exactly
    as trustworthy as a written one, which is to say: as trustworthy as its
    agreement with you, and not one point more.

    That is the whole reason we did it the long way round. A judge you configured
    is a box you trust. A judge you wrote, aligned against human labels, and found
    to be mediocre is a *measurement* — and you know exactly how much to trust it,
    which is the only number that was ever worth having.

    ---

    ### Checkpoint

    Reference state: **`step-08`**

    ```
    git diff origin/step-08 -- stargate/
    ```

    Next: `notebooks/09_telegram.py` — putting the whole thing in front of
    real users.

    To get there: go back to marimo's home page in your browser, shut
    **this** notebook down (**Running notebooks** → the round Shutdown
    button on its row), then click the next one in the list.

    Launched marimo on this single file instead? `Ctrl+C` in its terminal,
    then `uv run marimo edit --no-token notebooks/09_telegram.py`.

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
