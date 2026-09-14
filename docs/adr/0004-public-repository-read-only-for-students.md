# The repository is public, and students get read access only

Students need to create a Codespace and open an issue from a link, and on a
private repository both require being invited one by one — using GitHub handles
that the Phase 0 issue is supposed to collect in the first place. The
repository is public, on a personal account, under MIT and CC-BY with a
public-domain corpus.

## Why not private with collaborators

Because read-only is the correct permission level here, not merely the
convenient one. A collaborator on a private repository has *write* access, and
`scripts/make_branches.py` force-pushes the nine `step-*` branches: with thirty
writers, the only thing protecting the course material is a warning in a
docstring. On a public repository a student's `git push` of their `mywork`
branch cannot damage anything — GitHub creates a fork on their account and
pushes there.

Branch protection rules and GitHub Actions minutes are also free on public
repositories, which is what makes the devcontainer prebuild in ADR 0005
affordable.

## Consequences

`main` carries every solution and is readable by anyone, students included.
That was already true by design — the `step-*` branches exist as escape
hatches — so nothing was given up.
