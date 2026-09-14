# Phase 0 readiness is reported as a GitHub issue, not a form

`scripts/check.py` ends by printing a link that opens an issue on this
repository with the `READY` line already filled in. The previous design pointed
at a form "linked in the course announcement", which was external
infrastructure somebody had to create, host and remember to read — and which
consequently never existed.

The gate itself is worth keeping: session 1 is hands-on from the first minute,
and the three-day margin is what lets a broken machine be fixed by email rather
than in the room.

## Consequences

An issue costs no new tooling and no new account, since the recommended route
already requires a GitHub one. It also does something a form could not: the
issues are visible to the other students, so a common failure gets answered
once instead of thirty times.

The `READY` line is only `label=value` pairs — no keys, no trace URLs, no bot
name — which is what makes it safe to post publicly. Keep it that way.
