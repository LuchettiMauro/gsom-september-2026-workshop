import marimo

__generated_with = "0.23.16"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 08 · How bad is it?

    **Behind? Start here.**

    ```
    git add -A && git commit -m "my work so far"
    git fetch origin
    git switch -c mywork-07 origin/step-07
    ```

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
    ## Postscript: the button

    Langfuse will run an LLM judge for you on every trace, forever, configured
    through a form: pick a model, paste a prompt, choose a score name.

    Go and look at it now — **Evaluators** in the sidebar. You will recognise every
    field, because you just built each one by hand.

    That is the whole reason we did it the long way round. A judge you configured
    is a box you trust. A judge you wrote, aligned against human labels, and found
    to be mediocre is a *measurement* — and you know exactly how much to trust it,
    which is the only number that was ever worth having.

    ---

    ### Checkpoint

    Reference state: **`step-08`** — the complete repository.

    ```
    git diff origin/step-08
    ```

    Optional, at home: `notebooks/09_workflows.py`
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
