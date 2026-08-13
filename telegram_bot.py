"""The agent, on Telegram. Notebook 07 drives this.

Run it with three terminals open:

    1.  uv run python telegram_bot.py
    2.  cloudflared tunnel --url http://localhost:7777
    3.  the setWebhook cell in notebooks/07_telegram.py

This is a script rather than a notebook cell on purpose. It is a long-running
HTTP server, and a notebook cell that blocks forever is a notebook you have
lost. The transition is the lesson: you explore in a notebook, you deploy a
process.
"""

from __future__ import annotations

import sys

from stargate.agents import archivist
from stargate.config import settings
from stargate.knowledge import knowledge_from_existing
from stargate.observability import enable_tracing

PORT = 7777


def build_app() -> object:
    """An AgentOS app exposing the archivist over Telegram."""
    from agno.os import AgentOS
    from agno.os.interfaces.telegram import Telegram

    cfg = settings()
    if not cfg.telegram_token:
        raise SystemExit(
            "TELEGRAM_TOKEN is not set. Get one from @BotFather — see PHASE0.md step 6."
        )

    enable_tracing()

    try:
        knowledge = knowledge_from_existing()
    except FileNotFoundError:
        print("No vector index found; the bot will answer without the documents.")
        print("Run notebook 05, or stargate.knowledge.restore_prebuilt_index().")
        knowledge = None

    agent = archivist(knowledge)
    agent_os = AgentOS(agents=[agent], interfaces=[Telegram(agent=agent)])
    return agent_os.get_app()


app = build_app() if __name__ != "__main__" else None


def main() -> int:
    import uvicorn

    print(f"Starting on http://localhost:{PORT}")
    print("Now, in a second terminal:")
    print(f"    cloudflared tunnel --url http://localhost:{PORT}")
    print("Then run the setWebhook cell in notebook 07 with the URL it prints.\n")
    uvicorn.run(build_app(), host="0.0.0.0", port=PORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
