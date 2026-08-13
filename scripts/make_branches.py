"""Instructor script: regenerate the step-* branches from `main`.

    uv run python scripts/make_branches.py            # rebuild locally
    uv run python scripts/make_branches.py --push     # and force-push

`main` is the only source of truth. Every `step-NN` branch is a snapshot of it
holding the package modules that exist by the end of that notebook — so a
student who falls behind switches to one and is unblocked immediately.

The alternative, a chain of ten dependent branches, means rebasing all ten
every time a typo is fixed on notebook 01. This regenerates all of them in
about a second instead.

Nothing here touches your working tree: the branches are built with git
plumbing against a temporary index, so it is safe to run with uncommitted work
in progress.

WARNING: this force-updates the step branches. Students must always work on
their own branch (`git switch -c mywork-05 origin/step-05`), never directly on
a step branch.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_BRANCH = "main"

# Files present on every step branch: the guide, the data, and the plumbing.
# The notebooks are all here from the start — they are what students read.
# What differs between steps is which package modules exist.
COMMON = [
    ".gitignore",
    ".python-version",
    ".env.example",
    "pyproject.toml",
    "uv.lock",
    "README.md",
    "PHASE0.md",
    "TROUBLESHOOTING.md",
    "LICENSE",
    "NOTICE",
    "data/",
    "notebooks/",
    "scripts/fetch_data.py",
    "scripts/check.py",
    "stargate/__init__.py",
    "stargate/config.py",
]

# step -> the modules (and their tests) that exist by the end of that notebook.
STEPS: list[tuple[str, str, list[str]]] = [
    ("step-00", "Starting point: setup complete, nothing built yet", []),
    (
        "step-01",
        "After notebook 01 — talking to a model directly",
        ["stargate/providers.py"],
    ),
    (
        "step-02",
        "After notebook 02 — tools, described to the model",
        [
            "stargate/providers.py",
            "stargate/tools.py",
            "stargate/sightings.py",
            "tests/test_tools.py",
            "tests/test_sightings.py",
        ],
    ),
    (
        "step-03",
        "After notebook 03 — the agent loop, by hand",
        [
            "stargate/providers.py",
            "stargate/tools.py",
            "stargate/sightings.py",
            "stargate/loop.py",
            "tests/test_tools.py",
            "tests/test_sightings.py",
            "tests/test_loop.py",
        ],
    ),
    (
        "step-04",
        "After notebook 04 — the same thing in Agno, traced",
        [
            "stargate/providers.py",
            "stargate/tools.py",
            "stargate/sightings.py",
            "stargate/loop.py",
            "stargate/observability.py",
            "stargate/agents.py",
            "tests/test_tools.py",
            "tests/test_sightings.py",
            "tests/test_loop.py",
        ],
    ),
    (
        "step-05",
        "After notebook 05 — knowledge. End of session 1.",
        [
            "stargate/providers.py",
            "stargate/tools.py",
            "stargate/sightings.py",
            "stargate/loop.py",
            "stargate/observability.py",
            "stargate/agents.py",
            "stargate/chunking.py",
            "stargate/knowledge.py",
            "tests/test_tools.py",
            "tests/test_sightings.py",
            "tests/test_loop.py",
            "tests/test_chunking.py",
        ],
    ),
    (
        "step-06",
        "After notebook 06 — a SQL agent and a team",
        [
            "stargate/providers.py",
            "stargate/tools.py",
            "stargate/sightings.py",
            "stargate/loop.py",
            "stargate/observability.py",
            "stargate/agents.py",
            "stargate/chunking.py",
            "stargate/knowledge.py",
            "stargate/teams.py",
            "tests/test_tools.py",
            "tests/test_sightings.py",
            "tests/test_loop.py",
            "tests/test_chunking.py",
        ],
    ),
    (
        "step-07",
        "After notebook 07 — the agent, on Telegram",
        [
            "stargate/providers.py",
            "stargate/tools.py",
            "stargate/sightings.py",
            "stargate/loop.py",
            "stargate/observability.py",
            "stargate/agents.py",
            "stargate/chunking.py",
            "stargate/knowledge.py",
            "stargate/teams.py",
            "telegram_bot.py",
            "tests/test_tools.py",
            "tests/test_sightings.py",
            "tests/test_loop.py",
            "tests/test_chunking.py",
        ],
    ),
    (
        "step-08",
        "After notebook 08 — evaluation. The complete repository.",
        [
            "stargate/providers.py",
            "stargate/tools.py",
            "stargate/sightings.py",
            "stargate/loop.py",
            "stargate/observability.py",
            "stargate/agents.py",
            "stargate/chunking.py",
            "stargate/knowledge.py",
            "stargate/teams.py",
            "stargate/evaluators/",
            "telegram_bot.py",
            "scripts/seed_traces.py",
            "tests/",
        ],
    ),
]


def git(*args: str, index: str | None = None, check: bool = True) -> str:
    env = dict(os.environ)
    if index:
        env["GIT_INDEX_FILE"] = index
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
    return result.stdout.strip()


def paths_in_source() -> list[str]:
    return git("ls-tree", "-r", "--name-only", SOURCE_BRANCH).splitlines()


def selected(patterns: list[str], every_path: list[str]) -> set[str]:
    """Expand the manifest into concrete paths. A trailing '/' means a directory."""
    keep: set[str] = set()
    for pattern in patterns:
        if pattern.endswith("/"):
            keep.update(p for p in every_path if p.startswith(pattern))
        elif pattern in every_path:
            keep.add(pattern)
    return keep


def build_branch(name: str, message: str, keep: set[str], every_path: list[str]) -> str:
    """Create a commit holding only `keep`, and point `name` at it."""
    with tempfile.TemporaryDirectory() as workdir:
        index = str(Path(workdir) / "index")
        git("read-tree", SOURCE_BRANCH, index=index)
        drop = [p for p in every_path if p not in keep]
        # Batched: a repo with hundreds of files would otherwise blow the
        # command-line length limit on Windows.
        for start in range(0, len(drop), 200):
            git("rm", "--cached", "--quiet", "--", *drop[start : start + 200], index=index)
        tree = git("write-tree", index=index)
        commit = git("commit-tree", tree, "-p", git("rev-parse", SOURCE_BRANCH), "-m", message)
    git("branch", "--force", name, commit)
    return commit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--push", action="store_true", help="force-push the branches")
    parser.add_argument("--remote", default="origin")
    args = parser.parse_args()

    if git("rev-parse", "--verify", "--quiet", SOURCE_BRANCH, check=False) == "":
        print(f"No `{SOURCE_BRANCH}` branch in this repository.")
        return 1

    every_path = paths_in_source()
    print(f"{SOURCE_BRANCH} holds {len(every_path)} files\n")

    missing: list[str] = []
    for name, description, modules in STEPS:
        patterns = COMMON + modules
        for pattern in patterns:
            if not pattern.endswith("/") and pattern not in every_path:
                missing.append(f"{name}: {pattern}")
        keep = selected(patterns, every_path)
        build_branch(name, f"{name}: {description}", keep, every_path)
        print(f"  {name:<9} {len(keep):>3} files   {description}")

    if missing:
        print("\nListed in the manifest but not on main:")
        for item in sorted(set(missing)):
            print(f"  {item}")

    if args.push:
        print()
        refs = [f"+{name}:refs/heads/{name}" for name, _, _ in STEPS]
        git("push", "--force", args.remote, *refs)
        print(f"Force-pushed {len(refs)} branches to {args.remote}.")
    else:
        print("\nBuilt locally. Re-run with --push to publish.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
