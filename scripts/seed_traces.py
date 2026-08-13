"""Push example traces into your own Langfuse project.

    uv run python scripts/seed_traces.py

Only needed if you arrive at session 2 without traces of your own — the
evaluation notebook needs something to analyse. Your own traces are better
material, because you remember asking the questions.

Writes ~20 interactions carrying the failures the week-1 agent actually
produces. No model is called; these are replayed, not generated.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from stargate.config import DATA_DIR, settings  # noqa: E402
from stargate.observability import enable_tracing, flush  # noqa: E402

EXAMPLES = DATA_DIR / "example_traces.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=None, help="seed only the first N")
    args = parser.parse_args()

    if not settings().langfuse_configured:
        print("Langfuse keys are not set. See PHASE0.md step 5.")
        return 1

    client = enable_tracing(quiet=True)
    if client is None:
        print("Could not connect to Langfuse.")
        return 1

    payload = json.loads(EXAMPLES.read_text(encoding="utf-8"))
    traces = payload["traces"][: args.limit]

    print(f"Seeding {len(traces)} traces...")
    for n, trace in enumerate(traces, start=1):
        with client.start_as_current_observation(name="archivist") as span:
            span.update(
                input=trace["question"],
                output=trace["answer"],
                metadata={
                    "seeded": True,
                    "tool_calls": trace.get("tool_calls", []),
                    "retrieved_ids": trace.get("retrieved_ids", []),
                    "gold_doc_id": trace.get("gold_doc_id"),
                    "expects_refusal": trace.get("expects_refusal"),
                },
            )
        if n % 5 == 0:
            print(f"  {n}/{len(traces)}")

    flush()
    print(
        "\nDone. They are tagged `seeded: true` in the metadata, so you can tell "
        "them apart from your own."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
