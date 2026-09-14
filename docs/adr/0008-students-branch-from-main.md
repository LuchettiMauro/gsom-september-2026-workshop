# Students branch from `main`; the step branches are checkpoints

Every notebook used to open with a **Start here** block: commit your work,
fetch, and `git switch -c mywork-NN origin/step-NN`, because that notebook's
modules only existed from that branch onwards. Skipping it produced
`cannot import name 'tools' from 'stargate'` in the middle of a lesson — and
recovering needed a second step nobody guesses, shutting the marimo kernel down
so it would look at the filesystem again.

The reveal was protecting nothing. The notebooks *import* finished modules;
they never ask a student to write one. So a student who could see
`stargate/knowledge.py` on day one was not being handed an answer, because
there was no question. What the switching did buy was a per-notebook failure
mode at the worst possible moment, and a student's own notes and edits
scattered across five branches called `mywork-02` through `mywork-07`.

Phase 0 now says `git switch -c mywork origin/main`, once, and nothing asks
for a branch again.

## Consequences

The `step-*` branches keep both jobs they already had: the escape hatch of
ADR 0004, for a student who breaks something beyond repair, and the reference
each notebook's Checkpoint block diffs against. What they stop being is the
path through the course.

`scripts/make_branches.py` still validates that a notebook can run on the
branch it names — the meaning shifted from "the branch this notebook sends you
to" to "the checkpoint someone lands on after breaking something", and a
checkpoint that cannot run its own notebook is a trap either way.

`ls stargate` no longer tells a student where they are in the story, and
someone browsing ahead sees the ending. Both were true of `main` already, which
is public and carries every solution.
