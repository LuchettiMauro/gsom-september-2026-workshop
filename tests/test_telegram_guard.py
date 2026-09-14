"""What stands between a public tunnel and the agent.

Two independent guards, and the bot is only reachable when both let a request
through:

    the webhook secret token   proves Telegram sent it (Agno enforces this)
    the chat allowlist         proves it is your conversation (we enforce this)

The first is not ours, but it is tested here anyway, because it is the one
that fails silently: a bot with no secret configured starts, looks healthy,
and answers nobody with a 403.
"""

from __future__ import annotations

from typing import Any

import pytest

from stargate.config import _chat_ids, settings

fastapi = pytest.importorskip("fastapi", reason="needs the `serve` extra")
pytest.importorskip("telebot", reason="needs the `serve` extra (agno[telegram])")

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

SECRET = "a-hard-to-guess-string"
MINE = 42
STRANGER = 999


def _update(chat_id: int, update_id: int = 1) -> dict[str, Any]:
    return {"update_id": update_id, "message": {"chat": {"id": chat_id}, "text": "hello"}}


@pytest.fixture
def env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_API_KEY", "fake")
    monkeypatch.setenv("TELEGRAM_TOKEN", "123:fake")
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET_TOKEN", SECRET)
    monkeypatch.setenv("TELEGRAM_ALLOWED_CHAT_IDS", str(MINE))
    settings.cache_clear()
    yield
    settings.cache_clear()


# --- parsing ---------------------------------------------------------------


def test_chat_ids_parses_a_messy_list() -> None:
    assert _chat_ids(" 123, 456 ;789 ") == frozenset({123, 456, 789})


def test_a_typo_drops_one_id_rather_than_breaking_the_bot() -> None:
    assert _chat_ids("123, oops, 456") == frozenset({123, 456})


def test_no_allowlist_means_no_restriction() -> None:
    assert _chat_ids(None) == frozenset()
    assert _chat_ids("") == frozenset()


def test_an_empty_allowlist_lets_everyone_through(env: None) -> None:
    """Absent configuration must not silently lock the owner out either."""
    import os

    os.environ.pop("TELEGRAM_ALLOWED_CHAT_IDS")
    settings.cache_clear()
    assert settings().telegram_chat_allowed(STRANGER)


# --- the allowlist middleware ----------------------------------------------


def _guarded_app() -> tuple[FastAPI, list[int]]:
    """A stand-in for the Agno router, so this tests our guard and not theirs."""
    from telegram_bot import WEBHOOK_PATH, add_chat_allowlist

    reached: list[int] = []
    app = FastAPI()

    @app.post(WEBHOOK_PATH)
    async def webhook(request: Request) -> dict[str, str]:
        body = await request.json()
        reached.append(body["message"]["chat"]["id"])
        return {"status": "processing"}

    @app.post("/elsewhere")
    async def elsewhere() -> dict[str, str]:
        return {"status": "fine"}

    add_chat_allowlist(app)
    return app, reached


def test_a_stranger_never_reaches_the_agent(env: None) -> None:
    app, reached = _guarded_app()
    response = TestClient(app).post("/telegram/webhook", json=_update(STRANGER))
    assert response.status_code == 200
    assert response.json() == {"status": "ignored"}
    assert reached == [], "the stranger's message cost a model call"


def test_your_own_chat_goes_through(env: None) -> None:
    app, reached = _guarded_app()
    response = TestClient(app).post("/telegram/webhook", json=_update(MINE))
    assert response.json() == {"status": "processing"}
    assert reached == [MINE]


def test_other_routes_are_untouched(env: None) -> None:
    app, _ = _guarded_app()
    assert TestClient(app).post("/elsewhere").json() == {"status": "fine"}


# --- the secret token, enforced by Agno ------------------------------------


@pytest.fixture
def real_app(env: None) -> Any:
    import telegram_bot

    return telegram_bot.build_app()


@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({}, id="no-header"),
        pytest.param({"X-Telegram-Bot-Api-Secret-Token": "wrong"}, id="wrong-secret"),
    ],
)
def test_an_unsigned_update_is_rejected(real_app: Any, headers: dict[str, str]) -> None:
    """Regression guard: without a secret configured, this 403s every message."""
    response = TestClient(real_app).post("/telegram/webhook", json=_update(MINE), headers=headers)
    assert response.status_code == 403


def test_a_signed_update_from_your_chat_is_accepted(real_app: Any) -> None:
    response = TestClient(real_app).post(
        "/telegram/webhook",
        json=_update(MINE, update_id=2),
        headers={"X-Telegram-Bot-Api-Secret-Token": SECRET},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processing"


def test_the_bot_refuses_to_start_without_a_secret(
    env: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Better a loud SystemExit than a bot that answers nobody."""
    import telegram_bot

    monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET_TOKEN")
    settings.cache_clear()
    with pytest.raises(SystemExit, match="TELEGRAM_WEBHOOK_SECRET_TOKEN"):
        telegram_bot.build_app()
