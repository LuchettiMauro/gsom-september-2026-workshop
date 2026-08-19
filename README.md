# Building and Measuring an Agent

Lab material for the Politecnico di Milano master's course on agents and AI.

Two hands-on sessions. In the first you write an agent loop by hand, then rebuild
it with a framework and give it a knowledge base. In the second you put it on
Telegram, and then find out how good it actually is.

The agent answers questions about declassified US government files: the CIA's
remote-viewing programme (STARGATE) and UFO sighting reports.

---

## Before session 1

**Do this at home, not in the room.** Follow **[PHASE0.md](PHASE0.md)** — it takes
about 25 minutes and covers installing the toolchain and getting the (free) API
keys you need. Nothing in session 1 works without it.

The last step prints a line like this:

```
READY  uv=0.9.2  python=3.12.8  gemini=ok  langfuse=ok  telegram=ok
       fastembed=ok  cloudflared=ok  marimo=ok
```

Paste that line into the readiness form linked in PHASE0.md at least three days
before the session, so anything broken can be fixed by email rather than in class.

---

## Quick start

All of these go into a **terminal** — your OS terminal, or the one built into
your editor; [PHASE0 step 0](PHASE0.md) covers which one and how to open it. Run
them from the repository root, the folder containing `pyproject.toml`.

```bash
git clone https://github.com/<org>/polimi-workshop.git
cd polimi-workshop
git switch -c mywork origin/step-00

uv sync
cp .env.example .env        # then fill in your keys
uv run python scripts/fetch_data.py
uv run python scripts/check.py
```

> **Always work on your own branch.** The `step-*` branches are regenerated and
> force-pushed between sessions. If you commit directly onto one, your work will
> be overwritten without warning.

---

## Running the notebooks

The notebooks are [marimo](https://marimo.io) notebooks. They are ordinary
Python files, and marimo serves them to your browser.

**Start the notebook server once, and leave it running for the whole session:**

```bash
uv run marimo edit
```

It prints a URL and opens your browser at marimo's home page, which lists every
notebook in the repository. Click `notebooks/01_chat_completions.py` to open it.

That terminal is now **busy** — it belongs to marimo until you stop it. Do not
type further commands into it. Open a second terminal window or tab for
anything else (`git`, `uv run pytest`, and in session 2 the tunnel).

### Moving from one notebook to the next

Each notebook ends with a **Checkpoint** naming the next one. To get there:

1. Go back to the marimo **home page** tab in your browser (the one at the
   server URL, listing the notebooks). If you closed it, open the URL the
   terminal printed.
2. Find the notebook you just finished under **Running notebooks** at the top,
   and click the small round **Shutdown** button on its row (hover to see the
   tooltip). Confirm. This kills that one notebook's Python kernel and frees the
   memory, the model client and the database handles it was holding.
   Do not confuse it with the **Shutdown** button in the page header — that one
   stops the *server* and every notebook with it.
3. Click the next notebook in the list to open it.

**Shut the previous one down before opening the next.** Every open notebook
keeps a live kernel; leaving five of them running is how you end up with five
copies of the embedding model in RAM, and, worse, with a stale cell somewhere
quietly re-running API calls against your rate limit.

You can also skip the home page and open one notebook directly:

```bash
uv run marimo edit notebooks/02_tool_calling.py
```

Then the way to close it is `Ctrl+C` in that terminal, which stops the server
entirely — and you start the next one with another `uv run marimo edit`. Both
workflows are fine; the home page is less typing.

### Two things about marimo that surprise people

- **It is reactive.** Editing a cell marks everything downstream stale. The repo
  ships in *lazy* mode, so stale cells wait for you to click them rather than
  re-running by themselves — which matters here, because re-running costs API
  calls.
- **Each variable is defined in exactly one cell.** Prefix a name with `_` to
  keep it local to its cell. See [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## The notebooks

| | Notebook | What you build |
|---|---|---|
| **Session 1** | `01_chat_completions` | One chat completion, three providers, three wire formats |
| | `02_tool_calling` | A tool call by hand — the model never calls anything, it asks you to |
| | `03_the_loop` | A `for` loop around the above. This is an agent. |
| | `04_agno_agent` | The same thing in six lines, with tracing |
| | `05_knowledge` | Vector search over the declassified corpus |
| **Session 2** | `06_teams` | A SQL agent over the sightings table, and a team that routes |
| | `07_telegram` | The agent, on your phone |
| | `08_evals` | What's actually wrong with it, and how you'd measure that |
| **Take-home** | `09_workflows` | Deterministic orchestration, when you don't want an agent deciding |

Each notebook opens with a **Start here** block: one `git switch` onto the
`step-NN` branch that carries the modules that notebook reads. That switch is
how the code reaches your machine, so run it even when you are not behind — a
notebook opened on the previous step will fail on its first import.

If you fall behind or break something, the same command is the escape hatch:
commit what you have, switch, and you are back in sync in ten seconds.

---

## Between the two sessions

**Use the agent. Don't fix it.**

Ask it 25 questions you actually find interesting — easy ones, nasty ones, a few in
Italian. Do not improve the prompt, do not adjust the chunking, do not correct
anything you see going wrong. Every conversation is traced automatically.

Session 2 opens with those traces. The homework is not busywork: it is the dataset
you'll spend the second half of the course analysing, and it works far better when
the failures are yours rather than someone else's.

Ask it about UFOs, not about yourself — you'll be sharing findings with the room.

---

## When something breaks

See **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**. It covers the failures that
actually happen, in the order they actually happen.

---

## Licence

Code is MIT. Prose and notebooks are CC-BY-4.0. The document corpus is US
Government work in the public domain — see [NOTICE](NOTICE) for provenance.
