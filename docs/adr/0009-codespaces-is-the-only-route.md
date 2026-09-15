# GitHub Codespaces is the only route

Supersedes ADR 0001, which made Codespaces the recommended route and kept
running locally as the documented alternative.

The alternative was where the document's weight sat. Route B of `PHASE0.md`
was installing `uv` and `cloudflared` on three operating systems, a PowerShell
execution policy, PATH that a running terminal does not see, `cp` versus `copy`
versus `Copy-Item`, and File Explorer saving `.env` as `.env.txt`. Every line
of it existed to arrive at the same four API keys as route A.

Two costs, and neither was the page count. A student who has not started yet
was asked to choose between two routes on the evidence of a paragraph, and the
one that is worse for them is the one that sounds more serious. And every
failure in route B is one the instructor debugs by email in the three days
before session 1, on a machine nobody can see, against an OS the repository
was never tested on.

ADR 0001 rejected this option because it "would force a GitHub account and a
quota on everyone with a working machine". The account was already required —
the repository is on GitHub and Phase 0 ends by opening an issue (ADR 0006).
The quota is 60 core-hours a month on a free personal account and this
workshop spends a few of them.

## Consequences

`PHASE0.md` loses its forked head and becomes linear: one way to reach a
terminal, one `.env` that already exists, one way to open marimo in a browser.
The bridging paragraph that promised both routes met again is gone with it.

The two things route B documented and route A did not — why
`git switch -c mywork origin/main`, and the warning not to type shell commands
into a Python cell — move into the Codespace section. Everything else in it
was installation.

A student who cannot use a Codespace is now unsupported by the written
material, not merely off the recommended path. Git history and the `docs`
branch still hold route B, which is enough to hand to one person by email, and
`uv sync --extra serve` plus `scripts/fetch_data.py` is what it amounted to.

`scripts/check.py` and `scripts/serve_bot.py` stop pointing at installation
instructions when something is missing. In a Codespace a missing `uv` or
`cloudflared` means an image that did not finish building, so they point at
rebuilding the container. The Windows and Homebrew paths in
`CLOUDFLARED_FALLBACKS` are gone: the only binary that matters now is the one
`.devcontainer/setup.sh` installs.

The Phase 0 issue template stops asking where the student is running it. There
is one answer, and a dropdown with one option is a question that implies a
choice.
