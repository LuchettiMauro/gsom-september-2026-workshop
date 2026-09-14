# The deploy path exists twice, on purpose

Notebook 07 walks through three terminals by hand — bot, tunnel, webhook
registration — and `scripts/serve_bot.py` does all three in one command. The
duplication is deliberate and should not be collapsed.

The manual route is the lesson: `telegram_bot.py`'s docstring makes the point
that you explore in a notebook and deploy a process, and that is only visible
when the pieces are separate. The script is the tool for the days afterwards.

## Why the script had to exist

Between the two sessions students are asked for 25 conversations, spread over
whenever a good question occurs to them. On a Codespace that stops after 30
minutes idle, each of those costs four manual steps, and the failure mode is
not inconvenience — it is 25 conversations becoming zero, and session 2 opening
on an empty dataset.

## Consequences

`serve_bot.py` is also where two other decisions physically live: it generates
the webhook secret from ADR 0003 on first run and writes it into `.env`, and
its `finally` block calls `deleteWebhook`, so cleaning up is the default
behaviour rather than a paragraph someone forgets to read. A registered webhook
outlives the tunnel it points at, and a stale one makes the next session start
with a bot that appears broken.
