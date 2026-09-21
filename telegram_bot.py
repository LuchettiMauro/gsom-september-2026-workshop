"""The agent, on Telegram. Notebook 09 drives this.

Run it with three terminals open:

    1.  uv run python telegram_bot.py
    2.  cloudflared tunnel --url http://localhost:7777
    3.  the setWebhook cell in notebooks/09_telegram.py

Once you have seen the three pieces separately, one command does all of them,
and cleans up after itself when you stop it:

    uv run python scripts/serve_bot.py

This is a script rather than a notebook cell on purpose. It is a long-running
HTTP server, and a notebook cell that blocks forever is a notebook you have
lost. The transition is the lesson: you explore in a notebook, you deploy a
process.

What answers is either the archivist from notebook 04 or the team from
notebook 06, chosen with STARGATE_BRAIN (`archivist`, the default, or `team`).
The archivist is the default because it costs two or three model calls per
message where the team costs eight or nine, and a free Gemini key allows
fifteen a minute.

Two things guard the door, because a tunnel puts this on the public internet:

    TELEGRAM_WEBHOOK_SECRET_TOKEN   proves a request really came from Telegram
    TELEGRAM_ALLOWED_CHAT_IDS       decides which chats the agent will answer

The first is checked by Agno itself and is *not* optional: without it every
update is rejected with 403. The second is ours, and it is what stops a
stranger who finds your bot from spending your Gemini quota and filling your
Langfuse project with conversations you did not have.
"""

from __future__ import annotations

import os
import sys
from typing import Any

from stargate.agents import archivist
from stargate.config import settings
from stargate.knowledge import knowledge_from_existing
from stargate.observability import enable_tracing
from stargate.teams import research_team

PORT = 7777
WEBHOOK_PATH = "/telegram/webhook"
BRAIN_ENV = "STARGATE_BRAIN"
BRAINS = ("archivist", "team")


def _chat_id_of(update: dict[str, Any]) -> int | None:
    """The chat a Telegram update came from, or None if it carries no message."""
    message = update.get("message") or update.get("edited_message") or {}
    chat_id = message.get("chat", {}).get("id")
    return int(chat_id) if isinstance(chat_id, int) else None


def add_chat_allowlist(app: Any) -> None:
    """Drop updates from chats that are not yours, before the agent sees them.

    Answering costs a model call, so the filter has to sit in front of the
    agent rather than inside it. Unknown chats are logged with their id — which
    is also how you find your own: message the bot once, read the id off this
    console, put it in TELEGRAM_ALLOWED_CHAT_IDS.
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def only_allowed_chats(request: Request, call_next: Any) -> Any:
        if request.url.path != WEBHOOK_PATH:
            return await call_next(request)

        cfg = settings()
        try:
            update = await request.json()
        except Exception:
            return await call_next(request)

        chat_id = _chat_id_of(update)
        if chat_id is not None and not cfg.telegram_chat_allowed(chat_id):
            print(
                f"ignored a message from chat {chat_id} — "
                "add it to TELEGRAM_ALLOWED_CHAT_IDS in .env if it is yours"
            )
            # 200, not 403: Telegram retries anything else, and there is
            # nothing here worth telling the sender about.
            return JSONResponse({"status": "ignored"})

        return await call_next(request)


def build_brain(name: str | None = None, knowledge: Any = None) -> Any:
    """The agent or team that will answer, by name.

    An environment variable rather than an argument, because nothing calls this
    directly: the notebook runs `python telegram_bot.py`, and `serve_bot.py`
    starts `uvicorn telegram_bot:app` in a subprocess. Both reach the same
    switch through the environment.
    """
    name = (name or os.environ.get(BRAIN_ENV) or "archivist").strip().lower()
    if name not in BRAINS:
        raise SystemExit(f"{BRAIN_ENV}={name!r} is not one of {BRAINS}.")
    return research_team(knowledge) if name == "team" else archivist(knowledge)


def build_app() -> object:
    """An AgentOS app exposing the archivist, or the team, over Telegram."""
    from agno.os import AgentOS
    from agno.os.interfaces.telegram import Telegram
    from agno.team import Team

    cfg = settings()
    if not cfg.telegram_token:
        raise SystemExit(
            "TELEGRAM_TOKEN is not set. Get one from @BotFather — "
            "see PHASE0.md, *Get a Telegram bot token*."
        )
    if not cfg.telegram_webhook_secret:
        # Agno rejects every unsigned update with 403, so without this the bot
        # starts, looks healthy, and silently answers nobody. Fail loudly here
        # instead.
        raise SystemExit(
            "TELEGRAM_WEBHOOK_SECRET_TOKEN is not set, and Agno rejects every update "
            "without it.\nPut any hard-to-guess string in .env — or let "
            "`uv run python scripts/serve_bot.py` generate one for you."
        )
    if not cfg.telegram_restricted:
        print(
            "WARNING: TELEGRAM_ALLOWED_CHAT_IDS is empty, so anyone who finds this bot "
            "can talk to it.\n         Message the bot once and this console will print "
            "your chat id.\n"
        )

    enable_tracing()

    try:
        knowledge = knowledge_from_existing()
    except FileNotFoundError:
        print("No vector index found; the bot will answer without the documents.")
        print("Run notebook 05, or stargate.knowledge.restore_prebuilt_index().")
        knowledge = None

    brain = build_brain(knowledge=knowledge)
    # A Team and an Agent go into different slots on both AgentOS and the
    # Telegram interface, so the one switch above decides two pairs of
    # arguments.
    if isinstance(brain, Team):
        agent_os = AgentOS(teams=[brain], interfaces=[Telegram(team=brain)])
    else:
        agent_os = AgentOS(agents=[brain], interfaces=[Telegram(agent=brain)])
    print(f"Answering with: {brain.name}")
    app = agent_os.get_app()
    add_chat_allowlist(app)
    return app


app = build_app() if __name__ != "__main__" else None


def main() -> int:
    import uvicorn

    print(f"Starting on http://localhost:{PORT}")
    print("Now, in a second terminal:")
    print(f"    cloudflared tunnel --url http://localhost:{PORT}")
    print("Then run the setWebhook cell in notebook 09 with the URL it prints.\n")
    uvicorn.run(build_app(), host="0.0.0.0", port=PORT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
