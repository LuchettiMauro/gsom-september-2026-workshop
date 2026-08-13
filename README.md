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

```bash
git clone https://github.com/<org>/polimi-workshop.git
cd polimi-workshop
git switch -c mywork origin/step-00

uv sync
cp .env.example .env        # then fill in your keys
uv run python scripts/fetch_data.py
uv run python scripts/check.py
```

Open the first notebook:

```bash
uv run marimo edit notebooks/01_chat_completions.py
```

> **Always work on your own branch.** The `step-*` branches are regenerated and
> force-pushed between sessions. If you commit directly onto one, your work will
> be overwritten without warning.

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

Each notebook opens with the git command that takes you to the state it assumes,
and closes with the branch that holds the reference solution. If you get stuck or
fall behind, that's the escape hatch — you're never blocked for more than the ten
seconds it takes to switch branches.

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
