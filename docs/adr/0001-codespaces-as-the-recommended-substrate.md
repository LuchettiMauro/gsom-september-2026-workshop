# GitHub Codespaces is the recommended way to follow the workshop

Phase 0 was 11 steps and 25 minutes, and most of that was installing a
toolchain — the part most likely to defeat someone on a locked-down laptop
before the course has even started. A Codespace is now the recommended route
and running locally is the documented alternative, so the friction lands on
the four API keys, which are the only part nobody can automate away.

## Considered options

**Google Colab** was rejected, and the reasons are specific rather than
aesthetic. The teaching mechanism of this repository is `git switch -c mywork
origin/step-NN`, which needs a durable working tree; Colab's VM is ephemeral.
The notebooks are marimo `.py` files served over HTTP, not `.ipynb` documents
Colab can render. Session 2 needs two terminals running side by side. And
`fastembed` downloads 80 MB and `lancedb` writes to local disk, both of which
Colab discards on every runtime reset.

**Local only** keeps the friction that motivated the change.

**Codespaces as the only route** would force a GitHub account and a quota on
everyone with a working machine.

## Consequences

`PHASE0.md` is a single file with a forked head and a common tail: the two
routes differ only in how the toolchain arrives, and are word-for-word
identical from *Get a Google AI Studio key* onwards. Two files were rejected
because the shared tail is five steps long and would drift — it already had,
between `PHASE0.md` and `README.md`, on the one line they duplicated.

A Codespace stops after 30 minutes idle, which breaks the between-sessions
homework: the bot dies and its webhook goes stale. See ADR 0007.
